"""
services.chronology_generator.project_scanner
=============================================

Scans an Operational Package project to collect BIN and SDOC file
information and constructs a ProjectChronology model.

This module is strictly responsible for filesystem scanning and 
metadata extraction. It does not perform validation, calculation,
or Excel report generation.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from services.chronology_generator.models import ChronologyEntry, ProjectChronology
from services.chronology_generator.parsers import FilenameParser


class ProjectScanner:
    """
    Scans the project directory to locate firmware (.bin) and ladder (.sdoc) 
    files, matching them by base filename to build a ProjectChronology.
    """

    def __init__(self, project_root: Path) -> None:
        """
        Initialize the project scanner.

        Args:
            project_root: The root directory of the operational package project.
        """
        self._project_root = project_root
        self._logger = logging.getLogger(__name__)

    def scan(self) -> ProjectChronology:
        """
        Executes the filesystem scan and constructs the project chronology.

        Locates all BIN files, finds their matching SDOC files, extracts 
        metadata from their paths and filenames, and creates entry models.

        Returns:
            A populated ProjectChronology instance.
        """
        self._logger.info(f"Starting chronology scan in {self._project_root}")

        chronology = ProjectChronology(project_root=self._project_root)

        bin_files = self._find_bin_files()
        sdoc_files = self._find_sdoc_files()
        sdoc_lookup = self._build_sdoc_lookup(sdoc_files)

        self._logger.debug(f"Found {len(bin_files)} BIN files and {len(sdoc_files)} SDOC files.")

        for bin_path in bin_files:
            bin_name = bin_path.name
            sdoc_path = self._match_sdoc(bin_path, sdoc_lookup)
            sdoc_name = sdoc_path.name if sdoc_path else None

            # Determine source code path (fallback to bin folder if SDOC is missing)
            source_folder = sdoc_path.parent if sdoc_path else bin_path.parent
            try:
                source_code_path = source_folder.relative_to(self._project_root)
            except ValueError:
                source_code_path = source_folder

            # Extract metadata
            try:
                version = FilenameParser.extract_version(bin_name)
            except Exception:
                version = "Unknown"
                
            plc_model = ""
            if sdoc_name:
                try:
                    plc_model = FilenameParser.extract_plc_model(sdoc_name)
                except Exception:
                    pass
            if not plc_model:
                try:
                    plc_model = FilenameParser.extract_plc_model(bin_name)
                except Exception:
                    plc_model = "Unknown"
                    
            try:
                bootloader_version = FilenameParser.extract_bootloader_version(bin_name)
            except Exception:
                bootloader_version = ""
                    
            testing_stage = self._determine_testing_stage(bin_path)

            self._logger.debug(
                f"Extracted metadata for {bin_name}: Version={version}, "
                f"Model={plc_model}, Stage={testing_stage}"
            )

            # Safely attempt CRC calculation if scanner supports it (placeholder implemented safely)
            crc_val = ""
            if hasattr(self, "_calculate_crc"):
                crc_val = getattr(self, "_calculate_crc")(bin_path)

            # Construct entry
            entry = ChronologyEntry(
                source_code_path=source_code_path,
                bin_file_path=bin_path,
                sdoc_file_path=sdoc_path,
                bin_file_name=bin_name,
                sdoc_file_name=sdoc_name,
                version=version,
                plc_model=plc_model,
                selpro_version="",
                bootloader_version=bootloader_version,
                crc=crc_val,
                testing_stage=testing_stage,
                release_date="",
                reason_for_upgrade="",
                released_by="",
                tested_by="",
                ladder_release_to_production="",
                operator_procedure_modification="",
                automation_setup_modification=""
            )

            chronology.add_entry(entry)

        self._logger.info(f"Scan complete. Built chronology with {len(chronology.entries)} entries.")
        return chronology

    def _find_bin_files(self) -> list[Path]:
        """
        Recursively locates all .bin files in the project.

        Returns:
            A list of Paths pointing to .bin files.
        """
        return list(self._project_root.rglob("*.bin"))

    def _find_sdoc_files(self) -> list[Path]:
        """
        Recursively locates all .sdoc files in the project.

        Returns:
            A list of Paths pointing to .sdoc files.
        """
        return list(self._project_root.rglob("*.sdoc"))

    def _build_sdoc_lookup(self, sdoc_files: list[Path]) -> dict[str, Path]:
        """
        Creates a case-insensitive lookup dictionary for SDOC files based on their stem.

        Args:
            sdoc_files: List of discovered SDOC file paths.

        Returns:
            A dictionary mapping lowercased stems to their full Paths.
        """
        return {sdoc.stem.casefold(): sdoc for sdoc in sdoc_files}

    def _match_sdoc(self, bin_file: Path, sdoc_lookup: dict[str, Path]) -> Path | None:
        """
        Finds the corresponding SDOC file for a given BIN file.

        Args:
            bin_file: The BIN file Path.
            sdoc_lookup: The pre-built SDOC lookup dictionary.

        Returns:
            The matching SDOC Path if found, otherwise None.
        """
        return sdoc_lookup.get(bin_file.stem.casefold())

    def _determine_testing_stage(self, filepath: Path) -> str:
        """
        Determines the testing stage based on the folder hierarchy.

        Evaluates the path parts for combinations of 'master', 'slave', 
        'initial', and 'final'.

        Args:
            filepath: The full path to the file.

        Returns:
            The testing stage as a strictly formatted string.
        """
        parts = [part.casefold() for part in filepath.parts]
        
        is_master = any("master" in p for p in parts)
        is_slave = any("slave" in p for p in parts)
        is_initial = any("initial" in p for p in parts)
        is_final = any("final" in p for p in parts)

        if is_master and is_initial:
            return "Master Initial"
        if is_master and is_final:
            return "Master Final"
        if is_slave and is_initial:
            return "Slave Initial"
        if is_slave and is_final:
            return "Slave Final"

        return "Unknown"

    def _calculate_crc(self, bin_path: Path) -> str:
        """
        Calculates the CRC checksum for the given BIN file.

        Args:
            bin_path: Path to the BIN file.

        Returns:
            The CRC checksum hex string, or an empty string if generation fails.
        """
        try:
            from services.crc.crc_generator import CRCGenerator
            generator = CRCGenerator()
            result = generator.generate_from_file(bin_path)
            return result.hex_value
        except Exception as e:
            self._logger.error(f"Failed to calculate CRC for {bin_path.name}: {e}")
            return ""