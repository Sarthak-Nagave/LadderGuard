"""
models.document_info
====================

Represents a validated engineering document.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from models.signature_info import SignatureInfo


@dataclass(slots=True)
class DocumentInfo:
    """
    Represents one engineering document.
    """

    folder_name: str

    file_path: Path

    document_name: str

    extension: str

    signed: bool = False

    extracted_text: str = ""

    signatures: list[SignatureInfo] = field(
        default_factory=list
    )

    validation_errors: list[str] = field(
        default_factory=list
    )

    @property
    def signer_count(self) -> int:
        return len(self.signatures)

    @property
    def valid_signature_count(self) -> int:
        return sum(
            signature.is_valid
            for signature in self.signatures
        )

    @property
    def invalid_signature_count(self) -> int:
        return (
            self.signer_count
            - self.valid_signature_count
        )

    @property
    def is_valid(self) -> bool:
        """
        Returns True when the document has
        no validation errors and all
        required signatures are valid.
        """

        return (
            self.signed
            and not self.validation_errors
            and self.invalid_signature_count == 0
        )

    def add_error(
        self,
        message: str,
    ) -> None:
        """
        Add a validation error.
        """

        self.validation_errors.append(message)

    def to_dict(self) -> dict:
        return {
            "folder_name": self.folder_name,
            "document_name": self.document_name,
            "file_path": str(self.file_path),
            "extension": self.extension,
            "signed": self.signed,
            "is_valid": self.is_valid,
            "signer_count": self.signer_count,
            "valid_signature_count": self.valid_signature_count,
            "invalid_signature_count": self.invalid_signature_count,
            "validation_errors": self.validation_errors,
            "signatures": [
                signature.to_dict()
                for signature in self.signatures
            ],
        }