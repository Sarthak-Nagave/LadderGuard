"""
services.pdf_reader
===================

Provides PDF text extraction functionality for the Operational Package
Validator.

Responsibilities
----------------
- Open PDF documents.
- Validate PDF integrity.
- Detect encrypted PDFs.
- Extract text from all pages.
- Return normalized text.

This module contains no business validation logic.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from loguru import logger

from exceptions.file_not_found_error import FileNotFoundValidationError


class PdfReaderService:
    """
    Service responsible for reading PDF documents.
    """

    @staticmethod
    def read(file_path: Path) -> str:
        """
        Extract text from a PDF document.

        Parameters
        ----------
        file_path
            PDF file to read.

        Returns
        -------
        str
            Complete extracted text.

        Raises
        ------
        FileNotFoundError
            If the PDF does not exist.

        PermissionError
            If the PDF is encrypted.

        RuntimeError
            If the PDF cannot be processed.
        """

        if not file_path.exists():
            raise FileNotFoundValidationError(
                f"PDF not found: {file_path}"
            )

        logger.info(f"Reading PDF: {file_path}")

        try:
            document = fitz.open(file_path)

            if document.needs_pass:
                raise PermissionError(
                    f"Encrypted PDF: {file_path.name}"
                )

            extracted_text: list[str] = []

            for page in document:
                page_text = page.get_text("text")

                if page_text:
                    extracted_text.append(page_text)

            document.close()

            text = "\n".join(extracted_text)

            logger.info(
                f"Successfully extracted "
                f"{len(text)} characters from "
                f"{file_path.name}"
            )

            return text

        except PermissionError:
            raise

        except Exception as exc:
            logger.exception(exc)

            raise RuntimeError(
                f"Failed to process PDF '{file_path.name}'."
            ) from exc