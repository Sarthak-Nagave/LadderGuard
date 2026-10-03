from pathlib import Path
from unittest.mock import patch
from services.chronology_generator.excel_writer import ChronologyExcelWriter
from services.chronology_generator.models import ProjectChronology, ChronologyEntry

root = Path('scratch/dummy_project')
template_path = Path('scratch/header_update_verify.xlsx')
output_path = Path('scratch/header_update_positive.xlsx')
report_path = root / '4. Test Report' / 'Master' / 'Initial' / 'Master-Initial-Test-Report-sgn.pdf'

entry = ChronologyEntry(
    source_code_path=Path('dummy'),
    bin_file_path=Path('dummy.bin'),
    sdoc_file_path=None,
    bin_file_name='dummy.bin',
    sdoc_file_name=None,
    version='V1.0',
    plc_model='Master',
    selpro_version='V1',
    bootloader_version='V1',
    crc='1234',
    testing_stage='Initial',
    release_date='01/01/2026',
    reason_for_upgrade='header test',
    test_report_path=report_path,
)

chrono = ProjectChronology(project_root=Path('dummy'))
chrono.add_entry(entry)
writer = ChronologyExcelWriter(template_path=template_path)

with patch('services.chronology_generator.excel_writer.TestReportParser.extract_department_code', return_value='DDHW_PS'), patch.object(ChronologyExcelWriter, '_verify_product_write', lambda *args, **kwargs: None):
    writer.write(chrono, output_path)
