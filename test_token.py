import re

files = [
    "M-final_Functional validation report_JIG.pdf",
    "Master Final Functional Validation.pdf",
    "M Final Validation.xlsx",
    "M-initial_Functional validation report_JIG.xlsx",
    "S-final_Functional validation report_JIG.pdf",
    "U-QC_Functional validation report_JIG.xlsx"
]

for f in files:
    stem = f.rsplit('.', 1)[0]
    norm = stem.lower().replace("-", " ").replace("_", " ")
    tokens = set(norm.split())
    
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
        print(f"{f} -> 4. Test Report/{fw_type}/{stage}")
    else:
        print(f"{f} -> NO MATCH")
