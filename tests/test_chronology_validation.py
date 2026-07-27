from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fitz

from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStatus
from services.file_search import FileSearchService
from validators.chronology_validator import ChronologyValidator


class ChronologyValidatorTests(unittest.TestCase):
    def test_non_empty_chronology_folder_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            chronology_folder.mkdir(parents=True, exist_ok=True)
            (chronology_folder / "timeline.txt").write_text(
                "Revision 1",
                encoding="utf-8",
            )

            context = ValidationContext(project_path=root)
            context.add_folder("7. Chronology", chronology_folder)

            validator = ChronologyValidator(FileSearchService())
            result = validator.validate(context)

            self.assertIsInstance(result, ValidationResult)
            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(result.reason, "Chronology folder validated successfully.")

    def test_empty_chronology_folder_passes_when_folder_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            chronology_folder.mkdir(parents=True, exist_ok=True)

            context = ValidationContext(project_path=root)
            context.add_folder("7. Chronology", chronology_folder)

            validator = ChronologyValidator(FileSearchService())
            result = validator.validate(context)

            self.assertIsInstance(result, ValidationResult)
            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(result.reason, "Chronology folder validated successfully.")

    def test_chronology_validator_uses_discovered_stage_paths(self) -> None:
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
                "Master\n"
                "Initial\n"
                "firmware_V1.02.bin\n"
                "V1.02\n"
                "12-03-2026\n"
                "N/A",
            )
            document.save(stage_folder / "chronology.pdf")
            document.close()

            context = ValidationContext(project_path=root)
            context.add_folder("7. Chronology", chronology_folder)
            context.add_discovered_path("Master/Initial", root / "1. Ladders" / "Master" / "Initial")

            validator = ChronologyValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(result.reason, "Chronology folder validated successfully.")

    def test_chronology_validator_fails_when_expected_pdf_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Master" / "Initial"
            stage_folder.mkdir(parents=True, exist_ok=True)
            (stage_folder / "chronology.txt").write_text("placeholder", encoding="utf-8")

            context = ValidationContext(project_path=root)
            context.add_folder("7. Chronology", chronology_folder)
            context.add_discovered_path("Master/Initial", root / "1. Ladders" / "Master" / "Initial")

            validator = ChronologyValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.FAIL)
            self.assertIn("Missing Chronology PDF", result.reason)
            self.assertIn("Master / Initial", result.reason)

    def test_chronology_validator_extracts_firmware_metadata_from_pdf(self) -> None:
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

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(result.reason, "Chronology folder validated successfully.")
            self.assertEqual(result.details["stages"][0]["board"], "Master")
            self.assertEqual(result.details["stages"][0]["stage"], "Initial")
            self.assertEqual(result.details["stages"][0]["bin_file"], "firmware_V1.02.bin")
            self.assertEqual(result.details["stages"][0]["version"], "V1.02")
            self.assertEqual(result.details["stages"][0]["release_date"], "12-03-2026")
            self.assertEqual(result.details["stages"][0]["reason_for_upgrade"], "N/A")

    def test_chronology_validator_fails_when_chronology_data_does_not_match_bin(self) -> None:
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
                "Initial\n"
                "abc_V1.00.bin\n"
                "V1.00\n"
                "14-05-2026\n"
                "Firmware upgraded for production release.",
            )
            document.save(stage_folder / "chronology.pdf")
            document.close()

            bin_root = root / "2. Bin File"
            bin_stage_folder = bin_root / "Slave" / "Final"
            bin_stage_folder.mkdir(parents=True, exist_ok=True)
            actual_bin_path = bin_stage_folder / "abc_V2.00.bin"
            actual_bin_path.write_bytes(b"bin")

            context = ValidationContext(project_path=root)
            context.add_folder("7. Chronology", chronology_folder)
            context.add_folder("2. Bin File", bin_root)
            context.add_discovered_path("Slave/Final", root / "1. Ladders" / "Slave" / "Final")
            context.add_bin_file("Slave/Final", actual_bin_path)

            validator = ChronologyValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.FAIL)
            self.assertIn("Testing Stage", result.reason)
            self.assertIn("Version", result.reason)
            self.assertIn("BIN filename", result.reason)

    def test_chronology_validator_handles_wrapped_bin_filenames(self) -> None:
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
                "LD_TCX03_very_long_\n"
                "firmware_name.bin\n"
                "V2.00\n"
                "14-05-2026\n"
                "Firmware upgraded for production release and protocol improvements.",
            )
            document.save(stage_folder / "chronology.pdf")
            document.close()

            bin_root = root / "2. Bin File"
            bin_stage_folder = bin_root / "Slave" / "Final"
            bin_stage_folder.mkdir(parents=True, exist_ok=True)
            actual_bin_path = bin_stage_folder / "LD_TCX03_very_long_firmware_name.bin"
            actual_bin_path.write_bytes(b"bin")

            context = ValidationContext(project_path=root)
            context.add_folder("7. Chronology", chronology_folder)
            context.add_folder("2. Bin File", bin_root)
            context.add_discovered_path("Slave/Final", root / "1. Ladders" / "Slave" / "Final")
            context.add_bin_file("Slave/Final", actual_bin_path)

            validator = ChronologyValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(result.details["stages"][0]["board"], "Slave")
            self.assertEqual(result.details["stages"][0]["stage"], "Final")
            self.assertEqual(result.details["stages"][0]["bin_file"], "LD_TCX03_very_long_firmware_name.bin")
            self.assertEqual(result.details["stages"][0]["version"], "V2.00")
            self.assertEqual(result.details["stages"][0]["release_date"], "14-05-2026")
            self.assertEqual(result.details["stages"][0]["reason_for_upgrade"], "Firmware upgraded for production release and protocol improvements.")


if __name__ == "__main__":
    unittest.main()
