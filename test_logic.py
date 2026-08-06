import re
from pathlib import Path

files = [
    'M-Initial-Test Report.pdf',
    'M-final-report_of_test-sgn.pdf',
    'S-final-report_of_test.xlsx',
    'U-QC-report_of_test.xlsx',
    'M_Initial_test_report.pdf'
]

test_report_root = Path("Test Report")

for file_name in files:
    file_path = Path(file_name)
    tokens = re.split(r'[-_]', file_path.stem)
    if len(tokens) >= 2:
        prefix = tokens[0].lower()
        stage_token = tokens[1]
        
        fw_type = None
        if prefix == "m":
            fw_type = "Master"
        elif prefix == "s":
            fw_type = "Slave"
        elif prefix == "u":
            fw_type = "UUT"
            
        if fw_type:
            stage_name = stage_token.capitalize() if stage_token.islower() else stage_token
            dest_folder = test_report_root / fw_type / stage_name
            print(f"{file_name} -> {dest_folder}")
