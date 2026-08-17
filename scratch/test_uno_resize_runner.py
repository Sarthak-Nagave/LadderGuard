import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.awt import Size
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
    
    in_props = (
        PropertyValue(Name='Hidden', Value=True),
    )
    doc_url = 'file:///' + os.path.abspath('ProjectValidator/backup_release_cleanup/archive/test_firmware_project/Master/Initial/Ladder_Chronology.xlsx').replace('\\', '/')
    doc = desktop.loadComponentFromURL(doc_url, '_blank', 0, in_props)
    
    sheets = doc.getSheets()
    sheet = sheets.getByIndex(0)
    dp = sheet.getDrawPage()
    for j in range(dp.getCount()):
        shape = dp.getByIndex(j)
        if shape.supportsService("com.sun.star.drawing.GraphicObjectShape"):
            # Set size to 299x120 pixels = 7911x3175 100th mm
            shape.setSize(Size(7911, 3175))
            
    out_props = (
        PropertyValue(Name='FilterName', Value='calc_pdf_Export'),
    )
    out_url = 'file:///' + os.path.abspath('ProjectValidator/scratch/uno_resize_out.pdf').replace('\\', '/')
    doc.storeToURL(out_url, out_props)
    doc.close(True)

run()
