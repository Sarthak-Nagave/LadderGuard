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

        html_content = cls._build_html(summary)

        report_path.write_text(
            html_content,
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

        chronology_result = None
        for result in summary.results:
            if result.step == ValidationStep.CHRONOLOGY:
                chronology_result = result
                continue

            color = {
                "PASS": "{THEME_SUCCESS}",
                "FAIL": "{THEME_ERROR}",
                "WARNING": "{THEME_WARNING}",
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
<td style="color:{color};font-weight:bold;">{result.status.name}</td>
<td>{html.escape(result.reason)}</td>
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
    background:{THEME_BG_DARK};
}}

.container {{
    background:white;
    padding:30px;
    border-radius:10px;
    box-shadow:0 2px 8px rgba(0,0,0,.15);
}}

h1 {{
    color:{THEME_PRIMARY};
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
    background:{THEME_BG_LIGHT};
    border-left:6px solid {THEME_PRIMARY};
}}

.card h3 {{
    margin:0;
}}

table {{
    width:100%;
    border-collapse:collapse;
}}

th {{
    background:{THEME_PRIMARY};
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
    border-left: 4px solid {THEME_PRIMARY};
    background: {THEME_BG_LIGHT};
    border-radius: 6px;
}}

.details-heading {{
    display: block;
    font-size: 1.08em;
    font-weight: 700;
    color: {THEME_TEXT_MAIN};
    margin-bottom: 8px;
}}

.details-row {{
    margin: 4px 0;
    color: {THEME_TEXT_MUTED};
}}

.details-label {{
    font-weight: 700;
    color: {THEME_TEXT_MAIN};
}}

.details-list {{
    margin: 4px 0 0 0;
    padding-left: 16px;
}}

.chronology-stage {{
    margin: 24px 0;
    padding: 20px;
    border: 1px solid {THEME_BORDER};
    border-radius: 12px;
    background: {THEME_BG_LIGHT};
}}

.chronology-stage h3 {{
    margin: 0 0 18px 0;
    font-size: 1.25em;
    color: {THEME_TEXT_MAIN};
    border-bottom: 1px solid {THEME_BORDER};
    padding-bottom: 10px;
}}

.chronology-table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}}

.chronology-table caption {{
    caption-side: top;
    text-align: left;
    font-weight: 700;
    margin-bottom: 8px;
    color: {THEME_TEXT_MAIN};
}}

.chronology-table td,
.chronology-table th {{
    padding: 10px 12px;
    border: 1px solid {THEME_BORDER};
    vertical-align: top;
}}

.chronology-table th {{
    background: {THEME_BG_DARK};
    font-weight: 700;
    color: {THEME_TEXT_MAIN};
    text-align: left;
}}

.stage-status {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 8px;
    background: {THEME_BG_DARK};
    border: 1px solid {THEME_BORDER};
    color: {THEME_TEXT_MAIN};
    font-weight: 700;
}}

.stage-status.pass {{
    border-color: {THEME_SUCCESS};
    color: {THEME_SUCCESS};
}}

.stage-status.fail {{
    border-color: {THEME_ERROR};
    color: {THEME_ERROR};
}}

.validation-summary {{
    margin-top: 36px;
    padding: 22px;
    border: 1px solid {THEME_BORDER};
    border-radius: 12px;
    background: {THEME_BG_LIGHT};
}}

.validation-summary h3 {{
    margin-top: 0;
    color: {THEME_TEXT_MAIN};
}}

.validation-summary table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 16px;
}}

.validation-summary th,
.validation-summary td {{
    text-align: left;
    padding: 10px 12px;
    border: 1px solid {THEME_BORDER};
}}

.validation-summary th {{
    background: {THEME_BG_DARK};
    font-weight: 700;
}}

.overall-failure {{
    margin-top: 20px;
    padding: 16px;
    border-radius: 10px;
    background: #FEF2F2;
    color: #B91C1C;
    border: 1px solid #FECACA;
}}

.validation-reasons {{
    margin: 12px 0 0 0;
    padding-left: 20px;
}}

