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

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
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

        self.verticalHeader().setVisible(False)

        header = self.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents,
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
            result.reason
        )

        self._apply_status_color(
            status_item,
            result.status.name,
        )

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

        self.setItem(
            row,
            2,
            reason_item,
        )

    # ---------------------------------------------------------

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

    # ---------------------------------------------------------

    def resize_columns(self) -> None:
        """
        Resize columns after loading data.
        """

        self.resizeColumnsToContents()

        self.horizontalHeader().setStretchLastSection(
            True
        )