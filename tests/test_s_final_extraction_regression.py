import os
import pytest
from services.signature_reader import SignatureReaderService

# Assuming tests run from project root
PDF_PATH = r"C:\Users\SM 464\Desktop\Operational Package\4. Test Report\Slave\Final\S-final_Functional validation report_JIG-sgn.pdf"

@pytest.mark.skipif(not os.path.exists(PDF_PATH), reason="S-final PDF not available on host")
def test_s_final_prepared_by_extraction_regression():
    """
    Regression test for a bug where 'PREPARED BY: Akshay B.' was incorrectly parsed 
    because it overlapped horizontally with the 'X:\Product\...' watermark 
    on a slightly different baseline. 
    """
    from pathlib import Path
    snapshots = SignatureReaderService.read_page_snapshots(Path(PDF_PATH))
    page_1 = snapshots[0]  # Page 1 is index 0

    # Verify that the words were not shattered/interleaved
    prepared_by_words = [w.text for w in page_1.words if "PREPARED" in w.text.upper() or "AKSHAY" in w.text.upper()]
    assert len(prepared_by_words) > 0, "Failed to extract 'PREPARED' or 'Akshay' from the page."
    
    # Check that 'Akshay' was successfully isolated from the watermark
    found_akshay = False
    for text in prepared_by_words:
        if "Akshay" in text or "AKSHAY" in text:
            found_akshay = True
            break
            
    assert found_akshay, "Akshay was not extracted correctly from the overlapping watermark."
