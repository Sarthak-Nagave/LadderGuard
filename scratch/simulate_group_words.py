import pdfplumber

class PageWord:
    def __init__(self, text, x0, y0, x1, y1):
        self.text = text
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

def dump():
    path = r"c:\Users\SM 464\Desktop\Operational Package\4. Test Report\Slave\Final\S-final_Functional validation report_JIG-sgn.pdf"
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        words_dicts = page.extract_words(x_tolerance=1.5, y_tolerance=1.5)
        words = []
        for wd in words_dicts:
            words.append(PageWord(wd["text"], wd["x0"], wd["top"], wd["x1"], wd["bottom"]))
            
        sorted_words = sorted(words, key=lambda w: (w.y0, w.x0))
        lines = []
        current_line = [sorted_words[0]] if sorted_words else []

        for word in sorted_words[1:]:
            prev = current_line[-1]
            if abs(word.y0 - prev.y0) < 2.0 or abs(word.y1 - prev.y1) < 2.0:
                current_line.append(word)
            else:
                lines.append(current_line)
                current_line = [word]
        if current_line:
            lines.append(current_line)

        for line in lines:
            line.sort(key=lambda w: w.x0)
            text = " ".join(w.text for w in line)
            if 'PREPARED' in text or 'CHECKED' in text or 'APPROVED' in text:
                print(f"LINE: {text}")

if __name__ == "__main__":
    dump()
