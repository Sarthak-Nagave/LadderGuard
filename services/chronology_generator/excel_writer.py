"""
services.chronology_generator.excel_writer
==========================================

Writes ProjectChronology data into an existing Ladder Chronology Excel template.

This module is strictly responsible for locating the correct columns in a 
provided template and populating them with data. It preserves existing 
formatting and does not calculate or scan data.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import logging
import math
import re
import shutil
import subprocess
import tempfile
from copy import copy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Font
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils import get_column_letter

from services.chronology_generator.models import ChronologyEntry, ProjectChronology
from services.chronology_generator.pdf_parser import TestReportParser


class ChronologyTemplateError(Exception):
    """
    Raised when the provided Excel template is invalid or missing required headers.
    """


@dataclass(slots=True)
class ProductWriteResult:
    """Captures written Product section coordinates and expected values."""

    mode: str
    product_cell: tuple[int, int]
    product_value: str
    applicable_label_cell: tuple[int, int] | None
    applicable_rows: list[tuple[int, int, int, str]]


class ChronologyExcelWriter:
    """
    Populates an existing Ladder Chronology Excel workbook with chronology entries.
    """

    # Normalized required headers
    REQUIRED_HEADERS = {
        "serial no.",
        "source code path",
        "bin file name",
        "crc",
        "ladder version no.",
        "reason for upgrade",
        "testing stage",
        "plc model",
        "selpro version & path",
        "bootloader version",
        "release date",
        "released by",
        "ladder release-to production",
        "operator procedure modification",
        "automation set up modification",
        "tested by",
    }

    COLUMN_PROFILE_LIMITS = {
        "SMALL": (6.0, 14.0),
        "MEDIUM": (9.0, 20.0),
        "LARGE": (14.0, 120.0),
        "EXTRA_LARGE": (18.0, 140.0),
    }

    LONG_TEXT_HEADERS = {
        "source code path",
        "bin file name",
        "selpro version & path",
        "reason for upgrade",
    }

    EXCEL_HEADER_LINE_BREAK = chr(10)

    def __init__(self, template_path: Path) -> None:
        """
        Initialize the Excel writer.

        Args:
            template_path: Path to the existing Excel template.
        """
        self._template_path = template_path
        self._logger = logging.getLogger(__name__)
        self._last_pdf_export_succeeded = False
        self._last_pdf_path: Path | None = None
        self._last_pdf_export_message: str = ""
        self._last_column_layout_report: list[dict[str, Any]] = []
        self._last_department_code: str = ""
        self._native_header_override: dict[str, str] | None = None

    @property
    def last_pdf_export_succeeded(self) -> bool:
        return self._last_pdf_export_succeeded

    @property
    def last_pdf_path(self) -> Path | None:
        return self._last_pdf_path

    @property
    def last_pdf_export_message(self) -> str:
        return self._last_pdf_export_message

    @property
    def last_column_layout_report(self) -> list[dict[str, Any]]:
        return list(self._last_column_layout_report)

    def write(self, chronology: ProjectChronology, output_path: Path) -> None:
        """
        Writes the chronology data to the template and saves it to the output path.

        Args:
            chronology: The populated ProjectChronology model.
            output_path: Path where the resulting Excel file should be saved.

        Raises:
            ChronologyTemplateError: If the template is invalid or missing headers.
            FileNotFoundError: If the template file does not exist.
        """
        self._logger.info(f"Starting chronology Excel export to {output_path}")
        self._last_pdf_export_succeeded = False
        self._last_pdf_path = output_path.with_suffix(".pdf")
        self._last_pdf_export_message = ""
        self._native_header_override = None

        workbook = self._load_workbook()
        sheet = workbook.active

        if sheet is None:
            raise ChronologyTemplateError("Template workbook contains no active worksheet.")

        header_row_idx = self._find_header_row(sheet)
        header_map = self._build_header_map(sheet, header_row_idx)
        first_data_row = self._first_data_row(header_row_idx)
        layout_snapshot = self._capture_print_layout(sheet)
        template_header_height = sheet.row_dimensions[header_row_idx].height
        template_data_height = sheet.row_dimensions[first_data_row].height

        entries = chronology.sorted_entries()
        if not entries:
            self._logger.warning("No chronology entries to write.")
            return

        self._logger.debug(f"Writing chronology update using {len(entries)} scanned entries.")

        newest_entry = entries[0]
        history_row = first_data_row
        while self._is_instruction_row(sheet, history_row, header_map):
            self._logger.debug(f"Skipping instruction row {history_row}")
            history_row += 1

        using_existing_workbook = self._is_existing_workbook(output_path)
        has_existing_history = self._has_history_row_data(sheet, history_row, header_map)

        is_duplicate = False
        if using_existing_workbook and has_existing_history:
            is_duplicate = self._is_same_release_row(sheet, history_row, newest_entry, header_map)

        if using_existing_workbook and has_existing_history and not is_duplicate:
            # Locate the end of the history table
            last_history_row = history_row
            temp_row = history_row
            while temp_row <= sheet.max_row:
                if self._is_instruction_row(sheet, temp_row, header_map):
                    last_history_row = temp_row
                    temp_row += 1
                    continue
                if self._has_history_row_data(sheet, temp_row, header_map):
                    last_history_row = temp_row
                    temp_row += 1
                    continue
                break
            
            # Collect and temporarily unmerge ranges that belong ONLY to the history table
            ranges_to_shift = []
            for merged_range in list(sheet.merged_cells.ranges):
                if merged_range.min_row >= history_row and merged_range.max_row <= last_history_row:
                    sheet.unmerge_cells(str(merged_range))
                    shifted = copy(merged_range)
                    shifted.shift(row_shift=1, col_shift=0)
                    ranges_to_shift.append(shifted)

            sheet.insert_rows(history_row, amount=1)
            
            # Re-apply shifted merged ranges
            for shifted_range in ranges_to_shift:
                try:
                    sheet.merge_cells(str(shifted_range))
                except Exception:
                    pass

            self._copy_row_format(sheet, history_row + 1, history_row)

        release_date = datetime.now().strftime("%d/%m/%Y")
        self._write_entry(sheet, history_row, newest_entry, header_map, serial_no=1, release_date=release_date)
        self._renumber_serials(sheet, history_row, header_map)

        product_write_result: ProductWriteResult | None = None
        if newest_entry.test_report_path:
            product_write_result = self._write_product_info(sheet, newest_entry, header_row_idx)

        if newest_entry.test_report_path:
            self._update_page_header_from_signed_report(sheet, newest_entry.test_report_path)

        self._write_signoff_fields(sheet, newest_entry, history_row)

        self._normalize_chronology_table_format(
            sheet,
            header_map,
            template_header_height,
            template_data_height,
        )
        self._restore_print_layout(sheet, layout_snapshot)
        self._debug_print_header_state(sheet, "before save")

        self._save(workbook, output_path)
        self._debug_print_header_state(sheet, "after save")
        workbook.close()

        self._recalculate_page_setup_from_saved_workbook(output_path)

        self._last_pdf_export_succeeded = self._export_generated_excel_to_pdf(output_path)

        if product_write_result is not None:
            self._verify_product_write(output_path, product_write_result)

        self._logger.info("Chronology Excel export completed successfully.")

    def _export_generated_excel_to_pdf(self, excel_path: Path) -> bool:
        """Export the just-generated chronology workbook to a PDF beside it using headless LibreOffice."""
        pdf_path = excel_path.with_suffix(".pdf")
        self._last_pdf_path = pdf_path
        print("Export engine: soffice")
        self._logger.info("Export engine: soffice")

        soffice_path = self._resolve_soffice_executable()
        if soffice_path is None:
            self._last_pdf_export_message = "PDF export skipped: LibreOffice is not installed or not available."
            self._logger.warning(
                "Chronology PDF export skipped: LibreOffice soffice executable not found. Excel kept at %s",
                excel_path,
            )
            return False

        try:
            if pdf_path.exists():
                pdf_path.unlink()
                self._logger.info("Removed previous chronology PDF before export: %s", pdf_path)
        except PermissionError as exc:
            self._last_pdf_export_message = "Previous Chronology PDF is currently open. Please close it and generate again."
            self._logger.warning(
                "Could not remove previous chronology PDF because it is likely open: %s (%s)",
                pdf_path,
                exc,
            )
            return False
        except Exception as exc:
            self._last_pdf_export_message = "PDF export failed while replacing previous chronology PDF."
            self._logger.warning("Failed to remove existing chronology PDF %s: %s", pdf_path, exc)
            return False

        command = [
            str(soffice_path),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(excel_path.parent),
            str(excel_path),
        ]

        self._apply_header_with_soffice_uno(excel_path, soffice_path)

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except Exception as exc:
            self._last_pdf_export_message = "PDF export failed while running LibreOffice."
            self._logger.warning(
                "Chronology PDF export failed for %s using %s: %s",
                excel_path,
                soffice_path,
                exc,
            )
            return False

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            self._last_pdf_export_message = "PDF export failed. Please check LibreOffice installation and logs."
            self._logger.warning(
                "Chronology PDF export failed for %s (exit=%s). stdout=%r stderr=%r",
                excel_path,
                result.returncode,
                stdout,
                stderr,
            )
            return False

        if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
            self._last_pdf_export_message = "PDF export failed: output file was not created correctly."
            self._logger.warning(
                "Chronology PDF export command succeeded but output PDF is missing/empty: %s",
                pdf_path,
            )
            return False

        self._last_pdf_export_message = ""
        self._logger.info("Chronology PDF export completed successfully: %s", pdf_path)
        return True

    def _recalculate_page_setup_from_saved_workbook(self, output_path: Path) -> None:
        """Reopen saved workbook and normalize page setup before PDF export."""
        workbook = openpyxl.load_workbook(filename=output_path)
        sheet = workbook.active
        if sheet is None:
            workbook.close()
            raise ChronologyTemplateError("Saved workbook contains no active worksheet for page-setup recalculation.")

        self._debug_print_header_state(sheet, "after reopening workbook")

        self._validate_merged_ranges(sheet)

        max_row, max_col = self._last_used_cell(sheet)
        end_col = get_column_letter(max_col)
        sheet.print_area = f"$A$1:${end_col}${max_row}"

        # Keep print titles unchanged.
        # Fit to width exactly one page, and allow natural vertical pagination.
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.page_setup.scale = None

        if sheet.sheet_properties.pageSetUpPr is None:
            from openpyxl.worksheet.properties import PageSetupProperties

            sheet.sheet_properties.pageSetUpPr = PageSetupProperties()
        sheet.sheet_properties.pageSetUpPr.fitToPage = True

        self._recalculate_page_breaks(sheet)

        workbook.save(filename=output_path)
        workbook.close()

        verify_workbook = openpyxl.load_workbook(filename=output_path)
        verify_sheet = verify_workbook.active
        if verify_sheet is None:
            verify_workbook.close()
            raise ChronologyTemplateError("Saved workbook contains no active worksheet during header verification.")
        self._debug_print_header_state(verify_sheet, "after recalculation save+reopen")
        verify_workbook.close()

    def _normalize_header_footer_linebreaks(self, sheet: Worksheet) -> None:
        """Replace Excel escaped newline tokens with real newlines in header/footer text."""
        for header in (sheet.oddHeader, sheet.evenHeader, sheet.firstHeader):
            header.left.text = self._decode_excel_newlines(self.safe_val(header.left.text))
            header.center.text = self._decode_excel_newlines(self.safe_val(header.center.text))
            header.right.text = self._decode_excel_newlines(self.safe_val(header.right.text))

    def _debug_print_header_state(self, sheet: Worksheet, stage: str) -> None:
        """Print exact oddHeader text values at critical persistence checkpoints."""
        print(f"[{stage}] worksheet.oddHeader.left.text = {sheet.oddHeader.left.text!r}")
        print(f"[{stage}] worksheet.oddHeader.center.text = {sheet.oddHeader.center.text!r}")
        print(f"[{stage}] worksheet.oddHeader.right.text = {sheet.oddHeader.right.text!r}")

    def _apply_header_with_soffice_uno(self, excel_path: Path, soffice_path: Path) -> None:
        """Write page headers via LibreOffice UNO before PDF conversion."""
        if not self._native_header_override:
            return

        lo_python = self._resolve_soffice_python_executable(soffice_path)
        if lo_python is None:
            self._logger.warning(
                "Native header override skipped: LibreOffice python executable not found for UNO header write."
            )
            return

        script_source = """
