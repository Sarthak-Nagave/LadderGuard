from pathlib import Path

from services.project_organizer import ProjectOrganizerService


def run():
    base = Path(r"c:\Users\SM 464\Desktop\Operational Package Validator\test_unorg_project")
    if base.exists():
        import shutil
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    
    # Create Ladder
    l1 = base / "Ladder" / "StationA" / "Initial"
    l1.mkdir(parents=True)
    (l1 / "ct.ld").write_text("dummy ld")
    
    # Create Bin Files
    b1 = base / "Bin Files" / "StationA" / "Initial"
    b1.mkdir(parents=True)
    (b1 / "Test.bin").write_text("dummy bin")
    
    # Bad stuff inside Bin Files
    (b1 / "h1.ssx").write_text("should be ignored")
    (b1 / "ct.ld").write_text("should be ignored")
    (b1 / "bad.sdoc").write_text("should be ignored")
    
    bad_dir = b1 / "Backup" / "BeforeSave"
    bad_dir.mkdir(parents=True)
    (bad_dir / "Test2.bin").write_text("should be ignored")
    
    # Root PDFs
    (base / "M-Initial-report_of_test-sgn.pdf").write_text("pdf content")
    
    # Execute
    organizer = ProjectOrganizerService()
    target = organizer.organize_if_needed(base)
    print("Generated structure at:", target)
    
if __name__ == "__main__":
    run()
