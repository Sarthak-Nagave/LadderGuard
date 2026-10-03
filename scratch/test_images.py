import pdfplumber

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\6. Ladder Flow\LRPS480 SERIES_Ladder flow-sgn.pdf"
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"Page {i+1}:")
            for img in page.images:
                print(f"  Image: {img.get('x0')}, {img.get('top')} -> {img.get('x1')}, {img.get('bottom')}")
            for line in page.lines:
                print(f"  Line: {line.get('x0')}, {line.get('top')} -> {line.get('x1')}, {line.get('bottom')}")
            for curve in page.curves:
                print(f"  Curve: {curve.get('x0')}, {curve.get('top')} -> {curve.get('x1')}, {curve.get('bottom')}")

if __name__ == "__main__":
    dump()
