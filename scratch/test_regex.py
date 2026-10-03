import re

def _sanitize_name_candidate(text: str) -> str:
    text = text.replace("\n", " ").replace("\r", "")
    text = re.sub(r"[\u200b\u200e\u200f\u202a-\u202e\ufeff]", "", text)
    text = re.sub(r"[_—\-\.]+$", "", text)
    text = re.sub(r"^[_—\-\.]+", "", text)
    text = re.sub(r"\(.*\)", "", text)
    text = re.sub(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}.*", "", text)
    text = re.sub(r"\d{2,4}[/-]\d{1,2}[/-]\d{1,2}.*", "", text)
    text = re.sub(r"[\s_]{2,}", " ", text)
    text = text.strip(" :.-_")
    return text

def _alias_pattern(alias: str) -> str:
    parts = re.split(r"[\s/]+", alias)
    return r"\s*[\s/]?\s*".join(re.escape(p) for p in parts if p)

def test():
    text = 'File Path: Prepared By: Akshay B. Verified By: Nitin K. Approved By: Sanjay P. Page'
    aliases = ['Approved By']
    
    stop_pattern = re.compile(
        r"(?i)\b("
        r"prepared\s*by|checked\s*by|verified\s*by|approved\s*by|"
        r"process\s*representative|production\s*/?\s*qc|hod|"
        r"page\s*\d+|file\s*path"
        r")\b|[A-Za-z]\s*:\\"
    )

    current = text.strip()
    for alias in aliases:
        alias_pattern = _alias_pattern(alias)
        match = re.search(rf"(?i)\b{alias_pattern}\b\s*[:\-]\s*(.+)$", current)
        if match:
            tail = match.group(1)
            print("Tail:", repr(tail))
            stop_match = stop_pattern.search(tail)
            if stop_match:
                print("Stop match found:", repr(stop_match.group(0)))
                tail = tail[: stop_match.start()]
            candidate = _sanitize_name_candidate(tail)
            print("Candidate:", repr(candidate))
        else:
            print("No match")

if __name__ == "__main__":
    test()
