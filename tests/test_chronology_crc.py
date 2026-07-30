from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fitz

from core.validation_context import ValidationContext
from core.validation_step import ValidationStatus
from services.file_search import FileSearchService
from validators.chronology_validator import ChronologyValidator


class ChronologyValidatorCRCTests(unittest.TestCase):
    def test_chronology_validator_reports_crc_values_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Master" / "Initial"
            stage_folder.mkdir(parents=True, exist_ok=True)

            document = fitz.open()
            page = document.new_page()
            page.insert_text(
                (72, 72),
                "Chronology Report - Master Initial\n"
                "Board\n"
                "Testing Stage\n"
                "BIN File\n"
                "Version\n"
                "Release Date\n"
                "Reason for Upgrade\n"
                "CRC\n"
                "0x1234ABCD\n"
                "Master\n"
                "Initial\n"
                "firmware_V1.02.bin\n"
                "V1.02\n"
                "12-03-2026\n"
                "N/A",
            )
            document.save(stage_folder / "chronology.pdf")
            document.close()

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

            self.assertEqual(result.status, ValidationStatus.FAIL)
            self.assertIn("CRC mismatch", result.reason)
            self.assertEqual(result.details["stages"][0]["crc"], "0X1234ABCD")
            self.assertEqual(result.details["stages"][0]["computed_crc"], "0xAA275AED")
            self.assertFalse(result.details["stages"][0]["crc_match"])

    def test_chronology_validator_fails_when_crc_missing_in_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Slave" / "Final"
            stage_folder.mkdir(parents=True, exist_ok=True)

            document = fitz.open()
            page = document.new_page()
            page.insert_text(
                (72, 72),
                "Chronology Report - Slave Final\n"
                "Board\n"
                "Testing Stage\n"
                "BIN File\n"
                "Version\n"
                "Release Date\n"
                "Reason for Upgrade\n"
                "Slave\n"
                "Final\n"
                "firmware_V1.00.bin\n"
                "V1.00\n"
                "14-05-2026\n"
                "Information update",
            )
            document.save(stage_folder / "chronology.pdf")
            document.close()

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

            self.assertEqual(result.status, ValidationStatus.FAIL)
            self.assertIn("CRC value missing", result.reason)
            self.assertIsNone(result.details["stages"][0].get("crc"))
            self.assertEqual(result.details["stages"][0].get("computed_crc"), "0xAA275AED")
            self.assertIsNone(result.details["stages"][0].get("crc_match"))


if __name__ == "__main__":
    unittest.main()
