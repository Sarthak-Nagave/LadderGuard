import os
import shutil
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
os.environ['PYTHONPATH'] = str(repo)

from reports.report_model import ReportDataModel

from core.validation_engine import ValidationEngine
from core.validation_step import ValidationStep
from services.logger import LoggerService

LoggerService.configure()

# reuse tmp project created earlier if exists
tmp = Path('tmp_gui_trace_project')
if tmp.exists():
    shutil.rmtree(tmp)

# Create minimal project
from config import REQUIRED_FOLDERS

for folder in REQUIRED_FOLDERS:
    (tmp / folder).mkdir(parents=True, exist_ok=True)

# ladder and bin
(tmp / '1. Ladders' / 'Master' / 'Initial').mkdir(parents=True, exist_ok=True)
(tmp / '2. Bin File' / 'Master' / 'Initial').mkdir(parents=True, exist_ok=True)
(tmp / '1. Ladders' / 'Master' / 'Initial' / 'firmware.sdoc').write_text('sdoc')
(tmp / '2. Bin File' / 'Master' / 'Initial' / 'firmware.bin').write_bytes(b'bin-data')

# chronology pdf
try:
    import fitz
    (tmp / '7. Chronology' / 'Master' / 'Initial').mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72,72), 'Board\nTesting Stage\nBIN File\nVersion\nRelease Date\nReason for Upgrade\nCRC\n0xDEADBEEF\nMaster\nInitial\nfirmware.bin\nV1.0\n01-01-2026\nN/A')
    doc.save(tmp / '7. Chronology' / 'Master' / 'Initial' / 'chronology.pdf')
    doc.close()
except Exception:
    (tmp / '7. Chronology' / 'Master' / 'Initial').mkdir(parents=True, exist_ok=True)
    (tmp / '7. Chronology' / 'Master' / 'Initial' / 'chronology.pdf').write_text('CRC\n0xDEADBEEF')

# Run validation
engine = ValidationEngine()
summary = engine.validate(tmp)

# locate chronology result
chron_result = None
for r in summary.results:
    if r.step == ValidationStep.CHRONOLOGY:
        chron_result = r
        break

print('\n--- ValidationResult.details["stages"] ---')
stages = chron_result.details.get('stages', [])
for idx, stage in enumerate(stages):
    print(f'-- stage {idx} object --')
    for k,v in stage.items():
        print(f'{k!s}: {v!r}')

# Build report model
report_model = ReportDataModel.from_summary(summary)

print('\n--- ReportDataModel.sections (detailed) ---')
for si, section in enumerate(report_model.sections):
    print(f'--- section {si}: {section.title} ---')
    print(' reason:', section.reason)
    print(' details count:', len(section.details))
    for ci, card in enumerate(section.details):
        print(f'  card {ci} title: {card.title!r}')
        for ri, row in enumerate(card.rows):
            print(f'    row {ri}: label={row.label!r}, value={row.value!r}')
        if card.children:
            print('    children:', len(card.children))

# Instantiate ReportWindow and inspect widget labels
from PySide6.QtWidgets import QApplication
from reports.report_window import ReportWindow

app = QApplication([])
window = ReportWindow(report_model)

print('\n--- ReportWindow UI inspection ---')
print('data model project_path =', window._data_model.project_path)
# walk sections container
sections_layout = window._sections_layout
for i in range(sections_layout.count()):
    item = sections_layout.itemAt(i)
    widget = item.widget()
    if widget is None:
        continue
        # print widget type name and the first few QLabel texts inside
        print(f'UI section widget {i}: type={type(widget)}')
        from PySide6.QtWidgets import QLabel
        qlabels = widget.findChildren(QLabel)
        print('  QLabel count:', len(qlabels))
        for ql in qlabels[:20]:
            try:
                print('   ', ql.text())
            except Exception:
                print('   ', '<non-text QLabel>')

print('\nDone')
