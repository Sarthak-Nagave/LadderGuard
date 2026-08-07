import sys
from pathlib import Path
import openpyxl

# Add src path
sys.path.append(str(Path(".").resolve()))

from services.chronology_generator.excel_writer import ChronologyExcelWriter
from services.chronology_generator.excel_writer import ChronologyExcelWriter
from services.chronology_generator.models import ChronologyEntry, ProductInfo

class DummyWriter(ChronologyExcelWriter):
    def __init__(self):
        super().__init__()
    
    # We patch out extract_product_info just for testing
    pass

def run():
    wb = openpyxl.Workbook()
    sheet = wb.active
    
    # Initialize some layout mimicking the template
    sheet.cell(5, 1).value = "Product Series:"
    sheet.merge_cells(start_row=5, start_column=1, end_row=5, end_column=8) # Suppose the template was fully merged! Wait, template has A5 and B5? Let's just merge A5:H5 for fun.
    
    writer = ChronologyExcelWriter(template_path=Path("dummy.xlsx"))
    
    # We need to mock _write_product_info's call to parser.extract_product_info
    info = ProductInfo(
        parse_status="Success",
        mode="Series",
        series_name="PRODUCT SERIES LPRS480",
        single_product="",
        products=["LPRS480-24-CE", "LPRS480-12-CE"]
    )
    
    # Monkey-patch
    import services.chronology_generator.pdf_parser
    class DummyParser:
        def extract_product_info(self, path):
            return info
    services.chronology_generator.pdf_parser.TestReportParser = DummyParser
    
    entry = ChronologyEntry(
        source_code_path=Path("dummy"),
        bin_path=Path("dummy"),
        sdoc_path=Path("dummy"),
        test_report_path=Path("dummy.pdf")
    )
    
    # Write product info
    # We pass 8 as header_row_idx
    writer._write_product_info(sheet, entry, header_row_idx=8)
    
    # Save the workbook (using writer's save method to trigger the prints)
    writer._save(wb, Path("test_write.xlsx"))
    
if __name__ == "__main__":
    run()
