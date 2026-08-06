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

from services.folder_structure_generator import FolderStructureGenerator
from services.hierarchy_discovery import HierarchyDiscovery
from services.logger import LoggerService

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
        from config import PROJECT_ROOT_FOLDER_NAME
        
        # If the selected folder is already an operational package root
        if (project_path / "1. Ladders").exists() or (project_path / "2. Bin File").exists():
            return project_path
            
        # Or if the user selected a parent that contains the root folder
        if (project_path / PROJECT_ROOT_FOLDER_NAME / "1. Ladders").exists():
            return project_path / PROJECT_ROOT_FOLDER_NAME
            
        logger.info(f"Unorganized or raw engineering package detected at {project_path}. Reorganizing to Desktop...")
        
        operational_pkg_path = self.generator.generate_structure(source_project_path=project_path)
        
        logger.info("Routing Document Files...")
        self._copy_document_files(project_path, operational_pkg_path)
            
        logger.info("Project reorganization complete.")
        return operational_pkg_path

    def _copy_document_files(self, source_dir: Path, target_root: Path) -> None:
        """Copy document files from the root of source_dir to the appropriate generated folders based on filename."""
        ladder_src = source_dir / "Ladder"
        bin_src = source_dir / "Bin Files"
        sources_to_scan = []
        if ladder_src.exists(): sources_to_scan.append(ladder_src)
        if bin_src.exists(): sources_to_scan.append(bin_src)
        
        firmware_dirs = HierarchyDiscovery.discover_firmware_hierarchy(sources_to_scan)
        test_report_root = target_root / "4. Test Report"

        # Scan all files at the root level for standard documents.
        for file_path in source_dir.iterdir():
            if not file_path.is_file():
                continue
                
            filename_lower = file_path.name.lower()
            normalized_filename = filename_lower.replace("-", " ").replace("_", " ")
            dest_folder = None
            
            if "operational flow" in normalized_filename:
                dest_folder = target_root / "3. Operational Flow"
            elif "automation input doc" in normalized_filename:
                dest_folder = target_root / "5. Automation Input Doc"
            elif "ladder flow" in normalized_filename:
                dest_folder = target_root / "6. Ladder Flow"
            elif "test report" in normalized_filename or "report of test" in normalized_filename or "validation" in normalized_filename:
                stem_norm = file_path.stem.lower().replace("-", " ").replace("_", " ")
                tokens = set(stem_norm.split())
                
                fw_type = None
                if "master" in tokens or "m" in tokens:
                    fw_type = "Master"
                elif "slave" in tokens or "s" in tokens:
                    fw_type = "Slave"
                elif "uut" in tokens or "u" in tokens:
                    fw_type = "UUT"
                    
                stage = None
                if "initial" in tokens:
                    stage = "Initial"
                elif "final" in tokens:
                    stage = "Final"
                elif "qc" in tokens:
                    stage = "QC"
                    
                if fw_type and stage:
                    dest_folder = test_report_root / fw_type / stage
                    try:
                        dest_folder.mkdir(parents=True, exist_ok=True)
                        dest_path = dest_folder / file_path.name
                        shutil.copy2(str(file_path), str(dest_path))
                        logger.info(f"Copied test report {file_path.name} to {dest_folder.relative_to(target_root)}")
                    except Exception as e:
                        logger.error(f"Failed to copy test report {file_path.name}: {e}")
                    continue
                
                logger.warning(f"File {file_path.name} could not be mapped dynamically. Leaving at root.")
                continue # Skip the default dest_folder block below since we handled it
            
            if dest_folder:
                try:
                    dest_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_folder / file_path.name
                    shutil.copy2(str(file_path), str(dest_path))
                    logger.info(f"Copied file {file_path.name} to {dest_folder.relative_to(target_root)}")
                except Exception as e:
                    logger.error(f"Failed to copy file {file_path.name}: {e}")

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
