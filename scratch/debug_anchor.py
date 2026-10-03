import sys
import os
from pathlib import Path

from core.validation_engine import ValidationEngine
from services.signature_reader import SignatureReaderService
from validators.document_validator import DocumentValidator

def test():
    pdf_path = Path(r"c:\Users\SM 464\Desktop\Operational Package\4. Test Report\Slave\Final\S-final_Functional validation report_JIG-sgn.pdf")
    snapshots = SignatureReaderService.read_page_snapshots(pdf_path)
    print(f"Extracted {len(snapshots)} snapshots")
    
    val = DocumentValidator(None, None, None, None, None)
    for i, snap in enumerate(snapshots):
        print(f"--- Page {i+1} ---")
        rect = val._find_alias_rect_in_words(snap.words, "Prepared By")
        if rect:
            print("FOUND Prepared By in words:", rect)
        else:
            print("NOT FOUND Prepared By in words")
            
        rect2 = val._find_alias_rect_in_words(snap.words, "Checked By")
        if rect2:
            print("FOUND Checked By in words:", rect2)
        else:
            print("NOT FOUND Checked By in words")
            
        rect3 = val._find_alias_rect_in_words(snap.words, "Approved By")
        if rect3:
            print("FOUND Approved By in words:", rect3)
        else:
            print("NOT FOUND Approved By in words")

if __name__ == "__main__":
    test()
