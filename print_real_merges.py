import openpyxl
from pathlib import Path
template_path = next(Path("C:/Users/SM 464/Desktop/Operational Package Validator/ProjectValidator/scratch").rglob("Chronology.xlsx"))
wb = openpyxl.load_workbook(template_path)
ws = wb.active
for rng in ws.merged_cells.ranges:
    print(rng)
