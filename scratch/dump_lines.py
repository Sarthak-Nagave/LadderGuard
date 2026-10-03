import pdfplumber

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\4. Test Report\Slave\Final\S-final_Functional validation report_JIG-sgn.pdf"
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        lines = page.extract_text_lines(x_tolerance=1.5, y_tolerance=1.5)
        for line in lines:
            text = line.get("text", "")
            if 'PREPARED' in text or 'CHECKED' in text or 'Akshay' in text:
                print("Found line:", text)

if __name__ == "__main__":
    dump()
