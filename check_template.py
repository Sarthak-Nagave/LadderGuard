import openpyxl
wb = openpyxl.load_workbook('tests/base_template.xlsx')
ws = wb.active
for i in range(1, 20):
    vals = [ws.cell(row=i, column=c).value for c in range(1, 6)]
    if any(vals):
        print(f"Row {i}: {vals}")
for merge in ws.merged_cells.ranges:
    print(f"Merge: {merge}")
