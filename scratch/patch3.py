import re

path = r"c:\Users\SM 464\Desktop\Operational Package Validator\ProjectValidator\validators\document_validator.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# I will find the start of _is_valid_printed_name_candidate and the start of the next method _find_alias_rect_in_words
start_idx = content.find("def _is_valid_printed_name_candidate")
end_idx = content.find("def _find_alias_rect_in_words", start_idx)

if start_idx != -1 and end_idx != -1:
    new_method = """def _is_valid_printed_name_candidate(
        self,
        candidate: str,
        all_alias_tokens: set[str],
    ) -> bool:
        original = candidate
        candidate = self._sanitize_name_candidate(candidate)
        if not candidate:
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (empty after sanitize)")
            return False

        normalized = self._normalize_token(candidate)
        if not normalized:
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (empty normalized)")
            return False
            
        if normalized in all_alias_tokens:
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (in all_alias_tokens)")
            return False
            
        if any(token and token in normalized for token in all_alias_tokens):
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (contains alias token)")
            return False
            
        if "digitalsignature" in normalized:
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (contains digitalsignature)")
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
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (blocked token)")
            return False

        if normalized in {"signature", "signed", "present", "missing", "na", "none", "pass", "fail"}:
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (exact blocked word)")
            return False
            
        if any(char.isdigit() for char in candidate):
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (contains digit)")
            return False

        if len(candidate) > 64:
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (too long)")
            return False

        if not re.fullmatch(r"[A-Za-z ./'\-]+", candidate):
            self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (invalid characters)")
            return False

        slash_parts = [p.strip() for p in candidate.split("/")]
        if len(slash_parts) > 1:
            for part in slash_parts:
                if len(part) < 2:
                    self.logger.debug(f"[DEBUG_NAME] '{original}' -> rejected (slash part too short)")
                    return False
        
        self.logger.debug(f"[DEBUG_NAME] '{original}' -> ACCEPTED")
        return True

    """
    
    new_content = content[:start_idx] + new_method + content[end_idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Patched!")
else:
    print("Could not find bounds")
