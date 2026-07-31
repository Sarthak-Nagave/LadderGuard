"""
services.chronology_generator.parsers
=====================================

Provides parsing utilities for filenames within the chronology generation workflow.

This module strictly handles string parsing and metadata extraction from filenames,
ensuring consistent version, model, and base name resolution.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from services.chronology_generator.exceptions import ChronologyParserError


class FilenameParser:
    """
    Utility class for extracting metadata from firmware and ladder filenames.
    """

    _logger = logging.getLogger(__name__)

    # Pre-compiled regular expressions for optimal performance
    _VERSION_PATTERN = re.compile(r"(V\d+\.\d+)", re.IGNORECASE)
    _LETTER_CHECK_PATTERN = re.compile(r"[A-Za-z]")
    
    # Matches valid PLC models (e.g., MIBRX, MIBRX-4M, FLEXYS, etc.)
    # Must start with uppercase letters, optionally followed by a hyphen, numbers, and uppercase letters
    _PLC_MODEL_PATTERN = re.compile(r"^[A-Z]+(?:-\d+[A-Z]*)?$")

    @classmethod
    def extract_version(cls, filename: str) -> str:
        """
        Extracts the version string from a given filename.

        Looks for a pattern like 'V1.00' or 'V2.10'.

        Args:
            filename: The filename to parse (e.g., 'ABC_V1.00.bin').

        Returns:
            The extracted version string.

        Raises:
            ChronologyParserError: If no valid version string is found.
        """
        cls._logger.debug(f"Extracting version from filename: {filename}")
        
        match = cls._VERSION_PATTERN.search(filename)
        if not match:
            error_msg = f"No version pattern (e.g., 'V1.00') found in filename: {filename}"
            cls._logger.error(error_msg)
            raise ChronologyParserError(error_msg)

        version = match.group(1).upper()
        cls._logger.debug(f"Extracted version: {version}")
        return version

    @classmethod
    def extract_plc_model(cls, filename: str) -> str:
        """
        Extracts the PLC model from the filename.
        Uses regex to identify standard models like MIBRX, MIBRX-4M, FLEXYS, etc.

        Args:
            filename: The filename to parse.

        Returns:
            The extracted PLC model string.

        Raises:
            ChronologyParserError: If no valid PLC model can be identified.
        """
        cls._logger.debug(f"Extracting PLC model from filename: {filename}")
        
        # Remove extension to prevent it from interfering with parsing
        name_only = cls.remove_extension(filename)
        
        # Split into segments by underscore or dot
        segments = re.split(r"[_\.]", name_only)
        candidates: list[str] = []

        for segment in segments:
            # Skip if the segment is a version string
            if cls._VERSION_PATTERN.match(segment):
                continue
            
            # Match PLC model pattern
            if cls._PLC_MODEL_PATTERN.match(segment):
                candidates.append(segment)

        if not candidates:
            error_msg = f"Could not identify an uppercase PLC model in filename: {filename}"
            cls._logger.error(error_msg)
            raise ChronologyParserError(error_msg)

        # The most specific model identifier is typically the last valid segment
        plc_model = candidates[-1]
        
        cls._logger.debug(f"Extracted PLC model: {plc_model}")
        return plc_model

    @staticmethod
    def remove_extension(filename: str) -> str:
        """
        Removes the file extension from a filename.

        Args:
            filename: The filename string (e.g., 'ABC_V2.00.bin').

        Returns:
            The filename without its extension (e.g., 'ABC_V2.00').
        """
        # Using pathlib to robustly handle edge cases with dots
        return Path(filename).stem

    @staticmethod
    def build_lookup_key(path: Path) -> str:
        """
        Builds a lookup key from a file path.

        Args:
            path: The file path.

        Returns:
            The base filename without the extension, intended for matching pairs.
        """
        return path.stem

    @classmethod
    def is_matching_pair(cls, bin_path: Path, sdoc_path: Path) -> bool:
        """
        Determines if a BIN file and an SDOC file are a matching pair.

        A match is established if their base filenames (without extensions)
        are identical (case-insensitive).

        Args:
            bin_path: The path to the BIN file.
            sdoc_path: The path to the SDOC file.

        Returns:
            True if the files match, False otherwise.
        """
        bin_key = cls.build_lookup_key(bin_path).casefold()
        sdoc_key = cls.build_lookup_key(sdoc_path).casefold()
        
        is_match = bin_key == sdoc_key
        
        cls._logger.debug(
            f"Comparing pairs -> BIN: '{bin_key}', SDOC: '{sdoc_key}' | Match: {is_match}"
        )
        return is_match