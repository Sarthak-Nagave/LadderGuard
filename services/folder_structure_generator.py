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

from config import DEFAULT_FOLDER_GENERATION_TARGET, PROJECT_ROOT_FOLDER_NAME, PROJECT_STRUCTURE
from services.logger import LoggerService

logger = LoggerService.get_logger()


class FolderStructureGenerator:
    """Create the configured operational package folder hierarchy."""

    def generate_structure(self, base_path: Path | None = None, source_project_path: Path | None = None) -> Path:
        """Create the configured hierarchy under the given path or the Desktop."""
        target_root = self._resolve_target_root(base_path)
        target_root.mkdir(parents=True, exist_ok=True)

        dynamic_structure = self.build_dynamic_structure(source_project_path)
        self._create_structure(target_root, dynamic_structure)
        return target_root

    def build_dynamic_structure(self, source_path: Path | None) -> dict[str, Any]:
        """Dynamically filters the project structure based on existing firmware groups."""
        import copy
        structure = copy.deepcopy(PROJECT_STRUCTURE)
        
        groups = {"Master": set(), "Slave": set()}
        
        if source_path and source_path.exists():
            for file_path in source_path.rglob("*"):
                if not file_path.is_file():
                    continue
                    
                # Skip files inside Backup, GRP, POU
                parts_lower = [p.lower() for p in file_path.parts]
                if any(ignored in parts_lower for ignored in ["backup", "grp", "pou"]):
                    continue
                    
                ext = file_path.suffix.lower()
                if ext not in [".bin", ".sdoc"]:
                    continue
                
                is_master = False
                is_slave = False
                is_initial = False
                is_final = False
                
                # Check filename first
                import re
                name = file_path.name.lower()
                tokens = set(re.findall(r'[a-z0-9]+', name))
                
                if "m" in tokens or "master" in tokens:
                    is_master = True
                elif "s" in tokens or "slave" in tokens:
                    is_slave = True
                    
                if "initial" in tokens:
                    is_initial = True
                elif "final" in tokens:
                    is_final = True
                
                # Check parts from immediate parent upwards if not fully determined
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
                
                if is_master and is_initial: groups["Master"].add("Initial")
                if is_master and is_final: groups["Master"].add("Final")
                if is_slave and is_initial: groups["Slave"].add("Initial")
                if is_slave and is_final: groups["Slave"].add("Final")

        # Filter the structure for specific keys
        for key in ["1. Ladders", "2. Bin File", "7. Chronology"]:
            if key in structure:
                structure[key] = {}
                if groups["Master"]:
                    structure[key]["Master"] = list(groups["Master"])
                if groups["Slave"]:
                    structure[key]["Slave"] = list(groups["Slave"])
                    
        return structure

    def _resolve_target_root(self, base_path: Path | None) -> Path:
        if base_path is not None:
            return base_path / PROJECT_ROOT_FOLDER_NAME

        desktop_path = Path.home() / DEFAULT_FOLDER_GENERATION_TARGET
        return desktop_path / PROJECT_ROOT_FOLDER_NAME

    def _create_structure(self, root: Path, structure: dict[str, Any]) -> None:
        for folder_name, children in structure.items():
            current_path = root / folder_name
            current_path.mkdir(parents=True, exist_ok=True)
            if isinstance(children, dict):
                self._create_structure(current_path, children)
            elif isinstance(children, list):
                for child_name in children:
                    (current_path / child_name).mkdir(parents=True, exist_ok=True)

        logger.debug("Created folder structure at %s", root)
