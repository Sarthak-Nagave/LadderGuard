"""
services.signature_reader
=========================

Provides PDF page-level signature extraction for section-based validation.

Responsibilities
----------------
- Read PDF pages and extract page text.
- Detect signed signature widgets on each page.
- Return page snapshots required by DocumentValidator.
- Never perform business validation.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

from exceptions.file_not_found_error import FileNotFoundValidationError
from services.logger import LoggerService


@dataclass(slots=True, frozen=True)
class PageTextLine:
    """One extracted text line with its vertical position."""

    text: str
    x0: float
    x1: float
    y0: float
    y1: float


@dataclass(slots=True, frozen=True)
class PageTextBlock:
    """One text block extracted from page.get_text("blocks") with coordinates."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(slots=True, frozen=True)
class PageOcrBlock:
    """One OCR block extracted with coordinates when OCR is available."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(slots=True, frozen=True)
class PageWord:
    """One word with coordinates for precise per-column extraction."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(slots=True, frozen=True)
class PageSignatureSnapshot:
    """Extracted page content required for signature section validation."""

    page_number: int
    page_height: float
    page_width: float
    lines: tuple[PageTextLine, ...]
    text_blocks: tuple[PageTextBlock, ...]
    signed_signature_rects: tuple[tuple[float, float, float, float], ...]
    image_rects: tuple[tuple[float, float, float, float], ...]
    vector_rects: tuple[tuple[float, float, float, float], ...]
    ocr_blocks: tuple[PageOcrBlock, ...]
    words: tuple[PageWord, ...]

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class SignatureReaderService:
    """
    Reads digital signature markers from PDF documents.

    Notes
    -----
    This service does not perform certificate trust validation.
    """

    logger = LoggerService.get_logger()

    @classmethod
    def read_page_snapshots(
        cls,
        file_path: Path,
    ) -> list[PageSignatureSnapshot]:
        """
        Read all pages and signed signature widgets from a PDF.

        Parameters
        ----------
        file_path
            PDF document.

        Returns
        -------
        list[PageSignatureSnapshot]
            Page text and signed signature widget geometry.

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
            snapshots: list[PageSignatureSnapshot] = []

            for page_index, page in enumerate(document):
                widgets = page.widgets()
                signed_signature_rects: list[tuple[float, float, float, float]] = []

                if widgets is not None:
                    for widget in widgets:
                        if getattr(widget, "field_type", None) != fitz.PDF_WIDGET_TYPE_SIGNATURE:
                            continue
                        if not getattr(widget, "is_signed", False):
                            continue

                        rect = getattr(widget, "rect", None)
                        if rect is None:
                            continue

                        signed_signature_rects.append(
                            (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
                        )

                text_blocks = cls._extract_text_blocks(page)
                image_rects = cls._extract_image_rects(page)
                vector_rects = cls._extract_vector_rects(page)
                ocr_blocks = cls._extract_ocr_blocks(page)
                words = cls._extract_words(page)

                snapshots.append(
                    PageSignatureSnapshot(
                        page_number=page_index + 1,
                        page_height=float(page.rect.height),
                        page_width=float(page.rect.width),
                        lines=cls._extract_page_lines(page),
                        text_blocks=text_blocks,
                        signed_signature_rects=tuple(signed_signature_rects),
                        image_rects=image_rects,
                        vector_rects=vector_rects,
                        ocr_blocks=ocr_blocks,
                        words=words,
                    )
                )

            cls.logger.info(
                f"Extracted signature snapshots for {len(snapshots)} page(s)."
            )

            return snapshots

        except Exception as exc:
            cls.logger.exception(exc)
            raise RuntimeError(
                f"Unable to inspect signatures in '{file_path.name}'."
            ) from exc

        finally:
            document.close()

    @classmethod
    def read(
        cls,
        file_path: Path,
    ) -> list[PageSignatureSnapshot]:
        """Backward-compatible wrapper returning page snapshots."""
        return cls.read_page_snapshots(file_path)

    @classmethod
    def _extract_page_lines(
        cls,
        page: fitz.Page,
    ) -> tuple[PageTextLine, ...]:
        lines: list[PageTextLine] = []
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                parts = []
                for span in spans:
                    text = str(span.get("text", ""))
                    if text:
                        parts.append(text)
                merged = "".join(parts).strip()
                if not merged:
                    continue
                bbox = line.get("bbox", (0.0, 0.0, 0.0, 0.0))
                x0 = float(bbox[0]) if len(bbox) >= 1 else 0.0
                x1 = float(bbox[2]) if len(bbox) >= 3 else x0
                y0 = float(bbox[1]) if len(bbox) >= 2 else 0.0
                y1 = float(bbox[3]) if len(bbox) >= 4 else y0
                lines.append(PageTextLine(text=merged, x0=x0, x1=x1, y0=y0, y1=y1))
        return tuple(lines)

    @classmethod
    def _extract_text_blocks(
        cls,
        page: fitz.Page,
    ) -> tuple[PageTextBlock, ...]:
        """Extract text blocks from page.get_text('blocks') exactly as required by role parser."""
        blocks: list[PageTextBlock] = []
        for raw in page.get_text("blocks"):
            if len(raw) < 7:
                continue
            x0, y0, x1, y1, text, _block_no, block_type = raw[:7]
            if int(block_type) != 0:
                continue
            merged = str(text or "").strip()
            if not merged:
                continue
            blocks.append(
                PageTextBlock(
                    text=merged,
                    x0=float(x0),
                    y0=float(y0),
                    x1=float(x1),
                    y1=float(y1),
                )
            )
        return tuple(blocks)

    @classmethod
    def _extract_image_rects(
        cls,
        page: fitz.Page,
    ) -> tuple[tuple[float, float, float, float], ...]:
        image_rects: list[tuple[float, float, float, float]] = []
        for raw in page.get_text("blocks"):
            if len(raw) < 7:
                continue
            x0, y0, x1, y1, _text, _block_no, block_type = raw[:7]
            if int(block_type) != 1:
                continue
            image_rects.append((float(x0), float(y0), float(x1), float(y1)))
        return tuple(image_rects)

    @classmethod
    def _extract_vector_rects(
        cls,
        page: fitz.Page,
    ) -> tuple[tuple[float, float, float, float], ...]:
        vector_rects: list[tuple[float, float, float, float]] = []
        try:
            drawings: list[dict[str, Any]] = page.get_drawings()
        except Exception:
            return tuple(vector_rects)

        for drawing in drawings:
            rect = drawing.get("rect")
            if rect is None:
                continue
            vector_rects.append((float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)))
        return tuple(vector_rects)

    @classmethod
    def _extract_ocr_blocks(
        cls,
        page: fitz.Page,
    ) -> tuple[PageOcrBlock, ...]:
        """Try OCR extraction for scanned/signature-like text; returns empty when OCR backend is unavailable."""
        ocr_blocks: list[PageOcrBlock] = []
        try:
            text_page = page.get_textpage_ocr(dpi=150)
            raw_blocks = text_page.extractBLOCKS()
        except Exception:
            return tuple(ocr_blocks)

        for raw in raw_blocks:
            if len(raw) < 5:
                continue
            x0, y0, x1, y1, text = raw[:5]
            merged = str(text or "").strip()
            if not merged:
                continue
            ocr_blocks.append(
                PageOcrBlock(
                    text=merged,
                    x0=float(x0),
                    y0=float(y0),
                    x1=float(x1),
                    y1=float(y1),
                )
            )
        return tuple(ocr_blocks)

    @classmethod
    def _extract_words(
        cls,
        page: fitz.Page,
    ) -> tuple[PageWord, ...]:
        words: list[PageWord] = []
        for raw in page.get_text("words"):
            if len(raw) < 5:
                continue
            x0, y0, x1, y1, text = raw[:5]
            token = str(text or "").strip()
            if not token:
                continue
            words.append(
                PageWord(
                    text=token,
                    x0=float(x0),
                    y0=float(y0),
                    x1=float(x1),
                    y1=float(y1),
                )
            )
        return tuple(words)