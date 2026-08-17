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
    
    in_props = (PropertyValue(Name='Hidden', Value=True),)
    doc_url = 'file:///' + os.path.abspath('ProjectValidator/backup_release_cleanup/archive/test_firmware_project/Master/Initial/Ladder_Chronology.xlsx').replace('\\', '/')
    doc = desktop.loadComponentFromURL(doc_url, '_blank', 0, in_props)
    
    sheets = doc.getSheets()
    sheet = sheets.getByIndex(0)
    dp = sheet.getDrawPage()
    for j in range(dp.getCount()):
        shape = dp.getByIndex(j)
        if shape.supportsService("com.sun.star.drawing.GraphicObjectShape"):
            try:
                # 2 is AT_PAGE, 0 is AT_PARAGRAPH, 4 is AT_CELL
                shape.setPropertyValue("AnchorType", uno.Enum("com.sun.star.text.TextContentAnchorType", "AT_PAGE"))
            except Exception as e:
                print("Error setting AnchorType enum:", e)
                try:
                    shape.setPropertyValue("AnchorType", 2)
                except Exception as e2:
                    print("Error setting AnchorType int:", e2)
            
            shape.setSize(Size(7911, 3175))
            
    out_props = (PropertyValue(Name='FilterName', Value='calc_pdf_Export'),)
    out_url = 'file:///' + os.path.abspath('ProjectValidator/scratch/uno_page_out2.pdf').replace('\\', '/')
    doc.storeToURL(out_url, out_props)
    doc.close(True)

run()
