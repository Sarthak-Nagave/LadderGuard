"""
services.chronology_generator.generator
=======================================

Orchestrates the Ladder Chronology Generation workflow.

This module acts as the coordinator between the project scanner and 
the Excel writer. It handles the high-level workflow of discovering 
chronology data in a project and writing it to the specified output.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import logging
from pathlib import Path

from config import FOLDER_KEYS
from services.chronology_generator.excel_writer import ChronologyExcelWriter
from services.chronology_generator.models import ProjectChronology
from services.chronology_generator.project_scanner import ProjectScanner


class ChronologyGenerationError(Exception):
    """
    Raised when the chronology generation workflow fails.
    """
    pass


class ChronologyGenerator:
    """
    Coordinates the generation of a project's Ladder Chronology.

    Delegates scanning to ProjectScanner and writing to ChronologyExcelWriter.
    """

    def __init__(
        self,
        project_root: Path,
        template_path: Path,
        template_paths_by_folder: dict[Path, Path] | None = None,
    ) -> None:
        """
        Initializes the ChronologyGenerator.

        Args:
            project_root: The root directory of the operational package project.
            template_path: The path to the existing Excel template.
            template_paths_by_folder: Optional per-firmware template overrides.
        """
        self._project_root = project_root
        self._template_path = template_path
        self._template_paths_by_folder = template_paths_by_folder or {}
        self._logger = logging.getLogger(__name__)

    def scan_project(self) -> ProjectChronology:
        """
        Scans the project directory to build a chronology model.

        Returns:
            A populated ProjectChronology object containing all discovered 
            firmware/ladder file pairs and their metadata.

        Raises:
            ChronologyGenerationError: If the scanning process fails.
        """
        self._logger.info(f"Initiating project scan for: {self._project_root}")
        
        try:
            scanner = self._create_scanner()
            chronology = scanner.scan()
            self._logger.info(f"Scan complete. Discovered {len(chronology.entries)} chronology entries.")
            return chronology
        except Exception as exc:
            error_msg = f"Failed to scan project: {exc}"
            self._logger.error(error_msg)
            raise ChronologyGenerationError(error_msg) from exc

    def generate(self, output_path: Path | None = None) -> ProjectChronology:
        """
        Executes the full chronology generation workflow.

        1. Scans the project for chronology entries.
        2. Groups entries by firmware folder.
        3. Writes the data into an Excel output path inside each folder.

        Args:
            output_path: Deprecated. Chronologies are now generated per-folder.

        Returns:
            The generated ProjectChronology model.

        Raises:
            ChronologyGenerationError: If any step of the generation workflow fails.
        """
        self._logger.info("Starting chronology generation workflow for firmware groups")

        try:
            # Step 1: Scan project
            chronology = self.scan_project()

            # Step 2: Group entries
            groups = chronology.group_by_firmware_folder()
            if not groups:
                self._logger.warning("No firmware groups found to generate chronology for.")
                return chronology

            # Step 3: Pass each group to writer and save workbook
            for folder, entries in groups.items():
                if not entries:
                    continue
                    
                sub_chronology = ProjectChronology(project_root=self._project_root, entries=entries)

                target_path = self._resolve_chronology_output_path(folder)
                target_path.parent.mkdir(parents=True, exist_ok=True)

                template_path = target_path if target_path.exists() else self._template_paths_by_folder.get(folder, self._template_path)
                writer = ChronologyExcelWriter(template_path)

                self._logger.info(f"Generating chronology for group {folder} at {target_path}")
                writer.write(sub_chronology, target_path)

            self._logger.info("Chronology generation completed successfully.")
            return chronology
            
        except ChronologyGenerationError:
            # Re-raise already wrapped exceptions
            raise
        except Exception as exc:
            error_msg = f"Chronology generation workflow failed: {exc}"
            self._logger.error(error_msg)
            raise ChronologyGenerationError(error_msg) from exc

    def _create_scanner(self) -> ProjectScanner:
        """
        Creates and returns a configured ProjectScanner instance.

        Returns:
            ProjectScanner: A new scanner instance.
        """
        return ProjectScanner(self._project_root)

    def _create_writer(self) -> ChronologyExcelWriter:
        """
        Creates and returns a configured ChronologyExcelWriter instance.

        Returns:
            ChronologyExcelWriter: A new writer instance.
        """
        return ChronologyExcelWriter(self._template_path)

    def _resolve_chronology_output_path(self, firmware_folder: Path) -> Path:
        """Mirror firmware folder hierarchy from 2. Bin File into 7. Chronology."""
        bin_root = self._project_root / FOLDER_KEYS["bin_file"]
        chronology_root = self._project_root / FOLDER_KEYS["chronology"]

        try:
            relative_folder = firmware_folder.resolve().relative_to(bin_root.resolve())
        except Exception:
            # Fallback to folder name if the path cannot be relativized for any reason.
            relative_folder = Path(firmware_folder.name)

        return chronology_root / relative_folder / "Ladder_Chronology.xlsx"
