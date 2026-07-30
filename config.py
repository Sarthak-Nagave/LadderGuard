"""
config.py
---------

Central configuration for the Operational Package Validator.

All values are loaded from ``config.json`` located next to this module.
The public API (constant names and types) is unchanged so that every
existing ``from config import …`` statement continues to work.

No business logic should exist here.

Author : Selec Controls R&D
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final


# ============================================================================
# JSON LOADER
# ============================================================================

_CONFIG_DIR: Final[Path] = Path(__file__).resolve().parent

def _load_config() -> dict:
    """Read and parse config.json once at import time."""
    config_path = _CONFIG_DIR / "config.json"
    with config_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

_CFG: Final[dict] = _load_config()


# ============================================================================
# APPLICATION INFORMATION
# ============================================================================

APP_NAME: Final[str] = _CFG["app"]["name"]
APP_VERSION: Final[str] = _CFG["app"]["version"]
COMPANY_NAME: Final[str] = _CFG["app"]["company_name"]
ORGANIZATION_NAME: Final[str] = _CFG["app"]["organization_name"]


# ============================================================================
# PROJECT STRUCTURE
# ============================================================================

REQUIRED_FOLDERS: Final[tuple[str, ...]] = tuple(_CFG["project_structure"]["required_folders"])

PROJECT_ROOT_FOLDER_NAME: Final[str] = _CFG["project_structure"]["root_folder_name"]

PROJECT_STRUCTURE: Final[dict[str, dict[str, list[str]] | dict[str, object]]] = _CFG["project_structure"]["folder_tree"]

LADDER_INITIAL_FOLDER: Final[str] = _CFG["project_structure"]["ladder_initial_folder"]
LADDER_FINAL_FOLDER: Final[str] = _CFG["project_structure"]["ladder_final_folder"]

BIN_INITIAL_FOLDER: Final[str] = _CFG["project_structure"]["bin_initial_folder"]
BIN_FINAL_FOLDER: Final[str] = _CFG["project_structure"]["bin_final_folder"]


# ============================================================================
# FILE EXTENSIONS
# ============================================================================

LADDER_EXTENSION: Final[str] = _CFG["file_extensions"]["ladder_extension"]
BIN_EXTENSION: Final[str] = _CFG["file_extensions"]["bin_extension"]

SUPPORTED_DOCUMENT_EXTENSIONS: Final[tuple[str, ...]] = tuple(
    _CFG["file_extensions"]["supported_document_extensions"]
)

# Signed document naming convention
SIGNED_DOCUMENT_SUFFIX: Final[str] = _CFG["document_validation"]["signed_document_suffix"]

# Backward compatibility
SIGNATURE_FILE_SUFFIX: Final[str] = SIGNED_DOCUMENT_SUFFIX


# ============================================================================
# DOCUMENT VALIDATION
# ============================================================================

DOCUMENT_VALIDATION_FOLDERS: Final[tuple[str, ...]] = tuple(
    _CFG["document_validation"]["document_validation_folders"]
)

EXPECTED_SIGNED_DOCUMENTS: Final[int] = _CFG["document_validation"]["expected_signed_documents"]

# Names that MUST appear in every signed document
REQUIRED_SIGNERS: Final[tuple[str, ...]] = tuple(
    _CFG["document_validation"]["required_signers"]
)

# Name comparison
CASE_SENSITIVE_SIGNER_MATCH: Final[bool] = _CFG["document_validation"]["case_sensitive_signer_match"]

# Signature validation
REQUIRE_DIGITAL_SIGNATURE: Final[bool] = _CFG["document_validation"]["require_digital_signature"]


# ============================================================================
# FOLDER KEYS  (canonical lookup keys for context.folders)
# ============================================================================

FOLDER_KEYS: Final[dict[str, str]] = _CFG["folder_keys"]


# ============================================================================
# SEARCH CONFIGURATION
# ============================================================================

RECURSIVE_SEARCH: Final[bool] = _CFG["search"]["recursive_search"]
MAX_FILE_SEARCH_DEPTH: Final[int] = _CFG["search"]["max_file_search_depth"]


# ============================================================================
# LOGGING
# ============================================================================

LOG_DIRECTORY: Final[Path] = Path(_CFG["paths"]["log_directory"])
LOG_FILE_NAME: Final[str] = _CFG["paths"]["log_file_name"]
CRC_ALGORITHM: Final[str] = _CFG["crc"]["algorithm"]
SUPPORTED_CRC_ALGORITHMS: Final[tuple[str, ...]] = tuple(_CFG["crc"]["supported_algorithms"])


# ============================================================================
# REPORTS
# ============================================================================

REPORT_DIRECTORY: Final[Path] = Path(_CFG["paths"]["report_directory"])
REPORT_NAME_PREFIX: Final[str] = _CFG["paths"]["report_name_prefix"]


# ============================================================================
# ASSET / FILE PATHS
# ============================================================================

STYLESHEET_PATH: Final[str] = _CFG["paths"]["stylesheet_path"]
ICON_PATH: Final[str] = _CFG["paths"]["icon_path"]
DEFAULT_OUTPUT_FILENAME: Final[str] = _CFG["paths"]["default_output_filename"]
DOCUMENT_VALIDATOR_DEBUG_LOG: Final[str] = _CFG["paths"]["document_validator_debug_log"]
DEFAULT_FOLDER_GENERATION_TARGET: Final[str] = _CFG["paths"]["default_folder_generation_target"]


# ============================================================================
# GUI SETTINGS
# ============================================================================

WINDOW_WIDTH: Final[int] = _CFG["gui"]["window_width"]
WINDOW_HEIGHT: Final[int] = _CFG["gui"]["window_height"]

MIN_WINDOW_WIDTH: Final[int] = _CFG["gui"]["min_window_width"]
MIN_WINDOW_HEIGHT: Final[int] = _CFG["gui"]["min_window_height"]


# ============================================================================
# THEME
# ============================================================================

PRIMARY_COLOR: Final[str] = _CFG["theme"]["primary_color"]
SUCCESS_COLOR: Final[str] = _CFG["theme"]["success_color"]
WARNING_COLOR: Final[str] = _CFG["theme"]["warning_color"]
ERROR_COLOR: Final[str] = _CFG["theme"]["error_color"]

BACKGROUND_COLOR: Final[str] = _CFG["theme"]["background_color"]
CARD_BACKGROUND: Final[str] = _CFG["theme"]["card_background"]


# ============================================================================
# VALIDATION LIMITS
# ============================================================================

EXPECTED_LADDER_FILES: Final[int] = _CFG["validation_limits"]["expected_ladder_files"]
EXPECTED_BIN_FILES: Final[int] = _CFG["validation_limits"]["expected_bin_files"]


# ============================================================================
# THREADING
# ============================================================================

WORKER_TIMEOUT_SECONDS: Final[int] = _CFG["threading"]["worker_timeout_seconds"]


# ============================================================================
# END
# ============================================================================