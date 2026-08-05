"""
validators.chronology_validator
===============================

Validates the Chronology folder.

Responsibilities
----------------
- Verify the Chronology folder exists.
- Verify it is accessible.
- Verify it contains at least one file.
- Cache metadata if required.
- Return a ValidationResult.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz
import pdfplumber

from config import FOLDER_KEYS
from core.base_validator import BaseValidator
from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStep
from services.file_search import FileSearchService


class ChronologyValidator(BaseValidator):
    """
    Validates the Chronology folder.
    """

    def __init__(
        self,
        file_search: FileSearchService,
    ) -> None:

        super().__init__(ValidationStep.CHRONOLOGY)

        self._file_search = file_search

    def validate(
        self,
        context: ValidationContext,
    ) -> ValidationResult:
        """
        Execute chronology validation.

        Parameters
        ----------
        context
            Shared validation context.

        Returns
        -------
        ValidationResult
        """

        self.logger.info(
            "Starting chronology validation."
        )

        chronology_folder = context.folders.get(
            FOLDER_KEYS["chronology"]
        )

        if chronology_folder is None:

            return self.skipped_result(
                reason="Chronology folder unavailable.",
            )

        try:

            files = self._file_search.recursive_files(
                chronology_folder,
                None,
            )

        except Exception as exc:

            return self.fail_result(
                reason="Unable to read Chronology folder.",
                checked_path=chronology_folder,
                details={
                    "exception": str(exc),
                },
            )

        discovered_folders = [
            relative_path
            for relative_path, _ in context.discovered_paths
        ]

        stages = []
        failures: list[str] = []

        for relative_path in discovered_folders:
            stage_path = chronology_folder / Path(*relative_path.split("/"))
            expected_stage_name = Path(relative_path).name
            expected_bin_path = context.bin_files.get(relative_path)

            if not stage_path.exists() or not stage_path.is_dir():
                error_msg = f"Stage directory missing for {relative_path}"
                failures.append(error_msg)
                stages.append(self._create_empty_stage_dict(
                    board=None,
                    stage=expected_stage_name,
                    result="FAIL",
                    errors=["Stage directory missing."]
                ))
                continue

            chronology_pdf = self._resolve_chronology_pdf(stage_path)
            if chronology_pdf is None:
                error_msg = f"Missing Chronology PDF for {relative_path.replace('/', ' / ')}."
                failures.append(error_msg)
                stages.append(self._create_empty_stage_dict(
                    board=None,
                    stage=expected_stage_name,
                    result="FAIL",
                    errors=["Missing Chronology PDF."]
                ))
                continue

            metadata = self._extract_metadata(chronology_pdf)

            board = metadata.get("board")
            extracted_stage = metadata.get("stage")

            raw_latest_bin = metadata.get("bin_file")
            latest_bin = self._normalize_filename_for_display(raw_latest_bin)
            
            latest_version = metadata.get("version")
            latest_release_date = metadata.get("release_date")
            latest_crc_raw = metadata.get("crc")
            latest_reason = metadata.get("reason_for_upgrade")

            prev_bin = metadata.get("previous_bin_file")
            prev_version = metadata.get("previous_version")
            prev_release_date = metadata.get("previous_release_date")
            prev_crc_raw = metadata.get("previous_crc")

            stage_validation_errors: list[str] = []

            if expected_bin_path is not None:
                self._apply_legacy_metadata_checks(
                    expected_stage_name=expected_stage_name,
                    extracted_stage=extracted_stage,
                    latest_bin=latest_bin,
                    latest_version=latest_version,
                    expected_bin_path=expected_bin_path,
                    stage_validation_errors=stage_validation_errors,
                )

            overall_result = "PASS" if not stage_validation_errors else "FAIL"

            previous_firmware = None
            if prev_bin or prev_version or prev_release_date or prev_crc_raw:
                previous_firmware = {
                    "bin_file": prev_bin,
                    "version": prev_version,
                    "release_date": prev_release_date,
                    "crc": prev_crc_raw,
                }

            stage_dict = {
                "board": board,
                "stage": extracted_stage,
                # Backward-compatible top-level keys retained for existing report/tests.
                "bin_file": latest_bin,
                "version": latest_version,
                "release_date": latest_release_date,
                "reason_for_upgrade": latest_reason,
                "crc": latest_crc_raw,
                "computed_crc": None,
                "crc_match": None,
                "latest_firmware": {
                    "bin_file": latest_bin,
                    "version": latest_version,
                    "release_date": latest_release_date,
                    "crc": latest_crc_raw,
                    "reason_for_upgrade": latest_reason,
                },
                "previous_firmware": previous_firmware,
                "validation": {
                    "crc": {
                        "chronology_crc": latest_crc_raw,
                        "ladder_crc": None,
                        "bin_crc": None,
                        "result": "NOT_CHECKED",
                    },
                },
                "overall_result": overall_result,
                "failure_reasons": stage_validation_errors,
            }
            
            stages.append(stage_dict)

            if overall_result == "FAIL":
                failures.extend(
                    f"{relative_path.replace('/', ' / ')}: {err}"
                    for err in stage_validation_errors
                )

        context.set_metadata("chronology_stages", stages)

        details = {
            "folder": chronology_folder.name,
            "file_count": len(files),
            "files": [
                file.name
                for file in files
            ],
            "discovered_ladder_folders": discovered_folders,
            "stages": stages,
        }

        if failures:
            self.logger.info(
                f"Chronology validation failed ({len(failures)} issue(s))."
            )
            return self.fail_result(
                reason="; ".join(failures),
                checked_path=chronology_folder,
                details=details,
            )

        self.logger.info(
            f"Chronology validation passed ({len(files)} files found)."
        )

        return self.pass_result(
            reason="Chronology folder validated successfully.",
            checked_path=chronology_folder,
            details=details,
        )

    @staticmethod
    def _apply_legacy_metadata_checks(
        expected_stage_name: str,
        extracted_stage: str | None,
        latest_bin: str | None,
        latest_version: str | None,
        expected_bin_path: Path,
        stage_validation_errors: list[str],
    ) -> None:
        if extracted_stage and extracted_stage.casefold() != expected_stage_name.casefold():
            stage_validation_errors.append(
                f"Testing Stage mismatch. Expected {expected_stage_name}. Found {extracted_stage}."
            )

        expected_bin_name = expected_bin_path.name
        if latest_bin is None:
            stage_validation_errors.append("BIN filename missing in chronology.")
        elif not ChronologyValidator._same_filename_loose(latest_bin, expected_bin_name):
            stage_validation_errors.append(
                f"BIN filename mismatch. Expected {expected_bin_name}. Found {latest_bin}."
            )

        expected_version = ChronologyValidator._extract_version_from_name(expected_bin_name)
        if expected_version and latest_version and expected_version.casefold() != latest_version.casefold():
            stage_validation_errors.append(
                f"Version mismatch. Expected {expected_version}. Found {latest_version}."
            )

    @staticmethod
    def _same_filename_loose(left: str, right: str) -> bool:
        def normalize(name: str) -> str:
            base = Path(name).name
            return re.sub(r"[^a-z0-9]", "", base.casefold())

        return normalize(left) == normalize(right)

    def _create_empty_stage_dict(
        self,
        board: str | None,
        stage: str | None,
        result: str,
        errors: list[str],
    ) -> dict:
        """Helper to create a unified missing/failed stage dictionary without duplicated keys."""
        return {
            "board": board,
            "stage": stage,
            "latest_firmware": {
                "bin_file": None,
                "version": None,
                "release_date": None,
                "crc": None,
                "reason_for_upgrade": None,
            },
            "previous_firmware": None,
            "validation": {
                "crc": {
                    "chronology_crc": None,
                    "generated_crc": None,
                    "result": "FAIL",
                },
            },
            "overall_result": result,
            "failure_reasons": errors,
        }

    @staticmethod
    def _extract_metadata(file_path: Path | None) -> dict[str, str | None]:
        if file_path is None:
            return {
                "board": None,
                "stage": None,
                "bin_file": None,
                "version": None,
                "release_date": None,
                "reason_for_upgrade": None,
            }

        try:
            document = fitz.open(file_path)
        except Exception:
            return {
                "board": None,
                "stage": None,
                "bin_file": None,
                "version": None,
                "release_date": None,
                "reason_for_upgrade": None,
            }

        try:
            text = "\n".join(page.get_text("text") for page in document if page.get_text("text"))
        finally:
            document.close()

        normalized = ChronologyValidator._normalize_text(text)
        lines = [line for line in normalized.splitlines() if line]

        metadata: dict[str, str | None] = {
            "testing_stage": None,
            "board": None,
            "stage": None,
            "bin_file": None,
            "version": None,
            "release_date": None,
            "reason_for_upgrade": None,
            "previous_version": None,
            "previous_release_date": None,
            "previous_bin_file": None,
            "previous_crc": None,
            "crc": None,
        }

        table_rows = ChronologyValidator._extract_table_rows(file_path)
        if table_rows:
            first_row = table_rows[0]
            metadata["testing_stage"] = first_row.get("testing_stage")
            metadata["board"], metadata["stage"] = ChronologyValidator._split_testing_stage(first_row.get("testing_stage"))
            metadata["bin_file"] = first_row.get("bin_file")
            metadata["version"] = first_row.get("version")
            metadata["release_date"] = first_row.get("release_date")
            metadata["reason_for_upgrade"] = first_row.get("reason_for_upgrade")
            metadata["crc"] = first_row.get("crc")

            if len(table_rows) > 1:
                previous_row = table_rows[1]
                metadata["previous_version"] = previous_row.get("version")
                metadata["previous_release_date"] = previous_row.get("release_date")
                metadata["previous_bin_file"] = previous_row.get("bin_file")
                metadata["previous_crc"] = previous_row.get("crc")

            return metadata

        try:
            document = fitz.open(file_path)
        except Exception:
            return metadata

        try:
            text = "\n".join(page.get_text("text") for page in document if page.get_text("text"))
        finally:
            document.close()

        normalized = ChronologyValidator._normalize_text(text)
        lines = [line for line in normalized.splitlines() if line]

        metadata["crc"] = ChronologyValidator._extract_crc_value(normalized)
        data_lines = ChronologyValidator._extract_data_lines(lines)
        if data_lines:
            board, stage, remaining = ChronologyValidator._split_first_data_row(data_lines)
            metadata["board"] = board
            metadata["stage"] = stage

            parsed_values = ChronologyValidator._parse_rows(remaining)
            metadata["bin_file"] = parsed_values.get("bin_file")
            metadata["version"] = parsed_values.get("version")
            metadata["release_date"] = parsed_values.get("release_date")
            metadata["reason_for_upgrade"] = parsed_values.get("reason_for_upgrade")
            metadata["previous_version"] = parsed_values.get("previous_version")
            metadata["previous_release_date"] = parsed_values.get("previous_release_date")
            metadata["previous_bin_file"] = parsed_values.get("previous_bin_file")
            metadata["previous_crc"] = parsed_values.get("previous_crc")

        return metadata

    @staticmethod
    def _normalize_text(text: str) -> str:
        lines = []
        for raw_line in text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if line:
                lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _extract_data_lines(lines: list[str]) -> list[str]:
        header_indices = [
            index
            for index, line in enumerate(lines)
            if ChronologyValidator._is_header_line(line)
        ]
        if not header_indices:
            return []

        data_lines = [line for line in lines[header_indices[-1] + 1:] if line]
        if not data_lines:
            return []

        crc_labels = {
            "crc",
            "crc32",
            "crc64",
            "checksum",
            "crc value",
            "crc32 value",
            "checksum value",
        }

        first_line = data_lines[0].casefold()
        if first_line in crc_labels:
            if len(data_lines) > 1 and re.fullmatch(r"(0x[0-9A-Fa-f]+|\d+)", data_lines[1].strip()):
                data_lines = data_lines[2:]
        elif re.search(r"^(crc|crc32|crc64|checksum)\b.*(0x[0-9A-Fa-f]+|\d+)", data_lines[0], re.IGNORECASE):
            data_lines = data_lines[1:]

        return data_lines

    @staticmethod
    def _is_header_line(value: str) -> bool:
        normalized = value.casefold()
        return normalized in {
            "board",
            "testing stage",
            "bin file",
            "version",
            "release date",
            "reason for upgrade",
        }

    @staticmethod
    def _split_first_data_row(lines: list[str]) -> tuple[str | None, str | None, list[str]]:
        if not lines:
            return None, None, []

        board = lines[0] if len(lines) > 0 else None
        stage = lines[1] if len(lines) > 1 else None
        remaining = lines[2:]
        return board, stage, remaining

    @staticmethod
    def _parse_rows(lines: list[str]) -> dict[str, str | None]:
        values: dict[str, str | None] = {
            "bin_file": None,
            "version": None,
            "release_date": None,
            "reason_for_upgrade": None,
            "previous_version": None,
            "previous_release_date": None,
            "previous_bin_file": None,
        }
        if not lines:
            return values

        rows = []
        version_indices = [
            index
            for index, line in enumerate(lines)
            if ChronologyValidator._is_version_value(line)
        ]
        if not version_indices:
            return values

        for version_index in version_indices:
            date_index = None
            for index in range(version_index + 1, len(lines)):
                if ChronologyValidator._is_release_date_value(lines[index]):
                    date_index = index
                    break
            if date_index is None:
                continue

            bin_parts: list[str] = []
            for index in range(version_index - 1, -1, -1):
                line = lines[index]
                if not line:
                    continue
                if ChronologyValidator._is_version_value(line) or ChronologyValidator._is_release_date_value(line):
                    break
                if not bin_parts:
                    bin_parts.append(line)
                    continue
                if bin_parts[-1].endswith("_"):
                    bin_parts[-1] = bin_parts[-1].rstrip("_") + "_" + line
                else:
                    bin_parts.append(line)
            bin_parts.reverse()

            if not bin_parts:
                for index in range(version_index - 1, -1, -1):
                    line = lines[index]
                    if not line:
                        continue
                    if ChronologyValidator._is_version_value(line) or ChronologyValidator._is_release_date_value(line):
                        break
                    if not bin_parts:
                        bin_parts.append(line)
                        continue
                    if bin_parts[-1].endswith("_"):
                        bin_parts[-1] = bin_parts[-1].rstrip("_") + "_" + line
                    else:
                        bin_parts.append(line)
                bin_parts.reverse()

            joined_bin_name = "".join(bin_parts).strip()
            joined_bin_name = re.sub(r"\s+", " ", joined_bin_name)

            reason_lines = []
            for index in range(date_index + 1, len(lines)):
                if ChronologyValidator._is_version_value(lines[index]):
                    break
                if ChronologyValidator._is_release_date_value(lines[index]):
                    break
                reason_lines.append(lines[index])

            rows.append(
                {
                    "bin_file": joined_bin_name if joined_bin_name else None,
                    "version": lines[version_index].strip(),
                    "release_date": lines[date_index].strip(),
                    "reason_for_upgrade": " ".join(reason_lines).strip() if reason_lines else None,
                }
            )

        if not rows:
            return values

        latest_row = rows[0]
        previous_row = rows[1] if len(rows) > 1 else None

        values["bin_file"] = latest_row.get("bin_file")
        values["version"] = latest_row.get("version")
        values["release_date"] = latest_row.get("release_date")
        values["reason_for_upgrade"] = latest_row.get("reason_for_upgrade")
        values["crc"] = latest_row.get("crc")

        if previous_row:
            values["previous_version"] = previous_row.get("version")
            values["previous_release_date"] = previous_row.get("release_date")
            values["previous_bin_file"] = previous_row.get("bin_file")
            values["previous_crc"] = previous_row.get("crc")

        return values

    @staticmethod
    def _extract_crc_value(text: str) -> str | None:
        if not text:
            return None

        normalized = re.sub(r"\s+", " ", text).strip()
        patterns = [
            r"\b(?:crc|crc32|crc64|checksum|crc value|crc32 value|checksum value)\b\s*[:=]?\s*(0x[0-9A-Fa-f]+|\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        crc_labels = {
            "crc",
            "crc32",
            "crc64",
            "checksum",
            "crc value",
            "crc32 value",
            "checksum value",
        }

        for index, line in enumerate(lines):
            if line.casefold() in crc_labels and index + 1 < len(lines):
                candidate = lines[index + 1]
                match = re.search(r"(0x[0-9A-Fa-f]+|\d+)", candidate)
                if match:
                    return match.group(1).upper()

        return None

    @staticmethod
    def _parse_crc_value(value: str | None) -> int | None:
        if value is None:
            return None

        match = re.search(r"(0x[0-9A-Fa-f]+|\d+)", value.strip(), re.IGNORECASE)
        if not match:
            return None

        candidate = match.group(1)
        try:
            return int(candidate, 0)
        except ValueError:
            return None

    @staticmethod
    def _extract_table_rows(file_path: Path) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []

        try:
            with pdfplumber.open(file_path) as document:
                for page in document.pages:
                    tables = []
                    found_tables = page.find_tables() or []
                    for table_obj in found_tables:
                        try:
                            tables.append(table_obj.extract())
                        except Exception:
                            continue

                    if not tables:
                        tables.extend(page.extract_tables() or [])

                    for table in tables:
                        if not table or len(table) < 2:
                            continue

                        header_row = table[0]
                        header_map = ChronologyValidator._normalize_table_headers(header_row)
                        if not ChronologyValidator._has_table_headers(header_map):
                            continue

                        for row in table[1:]:
                            if not row or not any(cell and str(cell).strip() for cell in row):
                                continue

                            parsed_row = ChronologyValidator._parse_table_row(row, header_map)
                            if parsed_row:
                                rows.append(parsed_row)

        except Exception:
            return []

        return rows

    @staticmethod
    def _normalize_table_headers(header_row: list[str | None]) -> dict[int, str]:
        header_map: dict[int, str] = {}
        for index, header in enumerate(header_row):
            normalized = ChronologyValidator._normalize_header(header)
            if not normalized:
                continue
            if normalized in {
                "testing stage",
                "stage",
                "testing_stage",
                "testingstage",
            }:
                header_map[index] = "testing_stage"
            elif normalized in {"bin file", "bin", "bin_file", "binfile"}:
                header_map[index] = "bin_file"
            elif normalized in {"crc", "crc32", "crc64", "checksum", "checksum value", "crc value", "crc32 value"}:
                header_map[index] = "crc"
            elif normalized in {"version"}:
                header_map[index] = "version"
            elif normalized in {"release date", "releasedate", "release_date"}:
                header_map[index] = "release_date"
            elif normalized in {"reason for upgrade", "reason", "reasonforupgrade", "remarks", "comments"}:
                header_map[index] = "reason_for_upgrade"

        return header_map

    @staticmethod
    def _has_table_headers(header_map: dict[int, str]) -> bool:
        return any(field == "testing_stage" for field in header_map.values()) and any(
            field == "bin_file" for field in header_map.values()
        )

    @staticmethod
    def _parse_table_row(row: list[str | None], header_map: dict[int, str]) -> dict[str, str | None]:
        parsed_row: dict[str, str | None] = {
            "testing_stage": None,
            "bin_file": None,
            "crc": None,
            "version": None,
            "release_date": None,
            "reason_for_upgrade": None,
        }

        for index, field_name in header_map.items():
            if index >= len(row):
                continue
            value = ChronologyValidator._normalize_table_value(row[index])
            if value is not None:
                parsed_row[field_name] = value

        if not parsed_row["testing_stage"] or not parsed_row["bin_file"]:
            return {}

        return parsed_row

    @staticmethod
    def _normalize_header(value: str | None) -> str:
        if value is None:
            return ""
        text = str(value).strip().lower()
        text = re.sub(r"[\W_]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _normalize_table_value(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _split_testing_stage(value: str | None) -> tuple[str | None, str | None]:
        if not value:
            return None, None
        text = str(value).strip()
        parts = [part.strip() for part in re.split(r"[/\\]", text) if part.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1]
        return text, None

    @staticmethod
    def _is_version_value(value: str) -> bool:
        return bool(re.fullmatch(r"V\d+(?:\.\d+)?", value))

    @staticmethod
    def _is_release_date_value(value: str) -> bool:
        return bool(
            re.fullmatch(r"\d{2}-\d{2}-\d{4}", value)
            or re.fullmatch(r"\d{4}[.-]\d{2}[.-]\d{2}", value)
        )

    @staticmethod
    def _resolve_chronology_pdf(stage_path: Path) -> Path | None:
        pdf_files = [
            file_path
            for file_path in FileSearchService.recursive_files(stage_path, ".pdf")
            if file_path.is_file() and file_path.suffix.casefold() == ".pdf"
        ]
        return pdf_files[0] if pdf_files else None

    @staticmethod
    def _extract_version_from_name(filename: str | None) -> str | None:
        if not filename:
            return None
        match = re.search(r"(?i)(V\d+(?:\.\d+)?)", filename)
        return match.group(1).upper() if match else None

    @staticmethod
    def _normalize_filename_for_display(filename: str | None) -> str | None:
        if not filename:
            return None
        t = re.sub(r"[\r\n\t]", "", filename)
        t = re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", t)
        t = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", t)
        t = re.sub(r" +", " ", t)
        return t.strip()

    @staticmethod
    def _same_text(left: str | None, right: str | None) -> bool:
        if left is None or right is None:
            return left is None and right is None

        def normalize(t: str) -> str:
            t = re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", t)
            t = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", t)
            t = re.sub(r"\s+", " ", t)
            return t.strip().casefold()

        return normalize(left) == normalize(right)

    @staticmethod
    def _validate_reason(version: str | None, reason: str | None) -> bool:
        if version is None:
            return False
        if version.startswith("V1."):
            return reason in {None, "", "N/A", "-"}
        return bool(reason and reason.strip())