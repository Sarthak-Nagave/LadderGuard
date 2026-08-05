"""
services.mirror_service
=======================

Provides independent mirroring strategies for Operational Package Generation.
It isolates Ladder, Bin Files, and Chronology generation into separate implementations
to prevent sharing traversal results or reusing recursive logic incorrectly.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

import shutil
from pathlib import Path

from services.logger import LoggerService

logger = LoggerService.get_logger()


class MirrorService:
    """Handles independent mirroring strategies for project generation."""

    @staticmethod
    def mirror_ladder(source: Path, target_root: Path) -> list[str]:
        """
        Strategy 1: Mirror Ladder
        Recursively copies everything from the Ladder source to the target.
        """
        errors = []
        if not source.exists() or not source.is_dir():
            errors.append(f"Source path {source} does not exist or is not a directory.")
            return errors

        try:
            if target_root.exists():
                shutil.rmtree(target_root)
            target_root.mkdir(parents=True, exist_ok=True)
            for item in source.iterdir():
                if item.is_dir():
                    shutil.copytree(item, target_root / item.name)
                else:
                    shutil.copy2(item, target_root / item.name)
        except Exception as e:
            errors.append(f"Failed to mirror Ladder directory {target_root}: {e}")
        return errors

    @staticmethod
    def mirror_bin_files(source: Path, target_root: Path) -> list[str]:
        """
        Strategy 2: Mirror Bin Files
        Recursively mirrors the Bin Files source to the target without filtering.
        """
        errors = []
        if not source.exists() or not source.is_dir():
            errors.append(f"Source path {source} does not exist or is not a directory.")
            return errors

        try:
            if target_root.exists():
                shutil.rmtree(target_root)
            target_root.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Failed to prepare target directory {target_root}: {e}")
            return errors

        try:
            for item in source.iterdir():
                if item.is_dir():
                    shutil.copytree(item, target_root / item.name)
                else:
                    shutil.copy2(item, target_root / item.name)
        except Exception as e:
            msg = f"Failed to mirror Bin Files directory {target_root}: {e}"
            logger.error(msg)
            errors.append(msg)
        return errors

    @staticmethod
    def generate_chronology(firmware_dirs: list[Path], target_root: Path) -> list[str]:
        """
        Strategy 3: Generate Chronology
        Creates empty matching directories based on the pre-discovered firmware hierarchy.
        Does not copy files. Does not descend into engineering folders.
        """
        errors = []
        target_root.mkdir(parents=True, exist_ok=True)
        
        for fw_dir in firmware_dirs:
            if str(fw_dir) == ".":
                continue
            dest_dir = target_root / fw_dir
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                msg = f"Failed to create Chronology directory '{fw_dir}': {e}"
                logger.error(msg)
                errors.append(msg)
                
        return errors
