"""
config.py
---------

Central configuration for the Operational Package Validator.

This module now acts purely as a compatibility wrapper for backward compatibility.
All values are loaded dynamically from the new JSON configuration structure
via ConfigManager. The public API (constant names and types) is unchanged
so that every existing ``from config import …`` statement continues to work.

Author : Selec Controls R&D
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from core.config_manager import ConfigManager

# Load all configurations immediately at import
ConfigManager.load()

# ============================================================================
# APPLICATION INFORMATION
# ============================================================================

APP_NAME: Final[str] = ConfigManager.get("config.app.name")
APP_VERSION: Final[str] = ConfigManager.get("config.app.version")
COMPANY_NAME: Final[str] = ConfigManager.get("config.app.company_name")
ORGANIZATION_NAME: Final[str] = ConfigManager.get("config.app.organization_name")
APP_SUBTITLE: Final[str] = ConfigManager.get("config.app.subtitle")


# ============================================================================
# PROJECT STRUCTURE
# ============================================================================

REQUIRED_FOLDERS: Final[tuple[str, ...]] = tuple(ConfigManager.get("config.project_structure.required_folders") or [])

PROJECT_ROOT_FOLDER_NAME: Final[str] = ConfigManager.get("config.project_structure.root_folder_name")

PROJECT_STRUCTURE: Final[dict] = ConfigManager.get("config.project_structure.folder_tree") or {}

LADDER_INITIAL_FOLDER: Final[str] = ConfigManager.get("config.project_structure.ladder_initial_folder")
LADDER_FINAL_FOLDER: Final[str] = ConfigManager.get("config.project_structure.ladder_final_folder")

BIN_INITIAL_FOLDER: Final[str] = ConfigManager.get("config.project_structure.bin_initial_folder")
BIN_FINAL_FOLDER: Final[str] = ConfigManager.get("config.project_structure.bin_final_folder")


# ============================================================================
# FILE EXTENSIONS
# ============================================================================

LADDER_EXTENSION: Final[str] = ConfigManager.get("config.rules.file_extensions.ladder_extension")
BIN_EXTENSION: Final[str] = ConfigManager.get("config.rules.file_extensions.bin_extension")

SUPPORTED_DOCUMENT_EXTENSIONS: Final[tuple[str, ...]] = tuple(
    ConfigManager.get("config.rules.file_extensions.supported_document_extensions") or []
)

# Signed document naming convention
SIGNED_DOCUMENT_SUFFIX: Final[str] = ConfigManager.get("signatures.document_validation.signed_document_suffix")

# Backward compatibility
SIGNATURE_FILE_SUFFIX: Final[str] = SIGNED_DOCUMENT_SUFFIX


# ============================================================================
# DOCUMENT VALIDATION
# ============================================================================

DOCUMENT_VALIDATION_FOLDERS: Final[tuple[str, ...]] = tuple(
    ConfigManager.get("signatures.document_validation.document_validation_folders") or []
)

EXPECTED_SIGNED_DOCUMENTS: Final[int] = ConfigManager.get("signatures.document_validation.expected_signed_documents")

# Required signing sections by folder. Each entry contains a canonical label
# and accepted aliases used during case-insensitive section detection.
DOCUMENT_SIGNING_SECTIONS: Final[dict[str, list[dict[str, object]]]] = (
    ConfigManager.get("signatures.document_validation.required_sections_by_folder") or {}
)


# ============================================================================
# FOLDER KEYS  (canonical lookup keys for context.folders)
# ============================================================================

FOLDER_KEYS: Final[dict[str, str]] = ConfigManager.get("config.folder_keys") or {}


# ============================================================================
# SEARCH CONFIGURATION
# ============================================================================

RECURSIVE_SEARCH: Final[bool] = ConfigManager.get("config.search.recursive_search")
MAX_FILE_SEARCH_DEPTH: Final[int] = ConfigManager.get("config.search.max_file_search_depth")


# ============================================================================
# LOGGING
# ============================================================================

LOG_DIRECTORY: Final[Path] = ConfigManager.get_base_dir() / ConfigManager.get("config.paths.log_directory")
LOG_FILE_NAME: Final[str] = ConfigManager.get("config.paths.log_file_name")
CRC_ALGORITHM: Final[str] = ConfigManager.get("config.crc.algorithm")
SUPPORTED_CRC_ALGORITHMS: Final[tuple[str, ...]] = tuple(ConfigManager.get("config.crc.supported_algorithms") or [])


# ============================================================================
# REPORTS
# ============================================================================

REPORT_DIRECTORY: Final[Path] = ConfigManager.get_base_dir() / ConfigManager.get("config.paths.report_directory")
REPORT_NAME_PREFIX: Final[str] = ConfigManager.get("config.paths.report_name_prefix")


# ============================================================================
# ASSET / FILE PATHS
# ============================================================================

STYLESHEET_PATH: Final[str] = str(ConfigManager.get_base_dir() / ConfigManager.get("config.paths.stylesheet_path"))
ICON_PATH: Final[str] = str(ConfigManager.get_base_dir() / ConfigManager.get("config.paths.icon_path"))
DEFAULT_OUTPUT_FILENAME: Final[str] = ConfigManager.get("config.paths.default_output_filename")
DOCUMENT_VALIDATOR_DEBUG_LOG: Final[str] = ConfigManager.get("config.paths.document_validator_debug_log")
DEFAULT_FOLDER_GENERATION_TARGET: Final[str] = ConfigManager.get("config.paths.default_folder_generation_target")


# ============================================================================
# GUI SETTINGS
# ============================================================================

WINDOW_WIDTH: Final[int] = ConfigManager.get("config.gui.window_width")
WINDOW_HEIGHT: Final[int] = ConfigManager.get("config.gui.window_height")

MIN_WINDOW_WIDTH: Final[int] = ConfigManager.get("config.gui.min_window_width")
MIN_WINDOW_HEIGHT: Final[int] = ConfigManager.get("config.gui.min_window_height")

PROGRESS_TITLE: Final[str] = ConfigManager.get("config.gui.progress_title")
GUI_MESSAGES: Final[dict] = ConfigManager.get("config.gui.messages") or {}


# ============================================================================
# THEME
# ============================================================================

THEME_PRIMARY: Final[str] = ConfigManager.get("config.theme.primary_color")
THEME_SUCCESS: Final[str] = ConfigManager.get("config.theme.success_color")
THEME_WARNING: Final[str] = ConfigManager.get("config.theme.warning_color")
THEME_ERROR: Final[str] = ConfigManager.get("config.theme.error_color")
THEME_BG_LIGHT: Final[str] = ConfigManager.get("config.theme.background_light")
THEME_BG_DARK: Final[str] = ConfigManager.get("config.theme.background_dark")
THEME_TEXT_MAIN: Final[str] = ConfigManager.get("config.theme.text_main")
THEME_TEXT_MUTED: Final[str] = ConfigManager.get("config.theme.text_muted")
THEME_BORDER: Final[str] = ConfigManager.get("config.theme.border_color")


# ============================================================================
# VALIDATION LIMITS
# ============================================================================

EXPECTED_LADDER_FILES: Final[int] = ConfigManager.get("config.validation_limits.expected_ladder_files")
EXPECTED_BIN_FILES: Final[int] = ConfigManager.get("config.validation_limits.expected_bin_files")


# ============================================================================
# THREADING
# ============================================================================

WORKER_TIMEOUT_SECONDS: Final[int] = ConfigManager.get("config.threading.worker_timeout_seconds")


# ============================================================================
# END
# ============================================================================