from pypdf import PdfReader

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\6. Ladder Flow\LRPS480 SERIES_Ladder flow-sgn.pdf"
    reader = PdfReader(path)
    for i, page in enumerate(reader.pages):
        print(f"Page {i+1}:")
        if "/Annots" in page:
            for annot_ref in page["/Annots"]:
                try:
                    annot = annot_ref.get_object()
                    subtype = annot.get("/Subtype")
                    ft = annot.get("/FT")
                    v = annot.get("/V")
                    rect = annot.get("/Rect")
                    print(f"  Annot: Subtype={subtype} FT={ft} V={'Present' if v else 'None'} Rect={rect}")
                    parent = annot.get("/Parent")
                    if parent:
                        parent_obj = parent.get_object()
                        p_ft = parent_obj.get("/FT")
                        print(f"    Parent: FT={p_ft}")
                except Exception as e:
                    print(f"  Error: {e}")

if __name__ == "__main__":
    dump()
