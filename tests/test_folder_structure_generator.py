from __future__ import annotations

from pathlib import Path

from config import PROJECT_ROOT_FOLDER_NAME, PROJECT_STRUCTURE
from services.folder_structure_generator import FolderStructureGenerator


def test_generates_complete_structure_from_config(tmp_path: Path) -> None:
    generator = FolderStructureGenerator()

    generated_root = generator.generate_structure(base_path=tmp_path)

    assert generated_root == tmp_path / PROJECT_ROOT_FOLDER_NAME
    assert generated_root.exists()
    assert (generated_root / "1. Ladders" / "Master" / "Initial").exists()
    assert (generated_root / "2. Bin File" / "Slave" / "Calb").exists()
    assert (generated_root / "3. Operational Flow").exists()
    assert (generated_root / "7. Chronology" / "Master" / "QC").exists()

    # Every configured top-level folder should be created.
    for folder_name in PROJECT_STRUCTURE:
        assert (generated_root / folder_name).exists()


def test_generate_structure_is_idempotent(tmp_path: Path) -> None:
    generator = FolderStructureGenerator()

    first_root = generator.generate_structure(base_path=tmp_path)
    second_root = generator.generate_structure(base_path=tmp_path)

    assert first_root == second_root
    assert (first_root / "1. Ladders" / "Master" / "Initial").exists()
    assert (first_root / "6. Ladder Flow").exists()
