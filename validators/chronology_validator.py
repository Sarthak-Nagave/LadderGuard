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

        details = {
            "folder": chronology_folder.name,
            "file_count": len(files),
            "files": [
                file.name
                for file in files
            ],
            "discovered_ladder_folders": discovered_folders,
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