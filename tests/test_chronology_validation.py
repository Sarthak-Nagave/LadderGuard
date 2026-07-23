from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
