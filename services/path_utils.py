"""
services.path_utils
==================

Utility helpers for working with filesystem paths.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

from __future__ import annotations

from pathlib import Path


class PathUtils:
    """Filesystem helper methods."""

    @staticmethod
    def exists(path: Path) -> bool:
        return path.exists()

    @staticmethod
    def is_directory(path: Path) -> bool:
        return path.exists() and path.is_dir()

    @staticmethod
    def is_file(path: Path) -> bool:
        return path.exists() and path.is_file()

    @staticmethod
    def stem(path: Path) -> str:
        return path.stem

    @staticmethod
    def extension(path: Path) -> str:
        return path.suffix.lower()

    @staticmethod
    def filename(path: Path) -> str:
        return path.name

    @staticmethod
    def compare_stem(file1: Path, file2: Path) -> bool:
        return file1.stem.casefold() == file2.stem.casefold()

    @staticmethod
    def has_extension(path: Path, extension: str) -> bool:
        return path.suffix.casefold() == extension.casefold()

    @staticmethod
    def normalize(path: Path) -> Path:
        return path.resolve()

    @staticmethod
    def ensure_directory(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)