import sys
import uno
import officehelper
from com.sun.star.beans import PropertyValue


def _prop(name, value):
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def _apply_header_to_style(style, left_text, center_text, right_text):
    style.HeaderIsOn = True

    right_content = style.RightPageHeaderContent
    right_content.LeftText.String = left_text
    right_content.CenterText.String = center_text
    right_content.RightText.String = right_text
    style.RightPageHeaderContent = right_content

    left_content = style.LeftPageHeaderContent
    left_content.LeftText.String = left_text
    left_content.CenterText.String = center_text
    left_content.RightText.String = right_text
    style.LeftPageHeaderContent = left_content


def main():
    workbook_path = sys.argv[1]
    left_text = sys.argv[2]
    center_text = sys.argv[3]
    right_text = sys.argv[4]

    context = officehelper.bootstrap()
    desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)
    hidden = (_prop("Hidden", True),)
    doc = None
    try:
        url = uno.systemPathToFileUrl(workbook_path)
        doc = desktop.loadComponentFromURL(url, "_blank", 0, hidden)
        sheets = doc.getSheets()
        page_styles = doc.StyleFamilies.getByName("PageStyles")

        for idx in range(sheets.getCount()):
            sheet = sheets.getByIndex(idx)
            style = page_styles.getByName(sheet.PageStyle)
            _apply_header_to_style(style, left_text, center_text, right_text)

        doc.store()
    finally:
        if doc is not None:
            doc.close(True)
        desktop.terminate()


if __name__ == "__main__":
    main()
