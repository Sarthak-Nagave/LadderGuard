"""
services.project_organizer
=========================

Organize legacy or flat project folders into the standard structure.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

import shutil
from pathlib import Path
from typing import Any

from config import (
    LADDER_EXTENSION,
    BIN_EXTENSION,
)
from services.logger import LoggerService
from services.folder_structure_generator import FolderStructureGenerator

logger = LoggerService.get_logger()

class ProjectOrganizerService:
    """Organizes flat release packages into the standard folder structure."""

    def __init__(self) -> None:
        self.generator = FolderStructureGenerator()

    def organize_if_needed(self, project_path: Path) -> Path:
        """
        Check if the selected folder needs organization.
        If it's already an Operational Package, return it.
        Otherwise, scan the flat release package and generate the Operational Package on the Desktop.
        """
        from config import PROJECT_ROOT_FOLDER_NAME, DEFAULT_FOLDER_GENERATION_TARGET
        
        # If the selected folder is already an operational package root
        if (project_path / "1. Ladders").exists() or (project_path / "2. Bin File").exists():
            return project_path
            
        # Or if the user selected a parent that contains the root folder
        if (project_path / PROJECT_ROOT_FOLDER_NAME / "1. Ladders").exists():
            return project_path / PROJECT_ROOT_FOLDER_NAME
            
        logger.info(f"Unorganized / Flat release package detected at {project_path}. Reorganizing to Desktop...")
        
        operational_pkg_path = Path.home() / DEFAULT_FOLDER_GENERATION_TARGET / PROJECT_ROOT_FOLDER_NAME
        operational_pkg_path.mkdir(parents=True, exist_ok=True)
        
        dynamic_structure = self.generator.build_dynamic_structure(project_path)
        self.generator._create_structure(operational_pkg_path, dynamic_structure)
        
        generated_ladder_folders = self._get_generated_firmware_folders(dynamic_structure, "1. Ladders")
        
        self._distribute_firmware_files(project_path, operational_pkg_path)
        self._distribute_ladder_supporting_files(project_path, operational_pkg_path, generated_ladder_folders)
        self._restore_project_resources(project_path, operational_pkg_path, generated_ladder_folders)
        self._copy_pdfs(project_path, operational_pkg_path)
            
        logger.info("Project reorganization complete.")
        return operational_pkg_path

    def _get_generated_firmware_folders(self, dynamic_structure: dict[str, Any], section: str) -> list[tuple[str, str]]:
        """Extract a list of (Master|Slave, Initial|Final) tuples that were generated for a specific section."""
        folders = []
        section_dict = dynamic_structure.get(section, {})
        for ms_key, stages in section_dict.items():
            if isinstance(stages, list):
                for stage in stages:
                    folders.append((ms_key, stage))
        return folders

    def _distribute_firmware_files(self, source_root: Path, target_root: Path) -> None:
        """Copy .bin and .sdoc files from source_root to the generated firmware folders."""
        for file_path in source_root.rglob("*"):
            if not file_path.is_file():
                continue
                
            parts_lower = [p.lower() for p in file_path.parts]
            if any(ignored in parts_lower for ignored in ["backup", "grp", "pou"]):
                continue

            ext = file_path.suffix.lower()
            if ext not in [LADDER_EXTENSION, BIN_EXTENSION]:
                continue
                
            ms, stage = self._determine_firmware_group(file_path)
            if not ms or not stage:
                logger.warning(f"File {file_path.name} does not match M-initial or S-final pattern. Skipping copy.")
                continue
                
            if ext == LADDER_EXTENSION:
                dest_folder = target_root / "1. Ladders" / ms / stage
            elif ext == BIN_EXTENSION:
                dest_folder = target_root / "2. Bin File" / ms / stage
                
            if dest_folder.exists():
                dest_path = dest_folder / file_path.name
                try:
                    shutil.copy2(str(file_path), str(dest_path))
                    logger.info(f"Copied {file_path.name} to {dest_folder.relative_to(target_root)}")
                except Exception as e:
                    logger.error(f"Failed to copy {file_path.name}: {e}")

    def _determine_firmware_group(self, file_path: Path) -> tuple[str | None, str | None]:
        """Determine Master/Slave and Initial/Final based on the exact same logic as structure generation."""
        is_master = False
        is_slave = False
        is_initial = False
        is_final = False
        
        import re
        name_lower = file_path.name.lower()
        tokens = set(re.findall(r'[a-z0-9]+', name_lower))
        
        if "m" in tokens or "master" in tokens:
            is_master = True
        elif "s" in tokens or "slave" in tokens:
            is_slave = True
            
        if "initial" in tokens:
            is_initial = True
        elif "final" in tokens:
            is_final = True
            
        if not (is_master or is_slave) or not (is_initial or is_final):
            for p in reversed(file_path.parts[:-1]):
                p_low = p.lower()
                p_tokens = set(re.findall(r'[a-z0-9]+', p_low))
                if not (is_master or is_slave):
                    if "m" in p_tokens or "master" in p_tokens: is_master = True
                    elif "s" in p_tokens or "slave" in p_tokens: is_slave = True
                if not (is_initial or is_final):
                    if "initial" in p_tokens: is_initial = True
                    elif "final" in p_tokens: is_final = True

        ms = "Master" if is_master else ("Slave" if is_slave else None)
        stage = "Initial" if is_initial else ("Final" if is_final else None)
        return ms, stage

    def _distribute_ladder_supporting_files(self, source_root: Path, target_root: Path, ladder_folders: list[tuple[str, str]]) -> None:
        """Copy ct.ld, h1.ssx, h2.ssx from the source to every generated ladder firmware folder."""
        supporting_files = ["ct.ld", "h1.ssx", "h2.ssx"]
        
        for file_name in supporting_files:
            found_files = list(source_root.rglob(file_name))
            if not found_files:
                logger.debug(f"Supporting file {file_name} not found in {source_root}.")
                continue
                
            source_file = found_files[0]
            for ms, stage in ladder_folders:
                dest_folder = target_root / "1. Ladders" / ms / stage
                if dest_folder.exists():
                    dest_path = dest_folder / file_name
                    try:
                        shutil.copy2(str(source_file), str(dest_path))
                        logger.info(f"Copied {file_name} to {dest_folder.relative_to(target_root)}")
                    except Exception as e:
                        logger.error(f"Failed to copy {file_name} to {dest_folder}: {e}")

    def _restore_project_resources(self, source_root: Path, target_root: Path, ladder_folders: list[tuple[str, str]]) -> None:
        """Copy Backup, GRP, and POU folders directly into every generated ladder firmware folder."""
        resources = ["Backup", "GRP", "POU"]
        
        for res in resources:
            source_res = source_root / res
            if not source_res.exists():
                source_res = source_root / res.lower()
                
            if source_res.exists() and source_res.is_dir():
                for ms, stage in ladder_folders:
                    dest_res = target_root / "1. Ladders" / ms / stage / res
                    try:
                        shutil.copytree(str(source_res), str(dest_res), dirs_exist_ok=True)
                        logger.info(f"Restored project resource folder {res} to 1. Ladders/{ms}/{stage}")
                    except Exception as e:
                        logger.error(f"Failed to copy project resource folder {res} to {ms}/{stage}: {e}")

    def _copy_pdfs(self, source_dir: Path, target_root: Path) -> None:
        """Copy PDFs from source_dir to the appropriate generated folders based on filename."""
        for file_path in source_dir.rglob("*.pdf"):
            if not file_path.is_file():
                continue
                
            parts_lower = [p.lower() for p in file_path.parts]
            if any(ignored in parts_lower for ignored in ["backup", "grp", "pou"]):
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
                if "m-initial" in filename_lower or ("master" in filename_lower and "initial" in filename_lower):
                    dest_folder = target_root / "4. Test Report" / "Master" / "Initial"
                elif "s-final" in filename_lower or ("slave" in filename_lower and "final" in filename_lower):
                    dest_folder = target_root / "4. Test Report" / "Slave" / "Final"
                else:
                    ms, stage = self._determine_firmware_group(file_path)
                    if ms and stage:
                        dest_folder = target_root / "4. Test Report" / ms / stage
                    else:
                        dest_folder = target_root / "4. Test Report"
            
            if dest_folder:
                dest_folder.mkdir(parents=True, exist_ok=True)
                dest_path = dest_folder / file_path.name
                try:
                    shutil.copy2(str(file_path), str(dest_path))
                    logger.info(f"Copied PDF {file_path.name} to {dest_folder.relative_to(target_root)}")
                except Exception as e:
                    logger.error(f"Failed to copy PDF {file_path.name}: {e}")
