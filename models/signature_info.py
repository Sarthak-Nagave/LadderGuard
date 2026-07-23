"""
models.signature_info
=====================

Represents the validation result of a required signer within a signed
document.

This model is immutable and is shared between the SignatureReaderService,
DocumentValidator and ReportGenerator.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True, frozen=True)
class SignatureInfo:
    """
    Stores validation information for a single required signer.

    Attributes
    ----------
    signer_name
        Expected signer name.

    name_found
        True if the signer's name exists in the document.

    signature_found
        True if a digital signature belonging to the signer exists.

    signed_at
        Signing timestamp if available.

    certificate
        Certificate or issuer information if available.
    """

    signer_name: str

    name_found: bool = False

    signature_found: bool = False

    signed_at: Optional[str] = None

    certificate: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """
        Returns True only when both the name and digital signature exist.
        """
        return self.name_found and self.signature_found

    def to_dict(self) -> dict:
        """
        Convert the model into a serializable dictionary.
        """
        return {
            "signer_name": self.signer_name,
            "name_found": self.name_found,
            "signature_found": self.signature_found,
            "signed_at": self.signed_at,
            "certificate": self.certificate,
            "is_valid": self.is_valid,
        }