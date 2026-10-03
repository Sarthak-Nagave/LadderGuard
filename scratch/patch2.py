import re

path = r"c:\Users\SM 464\Desktop\Operational Package Validator\ProjectValidator\validators\document_validator.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

def repl(match):
    return '''    def _is_valid_printed_name_candidate(
        self,
        candidate: str,
        all_alias_tokens: set[str],
    ) -> bool:
        original = candidate
        candidate = self._sanitize_name_candidate(candidate)
        if not candidate:
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (empty after sanitize)")
            return False

        normalized = self._normalize_token(candidate)
        if not normalized:
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (empty normalized)")
            return False
            
        if normalized in all_alias_tokens:
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (in all_alias_tokens)")
            return False
            
        if any(token and token in normalized for token in all_alias_tokens):
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (contains alias token)")
            return False
            
        if "digitalsignature" in normalized:
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (contains digitalsignature)")
            return False

        blocked_tokens = {
            "prepared",
            "checked",
            "verified",
            "approved",
            "page",
            "filepath",
            "operationalflow",
            "automationinput",
            "testreport",
            "operatorsflow",
            "processrepresentative",
            "production",
            "qc",
            "hod",
        }
        if any(token in normalized for token in blocked_tokens):
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (blocked token)")
            return False

        if normalized in {"signature", "signed", "present", "missing", "na", "none", "pass", "fail"}:
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (exact blocked word)")
            return False
            
        if any(char.isdigit() for char in candidate):
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (contains digit)")
            return False

        if len(candidate) > 64:
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (too long)")
            return False

        if not re.fullmatch(r"[A-Za-z ./'\-]+", candidate):
            self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (invalid characters)")
            return False

        slash_parts = [p.strip() for p in candidate.split("/")]
        if len(slash_parts) > 1:
            for part in slash_parts:
                if len(part) < 2:
                    self.logger.warning(f"[DEBUG_NAME] '{original}' -> rejected (slash part too short)")
                    return False
        
        self.logger.warning(f"[DEBUG_NAME] '{original}' -> ACCEPTED")
        return True'''

new_content = re.sub(
    r'    def _is_valid_printed_name_candidate\([^)]+\)\s*->\s*bool:.*?return True',
    repl,
    content,
    flags=re.DOTALL
)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)
