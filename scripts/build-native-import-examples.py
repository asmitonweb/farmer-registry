"""Generate the documented CSV/XLSX contract from the native farmer mapper."""
import openg2p_registry_celery_worker.main  # Initialize the platform extension alias.
from pathlib import Path
from openg2p_registry_farmer_extension.ingestion_pipeline.enricher_services.farmer_file_mapping import (
    COLUMNS, build_csv, build_xlsx,
)

target = Path(__file__).resolve().parents[1] / 'docs/native-file-import'
target.mkdir(exist_ok=True)
(target/'farmer-import-template.csv').write_bytes(build_csv())
(target/'farmer-import-template.xlsx').write_bytes(build_xlsx())
(target/'columns.md').write_text(
    '# Farmer file-import columns\n\n'
    'Dates and identifiers must be text cells. XLSX reads the active worksheet. '
    'Replace synthetic examples with deployment-specific values.\n\n'
    '| Column | Group | Required | Description | Allowed values |\n'
    '| --- | --- | --- | --- | --- |\n' + ''.join(
        f'| {c.name} | {c.group} | {"Yes" if c.required else ""} | {c.description} | {", ".join(c.allowed)} |\n'
        for c in COLUMNS), encoding='utf-8')
print(f'Generated examples and documentation for {len(COLUMNS)} columns')
