import uno
from com.sun.star.beans import PropertyValue
import os
import time

def run():
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        'com.sun.star.bridge.UnoUrlResolver', localContext)
    ctx = None
    for i in range(10):
        try:
            ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
            break
        except Exception:
            time.sleep(0.5)
            
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
    
    in_props = (PropertyValue(Name='Hidden', Value=True),)
    doc_url = 'file:///' + os.path.abspath('ProjectValidator/scratch/col8_test.xlsx').replace('\\', '/')
    doc = desktop.loadComponentFromURL(doc_url, '_blank', 0, in_props)
    
    sheets = doc.getSheets()
    sheet = sheets.getByIndex(0)
    
    # Set Column A and B width in 100th of mm
    # 25 characters is approx 4.5 cm = 4500
    columns = sheet.getColumns()
    columns.getByIndex(0).Width = 4500
    columns.getByIndex(1).Width = 4500
    
    # Set Row 1 height to 90 points (90 / 72 * 25.4 * 100 = 3175)
    rows = sheet.getRows()
    rows.getByIndex(0).Height = 3175
    rows.getByIndex(1).Height = 100
    rows.getByIndex(2).Height = 100
    rows.getByIndex(3).Height = 100
    
    out_props = (PropertyValue(Name='FilterName', Value='calc_pdf_Export'),)
    out_url = 'file:///' + os.path.abspath('ProjectValidator/scratch/uno_colwidth_out.pdf').replace('\\', '/')
    doc.storeToURL(out_url, out_props)
    doc.close(True)

run()
