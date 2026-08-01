"""
services.hierarchy_discovery
=============================

Discover the engineering folder hierarchy dynamically from source projects
without hardcoding folder names or making assumptions.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

import os
from pathlib import Path
from typing import List, Set

from services.logger import LoggerService

logger = LoggerService.get_logger()


class HierarchyDiscovery:
    """Helper to extract the true engineering hierarchy from the source project."""

    @staticmethod
    def discover_firmware_hierarchy(sources: List[Path]) -> List[Path]:
        """
        Scan the source directories and return a distinct list of relative paths
        representing the firmware directory hierarchy (e.g. ['Master/Initial', 'StationA/QC']).
        
        It determines a firmware directory by searching for standard engineering folders
        (Backup, GRP, POU) or firmware files (.bin, .sdoc, .ld, .ssx) inside it.
        """
        firmware_dirs: Set[Path] = set()
        
        for source in sources:
            if not source.exists() or not source.is_dir():
                continue

            for root, dirs, files in os.walk(source):
                root_path = Path(root)
                rel_path = root_path.relative_to(source)

                child_dir_names = {directory.lower() for directory in dirs}
                has_engineering_markers = bool(child_dir_names.intersection({"backup", "grp", "pou"}))
                has_firmware_files = any(
                    Path(file).suffix.lower() in [".bin", ".sdoc", ".ld", ".ssx"]
                    for file in files
                )

                if str(rel_path) != "." and (has_engineering_markers or has_firmware_files):
                    firmware_dirs.add(rel_path)
                    # A detected firmware folder is a terminal node; do not discover inside it.
                    dirs[:] = []
                    continue
                            
        # Filter out the root path if it was accidentally added (e.g., flat packages)
        # But if it's a flat package, should we return Path('.')? 
        # Flat packages have no hierarchy.
        valid_dirs = [d for d in firmware_dirs if str(d) != "."]
        return sorted(valid_dirs)
