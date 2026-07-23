"""
validators.bin_validator
========================

Validates BIN firmware files against Ladder SDOC files.

Responsibilities
----------------
- Validate BIN folder structure.
- Discover Initial and Final BIN files.
- Ensure exactly one BIN exists per stage.
- Compare BIN filenames with SDOC filenames.
- Cache discovered BIN files.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from pathlib import Path

from config import BIN_EXTENSION

from core.base_validator import BaseValidator
from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStep

from services.file_search import FileSearchService
from services.path_utils import PathUtils


class BinValidator(BaseValidator):
    """
    Validates BIN firmware files.
    """

    def __init__(
        self,
        file_search: FileSearchService,
    ) -> None:

        super().__init__(ValidationStep.BIN_FILES)

        self._file_search = file_search

    def validate(
        self,
        context: ValidationContext,
    ) -> ValidationResult:

        self.logger.info("Starting BIN validation.")

        bin_root = context.folders.get("2. Bin File")

        if bin_root is None:

            return self.skipped_result(
                reason="BIN validation skipped because folder validation failed."
            )

        missing_directories: list[str] = []
        missing_files: list[str] = []
        multiple_files: list[str] = []
        filename_mismatch: list[str] = []
        failure_reasons: list[str] = []

        for relative_path, ladder_folder in context.discovered_paths:
            stage_directory = bin_root / Path(*relative_path.split("/"))

            if not stage_directory.exists() or not stage_directory.is_dir():
                missing_directories.append(relative_path)
                failure_reasons.append(f"{relative_path} exists in Ladders but is missing in Bin File.")
                continue

            bin_files = self._file_search.recursive_files(
                stage_directory,
                BIN_EXTENSION,
            )

            if len(bin_files) == 0:
                missing_files.append(relative_path)
                failure_reasons.append(f"{relative_path} is missing a .bin file.")
                continue

            if len(bin_files) > 1:
                multiple_files.append(relative_path)
                failure_reasons.append(f"{relative_path} has multiple .bin files.")
                continue

            bin_file = bin_files[0]
            context.add_bin_file(relative_path, bin_file)

            ladder_file = context.ladder_files.get(relative_path)
            if ladder_file is None:
                filename_mismatch.append(f"{relative_path}: Ladder file unavailable.")
                failure_reasons.append(f"{relative_path} has no matching ladder file.")
                continue

            if not PathUtils.compare_stem(ladder_file, bin_file):
                filename_mismatch.append(f"{relative_path} filename mismatch.")
                failure_reasons.append(f"{relative_path} filename mismatch.")

        if missing_directories or missing_files or multiple_files or filename_mismatch:
            return self.fail_result(
                reason="; ".join(failure_reasons),
                checked_path=bin_root,
                details={
                    "missing_directories": missing_directories,
                    "missing_files": missing_files,
                    "multiple_files": multiple_files,
                    "filename_mismatch": filename_mismatch,
                    "bin_files": {key: str(path) for key, path in context.bin_files.items()},
                },
            )

        self.logger.info("BIN validation completed successfully.")

        return self.pass_result(
            reason="BIN files successfully validated.",
            checked_path=bin_root,
            details={
                "bin_files": {key: str(path) for key, path in context.bin_files.items()},
            },
        )