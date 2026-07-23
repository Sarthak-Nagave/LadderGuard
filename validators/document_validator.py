"""
validators.document_validator
=============================

Generic validator for signed engineering documents.

A single instance validates one configured document folder.

Example
-------
DocumentValidator(
    step=ValidationStep.OPERATIONAL_FLOW,
    folder_name="3. Operational Flow",
)

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from pathlib import Path

from config import (
    EXPECTED_SIGNED_DOCUMENTS,
    REQUIRED_SIGNERS,
    SIGNED_DOCUMENT_SUFFIX,
)

from core.base_validator import BaseValidator
from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStep

from models.signature_info import SignatureInfo

from services.file_reader import FileReaderService
from services.file_search import FileSearchService
from services.signature_reader import SignatureReaderService


class DocumentValidator(BaseValidator):
    """
    Generic validator for a single signed document folder.
    """

    def __init__(
        self,
        step: ValidationStep,
        folder_name: str,
        file_search: FileSearchService,
        file_reader: FileReaderService,
        signature_reader: SignatureReaderService,
    ) -> None:

        super().__init__(step)

        self._folder_name = folder_name
        self._file_search = file_search
        self._file_reader = file_reader
        self._signature_reader = signature_reader

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def validate(
        self,
        context: ValidationContext,
    ) -> ValidationResult:

        self.logger.info(
            f"Validating '{self._folder_name}'."
        )
        self._write_debug_log(f"Starting validation for folder={self._folder_name}")

        folder = context.folders.get(
            self._folder_name,
        )

        if folder is None:
            self._write_debug_log(f"Folder missing: {self._folder_name}")
            return self.skipped_result(
                reason=f"Folder '{self._folder_name}' is unavailable.",
            )

        self._write_debug_log(f"Folder exists: {folder}")

        try:
            document = self._discover_document(
                folder,
            )
        except RuntimeError as exc:
            self._write_debug_log(f"Discovery failed: {exc}")
            return self.fail_result(
                reason=str(exc),
                checked_path=folder,
            )

        context.add_document(
            self._folder_name,
            document,
        )

        self.logger.info(
            f"Found signed document: {document.name}"
        )
        self._write_debug_log(f"Signed document discovered: {document}")

        try:

            document_text = self._file_reader.read(
                document,
            )

        except Exception as exc:
            self._write_debug_log(f"Read failed: {exc}")
            return self.fail_result(
                reason=f"Unable to read '{document.name}'.",
                checked_path=document,
                details={
                    "exception": str(exc),
                },
            )

        try:

            signatures = self._signature_reader.read(
                document,
            )

        except Exception as exc:
            self._write_debug_log(f"Signature inspection failed: {exc}")
            return self.fail_result(
                reason=f"Unable to inspect signatures in '{document.name}'.",
                checked_path=document,
                details={
                    "exception": str(exc),
                },
            )

        context.add_signature(
            self._folder_name,
            signatures,
        )
        self._write_debug_log(f"SignatureReader output for {document.name}: {[s.to_dict() for s in signatures]}")

        signer_results = self._validate_signers(
            document_text=document_text,
            signatures=signatures,
        )

        passed = all(
            signer.is_valid
            for signer in signer_results
        )
        self._write_debug_log(f"Signer results before final decision: {[s.to_dict() for s in signer_results]}")
        self._write_debug_log(f"Passed condition result: {passed}")

        details = {
            "document": document.name,
            "signers": [
                signer.to_dict()
                for signer in signer_results
            ],
        }

        if passed:
            self._write_debug_log("Final decision: PASS")

            self.logger.info(
                f"{self._folder_name} validated successfully."
            )

            return self.pass_result(
                reason=f"{self._folder_name} validated successfully.",
                checked_path=document,
                details=details,
            )

        detailed_reasons = []
        for signer in signer_results:
            if not signer.name_found:
                detailed_reasons.append(f"Required signer '{signer.signer_name}' not found.")
            elif not signer.signature_found:
                detailed_reasons.append(f"Adobe Digital Signature missing for '{signer.signer_name}'.")

        self.logger.warning(
            f"{self._folder_name} validation failed."
        )
        self._write_debug_log("Final decision: FAIL")

        return self.fail_result(
            reason="; ".join(detailed_reasons) if detailed_reasons else f"{self._folder_name} validation failed.",
            checked_path=document,
            details=details,
        )

    # ---------------------------------------------------------
    # Private Helpers
    # ---------------------------------------------------------

    def _discover_document(
        self,
        folder: Path,
    ) -> Path:
        """
        Discover the signed document inside the configured folder.

        Returns
        -------
        Path

        Raises
        ------
        RuntimeError
            If the document is missing or multiple signed
            documents are found.
        """

        documents = self._file_search.recursive_files(
            folder,
            ".pdf",
        )

        signed_documents = [

            document

            for document in documents

            if document.is_file()
            and SIGNED_DOCUMENT_SUFFIX.lower()
            in document.stem.lower()

        ]

        if len(signed_documents) == 0:

            raise RuntimeError(
                f"No signed document found in '{folder.name}'."
            )

        if len(signed_documents) != EXPECTED_SIGNED_DOCUMENTS:

            raise RuntimeError(
                f"Expected {EXPECTED_SIGNED_DOCUMENTS} signed "
                f"document but found {len(signed_documents)}."
            )

        return signed_documents[0]

    # ---------------------------------------------------------

    def _validate_signers(
        self,
        document_text: str,
        signatures: list[SignatureInfo],
    ) -> list[SignatureInfo]:
        """
        Validate every required signer.

        Parameters
        ----------
        document_text
            Extracted PDF text.

        signatures
            Digital signatures discovered inside the PDF.

        Returns
        -------
        list[SignatureInfo]
        """

        validated: list[SignatureInfo] = []

        for required_signer in REQUIRED_SIGNERS:

            signature = self._find_signature(
                signatures,
                required_signer,
            )

            name_found = bool(
                signature
                and signature.name_found
            )

            signature_found = bool(
                signature
                and signature.signature_found
            )

            self.logger.debug(
                "Signer '%s' | text_match=%s | signature_match=%s",
                required_signer,
                name_found,
                signature_found,
            )

            validated.append(

                SignatureInfo(

                    signer_name=required_signer,

                    name_found=name_found,

                    signature_found=signature_found,

                    signed_at=(
                        signature.signed_at
                        if signature
                        else None
                    ),

                    certificate=(
                        signature.certificate
                        if signature
                        else None
                    ),

                )

            )

        return validated

    def _write_debug_log(self, message: str) -> None:
        """Append a line to the validator debug log for the real package run."""
        log_path = Path(__file__).with_name('document_validator_debug.log')
        with log_path.open('a', encoding='utf-8') as handle:
            handle.write(message + '\n')
    
    # ---------------------------------------------------------

    @staticmethod
    def _find_signature(
        signatures: list[SignatureInfo],
        signer_name: str,
    ) -> SignatureInfo | None:
        """
        Find a required signer from the extracted signatures.

        Parameters
        ----------
        signatures
            Signature information extracted from the PDF.

        signer_name
            Required signer.

        Returns
        -------
        SignatureInfo | None
        """

        signer_name = signer_name.lower()

        for signature in signatures:

            if signature.signer_name.lower() == signer_name:
                return signature

        return None

    # ---------------------------------------------------------

    def _build_validation_details(
        self,
        document: Path,
        signer_results: list[SignatureInfo],
    ) -> dict:
        """
        Build validation details for reporting.

        Parameters
        ----------
        document
            Validated document.

        signer_results
            Validation results for all required signers.

        Returns
        -------
        dict
        """

        return {
            "folder": self._folder_name,
            "document": document.name,
            "overall_status": all(
                signer.is_valid
                for signer in signer_results
            ),
            "validated_signers": len(REQUIRED_SIGNERS),
            "passed_signers": sum(
                signer.is_valid
                for signer in signer_results
            ),
            "failed_signers": sum(
                not signer.is_valid
                for signer in signer_results
            ),
            "signers": [
                signer.to_dict()
                for signer in signer_results
            ],
        }

    # ---------------------------------------------------------

    def _log_validation(
        self,
        document: Path,
        signer_results: list[SignatureInfo],
    ) -> None:
        """
        Log validation summary.
        """

        self.logger.info(
            f"Document : {document.name}"
        )

        for signer in signer_results:

            if signer.is_valid:

                self.logger.info(
                    f"[PASS] {signer.signer_name}"
                )

            else:

                self.logger.warning(
                    f"[FAIL] {signer.signer_name}"
                )

                if not signer.name_found:

                    self.logger.warning(
                        f"Name not found : {signer.signer_name}"
                    )

                if not signer.signature_found:

                    self.logger.warning(
                        f"Digital signature not found : "
                        f"{signer.signer_name}"
                    )

    # ---------------------------------------------------------

    def _validate_document(
        self,
        document: Path,
        document_text: str,
        signatures: list[SignatureInfo],
    ) -> tuple[bool, dict]:
        """
        Complete validation workflow.

        Returns
        -------
        tuple[bool, dict]
        """

        signer_results = self._validate_signers(
            document_text=document_text,
            signatures=signatures,
        )

        self._log_validation(
            document,
            signer_results,
        )

        details = self._build_validation_details(
            document,
            signer_results,
        )

        return (
            all(
                signer.is_valid
                for signer in signer_results
            ),
            details,
        )