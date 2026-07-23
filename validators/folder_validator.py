"""
validators.folder_validator
===========================

Validates the mandatory project folder structure.

Responsibilities
----------------
- Verify all required top-level folders exist.
- Cache discovered folders in ValidationContext.
- Return a single ValidationResult.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from core.base_validator import BaseValidator
from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStep
from config import REQUIRED_FOLDERS
from services.file_search import FileSearchService


class FolderValidator(BaseValidator):
    """
    Validates the required top-level project folders.
    """

    def __init__(
        self,
        file_search: FileSearchService,
    ) -> None:

        super().__init__(ValidationStep.FOLDER_STRUCTURE)

        self._file_search = file_search

    def validate(
        self,
        context: ValidationContext,
    ) -> ValidationResult:

        self.logger.info("Folder validation started.")

        missing: list[str] = []

        discovered: list[str] = []

        for folder_name in REQUIRED_FOLDERS:

            folder = self._file_search.directory(
                context.project_path,
                folder_name,
            )

            if folder is None:
                missing.append(folder_name)
                continue

            context.add_folder(folder_name, folder)
            discovered.append(folder_name)

        if missing:

            self.logger.warning(
                f"Missing folders: {missing}"
            )

            return self.fail_result(
                reason="One or more required folders are missing.",
                checked_path=context.project_path,
                expected=list(REQUIRED_FOLDERS),
                found=discovered,
                details={
                    "missing_folders": missing,
                    "validated": len(discovered),
                    "missing": len(missing),
                },
            )

        self.logger.info(
            "Folder validation completed successfully."
        )

        return self.pass_result(
            reason="All required folders are present.",
            checked_path=context.project_path,
            details={
                "validated": len(discovered),
            },
        )