"""
core.base_validator
===================

Abstract base class for all validators used by the Operational Package
Validator.

Every validator must inherit from BaseValidator and implement the
validate() method.

Responsibilities
----------------
- Define the common validator interface.
- Provide helper methods for creating ValidationResult objects.
- Provide a configured application logger.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStatus, ValidationStep


class BaseValidator(ABC):
    """
    Abstract base class for all validators.
    """

    def __init__(self, step: ValidationStep) -> None:
        self._step = step
        self._logger = logger

    @property
    def step(self) -> ValidationStep:
        """Returns the validator execution step."""
        return self._step

    @property
    def logger(self):
        """Returns the configured application logger."""
        return self._logger

    @abstractmethod
    def validate(
        self,
        context: ValidationContext,
    ) -> ValidationResult:
        """
        Execute validation.

        Parameters
        ----------
        context
            Shared validation context.

        Returns
        -------
        ValidationResult
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Result Helpers
    # ------------------------------------------------------------------

    def pass_result(
        self,
        reason: str,
        **kwargs: Any,
    ) -> ValidationResult:
        return ValidationResult(
            step=self.step,
            status=ValidationStatus.PASS,
            reason=reason,
            **kwargs,
        )

    def fail_result(
        self,
        reason: str,
        **kwargs: Any,
    ) -> ValidationResult:
        return ValidationResult(
            step=self.step,
            status=ValidationStatus.FAIL,
            reason=reason,
            **kwargs,
        )

    def warning_result(
        self,
        reason: str,
        **kwargs: Any,
    ) -> ValidationResult:
        return ValidationResult(
            step=self.step,
            status=ValidationStatus.WARNING,
            reason=reason,
            **kwargs,
        )

    def skipped_result(
        self,
        reason: str,
        **kwargs: Any,
    ) -> ValidationResult:
        return ValidationResult(
            step=self.step,
            status=ValidationStatus.SKIPPED,
            reason=reason,
            **kwargs,
        )