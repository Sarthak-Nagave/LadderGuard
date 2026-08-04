"""
reports.report_model
===================

Convert ValidationSummary into UI-friendly report data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.validation_step import ValidationStatus, ValidationStep
from core.validation_summary import ValidationSummary


@dataclass(slots=True)
class ReportDetailRow:
    """A single label/value row within a details card."""

    label: str
    value: str


@dataclass(slots=True)
class ReportDetailCard:
    """A card-like block used to mirror the HTML report details."""

    title: str | None = None
    rows: list[ReportDetailRow] = field(default_factory=list)
    children: list["ReportDetailCard"] = field(default_factory=list)


@dataclass(slots=True)
class ReportSection:
    """Represents one validation row in the report."""

    title: str
    status: ValidationStatus
    reason: str
    summary: str = ""
    details: list[ReportDetailCard] = field(default_factory=list)


@dataclass(slots=True)
class ReportDataModel:
    """Convert validation summary data into a structure used by the UI and PDF exporter."""

    project_name: str
    project_path: str
    validation_date: str
    validation_time: str
    duration_seconds: float
    overall_status: ValidationStatus
    total_checks: int
    passed: int
    failed: int
    warnings: int
    sections: list[ReportSection] = field(default_factory=list)

    @classmethod
    def from_summary(cls, summary: ValidationSummary) -> "ReportDataModel":
        sections: list[ReportSection] = []
        for result in summary.results:
            sections.append(cls._build_section(result))

        return cls(
            project_name=summary.project_path.name if summary.project_path.name else "Project",
            project_path=summary.project_path.as_posix(),
            validation_date=summary.finished_at.strftime("%Y-%m-%d"),
            validation_time=summary.finished_at.strftime("%H:%M:%S"),
            duration_seconds=summary.duration_seconds,
            overall_status=summary.overall_status,
            total_checks=summary.total_steps,
            passed=summary.passed,
            failed=summary.failed,
            warnings=summary.warnings,
            sections=sections,
        )

    @staticmethod
    def _build_section(result: Any) -> ReportSection:
        detail_cards = ReportDataModel._build_detail_cards(result.step, result.details)
        if not detail_cards:
            detail_cards.append(ReportDetailCard(rows=[ReportDetailRow("Result", result.reason)]))

        summary = "Validation completed."
        if result.status == ValidationStatus.FAIL:
            summary = "Immediate action is required."
        elif result.status == ValidationStatus.WARNING:
            summary = "Review recommended."
        else:
            summary = "Validation passed."

        return ReportSection(
            title=str(result.step),
            status=result.status,
            reason=result.reason,
            summary=summary,
            details=detail_cards,
        )

    @staticmethod
    def _build_detail_cards(step: ValidationStep | None, details: Any) -> list[ReportDetailCard]:
        if details is None:
            return []
        if isinstance(details, dict):
            return ReportDataModel._render_dict_details(step, details)
        if isinstance(details, list):
            return ReportDataModel._render_list_details(step, details)
        return [ReportDetailCard(rows=[ReportDetailRow("", str(details))])]

    @classmethod
    def _render_dict_details(cls, step: ValidationStep | None, details: dict[str, Any]) -> list[ReportDetailCard]:
        if step == ValidationStep.FOLDER_STRUCTURE:
            return cls._render_folder_structure_details(details)
        if step in {ValidationStep.LADDER_FILES, ValidationStep.BIN_FILES}:
            return cls._render_stage_file_details(step, details)
        if step in {ValidationStep.OPERATIONAL_FLOW, ValidationStep.TEST_REPORT, ValidationStep.AUTOMATION_INPUT, ValidationStep.LADDER_FLOW}:
            return cls._render_signed_document_details(step, details)

        if "signers" in details and isinstance(details["signers"], list):
            return cls._render_signed_document_details(step, details)
        if "document" in details or "documents" in details:
            return cls._render_signed_document_details(step, details)

        rows: list[ReportDetailRow] = []
        for key, value in details.items():
            if isinstance(value, (dict, list)):
                continue
            rows.append(ReportDetailRow(cls._friendly_label(key), cls._friendly_value(value)))
        if not rows:
            return []
        return [ReportDetailCard(rows=rows)]

    @classmethod
    def _render_list_details(cls, step: ValidationStep | None, details: list[Any]) -> list[ReportDetailCard]:
        cards: list[ReportDetailCard] = []
        for item in details:
            if isinstance(item, dict):
                cards.extend(cls._render_dict_details(step, item))
            else:
                cards.append(ReportDetailCard(rows=[ReportDetailRow("", str(item))]))
        return cards

    @classmethod
    def _render_folder_structure_details(cls, details: dict[str, Any]) -> list[ReportDetailCard]:
        rows: list[ReportDetailRow] = []
        validated = details.get("validated")
        if validated is not None:
            rows.append(ReportDetailRow("Validated Folders", str(validated)))
        missing = details.get("missing_folders")
        if isinstance(missing, list) and missing:
            rows.append(ReportDetailRow("Missing Folders", ", ".join(str(item) for item in missing)))
        if not rows:
            return []
        return [ReportDetailCard(rows=rows)]

    @classmethod
    def _render_stage_file_details(cls, step: ValidationStep | None, details: dict[str, Any]) -> list[ReportDetailCard]:
        cards: list[ReportDetailCard] = []
        if step == ValidationStep.LADDER_FILES:
            entries = details.get("discovered_files")
            if isinstance(entries, dict):
                for relative_path, path in entries.items():
                    heading = cls._stage_heading(relative_path)
                    cards.append(ReportDetailCard(title=heading, rows=[ReportDetailRow("SDOC File", str(path))]))
        else:
            entries = details.get("bin_files") if isinstance(details.get("bin_files"), dict) else {}
            crc_records = details.get("bin_crcs") if isinstance(details.get("bin_crcs"), dict) else {}

            stage_keys = sorted(set(entries.keys()) | set(crc_records.keys()))
            for relative_path in stage_keys:
                heading = cls._stage_heading(relative_path)
                stage_bin_path = entries.get(relative_path)
                crc_record = crc_records.get(relative_path, {})

                ladder_bin_name = crc_record.get("ladder_bin_name")
                ladder_crc = crc_record.get("ladder_crc")
                bin_name = crc_record.get("bin_name") or stage_bin_path
                bin_crc = crc_record.get("bin_crc") or crc_record.get("crc")
                status_text = crc_record.get("status") or ("PASS" if crc_record.get("crc") else "FAILED")
                reason_text = crc_record.get("reason")

                rows = [
                    ReportDetailRow("Ladder BIN", cls._friendly_value(ladder_bin_name)),
                    ReportDetailRow("Ladder CRC", cls._friendly_value(ladder_crc)),
                    ReportDetailRow("Bin File BIN", cls._friendly_value(bin_name)),
                    ReportDetailRow("Bin File CRC", cls._friendly_value(bin_crc)),
                    ReportDetailRow("Validation Result", cls._friendly_value(status_text)),
                ]
                if reason_text:
                    rows.append(ReportDetailRow("Reason", cls._friendly_value(reason_text)))
                cards.append(ReportDetailCard(title=heading, rows=rows))

        failures = details.get("failures")
        if isinstance(failures, list) and failures:
            cards.append(ReportDetailCard(title="Issues", rows=[ReportDetailRow("", str(failure)) for failure in failures]))

        stage_errors = details.get("stage_errors")
        if isinstance(stage_errors, list) and stage_errors:
            cards.append(ReportDetailCard(title="Issues", rows=[ReportDetailRow("", str(item)) for item in stage_errors]))
        return cards

    @classmethod
    def _render_signed_document_details(cls, step: ValidationStep | None, details: dict[str, Any]) -> list[ReportDetailCard]:
        cards: list[ReportDetailCard] = []
        document_name = details.get("document")
        if document_name:
            cards.append(ReportDetailCard(title="Document", rows=[ReportDetailRow("", str(document_name))]))

        signers = details.get("signers")
        if isinstance(signers, list):
            signer_rows: list[ReportDetailRow] = []
            for signer in signers:
                if not isinstance(signer, dict):
                    continue
                name = signer.get("signer_name") or signer.get("name")
                status = signer.get("is_valid")
                if status is None:
                    status = signer.get("signature_found")
                if name is None:
                    continue
                signer_rows.append(ReportDetailRow("", str(name)))
                signer_rows.append(ReportDetailRow("Digital Signature", "Valid" if status else "Invalid"))
            if signer_rows:
                cards.append(ReportDetailCard(title="Signers", rows=signer_rows))

        documents = details.get("documents")
        if isinstance(documents, list):
            for item in documents:
                if not isinstance(item, dict):
                    continue
                doc_name = item.get("path") or item.get("document")
                if not doc_name:
                    continue
                child_rows: list[ReportDetailRow] = []
                status = item.get("status")
                if status:
                    child_rows.append(ReportDetailRow("Status", str(status)))
                reason = item.get("reason")
                if reason:
                    child_rows.append(ReportDetailRow("Reason", str(reason)))
                nested_details = item.get("details")
                child_cards: list[ReportDetailCard] = []
                if isinstance(nested_details, dict):
                    child_cards.extend(cls._render_signed_document_details(step, nested_details))
                cards.append(ReportDetailCard(title=str(doc_name), rows=child_rows, children=child_cards))
        return cards


    @staticmethod
    def _friendly_label(key: str) -> str:
        replacements = {
            "bin_file": "BIN File",
            "version": "Version",
            "release_date": "Release Date",
            "crc": "CRC",

            "computed_crc": "Computed CRC",
            "computed_crc_decimal": "Computed CRC (dec)",
            "crc_match": "CRC Match",
            "reason_for_upgrade": "Upgrade Reason",
            "document": "Document",
            "signers": "Signers",
            "validated": "Validated Folders",
            "missing_folders": "Missing Folders",
            "missing": "Missing Count",
        }
        return replacements.get(key, key.replace("_", " ").title())

    @staticmethod
    def _friendly_value(value: Any) -> str:
        if value is None:
            return "None"
        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(item) for item in value)
        if isinstance(value, dict):
            return ", ".join(f"{key}={item}" for key, item in value.items())
        text = str(value)
        return text if len(text) <= 120 else text[:117] + "..."

    @staticmethod
    def _stage_heading(relative_path: str) -> str:
        parts = [part for part in relative_path.split("/") if part]
        if len(parts) >= 2:
            return f"{parts[0]} / {parts[1]}"
        return relative_path

    def status_text(self) -> str:
        return self.overall_status.name

    def status_color(self) -> str:
        if self.overall_status == ValidationStatus.FAIL:
            return "#D32F2F"
        if self.overall_status == ValidationStatus.WARNING:
            return "#ED6C02"
        return "#2E7D32"