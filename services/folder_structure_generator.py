"""
services.folder_structure_generator
=================================

Generate the operational package folder structure from configuration.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from config import DEFAULT_FOLDER_GENERATION_TARGET, PROJECT_ROOT_FOLDER_NAME, REQUIRED_FOLDERS
from services.logger import LoggerService
from services.mirror_service import MirrorService
from services.hierarchy_discovery import HierarchyDiscovery

logger = LoggerService.get_logger()


class FolderStructureGenerator:
    """Create the configured operational package folder hierarchy."""

    def generate_structure(self, base_path: Path | None = None, source_project_path: Path | None = None) -> Path:
        """Create the configured hierarchy under the given path or the Desktop."""
        target_root = self._resolve_target_root(base_path)
        target_root.mkdir(parents=True, exist_ok=True)

        # Always create only the required top-level baseline folders.
        # Intentionally ignore any nested hierarchy that may be present in config.
        self._create_required_roots(target_root)
            
        if not source_project_path or not source_project_path.exists():
            return target_root
            
        ladder_src = source_project_path / "Ladder"
        bin_src = source_project_path / "Bin Files"
        
        # Discover firmware hierarchy
        sources_to_scan = []
        if ladder_src.exists(): sources_to_scan.append(ladder_src)
        if bin_src.exists(): sources_to_scan.append(bin_src)
        
        # Discover dynamic hierarchy from engineering folders
        firmware_dirs = HierarchyDiscovery.discover_firmware_hierarchy(sources_to_scan)
        
        # Strategy 1: Ladder
        if ladder_src.exists():
            logger.info("Mirroring Ladder...")
            MirrorService.mirror_ladder(ladder_src, target_root / "1. Ladders")
            
        # Strategy 2: Bin Files
        if bin_src.exists():
            logger.info("Mirroring Bin Files...")
            MirrorService.mirror_bin_files(bin_src, target_root / "2. Bin File")
            
        # Strategy 3: Chronology
        if firmware_dirs:
            logger.info("Creating Chronology hierarchy...")
            MirrorService.generate_chronology(firmware_dirs, target_root / "7. Chronology")
            
        return target_root



    def _resolve_target_root(self, base_path: Path | None) -> Path:
        if base_path is not None:
            return base_path / PROJECT_ROOT_FOLDER_NAME

        desktop_path = Path.home() / DEFAULT_FOLDER_GENERATION_TARGET
        return desktop_path / PROJECT_ROOT_FOLDER_NAME

    def _create_required_roots(self, root: Path) -> None:
        for folder_name in REQUIRED_FOLDERS:
            (root / folder_name).mkdir(parents=True, exist_ok=True)

        logger.debug("Created required root folders at %s", root)
