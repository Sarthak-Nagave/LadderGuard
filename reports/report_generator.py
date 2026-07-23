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

from datetime import datetime
from pathlib import Path

from config import (
    APP_NAME,
    APP_VERSION,
    COMPANY_NAME,
    REPORT_DIRECTORY,
    REPORT_NAME_PREFIX,
)

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
                result.details
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
        details: object,
        indent: int = 0,
    ) -> str:
        """
        Recursively format dictionaries and lists
        into HTML.
        """

        if details is None:
            return ""

        if isinstance(details, dict):

            html = ""

            for key, value in details.items():

                html += (
                    "&nbsp;" * indent
                    + f"<b>{key}</b>: "
                    + cls._build_details(
                        value,
                        indent + 4,
                    )
                    + "<br>"
                )

            return html

        if isinstance(details, list):

            html = ""

            for item in details:

                html += (
                    "&nbsp;" * indent
                    + "• "
                    + cls._build_details(
                        item,
                        indent + 4,
                    )
                    + "<br>"
                )

            return html

        return str(details)