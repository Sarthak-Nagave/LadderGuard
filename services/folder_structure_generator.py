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

from config import PROJECT_ROOT_FOLDER_NAME, PROJECT_STRUCTURE
from services.logger import LoggerService

logger = LoggerService.get_logger()


class FolderStructureGenerator:
    """Create the configured operational package folder hierarchy."""

    def generate_structure(self, base_path: Path | None = None) -> Path:
        """Create the configured hierarchy under the given path or the Desktop."""
        target_root = self._resolve_target_root(base_path)
        target_root.mkdir(parents=True, exist_ok=True)

        self._create_structure(target_root, PROJECT_STRUCTURE)
        return target_root

    def _resolve_target_root(self, base_path: Path | None) -> Path:
        if base_path is not None:
            return base_path / PROJECT_ROOT_FOLDER_NAME

        desktop_path = Path.home() / "Desktop"
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
