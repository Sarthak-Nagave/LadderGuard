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
from pathlib import Path

from config import FOLDER_KEYS
from services.chronology_generator.models import ChronologyEntry, ProjectChronology
from services.chronology_generator.parsers import FilenameParser
from services.hierarchy_discovery import HierarchyDiscovery


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

        firmware_stages = self._discover_firmware_stages()

        selected_bin_count = 0
        for stage in firmware_stages:
            bin_files = self._find_bin_files_for_stage(stage)
            selected_bin = self._select_newest_bin(bin_files)
            if selected_bin is None:
                self._logger.warning(f"No BIN files found for firmware stage: {stage}")
                continue

            selected_bin_count += 1

            bin_name = selected_bin.name

            # Source Code Path is the absolute selected BIN path.
            source_code_path = selected_bin.resolve()

            # Extract metadata
            try:
                version = FilenameParser.extract_version(bin_name)
            except Exception:
                version = "Unknown"

            try:
                plc_model = FilenameParser.extract_plc_model(bin_name)
            except Exception:
                plc_model = "Unknown"

            try:
                bootloader_version = FilenameParser.extract_bootloader_version(bin_name)
            except Exception:
                bootloader_version = ""

            testing_stage = self._determine_testing_stage(stage)

            self._logger.debug(
                f"Extracted metadata for {bin_name}: Version={version}, "
                f"Model={plc_model}, Stage={testing_stage}"
            )

            # One firmware folder -> one chronology entry (newest BIN only).
            entry = ChronologyEntry(
                source_code_path=source_code_path,
                bin_file_path=selected_bin,
                sdoc_file_path=None,
                bin_file_name=bin_name,
                sdoc_file_name=None,
                version=version,
                plc_model=plc_model,
                selpro_version="",
                bootloader_version=bootloader_version,
                crc="",
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

        self._logger.debug(f"Found {len(firmware_stages)} firmware stages and {selected_bin_count} selected BIN files.")
        self._logger.info(f"Scan complete. Built chronology with {len(chronology.entries)} entries.")
        return chronology

    def _discover_firmware_stages(self) -> list[Path]:
        bin_root = self._resolve_bin_root()
        return HierarchyDiscovery.discover_firmware_hierarchy([bin_root])

    def _find_bin_files_for_stage(self, stage: Path) -> list[Path]:
        stage_root = self._resolve_bin_root() / stage
        # Business rule: search only in the discovered firmware folder itself.
        return list(stage_root.glob("*.bin")) if stage_root.exists() else []

    def _resolve_bin_root(self) -> Path:
        return self._project_root / FOLDER_KEYS["bin_file"]

    @staticmethod
    def _select_newest_bin(bin_files: list[Path]) -> Path | None:
        if not bin_files:
            return None

        def key(path: Path) -> tuple[int, str]:
            stat = path.stat()
            mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
            return (-mtime_ns, path.name.casefold())

        return min(bin_files, key=key)

    def _determine_testing_stage(self, stage: Path) -> str:
        """
        Determines the testing stage from the discovered firmware stage path.

        Args:
            stage: Firmware stage path relative to bin root.

        Returns:
            The testing stage as a human-readable string.
        """
        parts = [part.strip() for part in stage.parts if part.strip()]
        if not parts:
            return "Unknown"
        return " ".join(parts)