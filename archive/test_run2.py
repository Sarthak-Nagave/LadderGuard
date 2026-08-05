from pathlib import Path

from services.project_organizer import ProjectOrganizerService


def run():
    base = Path(r"c:\Users\SM 464\Desktop\Operational Package Validator\test_unorg_project2")
    if base.exists():
        import shutil
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    
    # Create Ladder
    l1 = base / "Ladder" / "Master" / "Initial"
    l1.mkdir(parents=True)
    
    # Engineering folders that indicate this is a firmware folder
    (l1 / "Backup").mkdir()
    (l1 / "GRP").mkdir()
    (l1 / "POU").mkdir()
    
    # Some other firmware folder that has no engineering folders but has a file
    l2 = base / "Ladder" / "Slave" / "Final"
    l2.mkdir(parents=True)
    (l2 / "Test.sdoc").write_text("dummy")
    
    # UUT QC has both
    l3 = base / "Ladder" / "UUT" / "QC"
    l3.mkdir(parents=True)
    (l3 / "Test.bin").write_text("dummy")
    (l3 / "Backup").mkdir()
    
    # Create Bin Files
    b1 = base / "Bin Files" / "Master" / "Initial"
    b1.mkdir(parents=True)
    (b1 / "Boot.bin").write_text("dummy")
    (b1 / "Firmware.bin").write_text("dummy")
    
    # Execute
    organizer = ProjectOrganizerService()
    target = organizer.organize_if_needed(base)
    print("Generated structure at:", target)
    
if __name__ == "__main__":
    run()
