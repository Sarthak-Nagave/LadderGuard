import openpyxl
wb = openpyxl.load_workbook('base_template.xlsx')
ws = wb.active
ws.insert_rows(15, 1)
wb.save('test_saved.xlsx')

wb2 = openpyxl.load_workbook('test_saved.xlsx')
ws2 = wb2.active
for merge in ws2.merged_cells.ranges:
    print(f"Merge after save: {merge}")
