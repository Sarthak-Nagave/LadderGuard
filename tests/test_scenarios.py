from pathlib import Path

import openpyxl

from services.chronology_generator.excel_writer import ChronologyExcelWriter
from services.chronology_generator.models import ChronologyEntry, ProjectChronology


def create_base_template(path: Path, num_history: int = 0):
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Scenario 6: Merged title row
    ws.cell(row=1, column=2, value="COMPANY TITLE")
    ws.merge_cells("B1:P1")
    
    headers = {
        1: 'Serial No.', 2: 'Source Code Path', 3: 'Bin File Name', 4: 'CRC', 
        5: 'Ladder Version No.', 6: 'Reason For Upgrade', 7: 'Testing Stage', 
        8: 'PLC Model', 9: 'Selpro Version & Path', 10: 'Bootloader Version',
        11: 'Release Date', 12: 'Released By', 13: 'Ladder Release-To Production',
        14: 'Operator Procedure Modification', 15: 'Automation Set Up Modification', 16: 'Tested By'
    }
    # Place header at row 14
    for col, val in headers.items():
        ws.cell(row=14, column=col, value=val)
        
    next_row = 15
    for i in range(num_history):
        data = {
            1: num_history - i,
            2: f"C:\\Path\\V1.0{num_history - i}",
            3: f"FW_V1.0{num_history - i}.bin",
            4: "ABCD1234",
            5: f"V1.0{num_history - i}",
            6: "Release",
            7: "Production",
            8: "MIBRX-4M"
        }
        for col, val in data.items():
            ws.cell(row=next_row, column=col, value=val)
        next_row += 1
        
    # Scenario 4: Merged instruction rows
    ws.cell(row=next_row, column=2, value="Some instructions")
    ws.merge_cells(f"B{next_row}:P{next_row}")
    
    # Scenario 5: Merged footer
    ws.cell(row=next_row + 4, column=2, value="Footer Text")
    ws.merge_cells(f"B{next_row + 4}:D{next_row + 4}")
    
    wb.save(path)
    wb.close()

def generate_release(path: Path, version: str):
    chronology = ProjectChronology(Path("."))
    entry = ChronologyEntry(
        version=version,
        source_code_path=Path(f"C:\\Path\\To\\{version}"),
        bin_file_path=Path(f"C:\\Path\\To\\{version}\\FW.bin"),
        sdoc_file_path=None,
        bin_file_name=f"FW_{version}.bin",
        sdoc_file_name=None,
        crc="9876FEDC",
        plc_model="MIBRX-4M",
        testing_stage="Production",
        bootloader_version="BL20",
        selpro_version="SP4",
        reason_for_upgrade="Bug Fix",
        release_date="05/08/2026",
    )
    chronology.entries.append(entry)
    writer = ChronologyExcelWriter(path)
    writer.write(chronology, path)

def print_sheet_state(path: Path):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    print("Merged cells:", list(ws.merged_cells.ranges))
    for r in range(14, ws.max_row + 1):
        row_vals = [ws.cell(row=r, column=c).value for c in range(1, 6)]
        # Stop printing if empty
        if not any(row_vals):
            continue
        print(f"Row {r}: {row_vals}")
    wb.close()

def main():
    print("=== Scenario 1: Empty chronology template -> Generate first release ===")
    p1 = Path("scen1.xlsx")
    create_base_template(p1, num_history=0)
    generate_release(p1, "V1.01")
    print_sheet_state(p1)
    
    print("\n=== Scenario 2: One previous release -> Generate second release ===")
    p2 = Path("scen2.xlsx")
    create_base_template(p2, num_history=1)
    generate_release(p2, "V1.02")
    print_sheet_state(p2)
    
    print("\n=== Scenario 3: Three previous releases -> Generate fourth release ===")
    p3 = Path("scen3.xlsx")
    create_base_template(p3, num_history=3)
    generate_release(p3, "V1.04")
    print_sheet_state(p3)

if __name__ == "__main__":
    main()
