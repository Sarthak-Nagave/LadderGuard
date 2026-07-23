"""
core.validation_result
======================

Represents the result of a single validation step.

Every validator returns this object.

Author:
    Selec Controls R&D

Python:
    3.12+
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.validation_step import ValidationStatus, ValidationStep


@dataclass(slots=True)
class ValidationResult:
    """
    Represents one validation result.

    Attributes
    ----------
    step:
        Validation step.

    status:
        PASS / FAIL / WARNING / SKIPPED.

    reason:
        Human-readable explanation.

    checked_path:
        Folder or file that was validated.

    expected:
        Expected value.

    found:
        Actual detected value.

    details:
        Additional information.

    timestamp:
        Result creation time.
    """

    step: ValidationStep

    status: ValidationStatus

    reason: str

    checked_path: Path | None = None

    expected: Any | None = None

    found: Any | None = None

    details: dict[str, Any] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_passed(self) -> bool:
        """
        Returns True if validation passed.
        """
        return self.status == ValidationStatus.PASS

    @property
    def is_failed(self) -> bool:
        """
        Returns True if validation failed.
        """
        return self.status == ValidationStatus.FAIL

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the object into a serializable dictionary.
        """

        return {
            "step": str(self.step),
            "status": str(self.status),
            "reason": self.reason,
            "checked_path": (
                str(self.checked_path)
                if self.checked_path
                else None
            ),
            "expected": self.expected,
            "found": self.found,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    def __bool__(self) -> bool:
        """
        Allows:

            if result:

        Returns True only for PASS.
        """
        return self.is_passed