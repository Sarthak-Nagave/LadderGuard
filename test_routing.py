import os
from pathlib import Path
from services.folder_structure_generator import FolderStructureGenerator
from services.project_organizer import ProjectOrganizerService
from config import PROJECT_ROOT_FOLDER_NAME
import shutil

def setup_test_project():
    test_dir = Path("test_dynamic_project")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        
    test_dir.mkdir()
    
    # Create Ladder directory with custom hierarchy
    ladder_dir = test_dir / "Ladder"
    (ladder_dir / "StationA" / "PreQC").mkdir(parents=True)
    (ladder_dir / "StationA" / "PreQC" / "Backup").mkdir()
    (ladder_dir / "StationA" / "PreQC" / "test.ld").touch()
    
    (ladder_dir / "Sim" / "Test").mkdir(parents=True)
    (ladder_dir / "Sim" / "Test" / "GRP").mkdir()
    
    # Create Bin Files directory mirroring it
    bin_dir = test_dir / "Bin Files"
    (bin_dir / "StationA" / "PreQC").mkdir(parents=True)
    (bin_dir / "StationA" / "PreQC" / "firmware.bin").touch()
    
    (bin_dir / "Sim" / "Test").mkdir(parents=True)
    (bin_dir / "Sim" / "Test" / "sim_firmware.hex").touch()
    
    # Create PDFs in root
    (test_dir / "StationA-PreQC-report_of_test-sgn.pdf").touch()
    (test_dir / "Sim_Test_test_report.pdf").touch()
    (test_dir / "Ambiguous-report_of_test.pdf").touch() # Should fail to route
    
    # Create some legacy naming to ensure they don't route magically
    (test_dir / "M-Initial-report_of_test.pdf").touch()
    
    return test_dir

if __name__ == "__main__":
    print("Setting up test project...")
    test_dir = setup_test_project()
    
    print("Organizing project...")
    organizer = ProjectOrganizerService()
    pkg_path = organizer.organize_if_needed(test_dir)
    
    print(f"\nVerification - Operational Package generated at {pkg_path}")
    
    def print_tree(dir_path, prefix=""):
        contents = list(dir_path.iterdir())
        pointers = [getattr(Path, 'name', '├── ')] * (len(contents) - 1) + ['└── ']
        for pointer, path in zip(pointers, sorted(contents, key=lambda p: (p.is_file(), p.name))):
            print(prefix + pointer + path.name)
            if path.is_dir():
                extension = '    ' if pointer == '└── ' else '│   '
                print_tree(path, prefix=prefix+extension)

    print("\nDirectory Tree:")
    print_tree(pkg_path)
    
