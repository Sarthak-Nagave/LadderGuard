from __future__ import annotations

from pathlib import Path

from services.folder_structure_generator import FolderStructureGenerator


def test_generates_complete_structure_from_config(tmp_path: Path) -> None:
    generator = FolderStructureGenerator()
    (tmp_path / "m-initial.bin").touch()

    first_root = generator.generate_structure(base_path=tmp_path, source_project_path=tmp_path)
    second_root = generator.generate_structure(base_path=tmp_path, source_project_path=tmp_path)

    assert first_root == second_root
    assert (first_root / "1. Ladders").exists()
    assert not (first_root / "1. Ladders" / "Master" / "Initial").exists()
    assert (first_root / "6. Ladder Flow").exists()
