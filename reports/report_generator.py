"""
reports.report_generator
========================

Generates validation reports for the Operational Package Validator.

Responsibilities
----------------
- Generate HTML validation reports.
- Summarize validation results.
- Display per-step validation status.
- Display signer validation.
- Save reports to the reports directory.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from config import (
    APP_NAME,
    APP_VERSION,
    COMPANY_NAME,
    REPORT_DIRECTORY,
    REPORT_NAME_PREFIX,
)

from core.validation_step import ValidationStep
from core.validation_summary import ValidationSummary

from services.logger import LoggerService


class ReportGenerator:
    """
    Generates validation reports.
    """

    logger = LoggerService.get_logger()

    @classmethod
    def generate(
        cls,
        summary: ValidationSummary,
    ) -> Path:
        """
        Generate an HTML report.

        Parameters
        ----------
        summary
            Validation summary.

        Returns
        -------
        Path
            Generated report.
        """

        REPORT_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        report_path = (
            REPORT_DIRECTORY
            / f"{REPORT_NAME_PREFIX}_{timestamp}.html"
        )

        cls.logger.info(
            f"Generating report: {report_path.name}"
        )

        html = cls._build_html(summary)

        report_path.write_text(
            html,
            encoding="utf-8",
        )

        cls.logger.info(
            "Report generated successfully."
        )

        return report_path

    # ---------------------------------------------------------

    @classmethod
    def _build_html(
        cls,
        summary: ValidationSummary,
    ) -> str:

        rows = []

        for result in summary.results:

            color = {
                "PASS": "#2E7D32",
                "FAIL": "#D32F2F",
                "WARNING": "#ED6C02",
                "SKIPPED": "#757575",
            }.get(result.status.name, "#000000")

            details_html = cls._build_details(
                result.step,
                result.details,
            )

            rows.append(
                f"""
