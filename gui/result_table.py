"""
gui.result_table
================

Displays validation results in a table.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QHBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
)

from core.validation_result import ValidationResult
from core.validation_summary import ValidationSummary


class ResultTable(QTableWidget):
    """
    Displays all validation results.
    """

    HEADERS = (
        "Validation Step",
        "Status",
        "Reason",
    )

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._setup_table()

# ---------------------------------------------------------

    def _setup_table(self) -> None:
        """
        Configure the table.
        """

        self.setColumnCount(len(self.HEADERS))

        self.setHorizontalHeaderLabels(self.HEADERS)

        self.setAlternatingRowColors(True)
        self.setFrameShape(QTableWidget.NoFrame)

        self.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.setSelectionMode(
            QAbstractItemView.SingleSelection
        )

        self.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.setWordWrap(True)
        self.setCornerButtonEnabled(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(0)

        self.verticalHeader().setVisible(False)

        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setMinimumSectionSize(90)

        header.setSectionResizeMode(
            0,
            QHeaderView.Interactive,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeToContents,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.Stretch,
        )

        self.setSortingEnabled(False)
        self.setColumnWidth(0, 260)

        self.clear_results()

 # ---------------------------------------------------------

    def clear_results(self) -> None:
        """
        Remove all rows.
        """

        self.setRowCount(0)

    # ---------------------------------------------------------

    def load_summary(
        self,
        summary: ValidationSummary,
    ) -> None:
        """
        Populate the table.
        """

        self.clear_results()

        for result in summary.results:

            self.add_result(result)

    # ---------------------------------------------------------

    def add_result(
        self,
        result: ValidationResult,
    ) -> None:
        """
        Add one validation result.
        """

        row = self.rowCount()

        self.insertRow(row)

        step_item = QTableWidgetItem(
            str(result.step)
        )

        status_item = QTableWidgetItem(
            result.status.name
        )

        reason_item = QTableWidgetItem(
            self._format_reason(result.reason)
        )

        self._apply_status_color(status_item, result.status.name)

        self.setItem(
            row,
            0,
            step_item,
        )

        self.setItem(
            row,
            1,
            status_item,
        )
        self.setCellWidget(row, 1, self._status_badge(result.status.name))

        self.setItem(
            row,
            2,
            reason_item,
        )

        step_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        reason_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setRowHeight(row, 30)

    # ---------------------------------------------------------

    @staticmethod
    def _format_reason(reason: str) -> str:
        """Remove only leading numeric prefixes from display reasons."""
        cleaned = reason.strip()
        while True:
            match = re.match(r"^\d+\.\s*", cleaned)
            if match is None:
                break
            cleaned = cleaned[match.end():]
        return cleaned

    @staticmethod
    def _apply_status_color(
        item: QTableWidgetItem,
        status: str,
    ) -> None:
        """
        Color-code status cells.
        """

        status = status.upper()

        if status == "PASS":

            item.setForeground(
                QColor("#2E7D32")
            )

        elif status == "FAIL":

            item.setForeground(
                QColor("#C62828")
            )

        elif status == "WARNING":

            item.setForeground(
                QColor("#EF6C00")
            )

        elif status == "SKIPPED":

            item.setForeground(
                QColor("#616161")
            )

        item.setTextAlignment(
            Qt.AlignCenter
        )

    @staticmethod
    def _status_badge(status: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        badge = QLabel(status.upper())
        badge.setObjectName("TableStatusBadge")
        badge.setProperty("status", status.lower())
        badge.setAlignment(Qt.AlignCenter)
        badge.setMinimumWidth(86)
        badge.setFixedHeight(22)
        layout.addWidget(badge)
        return container

    # ---------------------------------------------------------

    def resize_columns(self) -> None:
        """
        Resize columns after loading data.
        """

        self.resizeColumnsToContents()

        self.horizontalHeader().setStretchLastSection(
            True
        )