import openpyxl
from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, AnchorMarker
import shutil
import copy

template_path = 'ProjectValidator/backup_release_cleanup/archive/test_firmware_project/Master/Initial/Ladder_Chronology.xlsx'
test_path = 'ProjectValidator/scratch/final_compact_test.xlsx'
shutil.copy(template_path, test_path)

wb = openpyxl.load_workbook(test_path)
ws = wb.active

# 1. Page Margins
ws.page_margins.header = 0.3
ws.page_margins.top = 0.45

# 2. Row Heights
ws.row_dimensions[1].height = 90.0
for i in range(2, 8):
    ws.row_dimensions[i].height = 0  # Hide empty rows

# 3. Logo Anchor
img = ws._images[0]
new_anchor = OneCellAnchor()
new_anchor._from = AnchorMarker(col=0, colOff=47520, row=0, rowOff=95400)
new_anchor.ext.cx = 299 * 9525
new_anchor.ext.cy = 120 * 9525
new_anchor.pic = img.anchor.pic
img.anchor = new_anchor

wb.save(test_path)
wb.close()
