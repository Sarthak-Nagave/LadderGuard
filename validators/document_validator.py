"""
validators.document_validator
=============================

Generic validator for signed engineering documents.

A single instance validates one configured document folder.

Example
-------
DocumentValidator(
    step=ValidationStep.OPERATIONAL_FLOW,
    folder_name="3. Operational Flow",
)

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from config import (
    DOCUMENT_SIGNING_SECTIONS,
    DOCUMENT_VALIDATOR_DEBUG_LOG,
    EXPECTED_SIGNED_DOCUMENTS,
    LOG_DIRECTORY,
    SIGNED_DOCUMENT_SUFFIX,
)
from core.base_validator import BaseValidator
from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStep
from models.signature_info import SignatureInfo
from services.file_search import FileSearchService
from services.signature_reader import PageSignatureSnapshot, PageTextBlock, PageWord, SignatureReaderService


class _SectionAnchor:
    """Resolved location of one section label on a page."""

    __slots__ = ("section_name", "x0", "y0", "x1", "y1", "x_center", "y_center")

    def __init__(
        self,
        section_name: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> None:
        self.section_name = section_name
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.x_center = (x0 + x1) / 2.0
        self.y_center = (y0 + y1) / 2.0

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


class DocumentValidator(BaseValidator):
    """
    Generic validator for a single signed document folder.
    """

    def __init__(
        self,
        step: ValidationStep,
        folder_name: str,
        file_search: FileSearchService,
        file_reader,  # retained for constructor compatibility
        signature_reader: SignatureReaderService,
    ) -> None:
        super().__init__(step)
        self._folder_name = folder_name
        self._file_search = file_search
        self._signature_reader = signature_reader

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def validate(
        self,
        context: ValidationContext,
    ) -> ValidationResult:
        self.logger.info(f"Validating '{self._folder_name}'.")
        self._write_debug_log(f"Starting validation for folder={self._folder_name}")

        folder = context.folders.get(self._folder_name)
        if folder is None:
            self._write_debug_log(f"Folder missing: {self._folder_name}")
            return self.skipped_result(
                reason=f"Folder '{self._folder_name}' is unavailable.",
            )

        self._write_debug_log(f"Folder exists: {folder}")

        if self.step == ValidationStep.TEST_REPORT:
            return self._validate_test_report_folder(
                context=context,
                folder=folder,
            )

        discovered_paths = [
            relative_path
            for relative_path, _ in context.discovered_paths
            if relative_path and "/" in relative_path
        ]

        if not discovered_paths:
            return self.fail_result(
                reason="No ladder-discovered stages were available for document validation.",
                checked_path=folder,
            )

        try:
            document = self._discover_document(folder)
        except RuntimeError as exc:
            self._write_debug_log(f"Discovery failed: {exc}")
            return self.fail_result(
                reason=str(exc),
                checked_path=folder,
            )

        context.add_document(self._folder_name, document)
        self.logger.info(f"Found signed document: {document.name}")
        self._write_debug_log(f"Signed document discovered: {document}")

        return self._validate_single_document(document, context)

    # ---------------------------------------------------------
    # Private Helpers
    # ---------------------------------------------------------

    def _validate_test_report_folder(
        self,
        context: ValidationContext,
        folder: Path,
    ) -> ValidationResult:
        """Validate Test Report folder using root-first then stage-based discovery."""
        root_documents = [
            document
            for document in folder.iterdir()
            if document.is_file()
            and document.suffix.casefold() == ".pdf"
            and SIGNED_DOCUMENT_SUFFIX.lower() in document.stem.lower()
        ]

        if root_documents:
            if len(root_documents) != 1:
                return self.fail_result(
                    reason="Expected exactly one signed PDF in the Test Report root.",
                    checked_path=folder,
                    details={"documents": [str(path) for path in root_documents]},
                )

            document = root_documents[0]
            context.add_document(self._folder_name, document)
            return self._validate_single_document(document, context)

        discovered_paths = [
            relative_path
            for relative_path, _ in context.discovered_paths
            if relative_path and "/" in relative_path
        ]

        if not discovered_paths:
            return self.fail_result(
                reason="No signed PDF found in the Test Report root and no ladder structure was discovered.",
                checked_path=folder,
            )

        expected_paths = sorted({relative_path for relative_path in discovered_paths})
        failures: list[str] = []
        discovered_documents: list[Path] = []
        section_payloads: list[dict] = []

        for relative_path in expected_paths:
            stage_directory = folder / relative_path
            if not stage_directory.exists():
                failures.append(f"Missing folder '{relative_path}'.")
                continue

            staged_documents = [
                document
                for document in self._file_search.recursive_files(stage_directory, ".pdf")
                if document.is_file()
                and SIGNED_DOCUMENT_SUFFIX.lower() in document.stem.lower()
            ]

            if len(staged_documents) == 0:
                failures.append(f"No signed PDF found in '{relative_path}'.")
                continue

            if len(staged_documents) != 1:
                failures.append(f"Expected exactly one signed PDF in '{relative_path}'.")
                continue

            document = staged_documents[0]
            context.add_document(self._folder_name, document)
            discovered_documents.append(document)

            result = self._validate_single_document(document, context)
            section_payloads.append(
                {
                    "path": str(document),
                    "status": result.status.name,
                    "reason": result.reason,
                    "details": result.details,
                }
            )
            if result.status.name == "FAIL":
                failures.append(f"{relative_path}: {result.reason}")

        if failures:
            return self.fail_result(
                reason="; ".join(failures),
                checked_path=folder,
                details={"failures": failures, "documents": section_payloads},
            )

        if len(discovered_documents) != len(expected_paths):
            return self.fail_result(
                reason="Structured Test Report validation did not discover the expected number of signed PDFs.",
                checked_path=folder,
                details={
                    "expected": len(expected_paths),
                    "found": len(discovered_documents),
                    "documents": section_payloads,
                },
            )

        return self.pass_result(
            reason="Structured Test Report validation completed successfully.",
            checked_path=folder,
            details={"documents": section_payloads},
        )

    def _validate_single_document(
        self,
        document: Path,
        context: ValidationContext,
    ) -> ValidationResult:
        """Validate one signed document using section-based page checks."""
        try:
            snapshots = self._signature_reader.read_page_snapshots(document)
        except Exception as exc:
            self._write_debug_log(f"Signature inspection failed: {exc}")
            self.logger.warning(
                f"Unable to inspect signatures in '{document.name}'; using discovered document path as the validation signal."
            )
            context.add_signature(self._folder_name, [])
            return self.pass_result(
                reason=f"{self._folder_name} validated successfully.",
                checked_path=document,
                details={"document": document.name, "signature_inspection": "skipped", "exception": str(exc)},
            )

        section_specs = self._section_specs_for_folder()
        if not section_specs:
            return self.fail_result(
                reason=f"No section rules configured for '{self._folder_name}'.",
                checked_path=document,
            )

        section_results: list[SignatureInfo] = []
        for snapshot in snapshots:
            page_results = self._validate_page_sections(
                snapshot=snapshot,
                section_specs=section_specs,
            )
            section_results.extend(page_results)

        summary_sections = self._summarize_section_results(section_specs, section_results)

        context.add_signature(self._folder_name, summary_sections)
        self._write_debug_log(
            f"Section results for {document.name}: {[section.to_dict() for section in section_results]}"
        )

        all_passed = all(section.is_valid for section in summary_sections)
        first_failure = next((section for section in summary_sections if not section.is_valid), None)

        details = {
            "document": document.name,
            "document_type": self._document_type_label(),
            "sections": [section.to_dict() for section in summary_sections],
        }

        if all_passed:
            self._write_debug_log("Final decision: PASS")
            self.logger.info(f"{self._folder_name} validated successfully.")
            return self.pass_result(
                reason="All required signatures found on every page.",
                checked_path=document,
                details=details,
            )

        combined_reason = (
            first_failure.reason
            if first_failure and first_failure.reason
            else f"{self._folder_name} validation failed."
        )

        self._write_debug_log("Final decision: FAIL")
        self.logger.warning(f"{self._folder_name} validation failed.")

        return self.fail_result(
            reason=combined_reason,
            checked_path=document,
            details=details,
        )

    def _validate_page_sections(
        self,
        snapshot: PageSignatureSnapshot,
        section_specs: list[dict[str, list[str] | str]],
    ) -> list[SignatureInfo]:
        require_printed_name = self._requires_printed_name()
        all_alias_tokens = {
            self._normalize_token(alias)
            for section in section_specs
            for alias in section["aliases"]
        }

        anchors: list[_SectionAnchor | None] = []
        for section in section_specs:
            section_name = str(section["section"])
            aliases = [str(alias) for alias in section["aliases"]]
            anchor = self._find_section_anchor(snapshot.words, snapshot.text_blocks, aliases)
            anchors.append(anchor)

        results: list[SignatureInfo] = []

        for index, section in enumerate(section_specs):
            section_name = str(section["section"])
            aliases = [str(alias) for alias in section["aliases"]]
            anchor = anchors[index]

            if anchor is None:
                debug_line = (
                    f"[SIG_TRACE] Role={section_name} Page={snapshot.page_number} KeywordRect=None "
                    f"DetectedName='' SignatureFound=False Source=none"
                )
                print(debug_line, flush=True)
                self._write_debug_log(debug_line)
                results.append(
                    SignatureInfo(
                        section_name=section_name,
                        page_number=snapshot.page_number,
                        section_found=False,
                        printed_name="",
                        printed_name_found=False,
                        digital_signature_found=False,
                        require_printed_name=require_printed_name,
                        reason=f"Page {snapshot.page_number}: {section_name} section missing.",
                    )
                )
                continue

            role_rect = self._build_role_region(
                anchor=anchor,
                anchors=anchors,
                page_width=snapshot.page_width,
                page_height=snapshot.page_height,
            )

            printed_name = self._extract_printed_name(
                snapshot=snapshot,
                role_rect=role_rect,
                anchor=anchor,
                aliases=aliases,
                all_alias_tokens=all_alias_tokens,
            )
            printed_name_found = bool(printed_name)

            signature_sources = self._detect_signature_sources(
                snapshot=snapshot,
                role_rect=role_rect,
                all_alias_tokens=all_alias_tokens,
            )
            digital_signature_found = bool(signature_sources)

            debug_line = (
                f"[SIG_TRACE] Role={section_name} Page={snapshot.page_number} "
                f"KeywordRect=({anchor.x0:.1f},{anchor.y0:.1f},{anchor.x1:.1f},{anchor.y1:.1f}) "
                f"DetectedName={printed_name!r} SignatureFound={digital_signature_found} "
                f"Source={','.join(signature_sources) if signature_sources else 'none'}"
            )
            print(debug_line, flush=True)
            self._write_debug_log(debug_line)

            reasons: list[str] = []
            if require_printed_name and not printed_name_found:
                reasons.append(f"Page {snapshot.page_number}: {section_name} printed name missing.")
            if not digital_signature_found:
                reasons.append(f"Page {snapshot.page_number}: {section_name} digital signature missing.")

            results.append(
                SignatureInfo(
                    section_name=section_name,
                    page_number=snapshot.page_number,
                    section_found=True,
                    printed_name=printed_name,
                    printed_name_found=printed_name_found,
                    digital_signature_found=digital_signature_found,
                    require_printed_name=require_printed_name,
                    reason=" ".join(reasons) if reasons else None,
                )
            )

        return results

    def _build_role_region(
        self,
        anchor: _SectionAnchor,
        anchors: list[_SectionAnchor | None],
        page_width: float,
        page_height: float,
    ) -> tuple[float, float, float, float]:
        same_row = [candidate for candidate in anchors if candidate is not None and abs(candidate.y_center - anchor.y_center) <= 28.0]
        same_row.sort(key=lambda item: item.x_center)

        left = 0.0
        right = page_width
        for idx, candidate in enumerate(same_row):
            if candidate is not anchor:
                continue
            if idx > 0:
                left = (same_row[idx - 1].x_center + candidate.x_center) / 2.0
            if idx < len(same_row) - 1:
                right = (candidate.x_center + same_row[idx + 1].x_center) / 2.0
            break

        top = max(0.0, anchor.y0 - 6.0)
        bottom = min(page_height, anchor.y1 + 110.0)

        below = [candidate for candidate in anchors if candidate is not None and candidate.y0 > anchor.y1 + 2.0]
        if below:
            next_row_top = min(candidate.y0 for candidate in below)
            bottom = min(bottom, max(top + 24.0, next_row_top - 3.0))

        if right <= left:
            left = max(0.0, anchor.x0 - 20.0)
            right = min(page_width, anchor.x1 + 180.0)

        return (left, top, right, bottom)

    def _detect_signature_sources(
        self,
        snapshot: PageSignatureSnapshot,
        role_rect: tuple[float, float, float, float],
        all_alias_tokens: set[str],
    ) -> list[str]:
        sources: list[str] = []

        if any(self._rect_intersects(role_rect, rect) for rect in snapshot.signed_signature_rects):
            sources.append("annotation")

        if any(self._rect_intersects(role_rect, rect) for rect in snapshot.image_rects):
            sources.append("image")

        for rect in snapshot.vector_rects:
            if not self._rect_intersects(role_rect, rect):
                continue
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            # Ignore thin table grid lines while accepting drawn signatures/strokes.
            if width < 1.2 or height < 1.2:
                continue
            if width > 220.0 or height > 120.0:
                continue
            if (width * height) < 8.0:
                continue
            if width / max(height, 1.0) > 20.0:
                continue
            sources.append("vector")
            break

        ocr_region = self._expand_rect(role_rect, margin_x=12.0, margin_y=8.0)
        printed_tokens = {
            self._normalize_token(word.text)
            for word in snapshot.words
            if self._rect_intersects(ocr_region, (word.x0, word.y0, word.x1, word.y1))
        }

        for block in snapshot.ocr_blocks:
            if not self._rect_intersects(ocr_region, (block.x0, block.y0, block.x1, block.y1)):
                continue
            if self._looks_signature_like(block.text, all_alias_tokens, printed_tokens):
                sources.append("OCR")
                break

        # Fallback: some signed PDFs expose signature text in extractable text blocks
        # without yielding annotation/image/vector geometry in the same role region.
        if "OCR" not in sources and self.step != ValidationStep.LADDER_FLOW:
            for block in snapshot.text_blocks:
                if not self._rect_intersects(ocr_region, (block.x0, block.y0, block.x1, block.y1)):
                    continue
                if self._contains_signature_phrase(block.text):
                    sources.append("OCR")
                    break

        return sources

    def _section_specs_for_folder(self) -> list[dict[str, list[str] | str]]:
        raw = DOCUMENT_SIGNING_SECTIONS.get(self._folder_name, [])
        specs: list[dict[str, list[str] | str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            section = item.get("section")
            aliases = item.get("aliases")
            if not isinstance(section, str) or not section.strip():
                continue
            if not isinstance(aliases, list):
                continue
            filtered_aliases = [alias.strip() for alias in aliases if isinstance(alias, str) and alias.strip()]
            if not filtered_aliases:
                continue
            specs.append({"section": section.strip(), "aliases": filtered_aliases})
        return specs

    def _document_type_label(self) -> str:
        if self.step == ValidationStep.LADDER_FLOW:
            return "Ladder Flow"
        if self.step == ValidationStep.OPERATIONAL_FLOW:
            return "Operational Flow"
        if self.step == ValidationStep.AUTOMATION_INPUT:
            return "Automation Input Document"
        if self.step == ValidationStep.TEST_REPORT:
            return "Test Report"
        return str(self.step)

    def _find_section_anchor(
        self,
        words: tuple[PageWord, ...],
        text_blocks: tuple[PageTextBlock, ...],
        aliases: list[str],
    ) -> _SectionAnchor | None:
        candidates: list[_SectionAnchor] = []

        for alias in aliases:
            rect = self._find_alias_rect_in_words(words, alias)
            if rect is not None:
                candidates.append(
                    _SectionAnchor(
                        section_name=aliases[0],
                        x0=rect[0],
                        y0=rect[1],
                        x1=rect[2],
                        y1=rect[3],
                    )
                )

        if candidates:
            candidates.sort(key=lambda item: (item.y0, item.x0))
            return candidates[0]

        # Fallback to text blocks if words are not available / OCR PDFs.
        alias_tokens = [self._normalize_token(alias) for alias in aliases]
        for block in sorted(text_blocks, key=lambda item: (item.y0, item.x0)):
            normalized = self._normalize_token(block.text)
            if not normalized:
                continue
            if any(token and token in normalized for token in alias_tokens):
                return _SectionAnchor(
                    section_name=aliases[0],
                    x0=block.x0,
                    y0=block.y0,
                    x1=block.x1,
                    y1=block.y1,
                )
        return None

    def _find_alias_rect_in_words(
        self,
        words: tuple[PageWord, ...],
        alias: str,
    ) -> tuple[float, float, float, float] | None:
        alias_tokens = [token for token in (self._normalize_token(part) for part in re.findall(r"[A-Za-z0-9]+", alias)) if token]
        if not alias_tokens:
            return None

        lines = self._group_words_by_line(words)
        for line in lines:
            normalized_words: list[tuple[int, str]] = []
            for idx, word in enumerate(line):
                sub_tokens = [
                    self._normalize_token(part)
                    for part in re.findall(r"[A-Za-z0-9]+", word.text)
                ]
                for token in sub_tokens:
                    if token:
                        normalized_words.append((idx, token))

            tokens = [token for _, token in normalized_words]
            for start in range(0, len(tokens) - len(alias_tokens) + 1):
                if tokens[start:start + len(alias_tokens)] != alias_tokens:
                    continue

                first_word_index = normalized_words[start][0]
                last_word_index = normalized_words[start + len(alias_tokens) - 1][0]
                word_slice = line[first_word_index:last_word_index + 1]
                x0 = min(word.x0 for word in word_slice)
                y0 = min(word.y0 for word in word_slice)
                x1 = max(word.x1 for word in word_slice)
                y1 = max(word.y1 for word in word_slice)
                return (x0, y0, x1, y1)

        return None

    def _summarize_section_results(
        self,
        section_specs: list[dict[str, list[str] | str]],
        section_results: list[SignatureInfo],
    ) -> list[SignatureInfo]:
        """Collapse per-page section outcomes to one row per section using role-level evidence."""
        summary: list[SignatureInfo] = []
        require_printed_name = self._requires_printed_name()

        for section in section_specs:
            section_name = str(section["section"])
            rows = [row for row in section_results if row.section_name == section_name]
            found_rows = [row for row in rows if row.section_found]

            if not found_rows:
                summary.append(
                    SignatureInfo(
                        section_name=section_name,
                        page_number=1,
                        section_found=False,
                        printed_name="",
                        printed_name_found=False,
                        digital_signature_found=False,
                        require_printed_name=require_printed_name,
                        reason=f"Page 1: {section_name} section missing.",
                    )
                )
                continue

            signature_rows = [row for row in found_rows if row.digital_signature_found]
            name_rows = [row for row in found_rows if row.printed_name_found]
            any_signature_found = bool(signature_rows)
            any_name_found = bool(name_rows)

            representative = signature_rows[0] if signature_rows else found_rows[0]
            first_printed_name = next((row.printed_name for row in found_rows if row.printed_name), "")

            reason_parts: list[str] = []
            if not any_signature_found:
                reason_parts.append(f"{section_name} digital signature missing.")
            if require_printed_name and not any_name_found:
                reason_parts.append(f"{section_name} printed name missing.")

            summary.append(
                SignatureInfo(
                    section_name=section_name,
                    page_number=representative.page_number,
                    section_found=True,
                    printed_name=first_printed_name,
                    printed_name_found=any_name_found,
                    digital_signature_found=any_signature_found,
                    require_printed_name=require_printed_name,
                    reason=" ".join(reason_parts) if reason_parts else None,
                )
            )

        return summary

    def _requires_printed_name(self) -> bool:
        return self.step != ValidationStep.LADDER_FLOW

    def _extract_printed_name(
        self,
        snapshot: PageSignatureSnapshot,
        role_rect: tuple[float, float, float, float],
        anchor: _SectionAnchor,
        aliases: list[str],
        all_alias_tokens: set[str],
    ) -> str:
        role_label = aliases[0] if aliases else anchor.section_name
        nearby_blocks = self._nearby_text_blocks(snapshot.text_blocks, anchor)

        keyword_line = (
            f"[SIG_NAME_TRACE] Role={role_label} Keyword={aliases!r} "
            f"KeywordRect=({anchor.x0:.1f},{anchor.y0:.1f},{anchor.x1:.1f},{anchor.y1:.1f})"
        )
        print(keyword_line, flush=True)
        self._write_debug_log(keyword_line)

        for index, entry in enumerate(nearby_blocks[:10], start=1):
            candidate_line = (
                f"[SIG_NAME_TRACE] Role={role_label} CandidateBlock#{index} "
                f"Dist={entry['distance']:.2f} Dx={entry['dx']:.2f} Dy={entry['dy']:.2f} "
                f"Text={entry['text']!r}"
            )
            print(candidate_line, flush=True)
            self._write_debug_log(candidate_line)

        chosen_name = ""
        chosen_reason = ""

        # Priority 1: same line after colon, e.g. "Prepared By: Akshay B."
        chosen_name, chosen_reason = self._pick_same_line_colon_name(
            aliases=aliases,
            nearby_blocks=nearby_blocks,
            all_alias_tokens=all_alias_tokens,
        )

        # Priority 2: first valid line immediately below the keyword.
        if not chosen_name:
            chosen_name, chosen_reason = self._pick_below_keyword_name(
                aliases=aliases,
                nearby_blocks=nearby_blocks,
                anchor=anchor,
                all_alias_tokens=all_alias_tokens,
            )

        # Priority 3: OCR fallback only inside role rectangle.
        if not chosen_name:
            chosen_name, chosen_reason = self._pick_ocr_name(
                aliases=aliases,
                role_rect=role_rect,
                ocr_blocks=snapshot.ocr_blocks,
                anchor=anchor,
                all_alias_tokens=all_alias_tokens,
            )

        decision_line = (
            f"[SIG_NAME_TRACE] Role={role_label} ChosenName={chosen_name!r} Reason={chosen_reason or 'none'}"
        )
        print(decision_line, flush=True)
        self._write_debug_log(decision_line)

        return chosen_name

    def _nearby_text_blocks(
        self,
        text_blocks: tuple[PageTextBlock, ...],
        anchor: _SectionAnchor,
    ) -> list[dict[str, object]]:
        anchor_cx = anchor.x_center
        anchor_cy = anchor.y_center
        entries: list[dict[str, object]] = []

        for block in text_blocks:
            text = " ".join(part.strip() for part in re.split(r"[\r\n]+", block.text) if part.strip())
            if not text:
                continue

            block_cx = (block.x0 + block.x1) / 2.0
            block_cy = (block.y0 + block.y1) / 2.0
            dx = block_cx - anchor_cx
            dy = block_cy - anchor_cy
            distance = (dx * dx + dy * dy) ** 0.5

            # Keep only physically nearby text around the keyword anchor.
            if abs(dx) > 320.0:
                continue
            if abs(dy) > 170.0:
                continue

            entries.append(
                {
                    "text": text,
                    "x0": block.x0,
                    "y0": block.y0,
                    "x1": block.x1,
                    "y1": block.y1,
                    "dx": dx,
                    "dy": dy,
                    "distance": distance,
                }
            )

        entries.sort(
            key=lambda item: (
                float(item["distance"]),
                abs(float(item["dy"])),
                abs(float(item["dx"])),
            )
        )
        return entries

    def _pick_same_line_colon_name(
        self,
        aliases: list[str],
        nearby_blocks: list[dict[str, object]],
        all_alias_tokens: set[str],
    ) -> tuple[str, str]:
        stop_pattern = re.compile(
            r"(?i)\b("
            r"prepared\s*by|checked\s*by|verified\s*by|approved\s*by|"
            r"process\s*representative|production\s*/?\s*qc|hod|"
            r"page\s*\d+|file\s*path"
            r")\b|[A-Za-z]\s*:\\"
        )
        for entry in nearby_blocks:
            text = str(entry["text"])
            for line in re.split(r"[\r\n]+", text):
                current = line.strip()
                if not current:
                    continue
                for alias in aliases:
                    alias_pattern = self._alias_pattern(alias)
                    match = re.search(rf"(?i)\b{alias_pattern}\b\s*[:\-]\s*(.+)$", current)
                    if not match:
                        continue
                    tail = match.group(1)
                    stop_match = stop_pattern.search(tail)
                    if stop_match is not None:
                        tail = tail[: stop_match.start()]
                    candidate = self._sanitize_name_candidate(tail)
                    if self._is_valid_printed_name_candidate(candidate, all_alias_tokens):
                        return candidate, "same-line-after-colon"
        return "", ""

    def _pick_below_keyword_name(
        self,
        aliases: list[str],
        nearby_blocks: list[dict[str, object]],
        anchor: _SectionAnchor,
        all_alias_tokens: set[str],
    ) -> tuple[str, str]:
        ranked = sorted(
            nearby_blocks,
            key=lambda item: (
                0 if float(item["y0"]) >= anchor.y0 else 1,
                abs(float(item["y0"]) - anchor.y1),
                abs(float(item["dx"])),
                float(item["distance"]),
            ),
        )

        for entry in ranked:
            lines = [line.strip() for line in re.split(r"[\r\n]+", str(entry["text"])) if line.strip()]
            if not lines:
                continue

            for index, line in enumerate(lines):
                matched_alias = self._line_matches_any_alias(line, aliases)
                if not matched_alias:
                    continue

                # Case: "Approved By" in one line and name on the next line.
                if index + 1 < len(lines):
                    candidate = self._sanitize_name_candidate(lines[index + 1])
                    if self._is_valid_printed_name_candidate(candidate, all_alias_tokens):
                        return candidate, "next-line-below-keyword"

            # Case: nearest independent block below keyword containing only the name.
            if float(entry["y0"]) < anchor.y0 - 2.0:
                continue
            for line in lines:
                if self._line_matches_any_alias(line, aliases):
                    continue
                candidate = self._sanitize_name_candidate(line)
                if self._is_valid_printed_name_candidate(candidate, all_alias_tokens):
                    return candidate, "first-nearby-line-below-keyword"

        return "", ""

    def _pick_ocr_name(
        self,
        aliases: list[str],
        role_rect: tuple[float, float, float, float],
        ocr_blocks,
        anchor: _SectionAnchor,
        all_alias_tokens: set[str],
    ) -> tuple[str, str]:
        entries: list[tuple[float, str]] = []
        for block in ocr_blocks:
            rect = (block.x0, block.y0, block.x1, block.y1)
            if not self._rect_intersects(role_rect, rect):
                continue
            cx = (block.x0 + block.x1) / 2.0
            cy = (block.y0 + block.y1) / 2.0
            dx = cx - anchor.x_center
            dy = cy - anchor.y_center
            distance = (dx * dx + dy * dy) ** 0.5
            entries.append((distance, str(block.text)))

        entries.sort(key=lambda item: item[0])
        for _distance, text in entries:
            for line in re.split(r"[\r\n]+", text):
                candidate = self._sanitize_name_candidate(line)
                if self._line_matches_any_alias(candidate, aliases):
                    continue
                if self._is_valid_printed_name_candidate(candidate, all_alias_tokens):
                    return candidate, "ocr-fallback-in-role-rectangle"

        return "", ""

    def _line_matches_any_alias(self, line: str, aliases: list[str]) -> bool:
        if not line.strip():
            return False
        for alias in aliases:
            alias_pattern = self._alias_pattern(alias)
            if re.search(rf"(?i)\b{alias_pattern}\b", line):
                return True
        return False

    def _sanitize_name_candidate(self, candidate: str) -> str:
        lines = [" ".join(part.split()) for part in re.split(r"[\r\n]+", candidate) if part.strip()]
        if not lines:
            return ""

        if len(lines) > 1:
            dedup_lines: list[str] = []
            seen_norm: set[str] = set()
            for line in lines:
                norm = self._normalize_token(line)
                if not norm or norm in seen_norm:
                    continue
                seen_norm.add(norm)
                dedup_lines.append(line)
            lines = dedup_lines or [lines[0]]

        merged = " ".join(lines)
        merged = re.sub(r"\s*\/\s*", "/", merged)
        merged = re.sub(r"\s+", " ", merged).strip(" .\t")

        # Collapse exact repeated phrase patterns.
        words = merged.split()
        if len(words) >= 2 and len(words) % 2 == 0:
            half = len(words) // 2
            left = [self._normalize_token(word) for word in words[:half]]
            right = [self._normalize_token(word) for word in words[half:]]
            if left == right:
                merged = " ".join(words[:half])

        # Trim tails where a second name restarts from the same first token,
        # e.g. "Nitin K Nitin Kale" -> "Nitin K".
        words = merged.split()
        if len(words) >= 3:
            first_norm = self._normalize_token(words[0])
            for index in range(2, len(words)):
                if self._normalize_token(words[index]) == first_norm:
                    merged = " ".join(words[:index])
                    break

        # Deduplicate slash-separated names while preserving order.
        if "/" in merged:
            parts = [part.strip() for part in merged.split("/") if part.strip()]
            unique_parts: list[str] = []
            seen_parts: set[str] = set()
            for part in parts:
                key = self._normalize_token(part)
                if not key or key in seen_parts:
                    continue
                seen_parts.add(key)
                unique_parts.append(part)
            merged = "/".join(unique_parts)

        return merged

    def _extract_name_from_inline_alias(
        self,
        text: str,
        aliases: list[str],
        all_alias_tokens: set[str],
    ) -> str:
        for alias in aliases:
            alias_pattern = self._alias_pattern(alias)
            for pattern in (
                re.compile(rf"(?i)\b{alias_pattern}\b\s*[:\-]\s*(.+)$"),
                re.compile(rf"(?i)\b{alias_pattern}\b\s+(.+)$"),
            ):
                match = pattern.search(text)
                if not match:
                    continue
                candidate = match.group(1).strip(" :-\t")
                if self._is_valid_printed_name_candidate(candidate, all_alias_tokens):
                    return candidate
        return ""

    @staticmethod
    def _group_words_by_line(words: tuple[PageWord, ...]) -> list[list[PageWord]]:
        ordered = sorted(words, key=lambda word: (word.y0, word.x0))
        lines: list[list[PageWord]] = []
        for word in ordered:
            if not lines:
                lines.append([word])
                continue
            last_line = lines[-1]
            avg_y = sum(item.y0 for item in last_line) / len(last_line)
            if abs(word.y0 - avg_y) <= 3.2:
                last_line.append(word)
            else:
                lines.append([word])

        for line in lines:
            line.sort(key=lambda token: token.x0)
        return lines

    @staticmethod
    def _rect_intersects(
        a: tuple[float, float, float, float],
        b: tuple[float, float, float, float],
    ) -> bool:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        return ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0

    @staticmethod
    def _expand_rect(
        rect: tuple[float, float, float, float],
        margin_x: float,
        margin_y: float,
    ) -> tuple[float, float, float, float]:
        x0, y0, x1, y1 = rect
        return (x0 - margin_x, y0 - margin_y, x1 + margin_x, y1 + margin_y)

    def _discover_document(
        self,
        folder: Path,
    ) -> Path:
        """Discover the signed document inside the configured folder."""
        documents = self._file_search.recursive_files(folder, ".pdf")
        signed_documents = [
            document
            for document in documents
            if document.is_file()
            and SIGNED_DOCUMENT_SUFFIX.lower() in document.stem.lower()
        ]

        if len(signed_documents) == 0:
            raise RuntimeError(f"No signed document found in '{folder.name}'.")

        if len(signed_documents) != EXPECTED_SIGNED_DOCUMENTS:
            raise RuntimeError(
                f"Expected {EXPECTED_SIGNED_DOCUMENTS} signed "
                f"document but found {len(signed_documents)}."
            )

        return signed_documents[0]

    @staticmethod
    def _normalize_token(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.casefold())

    @staticmethod
    def _alias_pattern(alias: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9]+", alias)
        if not tokens:
            return re.escape(alias)
        return r"\s*".join(re.escape(token) for token in tokens)

    def _is_valid_printed_name_candidate(
        self,
        candidate: str,
        all_alias_tokens: set[str],
    ) -> bool:
        candidate = self._sanitize_name_candidate(candidate)
        if not candidate:
            return False

        normalized = self._normalize_token(candidate)
        if not normalized:
            return False
        if normalized in all_alias_tokens:
            return False
        if any(token and token in normalized for token in all_alias_tokens):
            return False
        if "digitalsignature" in normalized:
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
            return False

        if normalized in {"signature", "signed", "present", "missing", "na", "none", "pass", "fail"}:
            return False
        if any(char.isdigit() for char in candidate):
            return False

        if len(candidate) > 64:
            return False

        if not re.fullmatch(r"[A-Za-z ./'\-]+", candidate):
            return False

        lowered = candidate.casefold()
        if any(
            token in lowered
            for token in (
                "digitally",
                "signed",
                "email",
                "cn=",
                "ou=",
                "o=",
                "c=",
                "http",
                "www",
                "@",
                "\\",
                "pvt",
                "ltd",
                "file",
                "path",
            )
        ):
            return False
        if "," in candidate or ";" in candidate:
            return False

        slash_parts = [part.strip() for part in candidate.split("/") if part.strip()]
        if not slash_parts:
            return False

        for part in slash_parts:
            words = re.findall(r"[A-Za-z]+\.?", part)
            if len(words) < 2 or len(words) > 4:
                return False
            if all(len(word.rstrip(".")) > 2 for word in words[1:]):
                # Require at least one short token (initial/surname-short) after first name.
                return False

        return True

    @staticmethod
    def _contains_signature_phrase(text: str) -> bool:
        lowered = text.casefold()
        return (
            "digitally signed" in lowered
            or "signed by" in lowered
            or "signature" in lowered
        )

    def _looks_signature_like(
        self,
        text: str,
        all_alias_tokens: set[str],
        printed_tokens: Iterable[str],
    ) -> bool:
        candidate = text.strip()
        if not candidate:
            return False

        normalized = self._normalize_token(candidate)
        if not normalized:
            return False
        if normalized in all_alias_tokens:
            return False
        if any(token and token in normalized for token in all_alias_tokens):
            return False
        if normalized in set(printed_tokens):
            return False
        if normalized in {"digitalsignature", "preparedby", "checkedby", "verifiedby", "approvedby", "productionqc"}:
            return False

        letters = [char for char in candidate if char.isalpha()]
        if len(letters) < 3:
            return False
        if len(candidate) > 28:
            return False
        return True

    def _write_debug_log(self, message: str) -> None:
        """Append a line to the validator debug log for the real package run."""
        LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIRECTORY / DOCUMENT_VALIDATOR_DEBUG_LOG
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
