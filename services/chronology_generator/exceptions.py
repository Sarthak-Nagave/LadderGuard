"""
services.chronology_generator.exceptions
========================================

Exception hierarchy for the Ladder Chronology Generator module.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations


class ChronologyError(Exception):
    """
    Base exception for the chronology generation module.
    """

    def __init__(
        self,
        message: str = "An error occurred in the chronology generator.",
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize the ChronologyError.

        Args:
            message: The error message detailing the failure.
            original_exception: The underlying exception that caused this error, if any.
        """
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception

    def __str__(self) -> str:
        """
        Returns a clean string representation of the exception, including the cause if present.

        Returns:
            Formatted error string.
        """
        if self.original_exception is not None:
            return f"{self.message} (Cause: {self.original_exception})"
        return self.message


class ChronologyScanError(ChronologyError):
    """
    Raised when project scanning fails.
    """

    def __init__(
        self,
        message: str = "Failed to scan the project for chronology files.",
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize the ChronologyScanError.

        Args:
            message: The error message detailing the scanning failure.
            original_exception: The underlying exception that caused this error, if any.
        """
        super().__init__(message, original_exception)


class ChronologyTemplateError(ChronologyError):
    """
    Raised when the Excel template is invalid, corrupted, or missing required elements.
    """

    def __init__(
        self,
        message: str = "The provided chronology Excel template is invalid.",
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize the ChronologyTemplateError.

        Args:
            message: The error message detailing the template validation failure.
            original_exception: The underlying exception that caused this error, if any.
        """
        super().__init__(message, original_exception)


class ChronologyWriterError(ChronologyError):
    """
    Raised when writing chronology data to the Excel file fails.
    """

    def __init__(
        self,
        message: str = "Failed to write chronology data to the Excel file.",
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize the ChronologyWriterError.

        Args:
            message: The error message detailing the write failure.
            original_exception: The underlying exception that caused this error, if any.
        """
        super().__init__(message, original_exception)


class ChronologyGenerationError(ChronologyError):
    """
    Raised when the overall chronology generation workflow process fails.
    """

    def __init__(
        self,
        message: str = "The overall chronology generation process failed.",
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize the ChronologyGenerationError.

        Args:
            message: The error message detailing the generation workflow failure.
            original_exception: The underlying exception that caused this error, if any.
        """
        super().__init__(message, original_exception)


class ChronologyParserError(ChronologyError):
    """
    Raised when filename or SDOC content parsing fails.
    """

    def __init__(
        self,
        message: str = "Failed to parse filename or SDOC metadata.",
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize the ChronologyParserError.

        Args:
            message: The error message detailing the parsing failure.
            original_exception: The underlying exception that caused this error, if any.
        """
        super().__init__(message, original_exception)