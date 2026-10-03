import fitz

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\6. Ladder Flow\LRPS480 SERIES_Ladder flow-sgn.pdf"
    doc = fitz.open(path)
    for i, page in enumerate(doc):
        print(f"Page {i+1}:")
        for annot in page.annots():
            print(f"  Annot: type={annot.type} rect={annot.rect}")
        for widget in page.widgets():
            print(f"  Widget: field_type={widget.field_type} rect={widget.rect}")

if __name__ == "__main__":
    dump()
