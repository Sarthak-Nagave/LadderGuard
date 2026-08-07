"""
models.signature_info
=====================

Represents section-level signature validation for a signed document page.

This model is immutable and is shared between the SignatureReaderService,
DocumentValidator and ReportGenerator.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SignatureInfo:
    """
    Stores validation information for one required signing section on a page.

    Attributes
    ----------
    section_name
        Canonical section label (for example, ``Prepared By``).

    page_number
        1-based page number when relevant.

    section_found
        True when the required section heading is present on the page.

    printed_name
        Extracted printed name for the section, if available.

    printed_name_found
        True when a non-empty printed name exists for the section.

    digital_signature_found
        True when a signed PDF signature widget exists for the section.

    require_printed_name
        True when printed name is part of pass/fail rules for this section.

    reason
        Failure reason for this section/page, if any.
    """

    section_name: str

    page_number: int | None

    section_found: bool = False

    printed_name: str = ""

    printed_name_found: bool = False

    digital_signature_found: bool = False

    require_printed_name: bool = True

    reason: str | None = None

    @property
    def is_valid(self) -> bool:
        """
        Returns True only when section, printed name and signature are present.
        """
        printed_name_ok = self.printed_name_found if self.require_printed_name else True
        return self.section_found and printed_name_ok and self.digital_signature_found

    @property
    def status(self) -> str:
        return "PASS" if self.is_valid else "FAIL"

    def to_dict(self) -> dict:
        """
        Convert the model into a serializable dictionary.
        """
        return {
            "section_name": self.section_name,
            "page_number": self.page_number,
            "section_found": self.section_found,
            "printed_name": self.printed_name,
            "printed_name_found": self.printed_name_found,
            "digital_signature_found": self.digital_signature_found,
            "require_printed_name": self.require_printed_name,
            "reason": self.reason,
            "status": self.status,
            "is_valid": self.is_valid,
        }