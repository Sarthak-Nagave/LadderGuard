import uno
from com.sun.star.awt import Size
def calc_pdf_Export(*args):
    desktop = XSCRIPTCONTEXT.getDesktop()
    doc = desktop.getCurrentComponent()
    sheets = doc.getSheets()
    sheet = sheets.getByIndex(0)
    dp = sheet.getDrawPage()
    for j in range(dp.getCount()):
        shape = dp.getByIndex(j)
        if shape.supportsService("com.sun.star.drawing.GraphicObjectShape"):
            # Set size to 299x120 pixels
            # 1 pixel = ~26.4583 hundredths of mm.
            # 299 * 26.4583 = 7911
            # 120 * 26.4583 = 3175
            shape.setSize(Size(7911, 3175))
            # Also reset its position so it's snapped to top-left of A1?
            # Or just let it be?
    doc.store()
