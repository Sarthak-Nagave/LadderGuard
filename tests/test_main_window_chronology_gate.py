from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from core.validation_result import ValidationResult
from core.validation_step import ValidationStatus, ValidationStep
from core.validation_summary import ValidationSummary
from gui.main_window import MainWindow


class MainWindowChronologyGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_chronology_requires_validation_before_opening_dialog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            window = MainWindow()
            window.project_path = project_root

            with patch("gui.main_window.QMessageBox.information") as info_mock, patch(
                "gui.main_window.ChronologyDialog"
            ) as dialog_mock:
                window.on_generate_chronology()

                info_mock.assert_called_once()
                args = info_mock.call_args[0]
                self.assertEqual(args[1], "Validation Required")
                self.assertIn("Please validate the generated Operational Package", args[2])
                dialog_mock.assert_not_called()

            window.close()

    def test_chronology_opens_with_crc_records_after_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            summary = ValidationSummary(
                project_path=project_root,
                started_at=datetime.now(),
                finished_at=datetime.now(),
                results=[
                    ValidationResult(
                        step=ValidationStep.BIN_FILES,
                        status=ValidationStatus.PASS,
                        reason="ok",
                        details={
                            "bin_crcs": {
                                "Master/Initial": {
                                    "status": "PASS",
                                    "bin_crc": "A3F91C7E",
                                    "bin_file": str(project_root / "2. Bin File" / "Master" / "Initial" / "FW.bin"),
                                    "bin_name": "FW.bin",
                                }
                            }
                        },
                    )
                ],
            )

            window = MainWindow()
            window.project_path = project_root
            window._validation_summaries_by_project[window._project_key(project_root)] = summary

            with patch("gui.main_window.ChronologyDialog") as dialog_mock:
                dialog_instance = MagicMock()
                dialog_instance.property.return_value = False
                dialog_mock.return_value = dialog_instance

                window.on_generate_chronology()

                dialog_mock.assert_called_once()
                kwargs = dialog_mock.call_args.kwargs
                self.assertEqual(kwargs["project_folder"], project_root)
                self.assertIn("validation_bin_crc_records", kwargs)
                self.assertIn("Master/Initial", kwargs["validation_bin_crc_records"])
                dialog_instance.exec.assert_called_once()

            window.close()

    def test_all_failed_crc_validation_shows_no_chronology_notification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            summary = ValidationSummary(
                project_path=project_root,
                started_at=datetime.now(),
                finished_at=datetime.now(),
                results=[
                    ValidationResult(
                        step=ValidationStep.BIN_FILES,
                        status=ValidationStatus.FAIL,
                        reason="CRC comparison failed",
                        details={
                            "bin_crcs": {
                                "Master/Initial": {
                                    "status": "FAILED",
                                    "reason": "CRC Mismatch",
                                    "bin_file": str(project_root / "2. Bin File" / "Master" / "Initial" / "FW.bin"),
                                    "bin_name": "FW.bin",
                                }
                            }
                        },
                    )
                ],
            )

            window = MainWindow()
            window.project_path = project_root
            window._validation_summaries_by_project[window._project_key(project_root)] = summary

            with patch("gui.main_window.QMessageBox.information") as info_mock, patch(
                "gui.main_window.ChronologyDialog"
            ) as dialog_mock:
                window.on_generate_chronology()

                info_mock.assert_called_once()
                args = info_mock.call_args[0]
                self.assertEqual(args[1], "No Chronology Generated")
                self.assertIn("All firmware folders failed CRC validation.", args[2])
                dialog_mock.assert_not_called()

            window.close()


if __name__ == "__main__":
    unittest.main()
