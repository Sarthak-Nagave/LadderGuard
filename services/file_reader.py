"""
services.file_reader
====================

Provides a unified interface for reading supported document types.

Responsibilities
----------------
- Validate file existence.
- Validate supported file types.
- Dispatch the file to the appropriate reader.
- Return extracted text content.

This service contains no business validation logic.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

from __future__ import annotations

from pathlib import Path

from config import SUPPORTED_DOCUMENT_EXTENSIONS
from exceptions.file_not_found_error import FileNotFoundValidationError
from services.pdf_reader import PdfReaderService


class FileReaderService:
    """
    Reads supported project documents.

    Currently supported:
        - PDF

    The design allows future support for DOC, DOCX, XLS and XLSX
    without modifying validators.
    """

    def __init__(self) -> None:
        self._pdf_reader = PdfReaderService()

    def read(self, file_path: Path) -> str:
        """
        Read a supported document.

        Parameters
        ----------
        file_path
            Path to the document.

        Returns
        -------
        str
            Extracted textual content.

        Raises
        ------
        FileNotFoundError
            If the file does not exist.

        ValueError
            If the file type is unsupported.
        """

        if not file_path.exists():
            raise FileNotFoundValidationError(
                f"File not found: {file_path}"
            )

        extension = file_path.suffix.lower()

        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            raise ValueError(
                f"Unsupported document type: {extension}"
            )

        if extension == ".pdf":
            return self._pdf_reader.read(file_path)

        raise ValueError(
            f"No reader registered for '{extension}'."
        )