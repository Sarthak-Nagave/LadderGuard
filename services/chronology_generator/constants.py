"""
services.chronology_generator.constants
=======================================

Shared constants for the Ladder Chronology Generator module.

This module now acts purely as a compatibility wrapper for backward compatibility.
All values are loaded dynamically from the new JSON configuration structure
via ConfigManager.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from typing import Final

from core.config_manager import ConfigManager

# =============================================================================
# FILE EXTENSIONS
# =============================================================================

EXT_BIN: Final[str] = ConfigManager.get("config.rules.file_extensions.bin_extension")
EXT_SDOC: Final[str] = ConfigManager.get("config.rules.file_extensions.ladder_extension")
# We assume excel_extensions are at [0] and [1] but it's safer to just fetch the array or hardcode the specific fields
_supported_excel = ConfigManager.get("config.rules.file_extensions.supported_excel_extensions")
EXT_EXCEL_XLSX: Final[str] = _supported_excel[0] if _supported_excel else ".xlsx"
EXT_EXCEL_XLSM: Final[str] = _supported_excel[1] if len(_supported_excel) > 1 else ".xlsm"

SUPPORTED_FIRMWARE_EXTENSIONS: Final[tuple[str, ...]] = tuple(ConfigManager.get("config.rules.file_extensions.supported_firmware_extensions"))
SUPPORTED_LADDER_EXTENSIONS: Final[tuple[str, ...]] = tuple(ConfigManager.get("config.rules.file_extensions.supported_ladder_extensions"))
SUPPORTED_EXCEL_EXTENSIONS: Final[tuple[str, ...]] = tuple(ConfigManager.get("config.rules.file_extensions.supported_excel_extensions"))

# =============================================================================
# TESTING STAGES
# =============================================================================

_testing_stages = ConfigManager.get("config.chronology.testing_stages")
STAGE_MASTER_INITIAL: Final[str] = _testing_stages[0] if len(_testing_stages) > 0 else "Master Initial"
STAGE_MASTER_FINAL: Final[str] = _testing_stages[1] if len(_testing_stages) > 1 else "Master Final"
STAGE_SLAVE_INITIAL: Final[str] = _testing_stages[2] if len(_testing_stages) > 2 else "Slave Initial"
STAGE_SLAVE_FINAL: Final[str] = _testing_stages[3] if len(_testing_stages) > 3 else "Slave Final"
STAGE_UNKNOWN: Final[str] = _testing_stages[4] if len(_testing_stages) > 4 else "Unknown"

ALL_TESTING_STAGES: Final[tuple[str, ...]] = tuple(_testing_stages)

# =============================================================================
# EXCEL HEADERS (Display Names)
# =============================================================================

HEADER_SERIAL_NO: Final[str] = ConfigManager.get("config.chronology.headers.serial_no")
HEADER_SOURCE_CODE_PATH: Final[str] = ConfigManager.get("config.chronology.headers.source_code_path")
HEADER_BIN_FILE_NAME: Final[str] = ConfigManager.get("config.chronology.headers.bin_file_name")
HEADER_CRC: Final[str] = ConfigManager.get("config.chronology.headers.crc")
HEADER_LADDER_VERSION: Final[str] = ConfigManager.get("config.chronology.headers.ladder_version")
HEADER_REASON_FOR_UPGRADE: Final[str] = ConfigManager.get("config.chronology.headers.reason_for_upgrade")
HEADER_TESTING_STAGE: Final[str] = ConfigManager.get("config.chronology.headers.testing_stage")
HEADER_PLC_MODEL: Final[str] = ConfigManager.get("config.chronology.headers.plc_model")
HEADER_SELPRO_VERSION: Final[str] = ConfigManager.get("config.chronology.headers.selpro_version")
HEADER_BOOTLOADER_VERSION: Final[str] = ConfigManager.get("config.chronology.headers.bootloader_version")
HEADER_RELEASE_DATE: Final[str] = ConfigManager.get("config.chronology.headers.release_date")
HEADER_RELEASED_BY: Final[str] = ConfigManager.get("config.chronology.headers.released_by")
HEADER_LADDER_RELEASE_TO_PROD: Final[str] = ConfigManager.get("config.chronology.headers.ladder_release_to_prod")
HEADER_OPERATOR_PROC_MOD: Final[str] = ConfigManager.get("config.chronology.headers.operator_proc_mod")
HEADER_AUTOMATION_SETUP_MOD: Final[str] = ConfigManager.get("config.chronology.headers.automation_setup_mod")
HEADER_TESTED_BY: Final[str] = ConfigManager.get("config.chronology.headers.tested_by")

REQUIRED_EXCEL_HEADERS: Final[tuple[str, ...]] = tuple(ConfigManager.get("config.chronology.required_headers"))

# =============================================================================
# EXCEL CONFIGURATION DEFAULTS
# =============================================================================

DEFAULT_MAX_HEADER_SCAN_ROWS: Final[int] = ConfigManager.get("config.chronology.defaults.max_header_scan_rows")
DEFAULT_WORKSHEET_INDEX: Final[int] = ConfigManager.get("config.chronology.defaults.worksheet_index")
DEFAULT_STARTING_SERIAL_NO: Final[int] = ConfigManager.get("config.chronology.defaults.starting_serial_no")

# =============================================================================
# REGEX PATTERNS (Keeping hardcoded as they are not business config usually)
# =============================================================================

PATTERN_VERSION_EXTRACT: Final[str] = r"(V\d+\.\d+)"
PATTERN_PLC_MODEL_EXTRACT: Final[str] = r"_([A-Z0-9\-]+)(?:_|\.)"
PATTERN_CONTAINS_LETTERS: Final[str] = r"[A-Za-z]"

# =============================================================================
# STANDARD VALUES & PLACEHOLDERS
# =============================================================================

VALUE_YES: Final[str] = ConfigManager.get("config.chronology.defaults.value_yes")
VALUE_NO: Final[str] = ConfigManager.get("config.chronology.defaults.value_no")
VALUE_NA: Final[str] = ConfigManager.get("config.chronology.defaults.value_na")
VALUE_UNKNOWN: Final[str] = ConfigManager.get("config.chronology.defaults.value_unknown")
VALUE_EMPTY: Final[str] = ConfigManager.get("config.chronology.defaults.value_empty")

DEFAULT_NUMERIC_FALLBACK: Final[int] = ConfigManager.get("config.chronology.defaults.numeric_fallback")