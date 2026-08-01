"""
services.project_organizer
=========================

Organize legacy or flat project folders into the standard structure.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

import re
import shutil
from pathlib import Path
from typing import Any, Tuple, Optional

from services.logger import LoggerService
from services.folder_structure_generator import FolderStructureGenerator
from services.hierarchy_discovery import HierarchyDiscovery

logger = LoggerService.get_logger()

class ProjectOrganizerService:
    """Organizes projects into the standard folder structure."""

    def __init__(self) -> None:
        self.generator = FolderStructureGenerator()

    def organize_if_needed(self, project_path: Path) -> Path:
        """
        Check if the selected folder needs organization.
        If it's already an Operational Package, return it.
        Otherwise, trigger the generation of the operational package.
        """
        from config import PROJECT_ROOT_FOLDER_NAME, DEFAULT_FOLDER_GENERATION_TARGET
        
        # If the selected folder is already an operational package root
        if (project_path / "1. Ladders").exists() or (project_path / "2. Bin File").exists():
            return project_path
            
        # Or if the user selected a parent that contains the root folder
        if (project_path / PROJECT_ROOT_FOLDER_NAME / "1. Ladders").exists():
            return project_path / PROJECT_ROOT_FOLDER_NAME
            
        logger.info(f"Unorganized or raw engineering package detected at {project_path}. Reorganizing to Desktop...")
        
        operational_pkg_path = self.generator.generate_structure(source_project_path=project_path)
        
        logger.info("Routing Test Reports and Signed PDFs...")
        self._copy_pdfs(project_path, operational_pkg_path)
            
        logger.info("Project reorganization complete.")
        return operational_pkg_path

    def _copy_pdfs(self, source_dir: Path, target_root: Path) -> None:
        """Copy PDFs from the root of source_dir to the appropriate generated folders based on filename."""
        ladder_src = source_dir / "Ladder"
        bin_src = source_dir / "Bin Files"
        sources_to_scan = []
        if ladder_src.exists(): sources_to_scan.append(ladder_src)
        if bin_src.exists(): sources_to_scan.append(bin_src)
        
        firmware_dirs = HierarchyDiscovery.discover_firmware_hierarchy(sources_to_scan)
        test_report_root = target_root / "4. Test Report"

        for fw_dir in firmware_dirs:
            (test_report_root / fw_dir).mkdir(parents=True, exist_ok=True)
        
        # Use glob to only scan the root level.
        for file_path in source_dir.glob("*.pdf"):
            if not file_path.is_file():
                continue
                
            filename_lower = file_path.name.lower()
            dest_folder = None
            
            if "operational_flow" in filename_lower:
                dest_folder = target_root / "3. Operational Flow"
            elif "automation_input_doc" in filename_lower:
                dest_folder = target_root / "5. Automation Input Doc"
            elif "ladder_flow" in filename_lower:
                dest_folder = target_root / "6. Ladder Flow"
            elif "test_report" in filename_lower or "report_of_test" in filename_lower:
                dest_folder = test_report_root
                matches = []

                for fw_dir in firmware_dirs:
                    if self._matches_firmware_dir(file_path.stem, fw_dir):
                        matches.append(fw_dir)
                
                if len(matches) == 1:
                    dest_folder = dest_folder / matches[0]
                elif len(matches) > 1:
                    logger.warning(f"PDF {file_path.name} matched multiple folders ({matches}). Leaving at root.")
                else:
                    logger.warning(f"PDF {file_path.name} could not be routed with certainty. Leaving at root.")
            
            if dest_folder:
                try:
                    dest_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_folder / file_path.name
                    shutil.copy2(str(file_path), str(dest_path))
                    logger.info(f"Copied PDF {file_path.name} to {dest_folder.relative_to(target_root)}")
                except Exception as e:
                    logger.error(f"Failed to copy PDF {file_path.name}: {e}")

    @staticmethod
    def _matches_firmware_dir(filename_stem: str, fw_dir: Path) -> bool:
        filename_tokens = [token for token in re.split(r"[-_]+", filename_stem.lower()) if token]
        folder_tokens = [part.lower() for part in fw_dir.parts]

        if len(filename_tokens) < len(folder_tokens):
            return False

        return all(
            filename_token.startswith(folder_token) or folder_token.startswith(filename_token)
            for filename_token, folder_token in zip(filename_tokens, folder_tokens)
        )
