"""
reports.report_window
=====================

Native PySide6 report window for validation results.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from config import THEME_PRIMARY, THEME_SUCCESS, THEME_WARNING, THEME_ERROR, THEME_BG_LIGHT, THEME_BG_DARK, THEME_TEXT_MAIN, THEME_TEXT_MUTED, THEME_BORDER
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QLayout,
)

from config import APP_NAME, APP_VERSION, COMPANY_NAME
from reports.report_model import ReportDataModel
from reports.report_widgets import ValidationRowWidget
from services.logger import LoggerService

logger = LoggerService.get_logger()


def _theme(value: str | None, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() else fallback


UI_THEME_PRIMARY = _theme(THEME_PRIMARY, "#F57C00")
UI_THEME_BG_LIGHT = _theme(THEME_BG_LIGHT, "#FFFFFF")
UI_THEME_TEXT_MAIN = _theme(THEME_TEXT_MAIN, "#202124")
UI_THEME_TEXT_MUTED = _theme(THEME_TEXT_MUTED, "#616161")
UI_THEME_BORDER = _theme(THEME_BORDER, "#E0E0E0")


class ReportWindow(QMainWindow):
    """A native PySide6 report window."""

    def __init__(self, data_model: ReportDataModel) -> None:
        super().__init__()
        self._data_model = data_model
        self._build_ui()

    def set_data_model(self, data_model: ReportDataModel) -> None:
        """Replace the report contents with the latest validation data."""
        self._data_model = data_model
        self._refresh_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle(f"{APP_NAME} Report")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        self._central_widget = central

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("ReportHeader")
        header.setMinimumHeight(70)
        header.setStyleSheet("QFrame#ReportHeader { background: #F57C00; border: none; }")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(2)

        self._title_label = QLabel(APP_NAME)
        self._title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        header_layout.addWidget(self._title_label)

        subtitle = QLabel(f"Version {APP_VERSION}")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.88); font-size: 10pt; font-weight: 500; background: transparent;")
        header_layout.addWidget(subtitle)
        root_layout.addWidget(header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        root_layout.addWidget(scroll_area, 1)

        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(16, 12, 16, 12)
        scroll_layout.setSpacing(10)
        scroll_area.setWidget(scroll_container)

        container = QFrame()
        container.setObjectName("ReportContainer")
        container.setStyleSheet(f"QFrame#ReportContainer {{ background: #FFFFFF; border: 1px solid {UI_THEME_BORDER}; border-radius: 6px; }}")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(8)
        scroll_layout.addWidget(container)

        self._info_layout = QVBoxLayout()
        self._info_layout.setSpacing(2)
        for label, value in [
            ("Company", COMPANY_NAME),
            ("Version", APP_VERSION),
            ("Generated", datetime.now().strftime("%d-%m-%Y %H:%M:%S")),
            ("Project", self._data_model.project_path),
        ]:
            row = QHBoxLayout()
            label_widget = QLabel(label)
            label_widget.setStyleSheet(f"font-weight: 700; color: {UI_THEME_TEXT_MAIN}; background: transparent; border: none;")
            value_widget = QLabel(str(value))
            value_widget.setStyleSheet(f"color: {UI_THEME_TEXT_MUTED}; background: transparent; border: none;")
            value_widget.setWordWrap(True)
            row.addWidget(label_widget)
            row.addWidget(value_widget, 1)
            self._info_layout.addLayout(row)
        container_layout.addLayout(self._info_layout)

        self._summary_frame = QFrame()
        self._summary_frame.setStyleSheet("background: transparent; border: 0px;")
        self._summary_layout = QHBoxLayout(self._summary_frame)
        self._summary_layout.setContentsMargins(0, 0, 0, 0)
        self._summary_layout.setSpacing(8)
        for label, value in [
            ("Overall", self._data_model.status_text()),
            ("Passed", str(self._data_model.passed)),
            ("Failed", str(self._data_model.failed)),
            ("Warnings", str(self._data_model.warnings)),
            ("Duration", f"{self._data_model.duration_seconds:.2f}s"),
        ]:
            card = QFrame()
            card.setStyleSheet("background: transparent; border: none;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            heading = QLabel(label)
            heading.setStyleSheet(f"color: {UI_THEME_TEXT_MUTED}; font-size: 9pt;")
            value_label = QLabel(str(value))
            value_label.setStyleSheet(f"color: {UI_THEME_TEXT_MAIN}; font-size: 10pt; font-weight: 700;")
            card_layout.addWidget(heading)
            card_layout.addWidget(value_label)
            self._summary_layout.addWidget(card)
        container_layout.addWidget(self._summary_frame)

        self._heading = QLabel("Validation Results")
        self._heading.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._heading.setStyleSheet(f"color: {UI_THEME_TEXT_MAIN}; margin-top: 10px;")
        container_layout.addWidget(self._heading)

        self._sections_container = QWidget()
        self._sections_container.setStyleSheet("background: transparent;")
        self._sections_layout = QVBoxLayout(self._sections_container)
        self._sections_layout.setContentsMargins(0, 0, 0, 0)
        self._sections_layout.setSpacing(8)

        for section in self._data_model.sections:
            self._sections_layout.addWidget(ValidationRowWidget(section))

        container_layout.addWidget(self._sections_container)

        toolbar = QFrame()
        toolbar.setStyleSheet("background: transparent; border: none;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 4, 0, 0)
        toolbar_layout.addStretch(1)

        export_button = QPushButton("Export PDF")
        export_button.clicked.connect(self._export_pdf)
        toolbar_layout.addWidget(export_button)

        toolbar_layout.addSpacerItem(QSpacerItem(8, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        toolbar_layout.addWidget(close_button)
        container_layout.addWidget(toolbar)

    def _refresh_ui(self) -> None:
        """Rebuild the visible report contents from the latest data model."""
        logger.info("Refreshing ReportWindow with data model project: %s", self._data_model.project_path)
        self._title_label.setText(APP_NAME)
        self._heading.setText("Validation Results")

        self._clear_layout(self._info_layout)
        self._clear_layout(self._summary_layout)
        self._clear_layout(self._sections_layout)

        self._info_layout.addLayout(self._build_info_layout())
        self._summary_layout.addWidget(self._build_summary_card("Overall", self._data_model.status_text()))
        self._summary_layout.addWidget(self._build_summary_card("Passed", str(self._data_model.passed)))
        self._summary_layout.addWidget(self._build_summary_card("Failed", str(self._data_model.failed)))
        self._summary_layout.addWidget(self._build_summary_card("Warnings", str(self._data_model.warnings)))
        self._summary_layout.addWidget(self._build_summary_card("Duration", f"{self._data_model.duration_seconds:.2f}s"))
        for section in self._data_model.sections:
            self._sections_layout.addWidget(ValidationRowWidget(section))

        self._central_widget.update()

    @staticmethod
    def _clear_layout(layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                ReportWindow._clear_layout(item.layout())

    def _build_info_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(2)
        for label, value in [
            ("Company", COMPANY_NAME),
            ("Version", APP_VERSION),
            ("Generated", datetime.now().strftime("%d-%m-%Y %H:%M:%S")),
            ("Project", self._data_model.project_path),
        ]:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(6)
            label_widget = QLabel(label)
            label_widget.setStyleSheet(f"font-weight: 700; color: {UI_THEME_TEXT_MAIN}; background: transparent; border: none;")
            value_widget = QLabel(str(value))
            value_widget.setStyleSheet(f"color: {UI_THEME_TEXT_MUTED}; background: transparent; border: none;")
            value_widget.setWordWrap(True)
            item_layout.addWidget(label_widget)
            item_layout.addWidget(value_widget, 1)
            layout.addLayout(item_layout)
        return layout

    def _build_summary_card(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background: transparent; border: none;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        heading = QLabel(label)
        heading.setStyleSheet(f"color: {UI_THEME_TEXT_MUTED}; font-size: 9pt;")
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {UI_THEME_TEXT_MAIN}; font-size: 10pt; font-weight: 700;")
        card_layout.addWidget(heading)
        card_layout.addWidget(value_label)
        return card

    def _export_pdf(self) -> None:
        try:
            from reports.pdf_exporter import PdfExporter
            exporter = PdfExporter(self)
            output_path = exporter.export(self._data_model)
            logger.info("Validation report exported to %s", output_path)
            QMessageBox.information(self, "Export Completed", "Validation report exported successfully.")
        except FileNotFoundError:
            logger.warning("PDF export cancelled by user")
        except PermissionError:
            logger.exception("Permission denied while exporting PDF")
            QMessageBox.critical(self, "Export Failed", "Permission denied while exporting the PDF.")
        except OSError as error:
            logger.exception("Unexpected filesystem error while exporting PDF: %s", error)
            QMessageBox.critical(self, "Export Failed", "An unexpected filesystem error occurred.")
        except Exception as error:
            logger.exception("Unexpected error while exporting PDF: %s", error)
            QMessageBox.critical(self, "Export Failed", str(error))