"""

        script_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix="_uno_header_write.py", delete=False, encoding="utf-8") as tf:
                tf.write(script_source)
                script_path = Path(tf.name)

            left = self._native_header_override.get("left", "")
            center = self._native_header_override.get("center", "")
            right = self._native_header_override.get("right", "")

            result = subprocess.run(
                [
                    str(lo_python),
                    str(script_path),
                    str(excel_path.resolve()),
                    left,
                    center,
                    right,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                self._logger.warning(
                    "Native header override via LibreOffice UNO failed (exit=%s). stdout=%r stderr=%r",
                    result.returncode,
                    (result.stdout or "").strip(),
                    (result.stderr or "").strip(),
                )
            else:
                self._logger.info("Applied page header through LibreOffice UNO before PDF export.")
        except Exception as exc:
            self._logger.warning("Native header override via LibreOffice UNO failed: %s", exc)
        finally:
            if script_path is not None:
                try:
                    script_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def _resolve_soffice_python_executable(self, soffice_path: Path) -> Path | None:
        """Resolve LibreOffice bundled python executable used for UNO automation."""
        candidate = soffice_path.parent / "python.exe"
        if candidate.exists():
            return candidate
        return None

    def _validate_merged_ranges(self, sheet: Worksheet) -> None:
        """Validate merged-cell ranges remain structurally valid after dynamic row insertion."""
        for merged_range in list(sheet.merged_cells.ranges):
            if merged_range.min_row > merged_range.max_row or merged_range.min_col > merged_range.max_col:
                raise ChronologyTemplateError(f"Invalid merged-cell range detected: {merged_range}")

    def _last_used_cell(self, sheet: Worksheet) -> tuple[int, int]:
        """Determine last used row/column for print-area recomputation."""
        max_row = max(1, sheet.max_row)
        max_col = max(1, sheet.max_column)

        used_max_row = 1
        used_max_col = 1
        for row_idx in range(1, max_row + 1):
            row_has_content = False
            for col_idx in range(1, max_col + 1):
                cell = sheet.cell(row=row_idx, column=col_idx)
                value = cell.value
                if value is not None and str(value).strip() != "":
                    row_has_content = True
                    if col_idx > used_max_col:
                        used_max_col = col_idx
            if row_has_content:
                used_max_row = row_idx

        return used_max_row, used_max_col

    def _recalculate_page_breaks(self, sheet: Worksheet) -> None:
        """Recalculate manual page-break anchors to remain in worksheet bounds after row shifts."""
        max_row = max(1, sheet.max_row)
        max_col = max(1, sheet.max_column)

        try:
            row_breaks = [brk for brk in getattr(sheet.row_breaks, "brk", []) if getattr(brk, "id", None) is not None]
            row_breaks = [brk for brk in row_breaks if 1 <= brk.id <= max_row]
            row_breaks.sort(key=lambda brk: brk.id)
            dedup_row_breaks = []
            last_id = None
            for brk in row_breaks:
                if brk.id == last_id:
                    continue
                dedup_row_breaks.append(brk)
                last_id = brk.id
            sheet.row_breaks.brk = dedup_row_breaks
        except Exception:
            pass

        try:
            col_breaks = [brk for brk in getattr(sheet.col_breaks, "brk", []) if getattr(brk, "id", None) is not None]
            col_breaks = [brk for brk in col_breaks if 1 <= brk.id <= max_col]
            col_breaks.sort(key=lambda brk: brk.id)
            dedup_col_breaks = []
            last_id = None
            for brk in col_breaks:
                if brk.id == last_id:
                    continue
                dedup_col_breaks.append(brk)
                last_id = brk.id
            sheet.col_breaks.brk = dedup_col_breaks
        except Exception:
            pass

    def _resolve_soffice_executable(self) -> Path | None:
        """Resolve LibreOffice soffice path from PATH or standard Windows install locations."""
        path_hit = shutil.which("soffice") or shutil.which("libreoffice")
        if path_hit:
            return Path(path_hit)

        candidates = [
            Path("C:/Program Files/LibreOffice/program/soffice.exe"),
            Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _is_existing_workbook(self, output_path: Path) -> bool:
        if not output_path.exists():
            return False
        try:
            return output_path.resolve() == self._template_path.resolve()
        except Exception:
            return output_path == self._template_path

    def _capture_print_layout(self, sheet: Worksheet) -> dict[str, Any]:
        """Capture template print/page configuration so generation does not mutate page style."""
        return {
            "print_area": copy(sheet.print_area) if sheet.print_area else None,
            "print_title_rows": sheet.print_title_rows,
            "print_title_cols": sheet.print_title_cols,
            "page_setup": copy(sheet.page_setup),
            "page_margins": copy(sheet.page_margins),
            "print_options": copy(sheet.print_options),
            "page_setup_pr": copy(sheet.sheet_properties.pageSetUpPr) if sheet.sheet_properties.pageSetUpPr else None,
        }

    def _restore_print_layout(self, sheet: Worksheet, snapshot: dict[str, Any]) -> None:
        """Restore captured print/page configuration from template."""
        sheet.page_setup = copy(snapshot["page_setup"])
        sheet.page_margins = copy(snapshot["page_margins"])
        sheet.print_options = copy(snapshot["print_options"])
        sheet.print_title_rows = snapshot["print_title_rows"]
        sheet.print_title_cols = snapshot["print_title_cols"]

        if snapshot["print_area"]:
            sheet.print_area = str(snapshot["print_area"])
        else:
            sheet.print_area = None

        sheet.sheet_properties.pageSetUpPr = (
            copy(snapshot["page_setup_pr"]) if snapshot["page_setup_pr"] is not None else None
        )

    def _load_workbook(self) -> Workbook:
        """
        Loads the existing Excel template.

        Returns:
            The loaded openpyxl Workbook.

        Raises:
            FileNotFoundError: If the template file does not exist.
            ChronologyTemplateError: If the workbook cannot be loaded.
        """
        if not self._template_path.exists():
            raise FileNotFoundError(f"Template not found: {self._template_path}")

        try:
            return openpyxl.load_workbook(filename=self._template_path)
        except Exception as exc:
            raise ChronologyTemplateError(f"Failed to load workbook: {exc}") from exc

    def _find_header_row(self, sheet: Worksheet) -> int:
        """
        Dynamically locates the header row by searching for a known header column.

        Args:
            sheet: The active worksheet.

        Returns:
            The 1-based index of the header row.

        Raises:
            ChronologyTemplateError: If the header row cannot be identified.
        """
        # Scan the first 50 rows to find the "Serial No." column, which indicates the header row
        for row_idx in range(1, 51):
            for col_idx in range(1, sheet.max_column + 1):
                cell_value = sheet.cell(row=row_idx, column=col_idx).value
                if self._normalize_header(cell_value) == "serial no.":
                    self._logger.debug(f"Identified header row at index {row_idx}.")
                    return row_idx

        raise ChronologyTemplateError("Could not locate the header row in the template.")

    def _build_header_map(self, sheet: Worksheet, header_row: int) -> dict[str, int]:
        """
        Builds a mapping of normalized header names to their 1-based column indices.
        Prints debugging information for header resolution.

        Args:
            sheet: The active worksheet.
            header_row: The 1-based index of the header row.

        Returns:
            A dictionary mapping normalized header strings to column integers.

        Raises:
            ChronologyTemplateError: If any required headers are missing.
        """
        header_map: dict[str, int] = {}
        
        for col_idx in range(1, sheet.max_column + 1):
            cell_value = sheet.cell(row=header_row, column=col_idx).value
            normalized_name = self._normalize_header(cell_value)
            
            if normalized_name:
                header_map[normalized_name] = col_idx

        # Normalize required headers to ensure safe comparison
        normalized_required = {self._normalize_header(h) for h in self.REQUIRED_HEADERS}
        found_headers = set(header_map.keys())

        missing_headers = normalized_required - found_headers
        if missing_headers:
            self._logger.error(f"Expected normalized headers: {sorted(normalized_required)}")
            self._logger.error(f"Found normalized headers: {sorted(found_headers)}")
            
            missing_str = ", ".join(f"'{h}'" for h in sorted(missing_headers))
            raise ChronologyTemplateError(f"Template is missing required headers: {missing_str}")

        return header_map

    def _first_data_row(self, header_row: int) -> int:
        """
        Determines the first writable row after the header row.

        Args:
            header_row: The 1-based index of the header row.

        Returns:
            The 1-based index of the first data row.
        """
        return header_row + 1

    def _is_instruction_row(self, sheet: Worksheet, row: int, header_map: dict[str, int]) -> bool:
        """
        Determines if a row is an instruction row (e.g., Row 16 with merged text).
        Checks if it's merged or contains existing text, but must NOT be a valid history row.
        """
        if self._has_history_row_data(sheet, row, header_map):
            return False
        return self._is_row_merged(sheet, row, header_map)

    def _is_row_merged(self, sheet: Worksheet, row: int, header_map: dict[str, int]) -> bool:
        """
        Determines if a row is a structural merged row (e.g., a section divider or instruction row).
        Checks if any horizontal merge on this row spans across multiple data columns.
        """
        for merged_range in sheet.merged_cells.ranges:
            if merged_range.min_row <= row <= merged_range.max_row:
                # If the horizontal merge spans 3 or more columns, it's considered structural
                if (merged_range.max_col - merged_range.min_col) >= 2:
                    return True
        return False

    def _get_writable_cell(self, sheet: Worksheet, row: int, column: int) -> Any:
        """
        Returns the writable master cell if the given coordinate belongs to a 
        merged range, otherwise returns the standard cell.
        
        Args:
            sheet: The active worksheet.
            row: The 1-based row index.
            column: The 1-based column index.
            
        Returns:
            The writable openpyxl Cell object.
        """
        for merged_range in sheet.merged_cells.ranges:
            if (merged_range.min_row <= row <= merged_range.max_row and
                merged_range.min_col <= column <= merged_range.max_col):
                # Return the top-left master cell of the merged range
                return sheet.cell(row=merged_range.min_row, column=merged_range.min_col)
        
        return sheet.cell(row=row, column=column)

    def _write_entry(
        self, 
        sheet: Worksheet, 
        row_idx: int, 
        entry: ChronologyEntry, 
        header_map: dict[str, int], 
        serial_no: int,
        release_date: str,
    ) -> None:
        """
        Writes a single ChronologyEntry to the specified row.

        Preserves formatting by strictly assigning to the cell.value property.
        Safely resolves merged cells to ensure writes target the master cell.

        Args:
            sheet: The active worksheet.
            row_idx: The 1-based index of the row to write to.
            entry: The ChronologyEntry to write.
            header_map: The header-to-column mapping.
            serial_no: The auto-incremented serial number for this row.
        """
        
        def safe_val(value: Any) -> str | int:
            return value if value is not None else ""

        # Only update business fields for chronology history entries.
        data = {
            "serial no.": serial_no,
            "source code path": str(entry.source_code_path) if entry.source_code_path else "",
            "bin file name": entry.bin_file_name,
            "crc": entry.crc,
            "ladder version no.": entry.version,
            "reason for upgrade": entry.reason_for_upgrade,
            "testing stage": self._normalize_testing_stage_display(entry.testing_stage),
            "plc model": entry.plc_model,
            "selpro version & path": entry.selpro_version,
            "bootloader version": entry.bootloader_version,
            "release date": release_date,
            "released by": entry.released_by,
            "ladder release-to production": entry.ladder_release_to_production,
            "operator procedure modification": entry.operator_procedure_modification,
            "automation set up modification": entry.automation_setup_modification,
            "tested by": entry.tested_by,
        }

        for header_name, col_idx in header_map.items():
            if header_name in data:
                writable_cell = self._get_writable_cell(sheet, row_idx, col_idx)
                writable_cell.value = safe_val(data[header_name])

    @staticmethod
    def _normalize_testing_stage_display(value: str | None) -> str:
        """Normalize only the Excel display value for testing stage."""
        stage = "" if value is None else str(value)
        if "/" in stage:
            return stage
        return "/".join(stage.split())

    def _renumber_serials(self, sheet: Worksheet, start_row: int, header_map: dict[str, int]) -> None:
        serial_column = header_map.get("serial no.")
        if serial_column is None:
            return

        history_rows: list[int] = []
        row_index = start_row
        while row_index <= sheet.max_row:
            if self._is_instruction_row(sheet, row_index, header_map):
                row_index += 1
                continue

            if not self._has_history_row_data(sheet, row_index, header_map):
                break

            history_rows.append(row_index)
            row_index += 1

        serial_no = len(history_rows)
        for row_index in history_rows:
            serial_cell = self._get_writable_cell(sheet, row_index, serial_column)
            serial_cell.value = serial_no
            serial_no -= 1

    def _normalize_chronology_table_format(
        self,
        sheet: Worksheet,
        header_map: dict[str, int],
        template_header_height: float | None,
        template_data_height: float | None,
    ) -> None:
        """Preserve template chronology sizing and normalize generated data-row alignment."""
        current_header_row = self._find_header_row(sheet)
        default_row_height = sheet.sheet_format.defaultRowHeight or 15.0
        # Keep header compact even when source template has oversized legacy row heights.
        header_height = max(18.0, min(54.0, template_header_height if template_header_height is not None else default_row_height * 1.2))
        sheet.row_dimensions[current_header_row].height = header_height

        self._apply_chronology_column_layout_profile(sheet, header_map)

        serial_col = header_map.get("serial no.")
        # Use a compact per-line baseline for generated rows to avoid excessive vertical whitespace.
        base_data_height = max(14.0, min(20.0, template_data_height if template_data_height is not None else default_row_height))
        row_idx = current_header_row + 1
        while row_idx <= sheet.max_row:
            if self._is_instruction_row(sheet, row_idx, header_map):
                row_idx += 1
                continue
            if not self._has_history_row_data(sheet, row_idx, header_map):
                break

            required_lines = self._estimate_required_lines_for_row(sheet, row_idx, header_map)
            sheet.row_dimensions[row_idx].height = max(base_data_height, base_data_height * required_lines)
            for _, col_idx in header_map.items():
                cell = self._get_writable_cell(sheet, row_idx, col_idx)
                alignment = copy(cell.alignment) if cell.alignment else None
                if alignment is None:
                    from openpyxl.styles import Alignment
                    alignment = Alignment()
                alignment.vertical = "center"
                alignment.wrap_text = True
                alignment.horizontal = "center" if col_idx == serial_col else "left"
                cell.alignment = alignment

            row_idx += 1

    def _apply_chronology_column_layout_profile(self, sheet: Worksheet, header_map: dict[str, int]) -> None:
        """Apply content-aware widths: compact short-value columns and distribute spare width only to long-text columns."""
        columns: list[tuple[str, int]] = sorted(header_map.items(), key=lambda item: item[1])
        if not columns:
            return

        default_width = 8.43
        self._last_column_layout_report = []

        history_rows = self._collect_history_rows(sheet, self._find_header_row(sheet), header_map)

        total_current_width = 0.0
        original_widths: dict[int, float] = {}
        widths: dict[int, float] = {}
        categories: dict[int, str] = {}
        stats: dict[int, dict[str, float]] = {}

        for header_name, col_idx in columns:
            col_letter = get_column_letter(col_idx)
            base_width = float(sheet.column_dimensions[col_letter].width or default_width)
            original_widths[col_idx] = base_width
            total_current_width += base_width

            values = [self.safe_val(sheet.cell(row=r, column=col_idx).value) for r in history_rows]
            non_empty = [v for v in values if v]
            max_len = max((len(v) for v in non_empty), default=0)
            avg_len = (sum(len(v) for v in non_empty) / len(non_empty)) if non_empty else 0.0
            header_token_max = max((len(tok) for tok in re.split(r"\s+", header_name.replace("-", " ").strip()) if tok), default=0)
            category = self._infer_column_category(header_name, non_empty, max_len, avg_len)
            categories[col_idx] = category
            stats[col_idx] = {
                "max_len": float(max_len),
                "avg_len": float(avg_len),
                "header_token_max": float(header_token_max),
            }

            min_w, max_w = self.COLUMN_PROFILE_LIMITS.get(category, self.COLUMN_PROFILE_LIMITS["SMALL"])
            content_need = max(stats[col_idx]["avg_len"], stats[col_idx]["header_token_max"])
            width_from_content = 2.0 + content_need * 0.95

            if header_name in self.LONG_TEXT_HEADERS:
                width = min(base_width * 0.94, width_from_content)
            else:
                width = min(base_width, width_from_content)

            widths[col_idx] = max(min_w, min(max_w, width))

        # Keep table near printable width by allocating remaining space only to designated long-text columns.
        target_width_total = total_current_width
        current_total = sum(widths.values())
        remaining = max(0.0, target_width_total - current_total)
        long_cols = [col_idx for header_name, col_idx in columns if header_name in self.LONG_TEXT_HEADERS]
        if remaining > 0 and long_cols:
            scores = {
                col_idx: max(1.0, math.log1p(stats[col_idx]["max_len"]) + 0.35 * math.log1p(stats[col_idx]["avg_len"]))
                for col_idx in long_cols
            }
            # Cap long-text columns slightly below template width to prefer vertical growth via wrapping.
            caps: dict[int, float] = {}
            for col_idx in long_cols:
                _, max_w = self.COLUMN_PROFILE_LIMITS.get(categories[col_idx], self.COLUMN_PROFILE_LIMITS["LARGE"])
                caps[col_idx] = max(widths[col_idx], min(max_w, original_widths[col_idx] * 0.98))

            # Multi-pass distribution so leftover keeps flowing only into eligible long-text columns.
            for _ in range(3):
                if remaining <= 0:
                    break
                eligible = [c for c in long_cols if widths[c] < caps[c] - 1e-6]
                if not eligible:
                    break
                score_total = sum(scores[c] for c in eligible)
                if score_total <= 0:
                    break
                distributed = 0.0
                for col_idx in eligible:
                    share = remaining * (scores[col_idx] / score_total)
                    room = caps[col_idx] - widths[col_idx]
                    delta = min(room, share)
                    if delta > 0:
                        widths[col_idx] += delta
                        distributed += delta
                if distributed <= 0:
                    break
                remaining -= distributed

        for _, col_idx in columns:
            category = categories[col_idx]
            min_w, max_w = self.COLUMN_PROFILE_LIMITS.get(category, self.COLUMN_PROFILE_LIMITS["SMALL"])
            widths[col_idx] = max(min_w, min(max_w, widths[col_idx]))
            
            # Enforce minimum width for columns A and B to protect the Product Information labels
            # from being visually truncated in LibreOffice PDF export.
            if col_idx == 1:
                widths[col_idx] = max(widths[col_idx], 22.0)
            elif col_idx == 2:
                widths[col_idx] = max(widths[col_idx], 22.0)

            col_letter = get_column_letter(col_idx)
            sheet.column_dimensions[col_letter].width = round(widths[col_idx], 2)
        for header_name, col_idx in columns:
            self._last_column_layout_report.append(
                {
                    "header": header_name,
                    "column": get_column_letter(col_idx),
                    "category": categories[col_idx],
                    "max_len": int(stats[col_idx]["max_len"]),
                    "avg_len": round(stats[col_idx]["avg_len"], 2),
                    "original_width": round(original_widths[col_idx], 2),
                    "assigned_width": round(widths[col_idx], 2),
                    "reason": (
                        "Long-text column received redistributed spare width"
                        if header_name in self.LONG_TEXT_HEADERS
                        else "Compact column width derived from measured content"
                    ),
                }
            )

    def _collect_history_rows(self, sheet: Worksheet, start_row: int, header_map: dict[str, int]) -> list[int]:
        rows: list[int] = []
        row_idx = start_row + 1
        while row_idx <= sheet.max_row:
            if self._is_instruction_row(sheet, row_idx, header_map):
                row_idx += 1
                continue
            if not self._has_history_row_data(sheet, row_idx, header_map):
                break
            rows.append(row_idx)
            row_idx += 1
        return rows

    def _infer_column_category(self, header_name: str, values: list[str], max_len: int, avg_len: float) -> str:
        if header_name in self.LONG_TEXT_HEADERS:
            return "LARGE"

        sample = [v.strip() for v in values if v.strip()]
        if not sample:
            return "SMALL"

        low = [s.casefold() for s in sample]
        if all(re.fullmatch(r"\d+", s) for s in sample):
            return "SMALL"
        if all(re.fullmatch(r"0x[0-9a-fA-F]{6,10}", s) for s in sample):
            return "SMALL"
        if all(re.fullmatch(r"v?\d+(?:\.\d+){0,3}", s, re.IGNORECASE) for s in sample):
            return "SMALL"
        if all(re.fullmatch(r"\d{2}/\d{2}/\d{4}", s) for s in sample):
            return "SMALL"
        if all(s in {"yes", "no", "n/a", "na"} for s in low):
            return "SMALL"

        if max_len <= 14 and avg_len <= 10:
            return "SMALL"
        if max_len <= 22 and avg_len <= 14:
            return "MEDIUM"
        return "MEDIUM"

    def _estimate_required_lines_for_row(self, sheet: Worksheet, row_idx: int, header_map: dict[str, int]) -> int:
        """Estimate wrapped line count needed for chronology row based on current column widths and text."""
        max_lines = 1
        seen_masters: set[tuple[int, int]] = set()
        for _, col_idx in header_map.items():
            cell = sheet.cell(row=row_idx, column=col_idx)
            master_row, master_col = row_idx, col_idx
            span_width = float(sheet.column_dimensions[get_column_letter(col_idx)].width or 8.43)

            for merged_range in sheet.merged_cells.ranges:
                if (
                    merged_range.min_row <= row_idx <= merged_range.max_row
                    and merged_range.min_col <= col_idx <= merged_range.max_col
                ):
                    master_row, master_col = merged_range.min_row, merged_range.min_col
                    span_width = 0.0
                    for c in range(merged_range.min_col, merged_range.max_col + 1):
                        span_width += float(sheet.column_dimensions[get_column_letter(c)].width or 8.43)
                    cell = sheet.cell(row=master_row, column=master_col)
                    break

            if (master_row, master_col) in seen_masters:
                continue
            seen_masters.add((master_row, master_col))

            text = self.safe_val(cell.value)
            if not text:
                continue

            char_capacity = max(6, int(span_width * 0.95))

            lines_for_cell = 0
            for segment in text.splitlines() or [text]:
                segment_len = max(1, len(segment))
                lines_for_cell += max(1, math.ceil(segment_len / char_capacity))

            max_lines = max(max_lines, lines_for_cell)

        return max_lines

    @staticmethod
    def _has_history_row_data(sheet: Worksheet, row: int, header_map: dict[str, int]) -> bool:
        probe_headers = [
            "bin file name",
            "ladder version no.",
            "testing stage",
            "source code path",
        ]

        for header in probe_headers:
            col_idx = header_map.get(header)
            if col_idx is None:
                continue
            value = sheet.cell(row=row, column=col_idx).value
            if value is not None and str(value).strip() != "":
                return True

        return False

    def _is_same_release_row(
        self,
        sheet: Worksheet,
        row: int,
        entry: ChronologyEntry,
        header_map: dict[str, int],
    ) -> bool:
        expected = {
            "bin file name": entry.bin_file_name,
            "ladder version no.": entry.version,
            "source code path": str(entry.source_code_path) if entry.source_code_path else "",
            "testing stage": entry.testing_stage,
            "plc model": entry.plc_model,
            "bootloader version": entry.bootloader_version,
        }

        for header, expected_value in expected.items():
            col_idx = header_map.get(header)
            if col_idx is None:
                continue
            current_value = sheet.cell(row=row, column=col_idx).value
            left = "" if current_value is None else str(current_value).strip()
            right = "" if expected_value is None else str(expected_value).strip()
            if left.casefold() != right.casefold():
                return False

        return True

    def _save(self, workbook: Workbook, output_path: Path) -> None:
        """
        Saves the workbook to the specified output path.

        Args:
            workbook: The openpyxl Workbook to save.
            output_path: Path where the resulting Excel file should be saved.

        Raises:
            ChronologyTemplateError: If the workbook fails to save.
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # DEBUG 4: Immediately before workbook.save()
        print("4. Immediately before workbook.save():")
        try:
            print("A5:", workbook.active.cell(5, 1).value)
            print("B5:", workbook.active.cell(5, 2).value)
        except Exception:
            pass

        try:
            workbook.save(filename=output_path)
            # DEBUG 5: Immediately after workbook.save()
            print("5. Immediately after workbook.save():")
            try:
                import openpyxl
                wb_reload = openpyxl.load_workbook(output_path)
                print("A5:", wb_reload.active.cell(5, 1).value)
                print("B5:", wb_reload.active.cell(5, 2).value)
            except Exception:
                pass
        except Exception as exc:
            raise ChronologyTemplateError(f"Failed to save Excel file to {output_path}: {exc}") from exc

    def _copy_row_format(self, sheet: Worksheet, source_row: int, target_row: int) -> None:
        """Copy style, dimensions, and merged-cell behavior from one row to another."""
        self._copy_row_dimensions(sheet, source_row, target_row)

        for column_idx in range(1, sheet.max_column + 1):
            source_cell = sheet.cell(row=source_row, column=column_idx)
            target_cell = sheet.cell(row=target_row, column=column_idx)

            if source_cell.has_style:
                target_cell._style = copy(source_cell._style)
            if source_cell.number_format:
                target_cell.number_format = source_cell.number_format
            if source_cell.font:
                target_cell.font = copy(source_cell.font)
            if source_cell.fill:
                target_cell.fill = copy(source_cell.fill)
            if source_cell.border:
                target_cell.border = copy(source_cell.border)
            if source_cell.alignment:
                target_cell.alignment = copy(source_cell.alignment)
            if source_cell.protection:
                target_cell.protection = copy(source_cell.protection)
            if source_cell.comment is not None:
                target_cell.comment = copy(source_cell.comment)
            if source_cell.hyperlink is not None:
                target_cell._hyperlink = copy(source_cell.hyperlink)

        merged_ranges = list(sheet.merged_cells.ranges)
        row_delta = target_row - source_row
        for merged_range in merged_ranges:
            if merged_range.min_row <= source_row <= merged_range.max_row:
                shifted_range = copy(merged_range)
                shifted_range.shift(row_shift=row_delta, col_shift=0)
                try:
                    sheet.merge_cells(str(shifted_range))
                except Exception:
                    continue

    def _copy_row_dimensions(self, sheet: Worksheet, source_row: int, target_row: int) -> None:
        """Copy row-level dimensions such as height and hidden state."""
        source_dimension = sheet.row_dimensions[source_row]
        target_dimension = sheet.row_dimensions[target_row]

        if source_dimension.height is not None:
            target_dimension.height = source_dimension.height
        if source_dimension.hidden is not None:
            target_dimension.hidden = source_dimension.hidden
        if source_dimension.outlineLevel is not None:
            target_dimension.outlineLevel = source_dimension.outlineLevel
        if source_dimension.collapsed is not None:
            target_dimension.collapsed = source_dimension.collapsed
        if hasattr(source_dimension, "style") and source_dimension.style is not None:
            try:
                target_dimension.style = source_dimension.style
            except Exception:
                pass

    @staticmethod
    def _normalize_header(value: Any) -> str:
        """
        Normalizes a header cell value for robust matching.

        Args:
            value: The raw cell value.

        Returns:
            The normalized header string.
        """
        if value is None:
            return ""
        
        text = str(value)
        
        # Replace whitespace variants with a standard space
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        
        # Replace unicode dashes with standard hyphen
        text = text.replace("–", "-").replace("—", "-")
        
        # Convert to lowercase
        text = text.lower()
        
        # Collapse multiple spaces into one
        text = re.sub(r"\s+", " ", text)
        
        # Remove spaces before and after hyphens
        text = re.sub(r"\s*-\s*", "-", text)
        
        # Strip trailing/leading spaces
        return text.strip()

    @staticmethod
    def safe_val(cell_val: Any) -> str:
        if cell_val is None:
            return ""
        if isinstance(cell_val, float) and cell_val.is_integer():
            return str(int(cell_val))
        return str(cell_val).strip()

    @staticmethod
    def _strip_field_prefix(value: str, field_name: str) -> str:
        """Strip leading field labels like 'PRODUCT NAME:' from parsed values."""
        return re.sub(rf"^{field_name}\s*:?\s*", "", value.strip(), flags=re.IGNORECASE)

    def _normalize_applicable_products(self, raw_products: list[str]) -> list[str]:
        """Split comma-separated product text into clean individual product names."""
        normalized: list[str] = []
        for raw in raw_products:
            text = self.safe_val(raw)
            if not text:
                continue
            text = self._strip_field_prefix(text, "PRODUCT\\s+NAME")
            for token in re.split(r"[,\uFF0C\u060C]+", text):
                name = self.safe_val(token)
                if name:
                    normalized.append(name)
        return normalized

    def _write_product_info(
        self,
        sheet: Worksheet,
        entry: ChronologyEntry,
        header_row_idx: int,
    ) -> ProductWriteResult | None:
        """
        Dynamically locates Product / Applicable Products headers and injects parsed product data.
        """
        
        if not entry.test_report_path or not entry.test_report_path.exists():
            return None

        parser = TestReportParser()
        info = parser.extract_product_info(entry.test_report_path)

        if info.parse_status != "Success":
            return None

        self._logger.info(
            f"[Chronology]\n"
            f"Firmware: {entry.testing_stage}\n"
            f"Signed Test Report: {entry.test_report_path.name}\n"
            f"Mode: {info.mode}\n"
            f"Series: {info.series_name or 'N/A'}\n"
            f"Products: {len(info.products)}\n"
            f"Status: {info.parse_status}"
        )

        if info.parse_status != "Success":
            return None

        product_label_row = 5
        product_label_col = 1
        product_value_col = 2  # Keep as 2 to satisfy verification and layout rules
        
        # Dynamically find the row that has 'Product' or 'Product Series'
        for r in range(1, 20):
            val = self._normalize_header(sheet.cell(row=r, column=1).value)
            if "product" in val:
                product_label_row = r
                break
                
        applicable_label_row = product_label_row + 1
        products_start_row = product_label_row + 2

        product_label_text = "Product Series:" if info.mode == "Series" else "Product:"

        # Unmerge any existing ranges in rows 5 and 6
        for m_range in list(sheet.merged_cells.ranges):
            if m_range.min_row in (product_label_row, applicable_label_row):
                try:
                    sheet.unmerge_cells(str(m_range))
                except Exception:
                    pass

        # We can merge B5 onwards to give the product value more space.
        # But for the labels in col 1, we just disable wrap text so they overflow gracefully,
        # or we increase the column width slightly if needed.
        sheet.merge_cells(start_row=product_label_row, start_column=2, end_row=product_label_row, end_column=8)
        # For Applicable Products, merge A6:H6 since the whole row is just the label.
        sheet.merge_cells(start_row=applicable_label_row, start_column=1, end_row=applicable_label_row, end_column=8)

        def _format_label(row: int, col: int, text: str) -> None:
            cell = self._get_writable_cell(sheet, row, col)
            cell.value = text
            self._set_cell_bold(sheet, row, col)
            if cell.alignment:
                align = copy(cell.alignment)
            else:
                from openpyxl.styles import Alignment
                align = Alignment()
            align.wrap_text = False
            align.horizontal = "left"
            align.vertical = "center"
            cell.alignment = align

        _format_label(product_label_row, product_label_col, product_label_text)
        product_target = self._get_writable_cell(sheet, product_label_row, product_value_col)
        product_row, product_col = product_target.row, product_target.column

        series_name = self._strip_field_prefix(self.safe_val(info.series_name or ""), "PRODUCT\\s+SERIES")
        single_product = self._strip_field_prefix(self.safe_val(info.single_product or ""), "PRODUCT")

        val_to_write = series_name if info.mode == "Series" else single_product
        if not val_to_write and info.products:
            first_products = self._normalize_applicable_products(info.products)
            if first_products:
                val_to_write = first_products[0]
        if not val_to_write:
            raise ChronologyTemplateError("Parsed product information is empty; cannot populate Product section.")

        product_target.value = val_to_write
        self._set_cell_bold(sheet, product_row, product_col)
        
        # Ensure the value cell doesn't wrap either
        if product_target.alignment:
            p_align = copy(product_target.alignment)
        else:
            from openpyxl.styles import Alignment
            p_align = Alignment()
        p_align.wrap_text = False
        p_align.horizontal = "left"
        p_align.vertical = "center"
        product_target.alignment = p_align
        
        # Widen Column A significantly to prevent LibreOffice from truncating 'Product Series:'
        sheet.column_dimensions['A'].width = 25.0
        sheet.column_dimensions['B'].width = 25.0

        self._logger.info(
            "Wrote Product value at %s%s = %r",
            openpyxl.utils.get_column_letter(product_col),
            product_row,
            val_to_write,
        )

        applicable_writes: list[tuple[int, int, int, str]] = []
        applicable_label_cell: tuple[int, int] | None = None
        if info.mode == "Series":
            applicable_label_cell = (applicable_label_row, 1)
            applicable_col = 1
            products = self._normalize_applicable_products(info.products)
            if not products:
                raise ChronologyTemplateError("Series mode detected but parser returned no applicable products.")

            original_header_row = header_row_idx
            # Calculate table_start_row = last_product_row + 2 
            # where last_product_row = applicable_label_row + number_of_products
            last_product_row = applicable_label_row + len(products)
            required_header_row = last_product_row + 2
            rows_to_insert = max(0, required_header_row - original_header_row)

            rows_inserted = 0
            if rows_to_insert > 0:
                insert_idx = original_header_row

                ranges_to_shift = []
                for merged_range in list(sheet.merged_cells.ranges):
                    if merged_range.min_row >= insert_idx:
                        sheet.unmerge_cells(str(merged_range))
                        shifted = copy(merged_range)
                        shifted.shift(row_shift=rows_to_insert, col_shift=0)
                        ranges_to_shift.append(shifted)

                # Insert below A6 by inserting at the chronology header row.
                sheet.insert_rows(insert_idx, amount=rows_to_insert)
                self._shift_row_breaks(sheet, insert_idx, rows_to_insert)

                for shifted_range in ranges_to_shift:
                    try:
                        sheet.merge_cells(str(shifted_range))
                    except Exception as exc:
                        self._logger.warning("Failed to reapply merged range %s: %s", shifted_range, exc)

                # Preserve template formatting for inserted rows.
                for offset in range(rows_to_insert):
                    self._copy_row_format(sheet, products_start_row, insert_idx + offset)

                self._logger.info("Rows Inserted below A6: %s", rows_to_insert)
                rows_inserted = rows_to_insert

            new_header_row = original_header_row + rows_inserted

            # Clear the entire product block area so no template/test-report rows leak into it.
            for clear_row in range(product_label_row, new_header_row):
                for clear_col in range(1, sheet.max_column + 1):
                    self._get_writable_cell(sheet, clear_row, clear_col).value = ""

            # Write labels after all row shifts so anchors are final.
            _format_label(product_label_row, product_label_col, product_label_text)
            _format_label(product_row, product_col, val_to_write)
            _format_label(applicable_label_row, 1, "Applicable Products:")
            # Do NOT clear col 2 and 3 here because they resolve to the merged A6 cell and clear it!

            first_product_row = products_start_row
            write_end_row = first_product_row + len(products) - 1
            if write_end_row >= new_header_row:
                raise ChronologyTemplateError(
                    "Applicable products would overwrite chronology header; insertion sizing failed."
                )

            style_source_row = self._resolve_product_style_source_row(
                sheet,
                products_start_row,
                new_header_row,
                header_row_idx,
            )

            for i, prod_name in enumerate(products):
                r = first_product_row + i
                # Additional rows reuse previous product-row formatting.
                if i == 0:
                    self._copy_product_row_style(sheet, style_source_row, r)
                else:
                    self._copy_product_row_style(sheet, r - 1, r)
                idx_cell = self._get_writable_cell(sheet, r, applicable_col)
                name_cell = self._get_writable_cell(sheet, r, applicable_col + 1)
                idx_cell.value = i + 1
                name_cell.value = prod_name
                applicable_writes.append((idx_cell.row, idx_cell.column, i + 1, prod_name))
                self._logger.info(
                    "Wrote Applicable Product #%s at %s%s/%s%s = %r",
                    i + 1,
                    openpyxl.utils.get_column_letter(idx_cell.column),
                    idx_cell.row,
                    openpyxl.utils.get_column_letter(name_cell.column),
                    name_cell.row,
                    prod_name,
                )

            # Required console verification counters.
            print(f"Parsed products: {len(products)}")
            print(f"Rows inserted: {rows_inserted}")
            print(f"Original chronology header row: {original_header_row}")
            print(f"New chronology header row: {new_header_row}")
            print(f"First row written: {first_product_row}")
            print(f"Last row written: {write_end_row}")
            print(f"Rows written: {len(products)}")

        else:
            # Single-product layout: keep chronology table position unchanged.
            for clear_row in range(6, header_row_idx):
                self._get_writable_cell(sheet, clear_row, 1).value = ""
                self._get_writable_cell(sheet, clear_row, 2).value = ""

        return ProductWriteResult(
            mode=info.mode,
            product_cell=(product_row, product_col),
            product_value=val_to_write,
            applicable_label_cell=applicable_label_cell,
            applicable_rows=applicable_writes,
        )

    def _verify_product_write(self, output_path: Path, write_result: ProductWriteResult) -> None:
        """Reopen saved workbook and verify Product section values are physically persisted."""
        wb = openpyxl.load_workbook(output_path)
        ws = wb.active
        if ws is None:
            wb.close()
            raise ChronologyTemplateError("Failed to verify Product write: workbook has no active sheet.")

        product_row = 5
        for r in range(1, 20):
            val = self._normalize_header(ws.cell(row=r, column=1).value)
            if "product" in val:
                product_row = r
                break

        product_col = 2
        
        # Verify the label itself was persisted correctly
        persisted_label = self.safe_val(ws.cell(row=product_row, column=1).value)
        expected_label = "Product Series:" if write_result.mode == "Series" else "Product:"
        if persisted_label != expected_label:
            wb.close()
            raise ChronologyTemplateError(
                f"Product label verification failed at A{product_row}: "
                f"expected {expected_label!r}, found {persisted_label!r}"
            )

        persisted_product = self.safe_val(ws.cell(row=product_row, column=product_col).value)
        if persisted_product != self.safe_val(write_result.product_value):
            wb.close()
            raise ChronologyTemplateError(
                f"Product value verification failed at {openpyxl.utils.get_column_letter(product_col)}{product_row}: "
                f"expected {write_result.product_value!r}, found {persisted_product!r}"
            )

        if write_result.applicable_rows:
            applicable_col = 1
            applicable_label_row = product_row + 1
            start_row = product_row + 2
            applicable_label = self.safe_val(ws.cell(row=applicable_label_row, column=1).value)
            if applicable_label.rstrip(":").casefold() != "applicable products":
                wb.close()
                raise ChronologyTemplateError(f"Applicable Products label verification failed at A{applicable_label_row}. Found: {applicable_label!r}")
            for offset, (_, _, expected_num, expected_name) in enumerate(write_result.applicable_rows):
                row_idx = start_row + offset
                persisted_num = self.safe_val(ws.cell(row=row_idx, column=applicable_col).value)
                persisted_name = self.safe_val(ws.cell(row=row_idx, column=applicable_col + 1).value)
                if persisted_num != str(expected_num) or persisted_name != self.safe_val(expected_name):
                    wb.close()
                    raise ChronologyTemplateError(
                        f"Applicable product verification failed at "
                        f"{openpyxl.utils.get_column_letter(applicable_col)}{row_idx}/"
                        f"{openpyxl.utils.get_column_letter(applicable_col + 1)}{row_idx}: "
                        f"expected ({expected_num!r}, {expected_name!r}), "
                        f"found ({persisted_num!r}, {persisted_name!r})"
                    )

        wb.close()

        self._logger.info(
            "Verified Product section after reopen at %s%s",
            openpyxl.utils.get_column_letter(product_col),
            product_row,
        )

    def _copy_product_row_style(self, sheet: Worksheet, source_row: int, target_row: int) -> None:
        """Copy row height and A/B cell style from template product row to target row."""
        self._copy_row_dimensions(sheet, source_row, target_row)
        for col_idx in (1, 2):
            source_cell = sheet.cell(row=source_row, column=col_idx)
            target_cell = sheet.cell(row=target_row, column=col_idx)
            if source_cell.has_style:
                target_cell._style = copy(source_cell._style)
            if source_cell.number_format:
                target_cell.number_format = source_cell.number_format
            if source_cell.font:
                target_cell.font = copy(source_cell.font)
            if source_cell.fill:
                target_cell.fill = copy(source_cell.fill)
            if source_cell.border:
                target_cell.border = copy(source_cell.border)
            if source_cell.alignment:
                target_cell.alignment = copy(source_cell.alignment)

        # Keep table-like alignment consistent for generated product rows.
        idx_cell = sheet.cell(row=target_row, column=1)
        name_cell = sheet.cell(row=target_row, column=2)
        idx_alignment = copy(idx_cell.alignment) if idx_cell.alignment else None
        name_alignment = copy(name_cell.alignment) if name_cell.alignment else None
        if idx_alignment is not None:
            idx_alignment.horizontal = "center"
            idx_alignment.vertical = "center"
            idx_cell.alignment = idx_alignment
        if name_alignment is not None:
            name_alignment.horizontal = "left"
            name_alignment.vertical = "center"
            name_cell.alignment = name_alignment

    def _set_cell_bold(self, sheet: Worksheet, row: int, col: int) -> None:
        """Force bold on a writable cell while preserving existing font attributes."""
        cell = self._get_writable_cell(sheet, row, col)
        if cell.font:
            updated_font = copy(cell.font)
            updated_font.bold = True
            cell.font = updated_font
        else:
            cell.font = Font(bold=True)

    def _resolve_product_style_source_row(
        self,
        sheet: Worksheet,
        start_row: int,
        header_row: int,
        original_header_row: int,
    ) -> int:
        """Find nearest row with usable A/B styling to reuse for product rows."""
        candidates = list(range(start_row, min(header_row, sheet.max_row + 1)))
        candidates.extend(range(header_row, min(header_row + 10, sheet.max_row + 1)))
        if original_header_row not in candidates and 1 <= original_header_row <= sheet.max_row:
            candidates.append(original_header_row)

        def has_style_or_border(row_idx: int) -> bool:
            for col_idx in (1, 2):
                cell = sheet.cell(row=row_idx, column=col_idx)
                if cell.has_style:
                    return True
                border = cell.border
                if border and (
                    border.left.style
                    or border.right.style
                    or border.top.style
                    or border.bottom.style
                ):
                    return True
            return False

        for row_idx in candidates:
            if has_style_or_border(row_idx):
                return row_idx

        return start_row

    def _write_signoff_fields(self, sheet: Worksheet, entry: ChronologyEntry, history_row: int) -> None:
        """
        Scans rows below the chronology data table for sign-off cells
        and replaces the template demo value with the actual personnel names.
        """
        if not entry.prepared_by and not entry.checked_by and not entry.approved_by:
            return

        updates = {
            "prepared by": ("Prepared By:", entry.prepared_by),
            "checked by": ("Checked By:", entry.checked_by),
            "approved by": ("Approved By:", entry.approved_by),
        }

        start_row = max(1, history_row)
        for row in range(start_row, min(start_row + 100, sheet.max_row + 1)):
            for col in range(1, min(sheet.max_column + 1, 10)):
                cell = self._get_writable_cell(sheet, row, col)
                val = str(cell.value or "").strip().lower()
                
                for key, (label, name) in updates.items():
                    if val.startswith(key):
                        new_val = f"{label} {name}".strip()
                        cell.value = new_val
                        self._logger.info(
                            "Updated signoff cell %s%s with %r",
                            openpyxl.utils.get_column_letter(cell.column),
                            cell.row,
                            new_val
                        )
                        break

    def _update_page_header_from_signed_report(self, sheet: Worksheet, signed_pdf_path: Path) -> None:
        """Update only page header fields using the corresponding signed test report."""
        parser = TestReportParser()
        department_code = parser.extract_department_code(signed_pdf_path)
        if not department_code:
            self._logger.warning(
                "Could not extract department code from signed report; keeping existing page header unchanged: %s",
                signed_pdf_path,
            )
            return

        department_code = self._decode_excel_newlines(self.safe_val(department_code)).strip()
        self._last_department_code = department_code

        today_text = datetime.now().strftime("%d/%m/%Y")

        # Left header: fixed company line + dynamic DDHW suffix.
        left_text = self._decode_excel_newlines(
            f"Selec Controls Pvt Ltd{self.EXCEL_HEADER_LINE_BREAK}{department_code}"
        )

        # Right header: keep existing code text and refresh Date line only.
        def refresh_right_text(original: str) -> str:
            base = self._decode_excel_newlines(self.safe_val(original))
            if not base:
                base = "FF/PM/DD-1120724"

            if re.search(r"(?i)Date\s*:", base):
                updated = re.sub(r"(?i)Date\s*:\s*[^\n\r]*", f"Date : {today_text}", base)
                return self._decode_excel_newlines(updated)

            if "FF/PM/DD-1120724" in base:
                return self._decode_excel_newlines(
                    f"FF/PM/DD-1120724{self.EXCEL_HEADER_LINE_BREAK}Date : {today_text}"
                )

            return self._decode_excel_newlines(
                f"{base}{self.EXCEL_HEADER_LINE_BREAK}Date : {today_text}"
            )

        for header in (sheet.oddHeader, sheet.evenHeader, sheet.firstHeader):
            header.left.text = left_text
            header.right.text = refresh_right_text(header.right.text)

        center_text = self._decode_excel_newlines(self.safe_val(sheet.oddHeader.center.text))
        if not center_text:
            center_text = "Title- Ladder Release Chronology"
            for header in (sheet.oddHeader, sheet.evenHeader, sheet.firstHeader):
                header.center.text = center_text

        self._native_header_override = {
            "left": left_text,
            "center": center_text,
            "right": refresh_right_text(sheet.oddHeader.right.text),
        }

        self._logger.info(
            "Updated page header from signed report: left=%r right-date=%s",
            department_code,
            today_text,
        )

    @staticmethod
    def _decode_excel_newlines(text: str) -> str:
        """Convert escaped/newline tokens into LibreOffice-compatible header line breaks."""
        line_sep = ChronologyExcelWriter.EXCEL_HEADER_LINE_BREAK
        normalized = text.replace("\\n", line_sep)
        normalized = re.sub(r"(?i)_x000a_", line_sep, normalized)
        normalized = re.sub(r"(?i)_x000d_", "", normalized)
        normalized = normalized.replace("\r\n", line_sep).replace("\r", line_sep)
        normalized = normalized.replace("&10", line_sep)
        parts = [part.strip() for part in normalized.split(line_sep)]
        parts = [part for part in parts if part]
        return line_sep.join(parts)

    def _shift_row_breaks(self, sheet: Worksheet, start_row: int, delta: int) -> None:
        """Shift manual row breaks after row insert/delete to preserve print pagination."""
        if delta == 0:
            return
        try:
            for brk in getattr(sheet.row_breaks, "brk", []):
                if getattr(brk, "id", None) is not None and brk.id >= start_row:
                    brk.id = max(1, brk.id + delta)
        except Exception:
            return

    def _refresh_print_layout(self, sheet: Worksheet) -> None:
        """Keep print area aligned with updated worksheet dimensions for PDF export."""
        max_row = max(1, sheet.max_row)
        max_col = max(1, sheet.max_column)
        end_col = get_column_letter(max_col)

        if sheet.print_area:
            first = sheet.print_area[0]
            m = re.match(r"\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)", str(first))
            if m:
                start_col, start_row = m.group(1), int(m.group(2))
                start_col = start_col or "A"
                start_row = max(1, start_row)
                sheet.print_area = f"${start_col}${start_row}:${end_col}${max_row}"
                return

        sheet.print_area = f"$A$1:${end_col}${max_row}"