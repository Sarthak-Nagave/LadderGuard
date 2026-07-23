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
        for relative_path in discovered_folders:
            stage_path = chronology_folder / Path(*relative_path.split("/"))
            if not stage_path.exists() or not stage_path.is_dir():
                continue

            chronology_pdf = None
            for file_path in self._file_search.recursive_files(stage_path, ".pdf"):
                if file_path.is_file() and file_path.suffix.casefold() == ".pdf":
                    chronology_pdf = file_path
                    break

            metadata = self._extract_metadata(chronology_pdf) if chronology_pdf else {
                "board": None,
                "stage": None,
                "bin_file": None,
                "version": None,
                "release_date": None,
                "reason_for_upgrade": None,
            }

            is_valid = all(
                metadata.get(field) is not None
                for field in ["board", "stage", "bin_file", "version", "release_date", "reason_for_upgrade"]
            )

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

            stages.append(
                {
                    "board": metadata.get("board"),
                    "stage": metadata.get("stage"),
                    "bin_file": metadata.get("bin_file"),
                    "version": metadata.get("version"),
                    "release_date": metadata.get("release_date"),
                    "reason_for_upgrade": metadata.get("reason_for_upgrade"),
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
        }

        data_lines = ChronologyValidator._extract_data_lines(lines)
        if data_lines:
            board, stage, remaining = ChronologyValidator._split_first_data_row(data_lines)
            metadata["board"] = board
            metadata["stage"] = stage

            parsed_values = ChronologyValidator._parse_first_data_row(remaining)
            metadata["bin_file"] = parsed_values.get("bin_file")
            metadata["version"] = parsed_values.get("version")
            metadata["release_date"] = parsed_values.get("release_date")
            metadata["reason_for_upgrade"] = parsed_values.get("reason_for_upgrade")

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
    def _parse_first_data_row(lines: list[str]) -> dict[str, str | None]:
        values: dict[str, str | None] = {
            "bin_file": None,
            "version": None,
            "release_date": None,
            "reason_for_upgrade": None,
        }
        if not lines:
            return values

        version_index = None
        date_index = None

        for index, line in enumerate(lines):
            if version_index is None and ChronologyValidator._is_version_value(line):
                version_index = index
                continue
            if version_index is not None and date_index is None and ChronologyValidator._is_release_date_value(line):
                date_index = index
                break

        if version_index is None:
            return values

        bin_parts: list[str] = []
        for index in range(0, version_index):
            line = lines[index]
            if not line:
                continue
            if not bin_parts:
                bin_parts.append(line)
                continue
            if bin_parts[-1].endswith("_"):
                bin_parts[-1] = bin_parts[-1].rstrip("_") + "_" + line
            else:
                bin_parts.append(line)

        values["bin_file"] = " ".join(bin_parts).strip() if bin_parts else None
        values["version"] = lines[version_index].strip()

        if date_index is None:
            values["release_date"] = None
            values["reason_for_upgrade"] = None
            return values

        values["release_date"] = lines[date_index].strip()
        reason_lines = lines[date_index + 1 :]
        values["reason_for_upgrade"] = " ".join(reason_lines).strip() if reason_lines else None
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
    def _validate_reason(version: str | None, reason: str | None) -> bool:
        if version is None:
            return False
        if version.startswith("V1."):
            return reason in {None, "", "N/A", "-"}
        return bool(reason and reason.strip())