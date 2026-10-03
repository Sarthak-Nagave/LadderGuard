from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reportlab.pdfgen import canvas

from core.validation_context import ValidationContext
from core.validation_step import ValidationStatus
from services.file_search import FileSearchService
from validators.chronology_validator import ChronologyValidator


class ChronologyValidatorCRCTests(unittest.TestCase):
    def test_chronology_validator_does_not_require_crc_comparison_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Master" / "Initial"
            stage_folder.mkdir(parents=True, exist_ok=True)

            c = canvas.Canvas(str(stage_folder / "chronology.pdf"))
            textobject = c.beginText()
            textobject.setTextOrigin(72, 750)
            text = (
                "Chronology Report - Master Initial\n"
                "Board\n"
                "Testing Stage\n"
                "BIN File\n"
                "Version\n"
                "Release Date\n"
                "Reason for Upgrade\n"
                "Master\n"
                "Initial\n"
                "firmware_V1.02.bin\n"
                "V1.02\n"
                "12-03-2026\n"
                "N/A"
            )
            for line in text.split("\n"):
                textobject.textLine(line)
            c.drawText(textobject)
            c.save()

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

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(result.details["stages"][0]["validation"]["crc"]["result"], "NOT_CHECKED")
            self.assertIsNone(result.details["stages"][0]["validation"]["crc"]["ladder_crc"])
            self.assertIsNone(result.details["stages"][0]["validation"]["crc"]["bin_crc"])

    def test_chronology_validator_keeps_crc_value_as_document_data_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Slave" / "Final"
            stage_folder.mkdir(parents=True, exist_ok=True)

            c = canvas.Canvas(str(stage_folder / "chronology.pdf"))
            textobject = c.beginText()
            textobject.setTextOrigin(72, 750)
            text = (
                "Chronology Report - Slave Final\n"
                "Board\n"
                "Testing Stage\n"
                "BIN File\n"
                "Version\n"
                "Release Date\n"
                "Reason for Upgrade\n"
                "CRC\n"
                "0xAA275AED\n"
                "Slave\n"
                "Final\n"
                "firmware_V1.00.bin\n"
                "V1.00\n"
                "14-05-2026\n"
                "Information update"
            )
            for line in text.split("\n"):
                textobject.textLine(line)
            c.drawText(textobject)
            c.save()

            bin_root = root / "2. Bin File"
            bin_stage_folder = bin_root / "Slave" / "Final"
            bin_stage_folder.mkdir(parents=True, exist_ok=True)
            actual_bin_path = bin_stage_folder / "firmware_V1.00.bin"
            actual_bin_path.write_bytes(b"bin")

            context = ValidationContext(project_path=root)
            context.add_folder("7. Chronology", chronology_folder)
            context.add_folder("2. Bin File", bin_root)
            context.add_discovered_path("Slave/Final", root / "1. Ladders" / "Slave" / "Final")
            context.add_bin_file("Slave/Final", actual_bin_path)

            validator = ChronologyValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(result.details["stages"][0]["crc"], "0XAA275AED")
            self.assertEqual(result.details["stages"][0]["validation"]["crc"]["result"], "NOT_CHECKED")


if __name__ == "__main__":
    unittest.main()