<tr>
<td>{result.step}</td>
<td style="color:{color};font-weight:bold;">
{result.status.name}
</td>
<td>{result.reason}</td>
<td>{details_html}</td>
</tr>
"""
            )

            table_rows = "\n".join(rows)

        return f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">

<title>{APP_NAME}</title>

<style>

body {{
    font-family: Segoe UI, Arial, sans-serif;
    margin:40px;
    background:#f5f5f5;
}}

.container {{
    background:white;
    padding:30px;
    border-radius:10px;
    box-shadow:0 2px 8px rgba(0,0,0,.15);
}}

h1 {{
    color:#F57C00;
    margin-bottom:0;
}}

h2 {{
    margin-top:30px;
}}

.info {{
    margin-bottom:25px;
}}

.summary {{
    display:flex;
    gap:20px;
    margin:20px 0;
}}

.card {{
    flex:1;
    padding:15px;
    border-radius:8px;
    background:#fafafa;
    border-left:6px solid #F57C00;
}}

.card h3 {{
    margin:0;
}}

table {{
    width:100%;
    border-collapse:collapse;
}}

th {{
    background:#F57C00;
    color:white;
    padding:10px;
}}

td {{
    padding:10px;
    border-bottom:1px solid #ddd;
    vertical-align:top;
}}

pre {{
    margin:0;
    white-space:pre-wrap;
    word-break:break-word;
}}

.details-card {{
    margin: 8px 0 14px 0;
    padding: 12px 14px;
    border-left: 4px solid #F57C00;
    background: #fafafa;
    border-radius: 6px;
}}

.details-heading {{
    display: block;
    font-size: 1.08em;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 8px;
}}

.details-row {{
    margin: 4px 0;
    color: #374151;
}}

.details-label {{
    font-weight: 700;
    color: #1f2937;
}}

.details-list {{
    margin: 4px 0 0 0;
    padding-left: 16px;
}}

</style>

</head>

<body>

<div class="container">

<h1>{APP_NAME}</h1>

<div class="info">

<b>Company</b> : {COMPANY_NAME}<br>

<b>Version</b> : {APP_VERSION}<br>

<b>Generated</b> :
{datetime.now().strftime("%d-%m-%Y %H:%M:%S")}<br>

<b>Project</b> :
{summary.project_path}

</div>

<div class="summary">

<div class="card">

<h3>Overall</h3>

<p>{summary.overall_status.name}</p>

</div>

<div class="card">

<h3>Passed</h3>

<p>{summary.passed}</p>

</div>

<div class="card">

<h3>Failed</h3>

<p>{summary.failed}</p>

</div>

<div class="card">

<h3>Warnings</h3>

<p>{summary.warnings}</p>

</div>

<div class="card">

<h3>Duration</h3>

<p>{summary.duration_seconds:.2f}s</p>

</div>

</div>

<h2>Validation Results</h2>

<table>

<tr>

<th>Validation Step</th>

<th>Status</th>

<th>Reason</th>

<th>Details</th>

</tr>

{table_rows}

</table>

</div>

</body>

</html>
"""

    # ---------------------------------------------------------

    @classmethod
    def _build_details(
        cls,
        step: ValidationStep | None,
        details: object,
        indent: int = 0,
    ) -> str:
        """
        Format structured validation details into readable HTML cards.
        """

        if details is None:
            return ""

        if isinstance(details, dict):
            return cls._render_dict_details(step, details, indent)

        if isinstance(details, list):
            return cls._render_list_details(step, details, indent)

        return f"<div class='details-row'>{html.escape(str(details))}</div>"

    @classmethod
    def _render_dict_details(
        cls,
        step: ValidationStep | None,
        details: dict,
        indent: int,
    ) -> str:
        if step == ValidationStep.FOLDER_STRUCTURE:
            return cls._render_folder_structure_details(details)

        if step in {ValidationStep.LADDER_FILES, ValidationStep.BIN_FILES}:
            return cls._render_stage_file_details(step, details)

        if step in {ValidationStep.OPERATIONAL_FLOW, ValidationStep.TEST_REPORT, ValidationStep.AUTOMATION_INPUT, ValidationStep.LADDER_FLOW}:
            return cls._render_signed_document_details(step, details)

        if step == ValidationStep.CHRONOLOGY or "stages" in details:
            return cls._render_chronology_details(details)

        if "signers" in details and isinstance(details["signers"], list):
            return cls._render_signed_document_details(step, details)

        if "document" in details or "documents" in details:
            return cls._render_signed_document_details(step, details)

        simple_rows = []
        for key, value in details.items():
            label = cls._friendly_label(key)
            if isinstance(value, (dict, list)):
                continue
            simple_rows.append(
                f"<div class='details-row'><span class='details-label'>{html.escape(label)}</span> : {html.escape(str(value))}</div>"
            )

        if not simple_rows:
            return ""

        return f"<div class='details-card'>{''.join(simple_rows)}</div>"

    @classmethod
    def _render_list_details(
        cls,
        step: ValidationStep | None,
        details: list,
        indent: int,
    ) -> str:
        items = []
        for item in details:
            rendered = cls._build_details(step, item, indent + 4)
            if rendered:
                items.append(f"<div class='details-row'>{rendered}</div>")

        if not items:
            return ""

        return f"<div class='details-card'><div class='details-list'>{''.join(items)}</div></div>"

    @classmethod
    def _render_folder_structure_details(cls, details: dict) -> str:
        rows = []
        validated = details.get("validated")
        if validated is not None:
            rows.append(f"<div class='details-row'><span class='details-label'>Validated Folders</span> : {validated}</div>")

        missing = details.get("missing_folders")
        if isinstance(missing, list) and missing:
            rows.append(
                "<div class='details-row'><span class='details-label'>Missing Folders</span> : "
                + ", ".join(html.escape(str(item)) for item in missing)
                + "</div>"
            )

        if not rows:
            return ""

        return f"<div class='details-card'>{''.join(rows)}</div>"

    @classmethod
    def _render_stage_file_details(cls, step: ValidationStep | None, details: dict) -> str:
        cards = []

        if step == ValidationStep.LADDER_FILES:
            entries = details.get("discovered_files")
            if isinstance(entries, dict):
                for relative_path, path in entries.items():
                    heading = cls._stage_heading(relative_path)
                    cards.append(
                        f"<div class='details-card'><div class='details-heading'>{html.escape(heading)}</div>"
                        f"<div class='details-row'><span class='details-label'>SDOC File</span> : {html.escape(str(path))}</div></div>"
                    )
        else:
            entries = details.get("bin_files")
            if isinstance(entries, dict):
                for relative_path, path in entries.items():
                    heading = cls._stage_heading(relative_path)
                    cards.append(
                        f"<div class='details-card'><div class='details-heading'>{html.escape(heading)}</div>"
                        f"<div class='details-row'><span class='details-label'>BIN File</span> : {html.escape(str(path))}</div></div>"
                    )

        failures = details.get("failures")
        if isinstance(failures, list) and failures:
            cards.append(
                "<div class='details-card'><div class='details-heading'>Issues</div>"
                + "".join(f"<div class='details-row'>{html.escape(str(failure))}</div>" for failure in failures)
                + "</div>"
            )

        return "".join(cards)

    @classmethod
    def _render_signed_document_details(cls, step: ValidationStep | None, details: dict) -> str:
        cards = []

        document_name = details.get("document")
        if document_name:
            cards.append(
                f"<div class='details-card'><div class='details-heading'>Document</div>"
                f"<div class='details-row'>{html.escape(str(document_name))}</div></div>"
            )

        signers = details.get("signers")
        if isinstance(signers, list):
            signer_rows = []
            for signer in signers:
                if not isinstance(signer, dict):
                    continue
                name = signer.get("signer_name") or signer.get("name")
                status = signer.get("is_valid")
                if status is None:
                    status = signer.get("signature_found")
                if name is None:
                    continue
                signer_rows.append(
                    f"<div class='details-row'>{html.escape(str(name))}</div>"
                    f"<div class='details-row'><span class='details-label'>Digital Signature</span> : {html.escape('Valid' if status else 'Invalid')}</div>"
                )
            if signer_rows:
                cards.append("<div class='details-card'><div class='details-heading'>Signers</div>" + "".join(signer_rows) + "</div>")

        documents = details.get("documents")
        if isinstance(documents, list):
            for item in documents:
                if not isinstance(item, dict):
                    continue
                doc_name = item.get("path") or item.get("document")
                if not doc_name:
                    continue
                doc_rows = [f"<div class='details-card'><div class='details-heading'>{html.escape(str(doc_name))}</div>"]
                status = item.get("status")
                if status:
                    doc_rows.append(f"<div class='details-row'><span class='details-label'>Status</span> : {html.escape(str(status))}</div>")
                reason = item.get("reason")
                if reason:
                    doc_rows.append(f"<div class='details-row'><span class='details-label'>Reason</span> : {html.escape(str(reason))}</div>")
                nested_details = item.get("details")
                if isinstance(nested_details, dict):
                    nested_html = cls._render_signed_document_details(step, nested_details)
                    if nested_html:
                        doc_rows.append(nested_html)
                doc_rows.append("</div>")
                cards.append("".join(doc_rows))

        return "".join(cards)

    @classmethod
    def _render_chronology_details(cls, details: dict) -> str:
        stages = details.get("stages")
        if not isinstance(stages, list):
            return ""

        cards = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            board = stage.get("board")
            stage_name = stage.get("stage")
            heading = f"{board} / {stage_name}" if board and stage_name else (board or stage_name or "Chronology")

            rows_html = []
            for key, label in [
                ("bin_file", "BIN File"),
                ("version", "Version"),
                ("release_date", "Release Date"),
                ("reason_for_upgrade", "Upgrade Reason"),
            ]:
                value = stage.get(key)
                if value is None:
                    continue
                rows_html.append(
                    f"<div class='details-row'><span class='details-label'>{html.escape(label)}</span> : {html.escape(str(value))}</div>"
                )

            if rows_html:
                cards.append(
                    "<div class='details-card'>"
                    f"<div class='details-heading'>{html.escape(heading)}</div>"
                    + "".join(rows_html)
                    + "</div>"
                )

        return "".join(cards)

    @staticmethod
    def _friendly_label(key: str) -> str:
        replacements = {
            "bin_file": "BIN File",
            "version": "Version",
            "release_date": "Release Date",
            "reason_for_upgrade": "Upgrade Reason",
            "document": "Document",
            "signers": "Signers",
            "validated": "Validated Folders",
            "missing_folders": "Missing Folders",
            "missing": "Missing Count",
        }
        return replacements.get(key, key.replace("_", " ").title())

    @staticmethod
    def _stage_heading(relative_path: str) -> str:
        parts = [part for part in relative_path.split("/") if part]
        if len(parts) >= 2:
            return f"{parts[0]} / {parts[1]}"
        return relative_path