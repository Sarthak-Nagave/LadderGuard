import datetime
import tempfile
from pathlib import Path

import fitz
from reports.report_model import ReportDataModel

from core.validation_context import ValidationContext
from services.file_search import FileSearchService
from services.logger import LoggerService
from validators.chronology_validator import ChronologyValidator

# Ensure logger configured
LoggerService.configure()

with tempfile.TemporaryDirectory() as tmpdir:
    root = Path(tmpdir)
    chronology_folder = root / "7. Chronology"
    stage_folder = chronology_folder / "Master" / "Initial"
    stage_folder.mkdir(parents=True, exist_ok=True)

    # Create chronology PDF with CRC value
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), (
        "Chronology Report - Master Initial\n"
        "Board\n"
        "Testing Stage\n"
        "BIN File\n"
        "Version\n"
        "Release Date\n"
        "Reason for Upgrade\n"
        "CRC\n"
        "0xDEADBEEF\n"
        "Master\n"
        "Initial\n"
        "firmware_V1.02.bin\n"
        "V1.02\n"
        "12-03-2026\n"
        "N/A\n"
    ))
    doc.save(stage_folder / "chronology.pdf")
    doc.close()

    bin_root = root / "2. Bin File"
    bin_stage_folder = bin_root / "Master" / "Initial"
    bin_stage_folder.mkdir(parents=True, exist_ok=True)
    actual_bin_path = bin_stage_folder / "firmware_V1.02.bin"
    actual_bin_path.write_bytes(b"bin")

    context = ValidationContext(project_path=root)
    context.add_folder("7. Chronology", chronology_folder)
    context.add_folder("2. Bin File", bin_root)
    context.add_discovered_path("Master/Initial", root / "1. Ladders" / "Master" / "Initial")
    context.add_bin_file("Master/Initial", actual_bin_path)

    validator = ChronologyValidator(FileSearchService())
    result = validator.validate(context)

    print("\nValidation result status:", result.status)
    print("Reason:", result.reason)
    print("Details keys:", list(result.details.keys()))
    stages = result.details.get("stages")
    print("Stages:")
    for s in stages:
        print(s)

    # Build report data model
    from core.validation_summary import ValidationSummary
    summary = ValidationSummary(project_path=root, started_at=datetime.datetime.now(), finished_at=datetime.datetime.now(), results=[result])
    # Avoid using datetime formatting; just inspect sections
    report = ReportDataModel.from_summary(summary)
    print('\nReport sections:')
    for sec in report.sections:
        print(sec.title)
        for card in sec.details:
            print(' -', card.title)
            for row in card.rows:
                print('    ', row.label, ':', row.value)

print('\nDemo complete')
