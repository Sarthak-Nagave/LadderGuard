"""
reports.report_widgets
=====================

Native PySide6 widgets used to mirror the HTML report.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QSpacerItem, QToolButton, QVBoxLayout, QWidget

from config import (
    THEME_PRIMARY,
    THEME_SUCCESS,
    THEME_WARNING,
    THEME_ERROR,
    THEME_BG_LIGHT,
    THEME_BG_DARK,
    THEME_TEXT_MAIN,
    THEME_TEXT_MUTED,
    THEME_BORDER,
)

from core.validation_step import ValidationStatus
from reports.report_model import ReportDetailCard, ReportDetailRow, ReportSection


def _theme(value: str | None, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() else fallback


UI_THEME_SUCCESS = _theme(THEME_SUCCESS, "#2E7D32")
UI_THEME_WARNING = _theme(THEME_WARNING, "#ED6C02")
UI_THEME_ERROR = _theme(THEME_ERROR, "#D32F2F")
UI_THEME_BG_LIGHT = _theme(THEME_BG_LIGHT, "#FFFFFF")
UI_THEME_TEXT_MAIN = _theme(THEME_TEXT_MAIN, "#202124")
UI_THEME_TEXT_MUTED = _theme(THEME_TEXT_MUTED, "#616161")
UI_THEME_BORDER = _theme(THEME_BORDER, "#E0E0E0")


class StatusBadge(QLabel):
    """Display a colored status badge matching the HTML report."""

    def __init__(self, status: ValidationStatus) -> None:
        super().__init__()
        self.setText(status.name)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(20)
        self.setMinimumWidth(74)
        self.setStyleSheet(self._style_for_status(status))

    @staticmethod
    def _style_for_status(status: ValidationStatus) -> str:
        if status == ValidationStatus.FAIL:
            return f"background-color: {UI_THEME_ERROR}; color: white; border-radius: 12px; padding: 0 10px;"
        if status == ValidationStatus.WARNING:
            return f"background-color: {UI_THEME_WARNING}; color: white; border-radius: 12px; padding: 0 10px;"
        return f"background-color: {UI_THEME_SUCCESS}; color: white; border-radius: 12px; padding: 0 10px;"


class DetailRowWidget(QWidget):
    """A borderless label/value row inside a detail section."""

    def __init__(self, row: ReportDetailRow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if row.label:
            label = QLabel(row.label or "")
            label.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {UI_THEME_TEXT_MAIN}; background: transparent; border: none;")
            label.setWordWrap(True)
            layout.addWidget(label)
            layout.addSpacerItem(QSpacerItem(8, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))

        value = QLabel(row.value or "")
        value.setWordWrap(True)
        value.setStyleSheet(f"font-size: 10px; color: {UI_THEME_TEXT_MUTED}; background: transparent; border: none;")
        layout.addWidget(value, 1)


class DetailCardWidget(QWidget):
    """A borderless details block that mirrors the HTML report."""

    def __init__(self, card: ReportDetailCard, indent: int = 0) -> None:
        super().__init__()
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        if card.title:
            title = QLabel(card.title or "")
            title.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            title.setStyleSheet(f"color: {UI_THEME_TEXT_MAIN}; background: transparent; border: none;")
            layout.addWidget(title)

        if card.rows:
            for row in card.rows:
                row_widget = DetailRowWidget(row)
                row_widget.setStyleSheet("background: transparent;")
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
            f"QFrame#ValidationRow {{ background: {UI_THEME_BG_LIGHT}; border: 1px solid {UI_THEME_BORDER}; border-radius: 6px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        step_label = QLabel(section.title or "")
        step_label.setStyleSheet(f"color: {UI_THEME_TEXT_MAIN}; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        step_label.setWordWrap(True)
        header_layout.addWidget(step_label, 1)
        header_layout.addWidget(StatusBadge(section.status))
        header_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(header_layout)

        reason_title = QLabel("Reason")
        reason_title.setStyleSheet(f"color: {UI_THEME_TEXT_MAIN}; font-size: 10px; font-weight: 600; background: transparent; border: none;")
        layout.addWidget(reason_title)

        reason_label = QLabel(section.reason or "")
        reason_label.setWordWrap(True)
        reason_label.setStyleSheet(f"color: {UI_THEME_TEXT_MUTED}; font-size: 10px; background: transparent; border: none;")
        layout.addWidget(reason_label)

        if section.details:
            details_toggle = QToolButton()
            details_toggle.setObjectName("DetailsToggle")
            details_toggle.setText("Validation Details")
            details_toggle.setCheckable(True)
            details_toggle.setChecked(True)
            details_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            details_toggle.setArrowType(Qt.ArrowType.DownArrow)
            layout.addWidget(details_toggle)

            details_container = QWidget()
            details_container.setObjectName("DetailsContainer")
            details_layout = QVBoxLayout(details_container)
            details_layout.setContentsMargins(6, 2, 2, 0)
            details_layout.setSpacing(4)

            for detail_card in section.details:
                details_layout.addWidget(DetailCardWidget(detail_card))

            def _toggle_details(expanded: bool) -> None:
                details_container.setVisible(expanded)
                details_toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)

            details_toggle.toggled.connect(_toggle_details)
            layout.addWidget(details_container)
