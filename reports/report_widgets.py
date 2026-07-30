"""
reports.report_widgets
=====================

Native PySide6 widgets used to mirror the HTML report.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget

from core.validation_step import ValidationStatus
from reports.report_model import ReportDetailCard, ReportDetailRow, ReportSection


class StatusBadge(QLabel):
    """Display a colored status badge matching the HTML report."""

    def __init__(self, status: ValidationStatus) -> None:
        super().__init__()
        self.setText(status.name)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        self.setMinimumWidth(85)
        self.setStyleSheet(self._style_for_status(status))

    @staticmethod
    def _style_for_status(status: ValidationStatus) -> str:
        if status == ValidationStatus.FAIL:
            return "background-color: #D32F2F; color: white; border-radius: 12px; padding: 0 10px;"
        if status == ValidationStatus.WARNING:
            return "background-color: #ED6C02; color: white; border-radius: 12px; padding: 0 10px;"
        return "background-color: #2E7D32; color: white; border-radius: 12px; padding: 0 10px;"


class DetailRowWidget(QHBoxLayout):
    """A borderless label/value row inside a detail section."""

    def __init__(self, row: ReportDetailRow) -> None:
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(6)

        if row.label:
            label = QLabel(row.label)
            label.setStyleSheet("font-weight: 700; color: #1f2937;")
            label.setWordWrap(True)
            self.addWidget(label)
            self.addSpacerItem(QSpacerItem(8, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))

        value = QLabel(row.value)
        value.setWordWrap(True)
        value.setStyleSheet("color: #374151;")
        self.addWidget(value, 1)


class DetailCardWidget(QWidget):
    """A borderless details block that mirrors the HTML report."""

    def __init__(self, card: ReportDetailCard, indent: int = 0) -> None:
        super().__init__()
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if card.title:
            title = QLabel(card.title)
            title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            title.setStyleSheet("color: #1f2937;")
            layout.addWidget(title)

        if card.rows:
            for row in card.rows:
                row_widget = QWidget()
                row_widget.setStyleSheet("background: transparent;")
                row_layout = DetailRowWidget(row)
                row_widget.setLayout(row_layout)
                layout.addWidget(row_widget)

        for child in card.children:
            child_container = QWidget()
            child_container.setStyleSheet("background: transparent;")
            child_layout = QVBoxLayout(child_container)
            child_layout.setContentsMargins(16 + indent * 10, 0, 0, 0)
            child_layout.setSpacing(4)
            child_layout.addWidget(DetailCardWidget(child, indent + 1))
            layout.addWidget(child_container)


class ValidationRowWidget(QFrame):
    """One clean validation card for the report."""

    def __init__(self, section: ReportSection) -> None:
        super().__init__()
        self.setObjectName("ValidationRow")
        self.setStyleSheet(
            "QFrame#ValidationRow { background: white; border: 1px solid #E0E0E0; border-radius: 8px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        step_label = QLabel(section.title)
        step_label.setStyleSheet("color: #111827; font-size: 11pt; font-weight: 700;")
        step_label.setWordWrap(True)
        header_layout.addWidget(step_label, 1)
        header_layout.addWidget(StatusBadge(section.status))
        header_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(header_layout)

        reason_title = QLabel("Reason")
        reason_title.setStyleSheet("color: #1f2937; font-size: 9pt; font-weight: 700;")
        layout.addWidget(reason_title)

        reason_label = QLabel(section.reason)
        reason_label.setWordWrap(True)
        reason_label.setStyleSheet("color: #374151; font-size: 9pt;")
        layout.addWidget(reason_label)

        if section.details:
            details_title = QLabel("Validation Details")
            details_title.setStyleSheet("color: #1f2937; font-size: 9pt; font-weight: 700; margin-top: 4px;")
            layout.addWidget(details_title)

            for detail_card in section.details:
                layout.addWidget(DetailCardWidget(detail_card))
