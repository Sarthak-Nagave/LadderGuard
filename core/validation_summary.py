"""
core.validation_summary
=======================

Represents the complete outcome of a validation session.

This object is produced by ValidationEngine and consumed by
the GUI, report generator and future integrations.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.validation_result import ValidationResult
from core.validation_step import ValidationStatus


@dataclass(slots=True)
class ValidationSummary:
    """
    Represents the complete validation session.
    """

    project_path: Path

    started_at: datetime

    finished_at: datetime

    results: list[ValidationResult] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(
            r.status == ValidationStatus.PASS
            for r in self.results
        )

    @property
    def failed(self) -> int:
        return sum(
            r.status == ValidationStatus.FAIL
            for r in self.results
        )

    @property
    def warnings(self) -> int:
        return sum(
            r.status == ValidationStatus.WARNING
            for r in self.results
        )

    @property
    def skipped(self) -> int:
        return sum(
            r.status == ValidationStatus.SKIPPED
            for r in self.results
        )

    @property
    def duration_seconds(self) -> float:
        return (
            self.finished_at - self.started_at
        ).total_seconds()

    @property
    def success(self) -> bool:
        """
        True only if every validation passed.
        """
        return self.failed == 0

    @property
    def overall_status(self) -> ValidationStatus:
        """
        Overall validation status.
        """

        if self.failed:
            return ValidationStatus.FAIL

        if self.warnings:
            return ValidationStatus.WARNING

        return ValidationStatus.PASS