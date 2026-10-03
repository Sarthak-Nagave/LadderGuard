import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from core.validation_summary import ValidationSummary
from core.validation_result import ValidationResult
from core.validation_step import ValidationStep, ValidationStatus
from gui.main_window import MainWindow

@pytest.fixture
def main_window():
    # Ensure a QApplication exists
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
        
    window = MainWindow()
    return window

def create_mock_summary(tmp_path: Path, passed_count: int, bin_records: dict) -> ValidationSummary:
    """Helper to create a mock ValidationSummary with a specific number of passes."""
    summary = ValidationSummary(
        project_path=tmp_path,
        started_at=None,
        finished_at=None,
    )
    
    # We populate the results so summary.passed evaluates to passed_count
    # The tests assume total validation steps would be 7, so we create 7 results.
    # passed_count of them are PASS, the rest are FAIL.
    results = []
    for i in range(passed_count):
        results.append(ValidationResult(step=ValidationStep.FOLDER_STRUCTURE, status=ValidationStatus.PASS, details={}, reason=""))
        
    for i in range(7 - passed_count):
        results.append(ValidationResult(step=ValidationStep.FOLDER_STRUCTURE, status=ValidationStatus.FAIL, details={}, reason=""))

    # If there are bin records, we inject them into one of the results (we'll just use the first one or append one if list is empty)
    # But wait, main_window checks for ValidationStep.BIN_FILES to extract bin records.
    # Let's ensure at least one BIN_FILES result exists if we have records, or just replace the first one.
    if results:
        results[0].step = ValidationStep.BIN_FILES
        results[0].details = {"bin_crcs": bin_records}
    else:
        results.append(ValidationResult(step=ValidationStep.BIN_FILES, status=ValidationStatus.PASS, details={"bin_crcs": bin_records}, reason=""))

    summary.results = results
    return summary


def test_validation_not_run(main_window, tmp_path):
    main_window.project_path = tmp_path
    # No summary stored means validation not run
    
    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is False
    assert result["validation_completed"] is False
    assert "Validation has not been completed" in result["reason"]

def test_validation_0_7_crc_pass(main_window, tmp_path):
    main_window.project_path = tmp_path
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=0, bin_records={"Master": {"status": "PASS"}})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is False
    assert result["passed_count"] == 0
    assert result["crc_passed"] is True
    assert "0/7" in result["reason"]

def test_validation_5_7_crc_pass(main_window, tmp_path):
    main_window.project_path = tmp_path
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=5, bin_records={"Master": {"status": "PASS"}})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is False
    assert result["passed_count"] == 5
    assert result["crc_passed"] is True
    assert "5/7" in result["reason"]
    assert "resolve the failed validation steps" in result["reason"]

def test_validation_6_7_crc_pass(main_window, tmp_path):
    main_window.project_path = tmp_path
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=6, bin_records={"Master": {"status": "PASS"}})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is True
    assert result["passed_count"] == 6
    assert result["crc_passed"] is True

def test_validation_7_7_crc_pass(main_window, tmp_path):
    main_window.project_path = tmp_path
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=7, bin_records={"Master": {"status": "PASS"}})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is True
    assert result["passed_count"] == 7
    assert result["crc_passed"] is True

def test_validation_6_7_crc_fail(main_window, tmp_path):
    main_window.project_path = tmp_path
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=6, bin_records={"Master": {"status": "FAIL"}})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is False
    assert result["passed_count"] == 6
    assert result["crc_passed"] is False
    assert result["crc_completed"] is True
    assert "CRC status: FAIL" in result["reason"]

def test_validation_7_7_crc_fail(main_window, tmp_path):
    main_window.project_path = tmp_path
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=7, bin_records={"Master": {"status": "FAIL"}})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is False
    assert result["passed_count"] == 7
    assert result["crc_passed"] is False
    assert result["crc_completed"] is True
    assert "CRC status: FAIL" in result["reason"]

def test_validation_6_7_crc_not_run(main_window, tmp_path):
    main_window.project_path = tmp_path
    # No bin records at all means not run
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=6, bin_records={})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is False
    assert result["passed_count"] == 6
    assert result["crc_passed"] is False
    assert result["crc_completed"] is False
    assert "CRC status: Not completed" in result["reason"]

def test_validation_7_7_crc_not_run(main_window, tmp_path):
    main_window.project_path = tmp_path
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=7, bin_records={})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is False
    assert result["passed_count"] == 7
    assert result["crc_passed"] is False
    assert result["crc_completed"] is False
    assert "CRC status: Not completed" in result["reason"]

def test_validation_5_7_crc_fail(main_window, tmp_path):
    main_window.project_path = tmp_path
    summary = create_mock_summary(tmp_path=tmp_path, passed_count=5, bin_records={"Master": {"status": "FAIL"}})
    main_window._validation_summaries_by_project[main_window._project_key(main_window.project_path)] = summary

    result = main_window.check_chronology_prerequisites()
    assert result["allowed"] is False
    assert result["passed_count"] == 5
    assert result["crc_passed"] is False
    assert "Both chronology prerequisites must be satisfied" in result["reason"]
