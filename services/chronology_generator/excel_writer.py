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
import re
from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from services.chronology_generator.models import ChronologyEntry, ProjectChronology


class ChronologyTemplateError(Exception):
    """
    Raised when the provided Excel template is invalid or missing required headers.
    """


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

    def __init__(self, template_path: Path) -> None:
        """
        Initialize the Excel writer.

        Args:
            template_path: Path to the existing Excel template.
        """
        self._template_path = template_path
        self._logger = logging.getLogger(__name__)

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

        workbook = self._load_workbook()
        sheet = workbook.active

        if sheet is None:
            raise ChronologyTemplateError("Template workbook contains no active worksheet.")

        header_row_idx = self._find_header_row(sheet)
        header_map = self._build_header_map(sheet, header_row_idx)
        first_data_row = self._first_data_row(header_row_idx)

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

        self._save(workbook, output_path)
        self._logger.info("Chronology Excel export completed successfully.")

    def _is_existing_workbook(self, output_path: Path) -> bool:
        if not output_path.exists():
            return False
        try:
            return output_path.resolve() == self._template_path.resolve()
        except Exception:
            return output_path == self._template_path

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
            "testing stage": entry.testing_stage,
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
            self._copy_row_dimensions(sheet, start_row, row_index)
            serial_cell = self._get_writable_cell(sheet, row_index, serial_column)
            serial_cell.value = serial_no
            serial_no -= 1

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
        
        try:
            workbook.save(filename=output_path)
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