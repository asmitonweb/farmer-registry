"""Exercise real native tasks on farmer_native_import_test; never the live DB."""
import asyncio
import csv
import importlib.util
import io
import json
import logging
import os
from pathlib import Path
import time
import uuid

assert os.environ.get('REGISTRY_CELERY_WORKERS_DB_DBNAME') == 'farmer_native_import_test'
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup', ROOT/'scripts/setup-native-file-import.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
setup.initialize()
logging.disable(logging.CRITICAL)
asyncio.run(setup.preflight())
setup.apply_configuration('/tmp/native-import-backup')
setup.apply_configuration('/tmp/native-import-rerun-backup')

from sqlalchemy import text
from openg2p_registry_celery_worker.engine import Engine
from openg2p_registry_core.helpers import get_document_handler
from openg2p_registry_core.models import DocumentBucket
from openg2p_registry_core.services.input_mechanism_data_service import InputMechanismDataService
from openg2p_registry_celery_worker.tasks import import_file_process_worker as unused
import importlib
file_task = importlib.import_module('openg2p_registry_celery_worker.tasks.import_file_process_worker')
transform = importlib.import_module('openg2p_registry_celery_worker.tasks.ingest_data_transformation_worker')
ingest = importlib.import_module('openg2p_registry_celery_worker.tasks.ingest_data_worker')
from openg2p_registry_farmer_extension.ingestion_pipeline.enricher_services.farmer_file_mapping import (
    row_to_submission, example_rows, build_csv, build_xlsx, COLUMNS)

engine = Engine.get_engine()
handler = get_document_handler()
loop = file_task._loop
# Keep all native async services on the same event loop for these direct task calls.
ingest._loop = loop

