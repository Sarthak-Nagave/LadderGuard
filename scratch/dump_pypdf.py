import pypdf

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\4. Test Report\Slave\Final\S-final_Functional validation report_JIG-sgn.pdf"
    with open(path, "rb") as f:
        reader = pypdf.PdfReader(f)
        for i, page in enumerate(reader.pages):
            print(f"--- Page {i+1} ---")
            text = page.extract_text()
            if text:
                for line in text.splitlines():
                    if 'prepared' in line.lower() or 'checked' in line.lower() or 'approved' in line.lower():
                        print("Found line:", repr(line))

if __name__ == "__main__":
    dump()
