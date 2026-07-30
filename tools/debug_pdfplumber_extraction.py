from __future__ import annotations

import tempfile
from pathlib import Path

import fitz
import pdfplumber

headers = [
    "Testing Stage",
    "BIN File",
    "CRC",
    "Version",
    "Release Date",
    "Reason for Upgrade",
]
row = [
    "Master / Initial",
    "firmware_V1.00.bin",
    "0x1234ABCD",
    "V1.00",
    "14.05.2026",
    "Firmware stability improvements.",
]

with tempfile.TemporaryDirectory() as temp_dir:
    path = Path(temp_dir) / "chronology.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), " | ".join(headers))
    page.insert_text((72, 90), " | ".join(row))
    document.save(str(path))
    document.close()

    print("pdf_path=", path)
    print("exists=", path.exists())

    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"page={i}")
            text = page.extract_text()
            print("text=", repr(text))
            print("tables=", page.extract_tables())
