from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel
from reports.report_model import ReportDataModel
from reports.report_window import ReportWindow

from core.validation_result import ValidationResult
from core.validation_step import ValidationStatus, ValidationStep
from core.validation_summary import ValidationSummary


def test_report_window_refreshes_from_new_report_model() -> None:
    QApplication.instance() or QApplication([])

    old_summary = ValidationSummary(
        project_path=Path("/tmp/old-project"),
        started_at=__import__("datetime").datetime(2024, 1, 1, 10, 0, 0),
        finished_at=__import__("datetime").datetime(2024, 1, 1, 10, 0, 5),
        results=[
            ValidationResult(
                step=ValidationStep.FOLDER_STRUCTURE,
                status=ValidationStatus.PASS,
                reason="All required folders are present.",
                details={},
            )
        ],
    )
    new_summary = ValidationSummary(
        project_path=Path("/tmp/new-project"),
        started_at=__import__("datetime").datetime(2024, 1, 2, 10, 0, 0),
        finished_at=__import__("datetime").datetime(2024, 1, 2, 10, 0, 7),
        results=[
            ValidationResult(
                step=ValidationStep.FOLDER_STRUCTURE,
                status=ValidationStatus.FAIL,
                reason="Missing required folders.",
                details={"missing_folders": ["1. Ladders"]},
            )
        ],
    )

    window = ReportWindow(ReportDataModel.from_summary(old_summary))
    window.set_data_model(ReportDataModel.from_summary(new_summary))

    labels = [label.text() for label in window.findChildren(QLabel)]
    assert any("/tmp/new-project" in label for label in labels if label)
    assert not any("/tmp/old-project" in label for label in labels if label)
