"""
services.project_organizer
=========================

Organize legacy or unformatted project folders into the standard structure.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

import shutil
from pathlib import Path

from config import (
    LADDER_EXTENSION,
    BIN_EXTENSION,
)
from services.logger import LoggerService
from services.folder_structure_generator import FolderStructureGenerator

logger = LoggerService.get_logger()

class ProjectOrganizerService:
    """Organizes existing project files into the standard folder structure."""

    def __init__(self) -> None:
        self.generator = FolderStructureGenerator()

    def organize_if_needed(self, project_path: Path) -> Path:
        """
        Check if the selected folder needs organization (contains 'ladders' or 'bin files').
        If so, generate the standard structure and move the files accordingly.
        Returns the path that should be used as the project root.
        """
        ladders_dir = project_path / "ladders"
        bin_dir = project_path / "bin files"

        from config import PROJECT_ROOT_FOLDER_NAME, DEFAULT_FOLDER_GENERATION_TARGET
        
        pdfs_to_move = list(project_path.glob("*.pdf"))
        needs_organization = ladders_dir.exists() or bin_dir.exists() or len(pdfs_to_move) > 0
        
        if not needs_organization:
            # If the user selected the parent folder which already contains the root folder
            if (project_path / PROJECT_ROOT_FOLDER_NAME).exists():
                return project_path / PROJECT_ROOT_FOLDER_NAME
            return project_path
            
        logger.info(f"Unorganized project detected at {project_path}. Reorganizing to Desktop...")
        
        operational_pkg_path = Path.home() / DEFAULT_FOLDER_GENERATION_TARGET / PROJECT_ROOT_FOLDER_NAME
        operational_pkg_path.mkdir(parents=True, exist_ok=True)
        
        from config import PROJECT_STRUCTURE
        self.generator._create_structure(operational_pkg_path, PROJECT_STRUCTURE)
        
        if ladders_dir.exists():
            self._move_files(ladders_dir, operational_pkg_path, LADDER_EXTENSION)
            
        if bin_dir.exists():
            self._move_files(bin_dir, operational_pkg_path, BIN_EXTENSION)
            
        self._move_pdfs(project_path, operational_pkg_path)
            
        logger.info("Project reorganization complete.")
        return operational_pkg_path

    def _move_files(self, source_dir: Path, target_root: Path, extension: str) -> None:
        """Move files from source_dir to the appropriate generated folders based on filename."""
        for file_path in source_dir.rglob(f"*{extension}"):
            if not file_path.is_file():
                continue
                
            filename_lower = file_path.name.lower()
            
            # Determine target subfolder based on extension and filename
            if extension == LADDER_EXTENSION:
                base_target = target_root / "1. Ladders"
            elif extension == BIN_EXTENSION:
                base_target = target_root / "2. Bin File"
            else:
                continue
                
            if "m-initial" in filename_lower:
                dest_folder = base_target / "Master" / "Initial"
            elif "s-final" in filename_lower:
                dest_folder = base_target / "Slave" / "Final"
            else:
                # If it doesn't match the specific names, we might just leave it or move to a default.
                # For now, skip moving if it doesn't match the pattern.
                logger.warning(f"File {file_path.name} does not match M-initial or S-final pattern. Skipping move.")
                continue
                
            dest_folder.mkdir(parents=True, exist_ok=True)
            dest_path = dest_folder / file_path.name
            
            try:
                shutil.move(str(file_path), str(dest_path))
                logger.info(f"Moved {file_path.name} to {dest_folder.relative_to(target_root)}")
            except Exception as e:
                logger.error(f"Failed to move {file_path.name}: {e}")
                
        # Try to remove the source directory if it's empty
        try:
            if any(source_dir.iterdir()):
                logger.info(f"Source directory {source_dir.name} is not empty, skipping removal.")
            else:
                source_dir.rmdir()
                logger.info(f"Removed empty source directory {source_dir.name}.")
        except Exception as e:
            logger.error(f"Failed to remove source directory {source_dir.name}: {e}")

    def _move_pdfs(self, source_dir: Path, target_root: Path) -> None:
        """Move PDFs from source_dir to the appropriate generated folders based on filename."""
        for file_path in source_dir.glob("*.pdf"):
            if not file_path.is_file():
                continue
                
            filename_lower = file_path.name.lower()
            dest_folder = None
            
            # Use specific filename keywords to determine target folder
            if "operational_flow" in filename_lower:
                dest_folder = target_root / "3. Operational Flow"
            elif "automation_input_doc" in filename_lower:
                dest_folder = target_root / "5. Automation Input Doc"
            elif "ladder_flow" in filename_lower:
                dest_folder = target_root / "6. Ladder Flow"
            elif "test_report" in filename_lower or "report_of_test" in filename_lower:
                if "m-initial" in filename_lower:
                    dest_folder = target_root / "4. Test Report" / "Master" / "Initial"
                elif "s-final" in filename_lower:
                    dest_folder = target_root / "4. Test Report" / "Slave" / "Final"
                else:
                    dest_folder = target_root / "4. Test Report"
            
            if dest_folder:
                dest_folder.mkdir(parents=True, exist_ok=True)
                dest_path = dest_folder / file_path.name
                try:
                    shutil.move(str(file_path), str(dest_path))
                    logger.info(f"Moved PDF {file_path.name} to {dest_folder.relative_to(target_root)}")
                except Exception as e:
                    logger.error(f"Failed to move PDF {file_path.name}: {e}")
