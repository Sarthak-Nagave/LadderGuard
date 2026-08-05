"""
validators.ladder_validator
===========================

Validates the Ladder folder structure and discovers the required
Initial and Final SDOC files.

Responsibilities
----------------
- Validate Initial and Final ladder folders.
- Discover stage-level SDOC files.
- Ensure exactly one SDOC exists in each stage.
- Cache discovered files in ValidationContext.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from pathlib import Path

from config import FOLDER_KEYS, LADDER_EXTENSION
from core.base_validator import BaseValidator
from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStep
from services.file_search import FileSearchService


class LadderValidator(BaseValidator):
    """
    Validates ladder files and caches discovered SDOC paths.
    """

    def __init__(
        self,
        file_search: FileSearchService,
    ) -> None:

        super().__init__(ValidationStep.LADDER_FILES)

        self._file_search = file_search

    def validate(
        self,
        context: ValidationContext,
    ) -> ValidationResult:

        self.logger.info("Starting ladder validation.")

        ladders_root = context.folders.get(FOLDER_KEYS["ladders"])

        if ladders_root is None:

            return self.skipped_result(
                reason="Ladder folder not available because folder validation failed."
            )

        discovered_folders: list[Path] = []
        failures: list[str] = []
        discovered_files: dict[str, str] = {}

        board_directories = self._file_search.subdirectories(ladders_root)
        if not board_directories:
            return self.fail_result(
                reason="No board folders were found under the ladders root.",
                checked_path=ladders_root,
                details={"failures": ["No board folders were found under the ladders root."]},
            )

        for board_directory in board_directories:
            child_folders = self._file_search.subdirectories(board_directory)
            if not child_folders:
                failures.append(f"{board_directory.name} has no stage subfolders.")
                continue

            for child_folder in child_folders:
                discovered_folders.append(child_folder)
                relative_path = f"{board_directory.name}/{child_folder.name}"

                context.add_discovered_path(relative_path, child_folder)

                files = self._file_search.direct_files(
                    child_folder,
                    LADDER_EXTENSION,
                )

                if len(files) == 0:
                    failures.append(f"{relative_path} has no .sdoc file.")
                    continue

                if len(files) > 1:
                    failures.append(f"{relative_path} has multiple .sdoc files.")
                    continue

                context.add_ladder_file(relative_path, files[0])
                discovered_files[relative_path] = str(files[0])

        if failures:
            return self.fail_result(
                reason="; ".join(failures),
                checked_path=ladders_root,
                details={
                    "failures": failures,
                    "discovered_files": discovered_files,
                },
            )

        self.logger.info("Ladder validation completed successfully.")

        return self.pass_result(
            reason="Ladder folders and SDOC files validated successfully.",
            checked_path=ladders_root,
            details={
                "discovered_folders": [folder.name for folder in discovered_folders],
                "discovered_files": discovered_files,
            },
        )