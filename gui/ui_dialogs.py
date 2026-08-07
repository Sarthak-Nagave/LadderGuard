from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _accent_color(variant: str) -> str:
    mapping = {
        "success": "#2E7D32",
        "error": "#D32F2F",
        "warning": "#F9A825",
        "info": "#1976D2",
    }
    return mapping.get(variant, "#1976D2")


def _accent_icon(variant: str) -> str:
    mapping = {
        "success": "\u2714",
        "error": "\u2716",
        "warning": "\u26A0",
        "info": "\u2139",
    }
    return mapping.get(variant, "\u2139")


def show_styled_message(parent: QWidget, title: str, message: str, variant: str = "info") -> None:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    dlg.setMinimumWidth(380)
    dlg.setMaximumWidth(560)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(16, 14, 16, 12)
    root.setSpacing(6)

    header = QHBoxLayout()
    header.setSpacing(8)
    icon = QLabel(_accent_icon(variant))
    icon.setStyleSheet(f"color: {_accent_color(variant)}; font-size: 18px; background: transparent;")
    icon.setFixedWidth(24)
    heading = QLabel(title)
    heading.setStyleSheet("font-family: 'Segoe UI'; font-size: 13px; font-weight: 700; color: #202124; background: transparent;")
    header.addWidget(icon)
    header.addWidget(heading, 1)
    root.addLayout(header)

    body = QLabel(message)
    body.setWordWrap(True)
    body.setStyleSheet("font-family: 'Segoe UI'; color: #616161; font-size: 10pt; background: transparent; padding-left: 32px;")
    root.addWidget(body)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    buttons.accepted.connect(dlg.accept)
    root.addWidget(buttons, 0, Qt.AlignRight)

    dlg.adjustSize()
    dlg.setFixedSize(dlg.sizeHint())
    dlg.exec()


def show_action_dialog(
    parent: QWidget,
    title: str,
    subtitle: str,
    description: str,
    accent: str,
    actions: list[tuple[str, str]],
) -> str:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    dlg.setMinimumWidth(400)
    dlg.setMaximumWidth(600)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(16, 14, 16, 12)
    root.setSpacing(6)

    header = QHBoxLayout()
    header.setSpacing(8)
    icon = QLabel(_accent_icon(accent))
    icon.setStyleSheet(f"color: {_accent_color(accent)}; font-size: 18px; background: transparent;")
    icon.setFixedWidth(24)
    title_label = QLabel(subtitle)
    title_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 13px; font-weight: 700; color: #202124; background: transparent;")
    header.addWidget(icon)
    header.addWidget(title_label, 1)
    root.addLayout(header)

    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    desc_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 10pt; color: #616161; background: transparent; padding-left: 32px;")
    root.addWidget(desc_label)

    action_layout = QHBoxLayout()
    action_layout.setSpacing(8)
    action_layout.addStretch(1)

    result = {"value": ""}

    for text, value in actions:
        button = QPushButton(text)
        button.setMinimumWidth(96)
        button.setMinimumHeight(32)

        def _on_click(checked: bool = False, selected: str = value) -> None:
            result["value"] = selected
            dlg.accept()

        button.clicked.connect(_on_click)
        action_layout.addWidget(button)

    root.addLayout(action_layout)
    dlg.adjustSize()
    dlg.setFixedSize(dlg.sizeHint())
    dlg.exec()
    return result["value"]
