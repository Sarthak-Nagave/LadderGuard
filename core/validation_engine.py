"""
core.validation_engine
======================

Coordinates execution of the complete validation pipeline.

Responsibilities
----------------
- Create ValidationContext.
- Execute validators in order.
- Collect ValidationResults.
- Generate ValidationSummary.

This module contains orchestration only.
No business validation logic belongs here.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from loguru import logger

from core.base_validator import BaseValidator
from core.validation_context import ValidationContext
from core.validation_summary import ValidationSummary


class ValidationEngine:
    """
    Executes the complete validation pipeline.
    """

    def __init__(
        self,
        validators: list[BaseValidator] | None = None,
    ) -> None:

        self._progress_callback: Callable[[int, str], None] | None = None
        self._validators = []

        self._set_validators(validators)

    def _set_validators(
        self,
        validators: list[BaseValidator] | None,
    ) -> None:
        """Register validators for the run."""

        if validators is None:
            from services.file_search import FileSearchService
            from services.file_reader import FileReaderService
            from services.signature_reader import SignatureReaderService
            from validators.bin_validator import BinValidator
            from validators.chronology_validator import ChronologyValidator
            from validators.document_validator import DocumentValidator
            from validators.folder_validator import FolderValidator
            from validators.ladder_validator import LadderValidator
            from config import DOCUMENT_VALIDATION_FOLDERS
            from core.validation_step import ValidationStep

            file_search = FileSearchService()
            file_reader = FileReaderService()
            signature_reader = SignatureReaderService()

            validators = [
                FolderValidator(file_search),
                LadderValidator(file_search),
                BinValidator(file_search),
                DocumentValidator(
                    ValidationStep.OPERATIONAL_FLOW,
                    DOCUMENT_VALIDATION_FOLDERS[0],
                    file_search,
                    file_reader,
                    signature_reader,
                ),
                DocumentValidator(
                    ValidationStep.TEST_REPORT,
                    DOCUMENT_VALIDATION_FOLDERS[1],
                    file_search,
                    file_reader,
                    signature_reader,
                ),
                DocumentValidator(
                    ValidationStep.AUTOMATION_INPUT,
                    DOCUMENT_VALIDATION_FOLDERS[2],
                    file_search,
                    file_reader,
                    signature_reader,
                ),
                DocumentValidator(
                    ValidationStep.LADDER_FLOW,
                    DOCUMENT_VALIDATION_FOLDERS[3],
                    file_search,
                    file_reader,
                    signature_reader,
                ),
                ChronologyValidator(file_search),
            ]

        self._validators = sorted(
            validators,
            key=lambda validator: validator.step,
        )

    def set_progress_callback(
        self,
        callback: Callable[[int, str], None] | None,
    ) -> None:
        """Attach an optional progress callback."""
        self._progress_callback = callback

    def _emit_progress(self, percentage: int, step: str) -> None:
        """Emit a progress update if a callback is attached."""
        if self._progress_callback is not None:
            self._progress_callback(percentage, step)

    def validate(
        self,
        project_path: Path,
    ) -> ValidationSummary:
        """
        Execute all validators.

        Parameters
        ----------
        project_path
            Root project directory.

        Returns
        -------
        ValidationSummary
        """

        logger.info(
            f"Validation started for project: {project_path}"
        )

        started_at = datetime.now()

        context = ValidationContext(
            project_path=project_path,
        )

        total_steps = len(self._validators)

        for index, validator in enumerate(self._validators, start=1):

            logger.info(
                f"Running validator: {validator.step}"
            )

            self._emit_progress(
                int((index / total_steps) * 100) if total_steps else 100,
                f"Running {validator.step}",
            )

            try:

                result = validator.validate(context)

            except Exception as exc:

                logger.exception(exc)

                result = validator.fail_result(
                    reason=str(exc),
                    checked_path=context.project_path,
                )

            context.add_result(result)

            self._emit_progress(
                int((index / total_steps) * 100) if total_steps else 100,
                f"Completed {validator.step}",
            )

        finished_at = datetime.now()

        summary = ValidationSummary(
            project_path=context.project_path,
            started_at=started_at,
            finished_at=finished_at,
            results=context.results,
        )

        logger.info(
            "Validation completed "
            f"({summary.overall_status.name}) | "
            f"Passed={summary.passed}, "
            f"Failed={summary.failed}, "
            f"Warnings={summary.warnings}"
        )

        return summary