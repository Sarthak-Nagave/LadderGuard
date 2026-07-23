"""
services.file_search
====================

Provides reusable filesystem search operations for the Operational Package
Validator.

Responsibilities
----------------
- Directory lookup
- Recursive file search
- Exact filename search
- Extension filtering
- Deterministic (sorted) results
- Case-insensitive matching

Business validation rules DO NOT belong here.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

from __future__ import annotations

from pathlib import Path


class FileSearchService:
    """
    Provides filesystem search operations.

    This service contains no business logic and is shared across all
    validators.
    """

    @staticmethod
    def directory(
        root: Path,
        directory_name: str,
    ) -> Path | None:
        """
        Returns a direct child directory.

        Example:
            root/
                1. Ladders/

        Returns:
            Path | None
        """

        directory = root / directory_name

        if directory.exists() and directory.is_dir():
            return directory

        return None

    @staticmethod
    def recursive_files(
        directory: Path,
        extension: str | None = None,
    ) -> list[Path]:
        """
        Recursively searches for files with the given extension.

        Returns a sorted list. If no extension is provided, all files are
        returned.
        """

        if not directory.exists():
            return []

        if extension is None or extension == "":
            return sorted(
                file
                for file in directory.rglob("*")
                if file.is_file()
            )

        return sorted(
            file
            for file in directory.rglob("*")
            if file.is_file()
            and file.suffix.casefold() == extension.casefold()
        )

    @staticmethod
    def first_file(
        directory: Path,
        extension: str,
    ) -> Path | None:
        """
        Returns the first matching file.
        """

        files = FileSearchService.recursive_files(
            directory,
            extension,
        )

        if files:
            return files[0]

        return None

    @staticmethod
    def all_files(
        directory: Path,
    ) -> list[Path]:
        """
        Returns every file recursively.
        """

        if not directory.exists():
            return []

        return sorted(
            file
            for file in directory.rglob("*")
            if file.is_file()
        )

    @staticmethod
    def file_exists(
        directory: Path,
        filename: str,
    ) -> bool:
        """
        Case-insensitive filename search.
        """

        filename = filename.casefold()

        return any(
            file.name.casefold() == filename
            for file in FileSearchService.all_files(directory)
        )

    @staticmethod
    def files_with_suffix(
        directory: Path,
        suffix: str,
    ) -> list[Path]:
        """
        Returns files whose stem ends with the given suffix.

        Example

            TestReport-sgn.pdf

        suffix = "-sgn"
        """

        if not directory.exists():
            return []

        suffix = suffix.casefold()

        return sorted(
            file
            for file in directory.rglob("*")
            if file.is_file()
            and file.stem.casefold().endswith(suffix)
        )

    @staticmethod
    def subdirectories(
        directory: Path,
    ) -> list[Path]:
        """
        Returns direct child directories.
        """

        if not directory.exists():
            return []

        return sorted(
            child
            for child in directory.iterdir()
            if child.is_dir()
        )

    @staticmethod
    def recursive_directories(
        directory: Path,
    ) -> list[Path]:
        """
        Returns every directory recursively.
        """

        if not directory.exists():
            return []

        return sorted(
            folder
            for folder in directory.rglob("*")
            if folder.is_dir()
        )