def scalar(sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def run_file(name, content, expect_failure=False):
    document = str(uuid.uuid4())
    key = handler.upload(io.BytesIO(content), len(content), DocumentBucket.IMPORT_FILES,
                         object_name='native-test/'+document+'/'+name)
    with engine.begin() as conn:
        conn.execute(text('INSERT INTO g2p_registry_documents (document_id,document_store_id,bucket,source_filename,created_by,created_at) VALUES (:id,:key,:bucket,:name,:actor,CURRENT_TIMESTAMP)'),
                     {'id':document,'key':key,'bucket':DocumentBucket.IMPORT_FILES.value,'name':name,'actor':'native-import-test'})
    queue = loop.run_until_complete(InputMechanismDataService().enqueue_import_file(
        document_id=document, data_model_id='FARMER_FILE_IMPORT_MODEL', register_id=setup.REGISTER,
        intake_form_id=setup.FORM, queued_by='native-import-test'))
    before = set()
    with engine.connect() as conn:
        before = set(conn.execute(text("SELECT ingest_id FROM incoming_classified_data WHERE data_model_id='FARMER_FILE_IMPORT_MODEL'")).scalars())
    file_task.import_file_process_worker.run(queue.import_file_id)
    with engine.connect() as conn:
        ids = set(conn.execute(text("SELECT ingest_id FROM incoming_classified_data WHERE data_model_id='FARMER_FILE_IMPORT_MODEL'")).scalars()) - before
    successes, failures = [], []
    for id in ids:
        try:
            transform.ingest_data_transformation_worker.run(id)
            ingest.ingest_data_worker.run(id)
            successes.append(id)
        except Exception as exc:
            failures.append((id, str(exc)))
    print(json.dumps({'file':name,'rows':len(ids),'successful':len(successes),'failures':failures},default=str))
    if not expect_failure:
        assert not failures, failures
    count_before = scalar('SELECT count(*) FROM incoming_raw_data')
    file_task.import_file_process_worker.run(queue.import_file_id)
    assert scalar('SELECT count(*) FROM incoming_raw_data') == count_before, 'Retry created duplicate raw records'
    for id in successes:
        submission = scalar('SELECT intake_form_submission_id FROM incoming_classified_data WHERE ingest_id=:id', id=id)
        assert submission
        assert scalar('SELECT draft_status FROM g2p_intake_form_submissions WHERE submission_id=:id', id=submission) == 'FINAL'
        assert scalar('SELECT approval_status FROM g2p_intake_form_submissions WHERE submission_id=:id', id=submission) == 'PENDING'
    return successes, failures


async def verify_and_approve(ids):
    from openg2p_registry_core.services import G2PIntakeFormDataService
    from openg2p_registry_core.services.g2p_verification_service import G2PRegisterVerificationService
    from openg2p_registry_core.schemas import AddVerificationPayload
    from openg2p_fastapi_common.context import get_async_session_maker
    intake = G2PIntakeFormDataService.get_component()
    for id in ids:
        submission = scalar('SELECT intake_form_submission_id FROM incoming_classified_data WHERE ingest_id=:id', id=id)
        payload = await intake.get_submission_payload(submission)
        assert payload.submission_source == 'PARTNER'  # Native platform behavior, not staff-submit.
        async with get_async_session_maker()() as session:
            sections = await intake._get_form_sections(setup.FORM, session)
            registers = {s.section_register_id for s in sections}
            rows_by_register = {}
            for register in registers:
                model = await intake._resolve_intake_form_class(register, session)
                rows_by_register[register] = await intake._get_intake_rows_list(model, submission, session)
            farmer = rows_by_register[setup.REGISTER][0]
            assert farmer.import_source == 'IMPORT_FILE'
            households = rows_by_register.get('9055ab43-c85d-4833-bd00-ca657bb72644', [])
            if households:
                assert farmer.link_internal_record_id == households[0].internal_record_id
                for section in sections:
                    if section.section_register_id in [setup.REGISTER, '9055ab43-c85d-4833-bd00-ca657bb72644']:
                        continue
                    for row in rows_by_register[section.section_register_id]:
                        expected = households[0].internal_record_id if section.section_mnemonic == 'fr_household_members' else farmer.internal_record_id
                        assert row.link_internal_record_id == expected, section.section_mnemonic
        for number in range(payload.number_of_verifications_required):
            await G2PRegisterVerificationService.get_component().add_verification(AddVerificationPayload(
                submission_id=submission, verified_by=f'native-test-verifier-{number}', is_approved=True,
                verification_observations='Isolated native import acceptance test'))
        await intake.approve_submission(submission, 'native-test-approver')
        await intake.process_submission_register_ingest(submission)
        result = await intake.get_submission_payload(submission)
        assert result.approval_status == 'APPROVED'
        assert result.register_ingest_process_status == 'PROCESSED'
        async with get_async_session_maker()() as session:
            for register, rows in rows_by_register.items():
                _, _, live_model, _, _ = await intake._resolve_submission_models(register, session)
                for row in rows:
                    live = await session.get(live_model, row.internal_record_id)
                    assert live is not None
                    assert live.link_internal_record_id == row.link_internal_record_id
    print('PASS: normal verification/approval, register ingestion, and persisted parent-child links')


if __name__ == '__main__':
    import sys
    if '--batch' in sys.argv:
        import resource
        content = 'first_name,father_first_name\n' + ''.join(f'NativeBatch{i},Parent\n' for i in range(1000))
        started = time.monotonic()
        ok, bad = run_file('batch.csv', content.encode())
        assert len(ok) == 1000 and not bad
        print(json.dumps({'batch_rows':1000,'seconds':round(time.monotonic()-started,2),
                          'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
        raise SystemExit(0)
    all_ids = []
    for name, content in [('minimal.csv', b'first_name,father_first_name\nNativeMinimal,Parent\n'),
                          ('full.csv', build_csv()), ('full.xlsx', build_xlsx())]:
        ok, bad = run_file(name, content)
        all_ids.extend(ok)
    ok, bad = run_file('mixed.csv', b'first_name,father_first_name,gender\nNativeValid,Parent,MALE\nNativeInvalid,Parent,INVALID\n', True)
    assert len(ok) == len(bad) == 1
    loop.run_until_complete(verify_and_approve(all_ids))
    print('PASS: native CSV/XLSX parsing, storage, enqueue, transformation, intake finalization and same-document retry')
