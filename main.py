"""
Application entry point.

Operational Package Validator

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from config import (
    APP_NAME,
    APP_VERSION,
    ICON_PATH,
    ORGANIZATION_NAME,
    STYLESHEET_PATH,
)
from gui.main_window import MainWindow
from services.logger import LoggerService


def load_stylesheet(
    app: QApplication,
) -> None:
    """
    Load the global application stylesheet.
    """

    stylesheet = (
        Path(__file__).parent / STYLESHEET_PATH
    )

    if stylesheet.exists():

        app.setStyleSheet(
            stylesheet.read_text(
                encoding="utf-8"
            )
        )


def load_icon(
    app: QApplication,
) -> None:
    """
    Load application icon if available.
    """

    icon = (
        Path(__file__).parent / ICON_PATH
    )

    if icon.exists():

        app.setWindowIcon(
            QIcon(str(icon))
        )


def main() -> int:
    """
    Application entry point.
    """

    LoggerService.configure()

    app = QApplication(sys.argv)

    app.setStyle("Fusion")
    app.setApplicationName(
        APP_NAME
    )

    app.setApplicationVersion(
        APP_VERSION
    )

    app.setOrganizationName(
        ORGANIZATION_NAME
    )

    load_stylesheet(app)

    load_icon(app)

    window = MainWindow()

    window.show()

    return app.exec()


if __name__ == "__main__":

    sys.exit(main())