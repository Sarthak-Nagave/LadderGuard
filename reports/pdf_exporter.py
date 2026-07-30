"""
reports.pdf_exporter
===================

Export the report data model to PDF using reportlab.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog

from config import APP_NAME, APP_VERSION, COMPANY_NAME
from reports.report_model import ReportDataModel, ReportDetailCard, ReportDetailRow

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("reportlab is required for PDF export") from exc


class PdfExporter:
    """Export a ReportDataModel to a PDF document."""

    def __init__(self, parent: Any | None = None) -> None:
        self._parent = parent

    def export(self, data_model: ReportDataModel) -> Path:
        path, _ = QFileDialog.getSaveFileName(
            self._parent,
            "Export Validation Report",
            str(Path.home() / "Desktop" / "validation_report.pdf"),
            "PDF Files (*.pdf)",
        )
        if not path:
            raise FileNotFoundError("No save location selected")

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(str(output_path), pagesize=letter, rightMargin=0.5 * inch, leftMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, textColor=colors.HexColor("#F57C00"), spaceAfter=10)
        subtitle_style = ParagraphStyle("SubtitleStyle", parent=styles["BodyText"], fontSize=9, textColor=colors.HexColor("#555555"), spaceAfter=4)
        section_style = ParagraphStyle("SectionStyle", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#F57C00"), spaceAfter=6)
        body_style = ParagraphStyle("BodyStyle", parent=styles["BodyText"], fontSize=9, leading=12)
        heading_style = ParagraphStyle("HeadingStyle", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#1f2937"), spaceBefore=4, spaceAfter=2)
        detail_style = ParagraphStyle("DetailStyle", parent=styles["BodyText"], fontSize=8.5, leading=10)

        story = []
        story.append(Paragraph(APP_NAME, title_style))
        story.append(Paragraph(f"Company : {COMPANY_NAME}", subtitle_style))
        story.append(Paragraph(f"Version : {APP_VERSION}", subtitle_style))
        story.append(Paragraph(f"Generated : {data_model.validation_date} {data_model.validation_time}", subtitle_style))
        story.append(Paragraph(f"Project : {data_model.project_path}", subtitle_style))
        story.append(Spacer(1, 0.12 * inch))

        summary_data = [
            ["Overall", data_model.status_text()],
            ["Passed", str(data_model.passed)],
            ["Failed", str(data_model.failed)],
            ["Warnings", str(data_model.warnings)],
            ["Duration", f"{data_model.duration_seconds:.2f}s"],
        ]
        table = Table(summary_data, colWidths=[1.6 * inch, 1.4 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F57C00")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.18 * inch))
        story.append(Paragraph("Validation Results", section_style))

        for section in data_model.sections:
            story.append(Paragraph(section.title, heading_style))
            story.append(Paragraph(section.reason, body_style))
            for card in section.details:
                story.extend(self._render_detail_card(card, 0, detail_style, heading_style))
            story.append(Spacer(1, 0.08 * inch))

        doc.build(story)
        return output_path

    @staticmethod
    def _render_detail_card(card: ReportDetailCard, indent: int, detail_style: Any, heading_style: Any) -> list[Any]:
        result = []
        if card.title:
            result.append(Paragraph(card.title, heading_style))
        for row in card.rows:
            label = row.label
            value = row.value
            if label:
                result.append(Paragraph(f"{label} : {value}", detail_style))
            else:
                result.append(Paragraph(value, detail_style))
        for child in card.children:
            result.extend(PdfExporter._render_detail_card(child, indent + 1, detail_style, heading_style))
        return result
