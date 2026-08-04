import tempfile
import time
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

    def test_ladder_validator_ignores_nested_sdoc_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ladders_root = root / "1. Ladders"
            stage = ladders_root / "Master" / "Initial"
            (stage / "Backup").mkdir(parents=True, exist_ok=True)
            (stage / "GRP").mkdir(parents=True, exist_ok=True)
            (stage / "LD_Project_V1.00.sdoc").write_text(
                "top-level",
                encoding="utf-8",
            )
            (stage / "Backup" / "Test.sdoc").write_text(
                "ignored",
                encoding="utf-8",
            )
            (stage / "GRP" / "Nested.sdoc").write_text(
                "ignored",
                encoding="utf-8",
            )

            context = ValidationContext(project_path=root)
            context.add_folder("1. Ladders", ladders_root)

            validator = LadderValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(
                context.ladder_files["Master/Initial"].name,
                "LD_Project_V1.00.sdoc",
            )

    def test_ladder_validator_fails_for_multiple_top_level_sdocs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ladders_root = root / "1. Ladders"
            stage = ladders_root / "Master" / "Initial"
            stage.mkdir(parents=True, exist_ok=True)
            (stage / "alpha.sdoc").write_text("alpha", encoding="utf-8")
            (stage / "beta.sdoc").write_text("beta", encoding="utf-8")

            context = ValidationContext(project_path=root)
            context.add_folder("1. Ladders", ladders_root)

            validator = LadderValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.FAIL)
            self.assertIn("Master/Initial has multiple .sdoc files.", result.reason)

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

            # Master/Initial -> make latest Ladder and latest Bin match.
            old_ladder_initial = ladders_root / "Master" / "Initial" / "alpha_old.bin"
            new_ladder_initial = ladders_root / "Master" / "Initial" / "alpha_new.bin"
            old_bin_initial = bin_root / "Master" / "Initial" / "alpha_old.bin"
            new_bin_initial = bin_root / "Master" / "Initial" / "alpha_new.bin"
            old_ladder_initial.write_bytes(b"old")
            old_bin_initial.write_bytes(b"old")
            time.sleep(0.01)
            new_ladder_initial.write_bytes(b"same-latest")
            new_bin_initial.write_bytes(b"same-latest")

            # Master/QC -> single matching files.
            qc_ladder = ladders_root / "Master" / "QC" / "beta.bin"
            qc_bin = bin_root / "Master" / "QC" / "beta.bin"
            qc_ladder.write_bytes(b"qc")
            qc_bin.write_bytes(b"qc")

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
            self.assertIn("Master/Initial", context.bin_files)
            self.assertEqual(context.bin_files["Master/Initial"].name, "alpha_new.bin")

    def test_bin_validator_fails_when_discovered_paths_are_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_root = root / "2. Bin File"
            bin_root.mkdir(parents=True, exist_ok=True)

            context = ValidationContext(project_path=root)
            context.add_folder("2. Bin File", bin_root)

            validator = BinValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.FAIL)
            self.assertIn("No firmware folders were discovered before BIN validation.", result.reason)
            self.assertIn("stage_errors", result.details)

    def test_bin_validator_reports_missing_firmware_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_root = root / "2. Bin File"
            bin_root.mkdir(parents=True, exist_ok=True)

            context = ValidationContext(project_path=root)
            context.add_folder("2. Bin File", bin_root)
            context.add_discovered_path("Master/Initial", root / "1. Ladders" / "Master" / "Initial")

            validator = BinValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.FAIL)
            self.assertIn("Master/Initial: Firmware folder not found in Bin File folder.", result.reason)
            self.assertIn("stage_errors", result.details)

    def test_bin_validator_ignores_nested_bin_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_root = root / "2. Bin File"
            stage = bin_root / "Master" / "Initial"
            (stage / "Backup").mkdir(parents=True, exist_ok=True)
            (stage / "firmware.bin").write_bytes(b"direct")
            (stage / "Backup" / "nested.bin").write_bytes(b"nested")

            context = ValidationContext(project_path=root)
            context.add_folder("2. Bin File", bin_root)
            context.add_discovered_path("Master/Initial", root / "1. Ladders" / "Master" / "Initial")

            validator = BinValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertEqual(context.bin_files["Master/Initial"].name, "firmware.bin")

    def test_bin_validator_fails_when_only_nested_bin_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_root = root / "2. Bin File"
            stage = bin_root / "Master" / "Initial"
            (stage / "Backup").mkdir(parents=True, exist_ok=True)
            (stage / "Backup" / "nested.bin").write_bytes(b"nested")

            context = ValidationContext(project_path=root)
            context.add_folder("2. Bin File", bin_root)
            context.add_discovered_path("Master/Initial", root / "1. Ladders" / "Master" / "Initial")

            validator = BinValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.FAIL)
            self.assertIn("Master/Initial: No BIN file found in Bin File folder.", result.reason)

    def test_bin_validator_keeps_report_contract_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_root = root / "2. Bin File"
            stage = bin_root / "Master" / "Initial"
            stage.mkdir(parents=True, exist_ok=True)
            (stage / "firmware.bin").write_bytes(b"abc")

            context = ValidationContext(project_path=root)
            context.add_folder("2. Bin File", bin_root)
            context.add_discovered_path("Master/Initial", root / "1. Ladders" / "Master" / "Initial")

            validator = BinValidator(FileSearchService())
            result = validator.validate(context)

            self.assertEqual(result.status, ValidationStatus.PASS)
            self.assertIn("bin_crcs", result.details)
            self.assertIn("bin_files", result.details)

            stage_crc = result.details["bin_crcs"]["Master/Initial"]
            self.assertIn("bin_file", stage_crc)
            self.assertIn("bin_name", stage_crc)
            self.assertIn("crc", stage_crc)
            self.assertEqual(stage_crc["bin_name"], "firmware.bin")

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
