"""
services.signature_reader
=========================

Provides PDF page-level signature extraction for section-based validation.
Uses pdfplumber for geometry/text and pypdf for widget structures.

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

import pdfplumber
import pypdf

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
    """One text block extracted with coordinates."""

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

        try:
            reader = pypdf.PdfReader(file_path)
            
            # Map page index to list of signed signature rects
            signature_rects_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
            
            for page_index, page in enumerate(reader.pages):
                rects: list[tuple[float, float, float, float]] = []
                if "/Annots" in page:
                    for annot_ref in page["/Annots"]:
                        try:
                            annot_obj = annot_ref.get_object()
                            if cls._is_signature_widget(annot_obj):
                                if cls._is_signed(annot_obj):
                                    rect = annot_obj.get("/Rect")
                                    if rect:
                                        rects.append(cls._normalize_rect(rect, page))
                        except Exception:
                            continue
                signature_rects_by_page[page_index] = rects

            snapshots: list[PageSignatureSnapshot] = []

            with pdfplumber.open(file_path) as pdf:
                for page_index, page in enumerate(pdf.pages):
                    signed_signature_rects = signature_rects_by_page.get(page_index, [])
                    
                    text_blocks = cls._extract_text_blocks(page)
                    image_rects = cls._extract_image_rects(page)
                    vector_rects = cls._extract_vector_rects(page)
                    ocr_blocks = tuple()  # OCR removed
                    words = cls._extract_words(page)
                    lines = cls._extract_page_lines(page)

                    snapshots.append(
                        PageSignatureSnapshot(
                            page_number=page_index + 1,
                            page_height=float(page.height),
                            page_width=float(page.width),
                            lines=lines,
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

    @classmethod
    def read(
        cls,
        file_path: Path,
    ) -> list[PageSignatureSnapshot]:
        """Backward-compatible wrapper returning page snapshots."""
        return cls.read_page_snapshots(file_path)

    @classmethod
    def _is_signature_widget(cls, annot_obj: dict) -> bool:
        if annot_obj.get("/Subtype") != "/Widget":
            return False
        ft = annot_obj.get("/FT")
        if ft == "/Sig":
            return True
        parent = annot_obj.get("/Parent")
        while parent:
            try:
                parent_obj = parent.get_object()
                if parent_obj.get("/FT") == "/Sig":
                    return True
                parent = parent_obj.get("/Parent")
            except Exception:
                break
        return False

    @classmethod
    def _is_signed(cls, annot_obj: dict) -> bool:
        if "/V" in annot_obj:
            return True
        parent = annot_obj.get("/Parent")
        while parent:
            try:
                parent_obj = parent.get_object()
                if "/V" in parent_obj:
                    return True
                parent = parent_obj.get("/Parent")
            except Exception:
                break
        return False

    @classmethod
    def _normalize_rect(cls, annot_rect: list, page: pypdf.PageObject) -> tuple[float, float, float, float]:
        """Normalizes a PDF /Rect into pdfplumber top-left coordinate space, respecting CropBox and Rotation."""
        box = page.cropbox if page.cropbox else page.mediabox
        c_left = float(box.left)
        c_bottom = float(box.bottom)
        c_right = float(box.right)
        c_top = float(box.top)
        
        width = c_right - c_left
        height = c_top - c_bottom
        
        rx0, ry0, rx1, ry1 = [float(v) for v in annot_rect]
        
        nx0 = rx0 - c_left
        nx1 = rx1 - c_left
        ny0 = ry0 - c_bottom
        ny1 = ry1 - c_bottom
        
        y0 = height - ny1
        y1 = height - ny0
        
        x0 = nx0
        x1 = nx1
        
        rotation = page.get("/Rotate", 0)
        if isinstance(rotation, pypdf.generic.NumberObject):
            rotation = int(rotation)
        else:
            rotation = 0
        rotation = rotation % 360
        
        if rotation == 90:
            new_x0 = y0
            new_y0 = width - x1
            new_x1 = y1
            new_y1 = width - x0
            x0, y0, x1, y1 = new_x0, new_y0, new_x1, new_y1
        elif rotation == 180:
            new_x0 = width - x1
            new_y0 = height - y1
            new_x1 = width - x0
            new_y1 = height - y0
            x0, y0, x1, y1 = new_x0, new_y0, new_x1, new_y1
        elif rotation == 270:
            new_x0 = height - y1
            new_y0 = x0
            new_x1 = height - y0
            new_y1 = x1
            x0, y0, x1, y1 = new_x0, new_y0, new_x1, new_y1

        return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    @classmethod
    def _get_baseline_grouped_words(cls, page: pdfplumber.page.Page) -> list[dict]:
        from collections import defaultdict
        from pdfplumber.utils import extract_words
        
        lines_by_top = defaultdict(list)
        for char in page.chars:
            top_key = round(float(char.get("top", 0.0)) / 2.0) * 2.0
            lines_by_top[top_key].append(char)
            
        final_words = []
        for top_key in sorted(lines_by_top.keys()):
            chars = lines_by_top[top_key]
            slice_words = extract_words(chars, x_tolerance=3.0, y_tolerance=3.0)
            final_words.extend(slice_words)
            
        return final_words

    @classmethod
    def _extract_page_lines(
        cls,
        page: pdfplumber.page.Page,
    ) -> tuple[PageTextLine, ...]:
        lines: list[PageTextLine] = []
        words = cls._get_baseline_grouped_words(page)
        
        from collections import defaultdict
        grouped_by_top = defaultdict(list)
        for w in words:
            grouped_by_top[w['top']].append(w)
            
        for top_key in sorted(grouped_by_top.keys()):
            line_words = grouped_by_top[top_key]
            line_words.sort(key=lambda w: w['x0'])
            text = " ".join(w['text'] for w in line_words)
            x0 = min(w['x0'] for w in line_words)
            x1 = max(w['x1'] for w in line_words)
            y0 = min(w['top'] for w in line_words)
            y1 = max(w['bottom'] for w in line_words)
            lines.append(PageTextLine(text=text, x0=x0, x1=x1, y0=y0, y1=y1))
            
        return tuple(lines)

    @classmethod
    def _extract_text_blocks(
        cls,
        page: pdfplumber.page.Page,
    ) -> tuple[PageTextBlock, ...]:
        blocks: list[PageTextBlock] = []
        for line in cls._extract_page_lines(page):
            blocks.append(
                PageTextBlock(
                    text=line.text,
                    x0=line.x0,
                    y0=line.y0,
                    x1=line.x1,
                    y1=line.y1,
                )
            )
        return tuple(blocks)

    @classmethod
    def _extract_image_rects(
        cls,
        page: pdfplumber.page.Page,
    ) -> tuple[tuple[float, float, float, float], ...]:
        image_rects: list[tuple[float, float, float, float]] = []
        for img in page.images:
            x0 = float(img.get("x0", 0.0))
            x1 = float(img.get("x1", 0.0))
            y0 = float(img.get("top", 0.0))
            y1 = float(img.get("bottom", 0.0))
            image_rects.append((x0, y0, x1, y1))
        return tuple(image_rects)

    @classmethod
    def _extract_vector_rects(
        cls,
        page: pdfplumber.page.Page,
    ) -> tuple[tuple[float, float, float, float], ...]:
        vector_rects: list[tuple[float, float, float, float]] = []
        for rect in page.rects:
            x0 = float(rect.get("x0", 0.0))
            x1 = float(rect.get("x1", 0.0))
            y0 = float(rect.get("top", 0.0))
            y1 = float(rect.get("bottom", 0.0))
            vector_rects.append((x0, y0, x1, y1))
        for rect in page.lines:
            x0 = float(rect.get("x0", 0.0))
            x1 = float(rect.get("x1", 0.0))
            y0 = float(rect.get("top", 0.0))
            y1 = float(rect.get("bottom", 0.0))
            vector_rects.append((x0, y0, x1, y1))
        for curve in page.curves:
            x0 = float(curve.get("x0", 0.0))
            x1 = float(curve.get("x1", 0.0))
            y0 = float(curve.get("top", 0.0))
            y1 = float(curve.get("bottom", 0.0))
            vector_rects.append((x0, y0, x1, y1))
        return tuple(vector_rects)

    @classmethod
    def _extract_words(
        cls,
        page: pdfplumber.page.Page,
    ) -> tuple[PageWord, ...]:
        words: list[PageWord] = []
        for word in cls._get_baseline_grouped_words(page):
            text = word.get("text", "").strip()
            if not text:
                continue
            x0 = float(word.get("x0", 0.0))
            x1 = float(word.get("x1", 0.0))
            y0 = float(word.get("top", 0.0))
            y1 = float(word.get("bottom", 0.0))
            words.append(PageWord(text=text, x0=x0, y0=y0, x1=x1, y1=y1))
        return tuple(words)