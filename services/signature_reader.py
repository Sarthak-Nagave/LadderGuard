"""
services.signature_reader
=========================

Provides PDF digital signature inspection for the Operational Package
Validator.

Responsibilities
----------------
- Detect whether a PDF contains digital signatures.
- Extract signer metadata where available.
- Match discovered signatures with required signers.
- Return structured SignatureInfo objects.
- Never perform business validation.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

import asn1crypto.cms as cms
import fitz

from config import (
    CASE_SENSITIVE_SIGNER_MATCH,
    REQUIRED_SIGNERS,
)

from exceptions.file_not_found_error import FileNotFoundValidationError
from models.signature_info import SignatureInfo
from services.logger import LoggerService


class SignatureReaderService:
    """
    Reads digital signature metadata from PDF documents.

    Notes
    -----
    This service extracts signer metadata from signed PDF signature
    dictionaries. It does not perform certificate trust validation.
    """

    logger = LoggerService.get_logger()

    _SIGNER_PATTERN = re.compile(rb"CN=([^,\r\n]+)", re.IGNORECASE)
    _DN_PATTERN = re.compile(rb"DN:\s*([^\r\n]+)", re.IGNORECASE)
    _DATE_PATTERN = re.compile(
        rb"Date:\s*([0-9]{4}\.[0-9]{2}\.[0-9]{2} \d{2}:\d{2}:\d{2} [+\-]\d{2}'\d{2}')"
    )
    _CONTENTS_PATTERN = re.compile(rb"/Contents\s*<([0-9A-Fa-f\s]+)>", re.DOTALL)
    _VREF_PATTERN = re.compile(rb"/V\s+(\d+)\s+0\s+R")

    @classmethod
    def read(
        cls,
        file_path: Path,
    ) -> list[SignatureInfo]:
        """
        Read digital signatures from a PDF.

        Parameters
        ----------
        file_path
            PDF document.

        Returns
        -------
        list[SignatureInfo]
            Validation information for every required signer.

        Raises
        ------
        FileNotFoundError
            If the PDF does not exist.

        RuntimeError
            If the PDF cannot be inspected.
        """

        if not file_path.exists():
            raise FileNotFoundValidationError(
                f"PDF not found: {file_path}"
            )

        cls.logger.info(
            f"Inspecting PDF signatures: {file_path.name}"
        )

        document = fitz.open(file_path)

        try:
            discovered_signers: dict[str, SignatureInfo] = {}

            for page in document:
                widgets = page.widgets()

                if widgets is None:
                    continue

                for widget in widgets:
                    if getattr(widget, "field_type", None) != fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        continue

                    if not getattr(widget, "is_signed", False):
                        continue

                    signature_bytes = cls._extract_signature_bytes(document, widget)
                    signer = cls._parse_signer_name(signature_bytes)
                    signing_time = cls._parse_signing_time(signature_bytes)
                    certificate = cls._parse_certificate_summary(signature_bytes)

                    if not signer:
                        continue

                    lookup = (
                        signer
                        if CASE_SENSITIVE_SIGNER_MATCH
                        else signer.casefold()
                    )

                    discovered_signers.setdefault(
                        lookup,
                        SignatureInfo(
                            signer_name=signer,
                            name_found=True,
                            signature_found=True,
                            signed_at=signing_time,
                            certificate=certificate,
                        ),
                    )

            signatures: list[SignatureInfo] = []

            for required_signer in REQUIRED_SIGNERS:
                lookup = (
                    required_signer
                    if CASE_SENSITIVE_SIGNER_MATCH
                    else required_signer.casefold()
                )
                matched = discovered_signers.get(lookup)

                signatures.append(
                    SignatureInfo(
                        signer_name=required_signer,
                        name_found=matched is not None,
                        signature_found=matched is not None,
                        signed_at=matched.signed_at if matched else None,
                        certificate=matched.certificate if matched else None,
                    )
                )

            cls.logger.info(
                f"Validated {len(signatures)} required signer(s)."
            )

            return signatures

        except Exception as exc:
            cls.logger.exception(exc)
            raise RuntimeError(
                f"Unable to inspect signatures in '{file_path.name}'."
            ) from exc

        finally:
            document.close()

    @classmethod
    def _extract_signature_bytes(
        cls,
        document: fitz.Document,
        widget: fitz.Widget,
    ) -> bytes:
        raw = cls._get_xref_bytes(document, widget.xref)
        if not raw:
            return b""

        vref_match = cls._VREF_PATTERN.search(raw)
        if not vref_match:
            return b""

        try:
            vref = int(vref_match.group(1))
        except ValueError:
            return b""

        vobj = cls._get_xref_bytes(document, vref)
        if not vobj:
            return b""

        contents_match = cls._CONTENTS_PATTERN.search(vobj)
        if not contents_match:
            return b""

        hex_value = re.sub(rb"\s+", b"", contents_match.group(1))
        try:
            return bytes.fromhex(hex_value.decode("ascii", errors="ignore"))
        except ValueError:
            return b""

    @classmethod
    def _get_xref_bytes(
        cls,
        document: fitz.Document,
        xref: int,
    ) -> bytes:
        try:
            xref_object = document.xref_object(xref)
        except Exception:
            return b""

        if isinstance(xref_object, bytes):
            return xref_object

        return str(xref_object).encode("latin1", errors="ignore")

    @classmethod
    def _parse_signer_name(
        cls,
        signature_bytes: bytes,
    ) -> str | None:
        if not signature_bytes:
            return None

        signer_name = cls._parse_name_from_certificate(signature_bytes)
        if signer_name:
            return signer_name

        signature_text = signature_bytes.decode("utf-8", errors="ignore")
        for required_signer in REQUIRED_SIGNERS:
            if required_signer in signature_text:
                return required_signer

        dn_match = cls._DN_PATTERN.search(signature_bytes)
        if dn_match:
            dn = dn_match.group(1).decode("utf-8", errors="ignore")
            cn_match = re.search(r"CN=([^,]+)", dn)
            if cn_match:
                return cn_match.group(1).strip()

        return None

    @classmethod
    def _parse_name_from_certificate(
        cls,
        signature_bytes: bytes,
    ) -> str | None:
        try:
            content_info = cms.ContentInfo.load(signature_bytes)
            if content_info["content_type"].native != "signed_data":
                return None

            signed_data = content_info["content"]
            for cert_choice in signed_data["certificates"] or []:
                if cert_choice.name != "certificate":
                    continue

                subject = cert_choice.chosen.subject
                common_name = subject.native.get("common_name")
                if isinstance(common_name, str) and common_name.strip():
                    return common_name.strip()

                if hasattr(subject, "human_friendly"):
                    return subject.human_friendly
        except Exception:
            return None

        return None

    @classmethod
    def _parse_signing_time(
        cls,
        signature_bytes: bytes,
    ) -> str | None:
        if not signature_bytes:
            return None

        try:
            content_info = cms.ContentInfo.load(signature_bytes)
            if content_info["content_type"].native == "signed_data":
                signed_data = content_info["content"]
                for signer_info in signed_data["signer_infos"] or []:
                    signed_attrs = signer_info["signed_attrs"]
                    if signed_attrs is None:
                        continue

                    for attr in signed_attrs:
                        if attr["type"].native == "signing_time":
                            values = attr["values"]
                            if values:
                                signed_at = values[0].native
                                if isinstance(signed_at, datetime.datetime):
                                    if signed_at.tzinfo is None:
                                        signed_at = signed_at.replace(tzinfo=datetime.timezone.utc)
                                    return signed_at.strftime("%Y.%m.%d %H:%M:%S %z")
                                return str(signed_at)
        except Exception:
            pass

        match = cls._DATE_PATTERN.search(signature_bytes)
        if match:
            return match.group(1).decode("ascii", errors="ignore").strip()

        custom_match = re.search(rb"/M\s*\(([^)]+)\)", signature_bytes)
        if custom_match:
            return custom_match.group(1).decode("utf-8", errors="ignore").strip()

        return None

    @classmethod
    def _parse_certificate_summary(
        cls,
        signature_bytes: bytes,
    ) -> str | None:
        if not signature_bytes:
            return None

        try:
            content_info = cms.ContentInfo.load(signature_bytes)
            if content_info["content_type"].native == "signed_data":
                signed_data = content_info["content"]
                for cert_choice in signed_data["certificates"] or []:
                    if cert_choice.name != "certificate":
                        continue
                    subject = cert_choice.chosen.subject
                    if hasattr(subject, "human_friendly"):
                        return subject.human_friendly
                    return str(subject.native)
        except Exception:
            pass

        dn_match = cls._DN_PATTERN.search(signature_bytes)
        if dn_match:
            return dn_match.group(1).decode("utf-8", errors="ignore").strip()

        return None