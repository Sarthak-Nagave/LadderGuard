"""
services.chronology_generator.constants
=======================================

Shared constants for the Ladder Chronology Generator module.

This module provides a centralized location for all static values,
strings, and configuration defaults used across the chronology
generation workflow.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from typing import Final

# =============================================================================
# FILE EXTENSIONS
# =============================================================================

EXT_BIN: Final[str] = ".bin"
EXT_SDOC: Final[str] = ".sdoc"
EXT_EXCEL_XLSX: Final[str] = ".xlsx"
EXT_EXCEL_XLSM: Final[str] = ".xlsm"

SUPPORTED_FIRMWARE_EXTENSIONS: Final[tuple[str, ...]] = (EXT_BIN,)
SUPPORTED_LADDER_EXTENSIONS: Final[tuple[str, ...]] = (EXT_SDOC,)
SUPPORTED_EXCEL_EXTENSIONS: Final[tuple[str, ...]] = (EXT_EXCEL_XLSX, EXT_EXCEL_XLSM)

# =============================================================================
# TESTING STAGES
# =============================================================================

STAGE_MASTER_INITIAL: Final[str] = "Master Initial"
STAGE_MASTER_FINAL: Final[str] = "Master Final"
STAGE_SLAVE_INITIAL: Final[str] = "Slave Initial"
STAGE_SLAVE_FINAL: Final[str] = "Slave Final"
STAGE_UNKNOWN: Final[str] = "Unknown"

ALL_TESTING_STAGES: Final[tuple[str, ...]] = (
    STAGE_MASTER_INITIAL,
    STAGE_MASTER_FINAL,
    STAGE_SLAVE_INITIAL,
    STAGE_SLAVE_FINAL,
    STAGE_UNKNOWN,
)

# =============================================================================
# EXCEL HEADERS (Display Names)
# =============================================================================

HEADER_SERIAL_NO: Final[str] = "Serial No."
HEADER_SOURCE_CODE_PATH: Final[str] = "Source Code Path"
HEADER_BIN_FILE_NAME: Final[str] = "Bin File Name"
HEADER_CRC: Final[str] = "CRC"
HEADER_LADDER_VERSION: Final[str] = "Ladder Version No."
HEADER_REASON_FOR_UPGRADE: Final[str] = "Reason For Upgrade"
HEADER_TESTING_STAGE: Final[str] = "Testing Stage"
HEADER_PLC_MODEL: Final[str] = "PLC Model"
HEADER_SELPRO_VERSION: Final[str] = "Selpro Version & Path"
HEADER_BOOTLOADER_VERSION: Final[str] = "Bootloader Version"
HEADER_RELEASE_DATE: Final[str] = "Release Date"
HEADER_RELEASED_BY: Final[str] = "Released By"
HEADER_LADDER_RELEASE_TO_PROD: Final[str] = "Ladder Release - To Production"
HEADER_OPERATOR_PROC_MOD: Final[str] = "Operator Procedure Modification"
HEADER_AUTOMATION_SETUP_MOD: Final[str] = "Automation Set Up Modification"
HEADER_TESTED_BY: Final[str] = "Tested By"

REQUIRED_EXCEL_HEADERS: Final[tuple[str, ...]] = (
    HEADER_SERIAL_NO,
    HEADER_SOURCE_CODE_PATH,
    HEADER_BIN_FILE_NAME,
    HEADER_CRC,
    HEADER_LADDER_VERSION,
    HEADER_REASON_FOR_UPGRADE,
    HEADER_TESTING_STAGE,
    HEADER_PLC_MODEL,
    HEADER_SELPRO_VERSION,
    HEADER_BOOTLOADER_VERSION,
    HEADER_RELEASE_DATE,
    HEADER_RELEASED_BY,
    HEADER_LADDER_RELEASE_TO_PROD,
    HEADER_OPERATOR_PROC_MOD,
    HEADER_AUTOMATION_SETUP_MOD,
    HEADER_TESTED_BY,
)

# =============================================================================
# EXCEL CONFIGURATION DEFAULTS
# =============================================================================

DEFAULT_MAX_HEADER_SCAN_ROWS: Final[int] = 50
DEFAULT_WORKSHEET_INDEX: Final[int] = 0
DEFAULT_STARTING_SERIAL_NO: Final[int] = 1

# =============================================================================
# REGEX PATTERNS
# =============================================================================

# Matches versions like V1.00, V2.10, v3.0
PATTERN_VERSION_EXTRACT: Final[str] = r"(V\d+\.\d+)"

# Matches PLC Models enclosed in underscores or dots containing uppercase/hyphens
PATTERN_PLC_MODEL_EXTRACT: Final[str] = r"_([A-Z0-9\-]+)(?:_|\.)"

# Ensures a segment contains at least one alphabetical character
PATTERN_CONTAINS_LETTERS: Final[str] = r"[A-Za-z]"

# =============================================================================
# STANDARD VALUES & PLACEHOLDERS
# =============================================================================

VALUE_YES: Final[str] = "Yes"
VALUE_NO: Final[str] = "No"
VALUE_NA: Final[str] = "N/A"
VALUE_UNKNOWN: Final[str] = "Unknown"
VALUE_EMPTY: Final[str] = ""

DEFAULT_NUMERIC_FALLBACK: Final[int] = 0