"""
exceptions.signature_error
==========================

Raised when document signature validation fails.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from pathlib import Path

from exceptions.validation_error import ValidationError


class SignatureValidationError(ValidationError):
    """
    Raised when required signatures are missing
    or invalid.
    """

    def __init__(
        self,
        message: str,
        *,
        signer: str | None = None,
        path: Path | None = None,
    ) -> None:
        self.signer = signer

        if signer:
            message = f"{message} [Signer: {signer}]"

        super().__init__(
            message,
            path=path,
        )