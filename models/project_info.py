"""
models.project_info
===================

Represents a project selected for validation.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class ProjectInfo:
    """
    Metadata describing the project being validated.
    """

    project_path: Path

    project_name: str

    created_at: datetime = field(default_factory=datetime.now)

    total_folders: int = 0

    total_files: int = 0

    validated_files: int = 0

    validation_success: bool = False

    @property
    def completion_percentage(self) -> float:
        """
        Returns validation completion percentage.
        """

        if self.total_files == 0:
            return 0.0

        return round(
            (self.validated_files / self.total_files) * 100,
            2,
        )

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "project_path": str(self.project_path),
            "created_at": self.created_at.isoformat(),
            "total_folders": self.total_folders,
            "total_files": self.total_files,
            "validated_files": self.validated_files,
            "validation_success": self.validation_success,
            "completion_percentage": self.completion_percentage,
        }