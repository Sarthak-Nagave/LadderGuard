import tempfile
import unittest
from pathlib import Path

from core.validation_context import ValidationContext
from core.validation_step import ValidationStatus, ValidationStep
from services.file_reader import FileReaderService
from services.file_search import FileSearchService
from services.signature_reader import SignatureReaderService
from validators.bin_validator import BinValidator
from validators.document_validator import DocumentValidator
from validators.ladder_validator import LadderValidator


class DynamicValidationTests(unittest.TestCase):
    def test_ladder_validator_discovers_dynamic_subfolders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ladders_root = root / "1. Ladders"
            master = ladders_root / "Master"
            slave = ladders_root / "Slave"
            (master / "Initial").mkdir(parents=True, exist_ok=True)
            (master / "QC").mkdir(parents=True, exist_ok=True)
            (slave / "Voltage").mkdir(parents=True, exist_ok=True)
            (master / "Initial" / "alpha.sdoc").write_text(
                "alpha",
                encoding="utf-8",
            )
            (master / "QC" / "beta.sdoc").write_text(
                "beta",
                encoding="utf-8",
            )
            (slave / "Voltage" / "gamma.sdoc").write_text(
                "gamma",
                encoding="utf-8",
            )

            context = ValidationContext(project_path=root)
            context.add_folder("1. Ladders", ladders_root)

            validator = LadderValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(
                sorted(context.ladder_files.keys()),
                ["Master/Initial", "Master/QC", "Slave/Voltage"],
            )

    def test_ladder_validator_discovers_arbitrary_board_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ladders_root = root / "1. Ladders"
            factory = ladders_root / "Factory"
            (factory / "BurnIn").mkdir(parents=True, exist_ok=True)
            (factory / "BurnIn" / "gamma.sdoc").write_text(
                "gamma",
                encoding="utf-8",
            )

            context = ValidationContext(project_path=root)
            context.add_folder("1. Ladders", ladders_root)

            validator = LadderValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertIn("Factory/BurnIn", context.ladder_files)

    def test_bin_validator_matches_discovered_folder_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ladders_root = root / "1. Ladders"
            bin_root = root / "2. Bin File"
            (ladders_root / "Master" / "Initial").mkdir(parents=True, exist_ok=True)
            (ladders_root / "Master" / "QC").mkdir(parents=True, exist_ok=True)
            (bin_root / "Master" / "Initial").mkdir(parents=True, exist_ok=True)
            (bin_root / "Master" / "QC").mkdir(parents=True, exist_ok=True)
            (ladders_root / "Master" / "Initial" / "alpha.sdoc").write_text(
                "alpha",
                encoding="utf-8",
            )
            (ladders_root / "Master" / "QC" / "beta.sdoc").write_text(
                "beta",
                encoding="utf-8",
            )
            (bin_root / "Master" / "Initial" / "alpha.bin").write_text(
                "bin",
                encoding="utf-8",
            )
            (bin_root / "Master" / "QC" / "beta.bin").write_text(
                "bin",
                encoding="utf-8",
            )

            context = ValidationContext(project_path=root)
            context.add_folder("1. Ladders", ladders_root)
            context.add_folder("2. Bin File", bin_root)
            context.add_discovered_path("Master/Initial", ladders_root / "Master" / "Initial")
            context.add_discovered_path("Master/QC", ladders_root / "Master" / "QC")
            context.add_ladder_file("Master/Initial", ladders_root / "Master" / "Initial" / "alpha.sdoc")
            context.add_ladder_file("Master/QC", ladders_root / "Master" / "QC" / "beta.sdoc")

            validator = BinValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)

    def test_document_validator_uses_discovered_stage_folders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            operational_root = root / "3. Operational Flow"
            (operational_root / "Factory" / "BurnIn").mkdir(parents=True, exist_ok=True)
            (operational_root / "Factory" / "BurnIn" / "flow-sgn.pdf").write_bytes(
                b"%PDF-1.4\n%fake",
                )

            context = ValidationContext(project_path=root)
            context.add_folder("3. Operational Flow", operational_root)
            context.add_discovered_path("Factory/BurnIn", operational_root / "Factory" / "BurnIn")

            validator = DocumentValidator(
                ValidationStep.OPERATIONAL_FLOW,
                "3. Operational Flow",
                FileSearchService(),
                FileReaderService(),
                SignatureReaderService(),
            )
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)

    def test_test_report_validator_accepts_simple_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_root = root / "4. Test Report"
            report_root.mkdir(parents=True, exist_ok=True)
            (report_root / "report_of_test-sgn.pdf").write_bytes(b"%PDF-1.4\n%fake")

            context = ValidationContext(project_path=root)
            context.add_folder("4. Test Report", report_root)

            validator = DocumentValidator(
                ValidationStep.TEST_REPORT,
                "4. Test Report",
                FileSearchService(),
                FileReaderService(),
                SignatureReaderService(),
            )
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)

    def test_test_report_validator_accepts_structured_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ladders_root = root / "1. Ladders"
            report_root = root / "4. Test Report"
            (ladders_root / "Master" / "Initial").mkdir(parents=True, exist_ok=True)
            (ladders_root / "Master" / "QC").mkdir(parents=True, exist_ok=True)
            (report_root / "Master" / "Initial").mkdir(parents=True, exist_ok=True)
            (report_root / "Master" / "QC").mkdir(parents=True, exist_ok=True)
            (ladders_root / "Master" / "Initial" / "alpha.sdoc").write_text(
                "alpha",
                encoding="utf-8",
            )
            (report_root / "Master" / "Initial" / "report_of_test-sgn.pdf").write_bytes(
                b"%PDF-1.4\n%fake",
                )
            (report_root / "Master" / "QC" / "report_of_test-sgn.pdf").write_bytes(
                b"%PDF-1.4\n%fake",
            )

            context = ValidationContext(project_path=root)
            context.add_folder("1. Ladders", ladders_root)
            context.add_folder("4. Test Report", report_root)
            context.add_discovered_path("Master/Initial", ladders_root / "Master" / "Initial")
            context.add_discovered_path("Master/QC", ladders_root / "Master" / "QC")

            validator = DocumentValidator(
                ValidationStep.TEST_REPORT,
                "4. Test Report",
                FileSearchService(),
                FileReaderService(),
                SignatureReaderService(),
            )
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)


if __name__ == "__main__":
    unittest.main()
