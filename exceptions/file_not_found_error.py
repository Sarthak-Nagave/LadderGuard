"""
exceptions.file_not_found_error
===============================

Raised when an expected project file or folder
cannot be found.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from pathlib import Path

from exceptions.validation_error import ValidationError


class FileNotFoundValidationError(ValidationError):
    """
    Raised when an expected file or folder is missing.
    """

    def __init__(
        self,
        path: Path,
        expected: str,
    ) -> None:
        self.expected = expected

        super().__init__(
            f"Expected {expected} not found.",
            path=path,
        )