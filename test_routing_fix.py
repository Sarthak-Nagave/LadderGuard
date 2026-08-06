import re
from pathlib import Path
import shutil

class FakeLogger:
    def info(self, msg): print("INFO:", msg)
    def warning(self, msg): print("WARNING:", msg)
    def error(self, msg): print("ERROR:", msg)

logger = FakeLogger()

def test_routing(files):
    for f in files:
        file_path = Path(f)
        filename_lower = file_path.name.lower()
        normalized_filename = filename_lower.replace("-", " ").replace("_", " ")
        
        if "test report" in normalized_filename or "report of test" in normalized_filename or "validation" in normalized_filename:
            # We don't include extension in tokens for checking exact match
            stem_norm = file_path.stem.lower().replace("-", " ").replace("_", " ")
            tokens = set(stem_norm.split())
            
            fw_type = None
            if "master" in tokens or "m" in tokens:
                fw_type = "Master"
            elif "slave" in tokens or "s" in tokens:
                fw_type = "Slave"
            elif "uut" in tokens or "u" in tokens:
                fw_type = "UUT"
                
            stage = None
            if "initial" in tokens:
                stage = "Initial"
            elif "final" in tokens:
                stage = "Final"
            elif "qc" in tokens:
                stage = "QC"
                
            if fw_type and stage:
                dest_folder = Path("4. Test Report") / fw_type / stage
                logger.info(f"Copied test report {file_path.name} to {dest_folder}")
                continue
            
            logger.warning(f"File {file_path.name} could not be mapped dynamically. Leaving at root.")
            continue

test_routing([
    "M-final_Functional validation report_JIG.pdf",
    "Master Final Functional Validation.pdf",
    "M Final Validation.xlsx",
    "M-initial_Functional validation report_JIG.xlsx",
    "S-final_Functional validation report_JIG.pdf",
    "U-QC_Functional validation report_JIG.xlsx"
])
