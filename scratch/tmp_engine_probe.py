from pathlib import Path
import shutil
from unittest.mock import patch

from services.chronology_generator.excel_writer import ChronologyExcelWriter
from services.chronology_generator.models import ChronologyEntry, ProjectChronology

src_template = Path("backup_release_cleanup/archive/test_firmware_project/Master/Initial/Ladder_Chronology.xlsx")
out_file = Path("scratch/header_engine_probe.xlsx")
shutil.copy(src_template, out_file)
report_path = Path("scratch/dummy_project/4. Test Report/Master/Initial/Master-Initial-Test-Report-sgn.pdf")

entry = ChronologyEntry(
    source_code_path=Path("dummy"),
    bin_file_path=Path("dummy.bin"),
    sdoc_file_path=None,
    bin_file_name="dummy.bin",
    sdoc_file_name=None,
    version="V1.0",
    plc_model="Master",
    selpro_version="V1",
    bootloader_version="V1",
    crc="1234",
    testing_stage="Initial",
    release_date="01/01/2026",
    reason_for_upgrade="header engine probe",
    test_report_path=report_path,
)

chrono = ProjectChronology(project_root=Path("dummy"))
chrono.add_entry(entry)
writer = ChronologyExcelWriter(template_path=out_file)

with patch("services.chronology_generator.excel_writer.TestReportParser.extract_department_code", return_value="DDHW_PS"), patch.object(ChronologyExcelWriter, "_verify_product_write", lambda *args, **kwargs: None):
    writer.write(chrono, out_file)
