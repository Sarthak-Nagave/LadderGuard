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

    def __init__(self, project_root: Path, template_path: Path) -> None:
        """
        Initializes the ChronologyGenerator.

        Args:
            project_root: The root directory of the operational package project.
            template_path: The path to the existing Excel template.
        """
        self._project_root = project_root
        self._template_path = template_path
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

    def generate(self, output_path: Path) -> ProjectChronology:
        """
        Executes the full chronology generation workflow.

        1. Scans the project for chronology entries.
        2. Sorts the entries (handled by the model/writer).
        3. Writes the data into the specified Excel output path using the template.

        Args:
            output_path: The destination path for the generated Excel file.

        Returns:
            The generated ProjectChronology model.

        Raises:
            ChronologyGenerationError: If any step of the generation workflow fails.
        """
        self._logger.info(f"Starting chronology generation targeting: {output_path}")

        try:
            # Step 1: Scan project
            chronology = self.scan_project()

            # Step 2 & 3 & 4: Pass chronology to writer and save workbook
            writer = self._create_writer()
            writer.write(chronology, output_path)

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