import sys

file_path = r"c:\Users\SM 464\Desktop\Operational Package Validator\ProjectValidator\validators\document_validator.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def _is_valid_printed_name_candidate" in line:
        print(f"Found at line {i+1}")
        for j in range(i, i+30):
            if j < len(lines):
                print(lines[j].rstrip())
