import openpyxl
wb = openpyxl.load_workbook('base_template.xlsx')
ws = wb.active
ws.insert_rows(15, 1)
for merge in ws.merged_cells.ranges:
    print(f"Merge after insert at 15: {merge}")
