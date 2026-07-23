"""
config.py
---------

Central configuration for the Operational Package Validator.

This module contains application-wide constants and configuration values.
No business logic should exist here.

Author : Selec Controls R&D
"""

from __future__ import annotations

from pathlib import Path
from typing import Final


# ============================================================================
# APPLICATION INFORMATION
# ============================================================================

APP_NAME: Final[str] = "Operational Package Validator"
APP_VERSION: Final[str] = "1.0.0"
COMPANY_NAME: Final[str] = "Selec Controls Pvt. Ltd."


# ============================================================================
# PROJECT STRUCTURE
# ============================================================================

REQUIRED_FOLDERS: Final[tuple[str, ...]] = (
    "1. Ladders",
    "2. Bin File",
    "3. Operational Flow",
    "4. Test Report",
    "5. Automation Input Doc",
    "6. Ladder Flow",
    "7. Chronology",
)

LADDER_INITIAL_FOLDER: Final[str] = "Initial"
LADDER_FINAL_FOLDER: Final[str] = "Final"

BIN_INITIAL_FOLDER: Final[str] = "Initial"
BIN_FINAL_FOLDER: Final[str] = "Final"


# ============================================================================
# FILE EXTENSIONS
# ============================================================================

LADDER_EXTENSION: Final[str] = ".sdoc"
BIN_EXTENSION: Final[str] = ".bin"

SUPPORTED_DOCUMENT_EXTENSIONS: Final[tuple[str, ...]] = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
)

# Signed document naming convention
SIGNED_DOCUMENT_SUFFIX: Final[str] = "-sgn"

# Backward compatibility
SIGNATURE_FILE_SUFFIX: Final[str] = SIGNED_DOCUMENT_SUFFIX


# ============================================================================
# DOCUMENT VALIDATION
# ============================================================================

DOCUMENT_VALIDATION_FOLDERS: Final[tuple[str, ...]] = (
    "3. Operational Flow",
    "4. Test Report",
    "5. Automation Input Doc",
    "6. Ladder Flow",
)

EXPECTED_SIGNED_DOCUMENTS: Final[int] = 1

# Names that MUST appear in every signed document
REQUIRED_SIGNERS: Final[tuple[str, ...]] = (
    "Arjun V.",
    "Piyush S.",
    "Mohit S.",
)

# Name comparison
CASE_SENSITIVE_SIGNER_MATCH: Final[bool] = False

# Signature validation
REQUIRE_DIGITAL_SIGNATURE: Final[bool] = True


# ============================================================================
# SEARCH CONFIGURATION
# ============================================================================

RECURSIVE_SEARCH: Final[bool] = True
MAX_FILE_SEARCH_DEPTH: Final[int] = 50


# ============================================================================
# LOGGING
# ============================================================================

LOG_DIRECTORY: Final[Path] = Path("logs")
LOG_FILE_NAME: Final[str] = "validator.log"


# ============================================================================
# REPORTS
# ============================================================================

REPORT_DIRECTORY: Final[Path] = Path("reports")
REPORT_NAME_PREFIX: Final[str] = "Validation_Report"


# ============================================================================
# GUI SETTINGS
# ============================================================================

WINDOW_WIDTH: Final[int] = 1050
WINDOW_HEIGHT: Final[int] = 700

MIN_WINDOW_WIDTH: Final[int] = 900
MIN_WINDOW_HEIGHT: Final[int] = 600


# ============================================================================
# THEME
# ============================================================================

PRIMARY_COLOR: Final[str] = "#F57C00"
SUCCESS_COLOR: Final[str] = "#2E7D32"
WARNING_COLOR: Final[str] = "#ED6C02"
ERROR_COLOR: Final[str] = "#D32F2F"

BACKGROUND_COLOR: Final[str] = "#FFFFFF"
CARD_BACKGROUND: Final[str] = "#F7F7F7"


# ============================================================================
# VALIDATION LIMITS
# ============================================================================

EXPECTED_LADDER_FILES: Final[int] = 1
EXPECTED_BIN_FILES: Final[int] = 1


# ============================================================================
# THREADING
# ============================================================================

WORKER_TIMEOUT_SECONDS: Final[int] = 300


# ============================================================================
# END
# ============================================================================