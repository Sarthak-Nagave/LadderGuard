import re

path = r"c:\Users\SM 464\Desktop\Operational Package Validator\ProjectValidator\validators\document_validator.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'def _is_valid_printed_name_candidate(self, text: str, role_tokens: set[str]) -> bool:',
    'def _is_valid_printed_name_candidate(self, text: str, role_tokens: set[str]) -> bool:\n        original_text = text'
)

# Replace all return False with logic to log
content = re.sub(
    r'(return False)',
    r'self.logger.warning(f"[DEBUG_NAME] Candidate=\'{original_text}\' Result=False"); \1',
    content
)

# And return True
content = re.sub(
    r'(return True)',
    r'self.logger.warning(f"[DEBUG_NAME] Candidate=\'{original_text}\' Result=True"); \1',
    content
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
