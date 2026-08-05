import os
import sys
from pathlib import Path

# Ensure repo on path
repo = Path(__file__).resolve().parents[1]
os.environ['PYTHONPATH'] = str(repo)

from reports.report_model import ReportDataModel

from core.validation_engine import ValidationEngine
from core.validation_step import ValidationStep
from services.logger import LoggerService

LoggerService.configure()

# Create a temporary project structure
tmp = Path('tmp_gui_trace_project')
if tmp.exists():
    import shutil
    shutil.rmtree(tmp)

# Build required folders and minimal files
from config import REQUIRED_FOLDERS

for folder in REQUIRED_FOLDERS:
    (tmp / folder).mkdir(parents=True, exist_ok=True)

# Create ladder file
lpath = tmp / '1. Ladders' / 'Master' / 'Initial'
lpath.mkdir(parents=True, exist_ok=True)
(lpath / 'firmware.sdoc').write_text('sdoc')

# Create bin file
bpath = tmp / '2. Bin File' / 'Master' / 'Initial'
bpath.mkdir(parents=True, exist_ok=True)
(bpath / 'firmware.bin').write_bytes(b'bin-data')

# Create chronology pdf with CRC text
try:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72,72), 'Board\nTesting Stage\nBIN File\nVersion\nRelease Date\nReason for Upgrade\nCRC\n0xDEADBEEF\nMaster\nInitial\nfirmware.bin\nV1.0\n01-01-2026\nN/A')
    (tmp / '7. Chronology' / 'Master' / 'Initial').mkdir(parents=True, exist_ok=True)
    doc.save(tmp / '7. Chronology' / 'Master' / 'Initial' / 'chronology.pdf')
    doc.close()
except Exception:
    # If fitz unavailable, write a fake pdf file as text; ChronologyValidator uses fitz to read, so this may fail
    (tmp / '7. Chronology' / 'Master' / 'Initial').mkdir(parents=True, exist_ok=True)
    (tmp / '7. Chronology' / 'Master' / 'Initial' / 'chronology.pdf').write_text('CRC\n0xDEADBEEF')

# Run validation using the same ValidationEngine the GUI uses
engine = ValidationEngine()
summary = engine.validate(tmp)

# Extract chronology result
chron_result = None
for res in summary.results:
    if res.step == ValidationStep.CHRONOLOGY:
        chron_result = res
        break

print('\n=== chronology ValidationResult ===')
print(chron_result)
print('details keys:', list(chron_result.details.keys()))
print('stages:', chron_result.details.get('stages'))

stages = chron_result.details.get('stages') or []
if stages:
    stage0 = stages[0]
    print('\n=== Stage 0 contents ===')
    for k, v in stage0.items():
        print(k, ':', v)
    print('\ncrc_match:', stage0.get('crc_match'))
    print('computed_crc:', stage0.get('computed_crc'))
    print('computed_crc_decimal:', stage0.get('computed_crc_decimal'))
    print('chronology_crc_decimal:', stage0.get('chronology_crc_decimal'))

print('\n=== ValidationSummary.results ===')
for r in summary.results:
    print(r.step, r.status, r.reason)

print('\n=== ReportDataModel ===')
report_model = ReportDataModel.from_summary(summary)
print('project_name:', report_model.project_name)
print('sections count:', len(report_model.sections))
for sec in report_model.sections:
    print('section:', sec.title)

# Instantiate ReportWindow object to show it's constructed (no GUI shown)
try:
    from PySide6.QtWidgets import QApplication
    from reports.report_window import ReportWindow
    app = QApplication(sys.argv)
    window = ReportWindow(report_model)
    print('\n=== ReportWindow constructed ===')
    print('window._data_model.project_path =', window._data_model.project_path)
    # clean up
    window.deleteLater()
    app.quit()
except Exception as e:
    print('\nReportWindow could not be constructed:', e)

print('\nDone')
