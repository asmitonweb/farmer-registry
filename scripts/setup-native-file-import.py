"""Run inside the farmer celery image with the deployment's worker environment.

Mount this checkout at /work. Default is read-only preflight. --apply BACKUP_DIR
backs up affected metadata and installs only native-import configuration. Never
run db-seed to enable imports on an existing registry.
"""
import argparse
import asyncio
import io
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / 'farmer-extension/src/openg2p_registry_farmer_extension'
REGISTER = 'a1a4d25a-1cd4-4356-abac-985a0b3c6bcd'
FORM = 'a1a4d25a-1cd4-4356-abac-8782382649'
TABLES = ['data_models', 'incoming_model_key_paths', 'incoming_model_semantic_patterns',
          'incoming_templates', 'g2p_registry_documents', 'g2p_registry_import_file_configurations',
          'g2p_input_mechanisms', 'g2p_intake_form_ui_tab_sections']


def initialize():
    import openg2p_registry_celery_worker.main  # noqa: F401
    logging.disable(logging.CRITICAL)


async def preflight():
    from openg2p_registry_celery_worker.config import Settings
    from openg2p_registry_core.helpers import PartnerManagementClient
    from openg2p_registry_core.interfaces import G2PPayloadEnricherFactory
    config = Settings.get_config()
    G2PPayloadEnricherFactory().get_enricher_service('G2PFarmerFileImportEnricherService')
    partner = await PartnerManagementClient.get_component().require_active_partner(config.import_file_sender_id)
    print('PASS: native enricher installed; configured sender resolves to an active partner')
    return partner


def apply_configuration(backup_dir):
    from sqlalchemy import text
    from openg2p_registry_celery_worker.engine import Engine
    from openg2p_registry_core.helpers import get_document_handler
    from openg2p_registry_core.models import DocumentBucket
    engine = Engine.get_engine()
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=False)
    handler = get_document_handler()
    with engine.begin() as conn:
        # Fail before writing anything if the expected farmer form is absent.
        assert conn.execute(text('SELECT 1 FROM g2p_intake_form_definitions WHERE form_id=:id'), {'id': FORM}).scalar(), 'Farmer form is missing'
        snapshot = {table: [dict(row) for row in conn.execute(text('SELECT * FROM '+table)).mappings()] for table in TABLES}
        (backup_dir / 'metadata.json').write_text(json.dumps(snapshot, default=str, indent=2))
        template = (EXT / 'templates/farmer_file_import.json.j2').read_bytes()
        # Content addressing preserves any previous object for rollback and avoids overwrites.
        import hashlib
        object_name = 'farmer-file-import/' + hashlib.sha256(template).hexdigest() + '.j2'
        handler.upload(io.BytesIO(template), len(template), DocumentBucket.TEMPLATES,
                       content_type='application/json', object_name=object_name)
        for rel in ['register-metadata/zz_farmer_bulk_import_household.sql',
                    'registry-inbound-message-rules/zz_farmer_file_import.sql']:
            conn.exec_driver_sql((EXT / 'meta_data' / rel).read_text())
        # Only a freshly inserted catalogue entry is pointed at this immutable template.
        if not any(row['document_id'] == 'farmer-file-import-template' for row in snapshot['g2p_registry_documents']):
            conn.execute(text('UPDATE g2p_registry_documents SET document_store_id=:key WHERE document_id=:id'),
                         {'key': object_name, 'id': 'farmer-file-import-template'})
    print('Native import configured; previous metadata saved in', backup_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', metavar='BACKUP_DIR')
    args = parser.parse_args()
    initialize()
    asyncio.run(preflight())
    if args.apply:
        apply_configuration(args.apply)
