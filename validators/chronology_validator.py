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
            "7. Chronology"
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
            expected_bin_name = expected_bin_path.name if expected_bin_path else None
            expected_bin_version = self._extract_version_from_name(expected_bin_name)

            if not stage_path.exists() or not stage_path.is_dir():
                stages.append(
                    {
                        "board": None,
                        "stage": expected_stage_name,
                        "bin_file": None,
                        "version": None,
                        "release_date": None,
                        "reason_for_upgrade": None,
                        "previous_version": None,
                        "previous_release_date": None,
                        "upgraded_version": None,
                        "upgraded_release_date": None,
                    }
                )
                continue

            chronology_pdf = self._resolve_chronology_pdf(stage_path)
            if chronology_pdf is None:
                failure_message = f"Missing Chronology PDF for {relative_path.replace('/', ' / ')}."
                failures.append(failure_message)
                stages.append(
                    {
                        "board": None,
                        "stage": expected_stage_name,
                        "bin_file": None,
                        "version": None,
                        "release_date": None,
                        "reason_for_upgrade": None,
                        "previous_version": None,
                        "previous_release_date": None,
                        "upgraded_version": None,
                        "upgraded_release_date": None,
                    }
                )
                continue

            metadata = self._extract_metadata(chronology_pdf)

            self.logger.debug(
                "Chronology parsed values | board=%s | stage=%s | bin=%s | version=%s | release_date=%s | upgrade_reason=%s",
                metadata.get("board"),
                metadata.get("stage"),
                metadata.get("bin_file"),
                metadata.get("version"),
                metadata.get("release_date"),
                metadata.get("reason_for_upgrade"),
            )

            if metadata.get("board") is None:
                self.logger.debug("Chronology parse failed: board field could not be extracted.")
            if metadata.get("stage") is None:
                self.logger.debug("Chronology parse failed: stage field could not be extracted.")
            if metadata.get("bin_file") is None:
                self.logger.debug("Chronology parse failed: bin filename field could not be extracted.")
            if metadata.get("version") is None:
                self.logger.debug("Chronology parse failed: version field could not be extracted.")
            if metadata.get("release_date") is None:
                self.logger.debug("Chronology parse failed: release date field could not be extracted.")
            if metadata.get("reason_for_upgrade") is None:
                self.logger.debug("Chronology parse failed: upgrade reason field could not be extracted.")

            stage_validation_errors: list[str] = []
            if metadata.get("stage") is None:
                stage_validation_errors.append("Testing Stage missing.")
            elif expected_stage_name and not self._same_text(metadata.get("stage"), expected_stage_name):
                stage_validation_errors.append(
                    f"Testing Stage mismatch. Expected {expected_stage_name}. Found {metadata.get('stage')}."
                )

            if expected_bin_name is not None:
                if metadata.get("bin_file") is None:
                    stage_validation_errors.append("BIN filename missing from chronology PDF.")
                elif not self._same_text(metadata.get("bin_file"), expected_bin_name):
                    stage_validation_errors.append(
                        f"BIN filename mismatch. Expected {expected_bin_name}. Found {metadata.get('bin_file')}."
                    )

            if expected_bin_version is not None:
                if metadata.get("version") is None:
                    stage_validation_errors.append("Chronology version missing.")
                elif not self._same_text(metadata.get("version"), expected_bin_version):
                    stage_validation_errors.append(
                        f"Version mismatch. Expected {expected_bin_version}. Found {metadata.get('version')}."
                    )

            required_fields = ["board", "stage", "bin_file", "version", "release_date"]
            for field in required_fields:
                if metadata.get(field) is None:
                    stage_validation_errors.append(f"{field.replace('_', ' ').title()} missing.")

            if not self._validate_reason(metadata.get("version"), metadata.get("reason_for_upgrade")):
                stage_validation_errors.append("Upgrade reason missing.")

            if stage_validation_errors:
                failures.extend(
                    f"{relative_path.replace('/', ' / ')}: {error}"
                    for error in stage_validation_errors
                )

            stages.append(
                {
                    "board": metadata.get("board"),
                    "stage": metadata.get("stage"),
                    "bin_file": metadata.get("bin_file"),
                    "version": metadata.get("version"),
                    "release_date": metadata.get("release_date"),
                    "reason_for_upgrade": metadata.get("reason_for_upgrade"),
                    "previous_version": metadata.get("previous_version"),
                    "previous_release_date": metadata.get("previous_release_date"),
                    "upgraded_version": metadata.get("upgraded_version"),
                    "upgraded_release_date": metadata.get("upgraded_release_date"),
                }
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
            f"Chronology validation passed "
            f"({len(files)} files found)."
        )

        return self.pass_result(
            reason="Chronology folder validated successfully.",
            checked_path=chronology_folder,
            details=details,
        )

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
            "board": None,
            "stage": None,
            "bin_file": None,
            "version": None,
            "release_date": None,
            "reason_for_upgrade": None,
            "previous_version": None,
            "previous_release_date": None,
            "upgraded_version": None,
            "upgraded_release_date": None,
        }

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
            metadata["upgraded_version"] = parsed_values.get("upgraded_version")
            metadata["upgraded_release_date"] = parsed_values.get("upgraded_release_date")

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
        start_index = header_indices[-1] + 1
        return [line for line in lines[start_index:] if line]

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
            "upgraded_version": None,
            "upgraded_release_date": None,
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
                for index in range(max(0, version_index - 2), -1, -1):
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
            joined_bin_name = re.sub(r"\s+", "", joined_bin_name)

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
        oldest_row = rows[-1]

        values["bin_file"] = latest_row.get("bin_file")
        values["version"] = latest_row.get("version")
        values["release_date"] = latest_row.get("release_date")
        values["reason_for_upgrade"] = latest_row.get("reason_for_upgrade")

        if len(rows) > 1:
            values["previous_version"] = oldest_row.get("version")
            values["previous_release_date"] = oldest_row.get("release_date")
            values["upgraded_version"] = latest_row.get("version")
            values["upgraded_release_date"] = latest_row.get("release_date")

        return values

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
    def _same_text(left: str | None, right: str | None) -> bool:
        if left is None or right is None:
            return left is None and right is None
        return re.sub(r"\s+", " ", left).strip().casefold() == re.sub(r"\s+", " ", right).strip().casefold()

    @staticmethod
    def _validate_reason(version: str | None, reason: str | None) -> bool:
        if version is None:
            return False
        if version.startswith("V1."):
            return reason in {None, "", "N/A", "-"}
        return bool(reason and reason.strip())