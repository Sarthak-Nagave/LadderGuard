import fitz

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\6. Ladder Flow\LRPS480 SERIES_Ladder flow-sgn.pdf"
    doc = fitz.open(path)
    for i, page in enumerate(doc):
        print(f"Page {i+1}:")
        for img in page.get_images(full=True):
            print(f"  Image: {img}")
        drawings = page.get_drawings()
        print(f"  Drawings count: {len(drawings)}")

if __name__ == "__main__":
    dump()
