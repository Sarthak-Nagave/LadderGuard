"""
core.validation_context
=======================

Shared validation context used throughout the validation pipeline.

This object is created once by the ValidationEngine and passed to every
validator. It acts as a shared state container, allowing validators to
reuse discovered information instead of repeatedly scanning the filesystem.

Responsibilities
----------------
- Store project metadata.
- Cache discovered folders and files.
- Store validation results.
- Share information between validators.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.validation_result import ValidationResult


@dataclass(slots=True)
class ValidationContext:
    """
    Shared validation context.

    Every validator receives the same instance during a validation session.
    """

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    project_path: Path

    # ------------------------------------------------------------------
    # Folder Cache
    # ------------------------------------------------------------------

    folders: dict[str, Path] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Ladder Files
    # ------------------------------------------------------------------

    ladder_files: dict[str, Path] = field(default_factory=dict)

    # Example:
    # {
    #     "Master/Initial": Path(...),
    #     "Slave/QC": Path(...)
    # }

    # ------------------------------------------------------------------
    # BIN Files
    # ------------------------------------------------------------------

    bin_files: dict[str, Path] = field(default_factory=dict)

    # Example:
    # {
    #     "Master/Initial": Path(...),
    #     "Slave/QC": Path(...)
    # }

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    documents: dict[str, Path] = field(default_factory=dict)

    # Example:
    # {
    #     "Operational Flow": Path(...),
    #     "Test Report": Path(...)
    # }

    # ------------------------------------------------------------------
    # Signature Information
    # ------------------------------------------------------------------

    signatures: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Discovered Folder Structure
    # ------------------------------------------------------------------

    discovered_paths: list[tuple[str, Path]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Validation Results
    # ------------------------------------------------------------------

    results: list[ValidationResult] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Shared Runtime Data
    # ------------------------------------------------------------------

    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    def add_result(self, result: ValidationResult) -> None:
        """
        Add a validation result to the context.
        """
        self.results.append(result)

    def add_folder(self, name: str, path: Path) -> None:
        """
        Cache a discovered folder.
        """
        self.folders[name] = path

    def add_ladder_file(self, stage: str, path: Path) -> None:
        """
        Cache a discovered ladder file.
        """
        self.ladder_files[stage] = path

    def add_bin_file(self, stage: str, path: Path) -> None:
        """
        Cache a discovered BIN file.
        """
        self.bin_files[stage] = path

    def add_document(self, name: str, path: Path) -> None:
        """
        Cache a discovered document.
        """
        self.documents[name] = path

    def add_signature(self, document: str, signature: Any) -> None:
        """
        Cache extracted signature information.
        """
        self.signatures[document] = signature

    def add_discovered_path(self, relative_path: str, path: Path) -> None:
        """
        Cache a discovered folder path relative to the ladders root.
        """
        self.discovered_paths.append((relative_path, path))

    def set_metadata(self, key: str, value: Any) -> None:
        """
        Store arbitrary runtime metadata.
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Retrieve runtime metadata.
        """
        return self.metadata.get(key, default)

    def clear(self) -> None:
        """
        Reset the context.

        Primarily intended for testing or reusing the instance.
        """
        self.folders.clear()
        self.ladder_files.clear()
        self.bin_files.clear()
        self.documents.clear()
        self.signatures.clear()
        self.results.clear()
        self.metadata.clear()