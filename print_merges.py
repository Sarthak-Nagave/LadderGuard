import openpyxl
wb = openpyxl.load_workbook("tests/base_template.xlsx")
ws = wb.active
for rng in ws.merged_cells.ranges:
    print(rng)