.validation-reasons li {{
    margin-bottom: 6px;
}}

.chronology-overview {{
    margin: 30px 0 10px 0;
    padding: 20px;
    border-left: 4px solid {THEME_PRIMARY};
    background: {THEME_BG_DARK};
    border-radius: 8px;
}}

.chronology-overview p {{
    margin: 0;
    color: {THEME_TEXT_MAIN};
    line-height: 1.6;
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

{cls._render_chronology_section(chronology_result) if chronology_result else ""}

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
    def _render_chronology_section(cls, chronology_result: object | None) -> str:
        if chronology_result is None or not hasattr(chronology_result, "details"):
            return ""

        details = getattr(chronology_result, "details")
        if not isinstance(details, dict):
            return ""

        reason = getattr(chronology_result, "reason", "") or ""
        section_html = (
            "<h2>CHRONOLOGY</h2>"
            "<div class='chronology-overview'>"
            f"<p>{html.escape(reason)}</p>"
            "</div>"
            f"{cls._render_chronology_details(details)}"
        )

        stages = details.get("stages")
        if isinstance(stages, list) and stages:
            summary_rows = []
            overall_status = "PASS"
            for stage in stages:
                if not isinstance(stage, dict):
                    continue
                heading = cls._chronology_stage_heading(stage.get("board"), stage.get("stage"))
                stage_status = stage.get("overall_result") or "FAIL"
                if stage_status != "PASS":
                    overall_status = "FAIL"
                summary_rows.append(
                    f"<tr><td>{html.escape(heading)}</td><td>{html.escape(stage_status)}</td></tr>"
                )

            section_html += (
                "<div class='validation-summary'>"
                "<h3>FINAL SUMMARY</h3>"
                "<table>"
                "<tr><th>Testing Stage</th><th>Result</th></tr>"
                + "".join(summary_rows)
                + "</table>"
                f"<div style='margin-top: 15px;' class='stage-status {overall_status.lower()}'>Overall: {html.escape(overall_status)}</div>"
                "</div>"
            )

        return section_html

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
            entries = details.get("bin_files") if isinstance(details.get("bin_files"), dict) else {}
            crc_records = details.get("bin_crcs") if isinstance(details.get("bin_crcs"), dict) else {}

            stage_keys = sorted(set(entries.keys()) | set(crc_records.keys()))
            for relative_path in stage_keys:
                heading = cls._stage_heading(relative_path)
                stage_bin_path = entries.get(relative_path)
                crc_record = crc_records.get(relative_path, {})

                ladder_bin_display = crc_record.get("ladder_bin_name")
                ladder_crc_display = crc_record.get("ladder_crc")
                bin_display = crc_record.get("bin_name") or stage_bin_path
                bin_crc_display = crc_record.get("bin_crc") or crc_record.get("crc")
                status_text = crc_record.get("status") or ("PASS" if crc_record.get("crc") else "FAILED")
                reason_text = crc_record.get("reason")

                rows = [
                    f"<div class='details-row'><span class='details-label'>Ladder BIN</span> : {html.escape(str(ladder_bin_display))}</div>",
                    f"<div class='details-row'><span class='details-label'>Ladder CRC</span> : {html.escape(str(ladder_crc_display))}</div>",
                    f"<div class='details-row'><span class='details-label'>Bin File BIN</span> : {html.escape(str(bin_display))}</div>",
                    f"<div class='details-row'><span class='details-label'>Bin File CRC</span> : {html.escape(str(bin_crc_display))}</div>",
                    f"<div class='details-row'><span class='details-label'>Validation Result</span> : {html.escape(str(status_text))}</div>",
                ]
                if reason_text:
                    rows.append(
                        f"<div class='details-row'><span class='details-label'>Reason</span> : {html.escape(str(reason_text))}</div>"
                    )

                cards.append(
                    f"<div class='details-card'><div class='details-heading'>{html.escape(heading)}</div>{''.join(rows)}</div>"
                )

        failures = details.get("failures")
        if isinstance(failures, list) and failures:
            cards.append(
                "<div class='details-card'><div class='details-heading'>Issues</div>"
                + "".join(f"<div class='details-row'>{html.escape(str(failure))}</div>" for failure in failures)
                + "</div>"
            )

        stage_errors = details.get("stage_errors")
        if isinstance(stage_errors, list) and stage_errors:
            cards.append(
                "<div class='details-card'><div class='details-heading'>Issues</div>"
                + "".join(f"<div class='details-row'>{html.escape(str(item))}</div>" for item in stage_errors)
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

        stage_cards = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            heading = cls._chronology_stage_heading(stage.get("board"), stage.get("stage"))
            stage_cards.append(cls._render_chronology_stage_card(heading, stage))

        return "".join(stage_cards)

    @classmethod
    def _render_chronology_stage_card(cls, heading: str, stage: dict) -> str:
        def fmt(value: object | None) -> str:
            return html.escape(str(value)) if value is not None else "Not Found"

        latest = stage.get("latest_firmware") or {}
        previous = stage.get("previous_firmware")
        validation = stage.get("validation") or {}
        overall = stage.get("overall_result") or "FAIL"
        failures = stage.get("failure_reasons") or []

        latest_html = (
            "<table class='chronology-table'>"
            "<caption>Latest Firmware</caption>"
            "<tr><th>BIN File</th><td>" + fmt(latest.get("bin_file")) + "</td></tr>"
            "<tr><th>Version</th><td>" + fmt(latest.get("version")) + "</td></tr>"
            "<tr><th>Release Date</th><td>" + fmt(latest.get("release_date")) + "</td></tr>"
            "<tr><th>Chronology CRC</th><td>" + fmt(latest.get("crc")) + "</td></tr>"
            "<tr><th>Reason for Upgrade</th><td>" + fmt(latest.get("reason_for_upgrade")) + "</td></tr>"
            "</table>"
        )

        if previous:
            previous_html = (
                "<table class='chronology-table'>"
                "<caption>Previous Firmware</caption>"
                "<tr><th>BIN File</th><td>" + fmt(previous.get("bin_file")) + "</td></tr>"
                "<tr><th>Version</th><td>" + fmt(previous.get("version")) + "</td></tr>"
                "<tr><th>Release Date</th><td>" + fmt(previous.get("release_date")) + "</td></tr>"
                "<tr><th>CRC</th><td>" + fmt(previous.get("crc")) + "</td></tr>"
                "</table>"
            )
        else:
            previous_html = (
                "<table class='chronology-table'>"
                "<caption>Previous Firmware</caption>"
                "<tr><td>N/A</td></tr>"
                "</table>"
            )

        v_crc = validation.get("crc") or {}

        validation_html = (
            "<table class='chronology-table'>"
            "<caption>Validation</caption>"
            "<tr><th>Chronology CRC</th><td>" + fmt(latest.get("crc")) + "</td></tr>"
            "<tr><th>Generated CRC</th><td>" + fmt(v_crc.get("generated_crc")) + "</td></tr>"
            "<tr><th>Result</th><td>" + fmt(overall) + "</td></tr>"
            "</table>"
        )

        overall_html = f"<div class='stage-status {overall.lower()}'>Overall Result: {html.escape(overall)}</div>"

        failures_html = ""
        if failures:
            list_items = "".join(f"<li>{html.escape(str(f))}</li>" for f in failures)
            failures_html = (
                "<div class='overall-failure'>"
                "<strong>Failure Reasons</strong>"
                "<ul class='validation-reasons'>"
                f"{list_items}"
                "</ul>"
                "</div>"
            )

        return (
            "<div class='chronology-stage'>"
            f"<h3>{html.escape(heading)}</h3>"
            f"{latest_html}"
            f"{previous_html}"
            f"{validation_html}"
            f"{overall_html}"
            f"{failures_html}"
            "</div>"
        )

    @staticmethod
    def _chronology_stage_heading(board: str | None, stage_name: str | None) -> str:
        if board and stage_name:
            return f"{board} / {stage_name}"
        if board:
            return str(board)
        if stage_name:
            return str(stage_name)
        return "Chronology"

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