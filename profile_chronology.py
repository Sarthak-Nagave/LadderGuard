import sys
import time
import logging
from pathlib import Path

# Add ProjectValidator to sys.path
sys.path.append(r'C:\Users\SM 464\Desktop\Operational Package Validator\ProjectValidator')

from services.chronology_generator.excel_writer import ChronologyExcelWriter
from services.chronology_generator.models import ProjectChronology, ChronologyEntry
from core.validation_summary import ValidationSummary

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("profiler")

def profile():
    project_root = Path(r"C:\Users\SM 464\Desktop\Ladder Release Structure")
    template_path = Path(r"C:\Users\SM 464\Desktop\Operational Package Validator\ProjectValidator\scratch\pdf_replace_verify\Ladder_Chronology.xlsx")
    output_path = Path(r"C:\Users\SM 464\Desktop\Ladder Release Structure\7. Chronology\Master\Initial\Ladder_Chronology.xlsx")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not template_path.exists():
        print(f"Template not found at {template_path}")
        return

    # Mock entry
    entry = ChronologyEntry(
        source_code_path=project_root / "1. Ladders/Master/Initial",
        bin_file_path=project_root / "2. Bin File/Master/Initial",
        sdoc_file_path=None,
        bin_file_name="FW.bin",
        sdoc_file_name="FW.sdoc",
        version="1.0.0",
        plc_model="Model A",
        selpro_version="6.1.3.15",
        bootloader_version="1.0",
        crc="AABB",
        testing_stage="Initial",
        release_date="21/08/2026",
        reason_for_upgrade="Initial Release",
        released_by="Dev",
        tested_by="QA",
        ladder_release_to_production="Yes",
        operator_procedure_modification="No",
        automation_setup_modification="No",
        test_report_path=Path(r"C:\Users\SM 464\Desktop\Ladder Release Structure\4. Test Report\Master\Initial\M-Initial-report_of_test-sgn.pdf"),
        prepared_by="Person A",
        checked_by="Person B",
        approved_by="Person C"
    )
    
    chronology = ProjectChronology(project_root)
    chronology.add_entry(entry)

    writer = ChronologyExcelWriter(template_path)
    
    start_time = time.time()
    
    # 1. Template Load
    t0 = time.time()
    workbook = writer._load_workbook()
    t1 = time.time()
    print(f"[CHRONOLOGY-PERF] Template load: {t1 - t0:.3f} sec")
    
    # 2. Data Preparation
    t0 = time.time()
    sheet = workbook.active
    header_row_idx = writer._find_header_row(sheet)
    header_map = writer._build_header_map(sheet, header_row_idx)
    first_data_row = writer._first_data_row(header_row_idx)
    layout_snapshot = writer._capture_print_layout(sheet)
    template_header_height = sheet.row_dimensions[header_row_idx].height
    template_data_height = sheet.row_dimensions[first_data_row].height
    
    entries = chronology.sorted_entries()
    newest_entry = entries[0]
    history_row = first_data_row
    while writer._is_instruction_row(sheet, history_row, header_map):
        history_row += 1
        
    writer._write_entry(sheet, history_row, newest_entry, header_map, serial_no=1, release_date="21/08/2026")
    writer._write_signoff_fields(sheet, newest_entry, history_row)
    t1 = time.time()
    print(f"[CHRONOLOGY-PERF] Data preparation: {t1 - t0:.3f} sec")
    
    # 3. Excel write
    t0 = time.time()
    writer._normalize_chronology_table_format(sheet, header_map, template_header_height, template_data_height)
    writer._restore_print_layout(sheet, layout_snapshot)
    writer._save(workbook, output_path)
    workbook.close()
    
    t1 = time.time()
    print(f"[CHRONOLOGY-PERF] Excel write: {t1 - t0:.3f} sec")
    
    # 4. LibreOffice export
    export_start = time.time()
    success = writer._export_generated_excel_to_pdf(output_path)
    export_time = time.time() - export_start
    print(f"[CHRONOLOGY-PERF] LibreOffice export (success={success}): {export_time:.3f} sec")
    
    total_time = time.time() - start_time
    print(f"[CHRONOLOGY-PERF] Total: {total_time:.3f} sec")

if __name__ == '__main__':
    profile()
