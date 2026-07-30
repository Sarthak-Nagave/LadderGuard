"""
services.chronology_generator.models
====================================

Data models for the Ladder Chronology Generator.

These models represent the paired firmware (.bin) and ladder logic (.sdoc) 
files that constitute a single chronology entry in a project.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ChronologyEntry:
    """
    Represents a single row in the Ladder Chronology.
    
    Combines extracted data from the BIN, SDOC, and source paths, 
    as well as user-editable fields destined for the final Excel report.
    """

    # --- Core File Paths ---
    source_code_path: Path
    bin_file_path: Path
    sdoc_file_path: Path | None

    # --- Derived File Names ---
    bin_file_name: str
    sdoc_file_name: str | None

    # --- Extracted Metadata ---
    version: str
    plc_model: str
    selpro_version: str
    bootloader_version: str
    crc: int
    testing_stage: str
    release_date: str
    reason_for_upgrade: str

    # --- User Editable Fields ---
    released_by: str = ""
    tested_by: str = ""
    ladder_release_to_production: str = ""
    operator_procedure_modification: str = ""
    automation_setup_modification: str = ""

    @property
    def version_tuple(self) -> tuple[int, ...]:
        """
        Parses the version string into a tuple of integers for reliable sorting.
        Example: "V1.02" -> (1, 2)
        
        Returns:
            A tuple of integers representing the version.
        """
        # Extract all contiguous digits from the version string
        numbers = re.findall(r"\d+", self.version)
        if not numbers:
            return (0,)
        return tuple(int(num) for num in numbers)


@dataclass(slots=True)
class ProjectChronology:
    """
    Represents the full chronology of ladder firmware updates for a given project.
    
    Provides utility methods to aggregate and sort chronology entries.
    """

    project_root: Path
    entries: list[ChronologyEntry] = field(default_factory=list)

    def add_entry(self, entry: ChronologyEntry) -> None:
        """
        Appends a new chronology entry to the project.

        Args:
            entry: The ChronologyEntry to add.
        """
        self.entries.append(entry)

    def sorted_entries(self) -> list[ChronologyEntry]:
        """
        Retrieves all chronology entries, sorted strictly by version in descending order
        (latest version first).

        Returns:
            A sorted list of ChronologyEntry objects.
        """
        return sorted(
            self.entries,
            key=lambda e: (e.version_tuple, e.release_date),
            reverse=True,
        )

    def latest_entry(self) -> ChronologyEntry | None:
        """
        Retrieves the most recent chronology entry based on version sorting.

        Returns:
            The latest ChronologyEntry, or None if no entries exist.
        """
        sorted_list = self.sorted_entries()
        if not sorted_list:
            return None
        return sorted_list[0]

    def previous_entries(self) -> list[ChronologyEntry]:
        """
        Retrieves all historical chronology entries, excluding the latest one.
        Entries are returned sorted in descending order (newest to oldest).

        Returns:
            A list of historical ChronologyEntry objects.
        """
        sorted_list = self.sorted_entries()
        if len(sorted_list) <= 1:
            return []
        return sorted_list[1:]