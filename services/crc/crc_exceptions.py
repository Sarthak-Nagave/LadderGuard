"""CRC related exceptions for the Operational Package Validator."""

from __future__ import annotations


class CRCError(Exception):
    """Base exception for CRC subsystem failures."""


class CRCMissingFileError(CRCError, FileNotFoundError):
    """Raised when a BIN file does not exist."""


class CRCEmptyFileError(CRCError, ValueError):
    """Raised when a BIN file is empty."""


class CRCPermissionError(CRCError, PermissionError):
    """Raised when the application cannot read a BIN file due to permissions."""


class CRCReadError(CRCError, OSError):
    """Raised when a BIN file cannot be read."""


class CRCUnsupportedAlgorithmError(CRCError, ValueError):
    """Raised when a requested CRC algorithm is not supported."""
