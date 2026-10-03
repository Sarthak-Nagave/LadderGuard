import pdfplumber

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\4. Test Report\Slave\Final\S-final_Functional validation report_JIG-sgn.pdf"
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(x_tolerance=1, y_tolerance=1)
        for w in words:
            if 'prepared' in w['text'].lower():
                print("Found word (tol=1):", w)
        
        words = page.extract_words(x_tolerance=0.5, y_tolerance=0.5)
        for w in words:
            if 'prepared' in w['text'].lower():
                print("Found word (tol=0.5):", w)

        print("Done")

if __name__ == "__main__":
    dump()
