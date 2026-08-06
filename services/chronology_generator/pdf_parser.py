"""
services.chronology_generator.pdf_parser
========================================

Parses the signed Test Report PDF to extract dynamic Product Information
destined for the Chronology Excel template.

Uses PyMuPDF (fitz) to read the PDF content.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import fitz  # PyMuPDF

from services.chronology_generator.models import ProductInfo


class TestReportParser:
    """
    Parses a signed Test Report PDF to extract product information.
    """

    _STOP_MARKERS = [
        "SR. NO.",
        "CONDITION",
        "OBSERVED",
        "EXPECTED RESULT",
        "TIME PARAMETER",
        "RATED OP CURRENT",
        "FACTORY SETTING",
        "OVER VOLTAGE PROTECTION",
        "OUTPUT VOLTAGE",
        "OUTPUT CURRENT",
    ]

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def extract_product_info(self, pdf_path: Path) -> ProductInfo:
        """
        Extracts product information from the given PDF.

        Args:
            pdf_path: The path to the *-sgn.pdf file.

        Returns:
            A populated ProductInfo dataclass.
        """
        info = ProductInfo(source_pdf=pdf_path)

        if not pdf_path.exists():
            info.parse_status = "Failed"
            info.warning = f"PDF file does not exist: {pdf_path}"
            self._logger.warning(info.warning)
            return info

        try:
            doc = fitz.open(pdf_path)
            
            # Print page 1 trace for user
            if len(doc) > 0:
                print("\n================================================")
                print("6.\nPDF being parsed (Page 1):")
                print(doc[0].get_text())

        except Exception as e:
            info.parse_status = "Failed"
            info.warning = f"Failed to open PDF {pdf_path}: {e}"
            self._logger.warning(info.warning)
            return info

        found_info = False

        for page_num, page in enumerate(doc):
            try:
                text = page.get_text()
                # Parse text
                series_match = re.search(r'PRODUCT\s+SERIES\s*:?\s*([^\n]+)', text, re.IGNORECASE)
                names_raw = self._extract_product_name_block(text)

                if series_match and names_raw:
                    info.mode = "Series"
                    info.series_name = series_match.group(1).strip()
                    info.products = self._split_product_names(names_raw)
                    if not info.products:
                        continue
                    info.page_number = page_num + 1
                    info.parse_status = "Success"
                    found_info = True
                    print("Parsed product_info.products:", info.products)
                    print("Parsed product count:", len(info.products))
                    break

                prod_match = re.search(r'PRODUCT\s*:?\s*([^\n]+)', text, re.IGNORECASE)
                if prod_match:
                    info.mode = "Single"
                    info.single_product = prod_match.group(1).strip()
                    info.page_number = page_num + 1
                    info.parse_status = "Success"
                    found_info = True
                    print("Parsed product_info.products:", [info.single_product])
                    print("Parsed product count:", 1)
                    break

            except Exception as e:
                self._logger.warning(f"Error reading page {page_num+1} of {pdf_path}: {e}")
                continue

        doc.close()

        if not found_info:
            info.parse_status = "Failed"
            info.warning = f"No Product Information found in {pdf_path}"
            self._logger.warning(info.warning)

        return info

    def extract_department_code(self, pdf_path: Path) -> str | None:
        """
        Extract DDHW_<suffix> from page 1 header text of the signed test report.

        Returns:
            Department code like 'DDHW_PS', or None when not found.
        """
        if not pdf_path.exists():
            self._logger.warning("Signed test report not found for header extraction: %s", pdf_path)
            return None

        try:
            doc = fitz.open(pdf_path)
        except Exception as exc:
            self._logger.warning("Failed to open signed report for header extraction %s: %s", pdf_path, exc)
            return None

        try:
            if len(doc) == 0:
                self._logger.warning("Signed report has no pages for header extraction: %s", pdf_path)
                return None

            page1_text = doc[0].get_text()
            match = re.search(
                r'(?i)\bDDHW(?:\s*[_\-/:]?\s*)([A-Z0-9]+(?:[_\-][A-Z0-9]+)*)\b',
                page1_text,
            )
            if not match:
                return None

            suffix = match.group(1).strip().upper()
            normalized_suffix = re.sub(r'[^A-Z0-9]+', '_', suffix).strip('_')
            if not normalized_suffix:
                return None

            return f"DDHW_{normalized_suffix}"
        except Exception as exc:
            self._logger.warning("Failed while extracting department code from %s: %s", pdf_path, exc)
            return None
        finally:
            doc.close()

    def _extract_product_name_block(self, text: str) -> str:
        """Extract PRODUCT NAME section and stop before table/header content."""
        marker_match = re.search(r'PRODUCT\s+NAME\s*:?\s*', text, re.IGNORECASE)
        if not marker_match:
            marker_match = re.search(r'APPLICABLE\s+PRODUCTS\s*:?\s*', text, re.IGNORECASE)
        if not marker_match:
            return ""

        start = marker_match.end()
        remainder = text[start:]
        remainder_upper = remainder.upper()

        stop_idx = len(remainder)
        for marker in self._STOP_MARKERS:
            idx = remainder_upper.find(marker)
            if idx != -1 and idx < stop_idx:
                stop_idx = idx

        block = remainder[:stop_idx]
        return block.strip()

    @staticmethod
    def _split_product_names(names_raw: str) -> list[str]:
        """Split comma/newline separated names and keep only non-empty product strings."""
        names: list[str] = []
        for token in re.split(r'[,\n\r]+', names_raw):
            value = token.strip()
            if not value:
                continue
            # Discard obvious table header fragments that may survive PDF extraction.
            if re.fullmatch(r'(SR\.\s*NO\.?|CONDITION|OBSERVED|EXPECTED\s+RESULT|TIME\s+PARAMETER)', value, re.IGNORECASE):
                break
            names.append(value)
        return names
