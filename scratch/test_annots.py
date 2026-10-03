import pdfplumber
from pdfplumber.utils import resolve

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\6. Ladder Flow\LRPS480 SERIES_Ladder flow-sgn.pdf"
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"Page {i+1}:")
            annots = page.annots
            if not annots:
                print("  No annots")
                continue
            for annot_ref in annots:
                annot = resolve(annot_ref)
                print("  Annot dict:", annot)

if __name__ == "__main__":
    dump()
