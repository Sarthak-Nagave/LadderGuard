import sys

with open(r'c:\Users\SM 464\Desktop\Operational Package Validator\ProjectValidator\scratch\val_out.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_test_report = False
for i, l in enumerate(lines):
    if 'S-final_Functional validation report_JIG-sgn.pdf' in l:
        in_test_report = True
    if in_test_report and 'U-QC_Functional validation report_JIG-sgn.pdf' in l:
        in_test_report = False
        break
    if in_test_report and '[SIG' in l:
        print(l.strip())
