"""
core.validation_step
====================

Defines validation workflow steps and result status used throughout the
Ladder Release Validator.

This module intentionally contains only enumerations and must not contain
business logic.

Author:
    Selec Controls R&D

Python:
    3.12+
"""

from __future__ import annotations

from enum import Enum, IntEnum, auto


class ValidationStatus(Enum):
    """
    Represents the outcome of a validation step.
    """

    PASS = auto()
    FAIL = auto()
    WARNING = auto()
    SKIPPED = auto()

    def __str__(self) -> str:
        return self.name


class ValidationStep(IntEnum):
    """
    Defines the validation execution order.

    IntEnum is used so the Validation Engine can naturally sort and
    execute the pipeline without additional ordering logic.
    """

    FOLDER_STRUCTURE = 1

    LADDER_FILES = 2

    BIN_FILES = 3

    OPERATIONAL_FLOW = 4

    TEST_REPORT = 5

    AUTOMATION_INPUT = 6

    LADDER_FLOW = 7

    CHRONOLOGY = 8

    COMPLETE = 9

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()