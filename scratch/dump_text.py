import pdfplumber

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\4. Test Report\Slave\Final\S-final_Functional validation report_JIG-sgn.pdf"
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"--- Page {i+1} ---")
            words = page.extract_words()
            for w in words:
                if 'prepared' in w['text'].lower() or 'checked' in w['text'].lower() or 'approved' in w['text'].lower():
                    print("Found word:", w)
            text = page.extract_text()
            if text:
                for line in text.splitlines():
                    if 'prepared' in line.lower() or 'checked' in line.lower() or 'approved' in line.lower():
                        print("Found line:", repr(line))

if __name__ == "__main__":
    dump()
