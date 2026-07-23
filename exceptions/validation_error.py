"""
exceptions.validation_error
===========================

Base exception for all validation-related errors.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from pathlib import Path


class ValidationError(Exception):
    """
    Base exception raised during project validation.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        if self.path is None:
            return self.message

        return f"{self.message} ({self.path})"