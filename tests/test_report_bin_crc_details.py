from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reports.report_model import ReportDataModel

from core.validation_result import ValidationResult
from core.validation_step import ValidationStatus, ValidationStep
from core.validation_summary import ValidationSummary


def test_report_model_shows_ladder_and_bin_crc_details() -> None:
    summary = ValidationSummary(
        project_path=Path("C:/tmp/project"),
        started_at=datetime.now(),
        finished_at=datetime.now(),
        results=[
            ValidationResult(
                step=ValidationStep.BIN_FILES,
                status=ValidationStatus.FAIL,
                reason="CRC mismatch detected",
                details={
                    "bin_files": {
                        "Master/Initial": "C:/tmp/project/2. Bin File/Master/Initial/FW.bin",
                    },
                    "bin_crcs": {
                        "Master/Initial": {
                            "ladder_bin_name": "FW_LADDER.bin",
                            "ladder_crc": "A3F91C7E",
                            "bin_name": "FW_BIN.bin",
                            "bin_crc": "DEADBEEF",
                            "status": "FAILED",
                            "reason": "CRC Mismatch",
                        }
                    },
                },
            )
        ],
    )

    model = ReportDataModel.from_summary(summary)
    section = model.sections[0]
    card = section.details[0]

    row_map = {row.label: row.value for row in card.rows}
    assert row_map["Ladder BIN"] == "FW_LADDER.bin"
    assert row_map["Ladder CRC"] == "A3F91C7E"
    assert row_map["Bin File BIN"] == "FW_BIN.bin"
    assert row_map["Bin File CRC"] == "DEADBEEF"
    assert row_map["Validation Result"] == "FAILED"
    assert row_map["Reason"] == "CRC Mismatch"
