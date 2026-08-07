"""
gui.progress_widget
===================

Reusable validation progress widget.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from config import PROGRESS_TITLE


class ProgressWidget(QFrame):
    """
    Displays the current validation progress.

    This widget is presentation-only and does not
    contain any validation logic.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._build_ui()

        self.reset()

    # ---------------------------------------------------------

    def _build_ui(self) -> None:
        """
        Create all controls.
        """

        self.setObjectName("ProgressWidget")

        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(8, 6, 8, 6)

        layout.setSpacing(2)

        title = QLabel(PROGRESS_TITLE)

        title.setObjectName("ProgressTitle")

        self.progress_bar = QProgressBar()

        self.progress_bar.setMinimum(0)

        self.progress_bar.setMaximum(100)

        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")

        self.progress_bar.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel()

        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("ProgressStatusText")

        layout.addWidget(title)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

    # ---------------------------------------------------------

    def reset(self) -> None:
        """
        Reset widget.
        """

        self.progress_bar.setValue(0)

        self.status_label.setText("Ready")

        self.status_label.setStyleSheet(
            ""
        )

    # ---------------------------------------------------------

    def set_step(
        self,
        step: str,
    ) -> None:
        """
        Update current validation step.
        """

    # ---------------------------------------------------------

    def set_progress(
        self,
        value: int,
    ) -> None:
        """
        Update progress percentage.
        """

        value = max(0, min(100, value))

        self.progress_bar.setValue(value)

    # ---------------------------------------------------------

    def set_running(self) -> None:
        """
        Show running state.
        """

        self.status_label.setText(
            "Running..."
        )

        self.status_label.setStyleSheet("")

    # ---------------------------------------------------------

    def set_success(self) -> None:
        """
        Show successful validation.
        """

        self.progress_bar.setValue(100)

        self.status_label.setText(
            "Validation Completed Successfully"
        )

        self.status_label.setStyleSheet("")

    # ---------------------------------------------------------

    def set_failure(
        self,
        message: str = "Validation Failed",
    ) -> None:
        """
        Show validation failure.
        """

        self.status_label.setText(message)

        self.status_label.setStyleSheet("")

    # ---------------------------------------------------------

    def finish(self) -> None:
        """
        Mark progress complete.
        """

        self.progress_bar.setValue(100)