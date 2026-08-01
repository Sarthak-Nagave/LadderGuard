"""
gui.chronology.chronology_dialog
================================

User interface dialog for generating the Ladder Chronology Excel report.

This module provides the frontend integration for the ChronologyGenerator,
allowing users to review scanned firmware entries, provide mandatory 
metadata, and export the final report.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import DEFAULT_OUTPUT_FILENAME
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QScrollArea,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from services.chronology_generator.exceptions import ChronologyGenerationError
from services.chronology_generator.generator import ChronologyGenerator
from services.chronology_generator.models import ProjectChronology

from .ui_chronology_dialog import Ui_ChronologyDialog


class ChronologyDialog(QDialog):
    """
    Dialog for configuring and generating the Project Chronology report.
    """

    def __init__(self, project_folder: Path, parent: QWidget | None = None) -> None:
        """
        Initialize the chronology dialog.

        Args:
            project_folder: The root path of the project being evaluated.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self._project_folder = project_folder
        self._logger = logging.getLogger(__name__)
        self._chronology: ProjectChronology | None = None
        self._groups: list[tuple[Path, list[Any]]] = []
        self._entry_cards: list[dict[str, Any]] = []
        self._cards_scroll_area: QScrollArea | None = None
        self._cards_container: QWidget | None = None
        self._cards_layout: QVBoxLayout | None = None

        # Standard PySide6 UI setup
        self.ui = Ui_ChronologyDialog()
        self.ui.setupUi(self)

        self._configure_ui()
        self._connect_signals()
        self._run_initial_scan()

    def _configure_ui(self) -> None:
        """
        Configures the base dialog layout and dynamic cards container.
        """
        self.setWindowTitle("Generate Ladder Chronology")
        self.resize(900, 600)

        # Set project folder path in the read-only field
        if hasattr(self.ui, "line_project_folder"):
            self.ui.line_project_folder.setText(str(self._project_folder))

        # Hide output file UI elements since paths are now automatic
        if hasattr(self.ui, "lbl_output_file"):
            self.ui.lbl_output_file.hide()
        if hasattr(self.ui, "line_output_file"):
            self.ui.line_output_file.hide()
        if hasattr(self.ui, "btn_browse_output"):
            self.ui.btn_browse_output.hide()

        # Release information is now rendered per firmware folder card.
        if hasattr(self.ui, "grp_release_info"):
            self.ui.grp_release_info.hide()

        # The legacy table is replaced by dynamic cards.
        if hasattr(self.ui, "table_chronology"):
            self.ui.table_chronology.hide()

        self._setup_dynamic_cards_area()
        self.ui.btn_generate.setEnabled(False)

    def _setup_dynamic_cards_area(self) -> None:
        if self._cards_scroll_area is not None:
            return

        self._cards_scroll_area = QScrollArea(self)
        self._cards_scroll_area.setWidgetResizable(True)

        self._cards_container = QWidget(self._cards_scroll_area)
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch(1)

        self._cards_scroll_area.setWidget(self._cards_container)
        self.ui.verticalLayoutFirmware.addWidget(self._cards_scroll_area)

    def _connect_signals(self) -> None:
        """
        Connects UI signals to their respective slots.
        """
        self.ui.btn_generate.clicked.connect(self._on_generate_clicked)
        self.ui.btn_cancel.clicked.connect(self.reject)
        
        # Connect browse buttons introduced in the new .ui
        if hasattr(self.ui, "btn_browse_template"):
            self.ui.btn_browse_template.clicked.connect(self._on_browse_template_clicked)
        if hasattr(self.ui, "btn_browse_output"):
            self.ui.btn_browse_output.clicked.connect(self._on_browse_output_clicked)

    def _run_initial_scan(self) -> None:
        """
        Executes the initial project scan to discover chronology entries
        and populates the table.
        """
        try:
            # We supply a dummy template path for the initial scan since 
            # the generator requires it in the constructor.
            dummy_template = Path("dummy.xlsx")
            generator = ChronologyGenerator(self._project_folder, dummy_template)
            
            self._chronology = generator.scan_project()
            
            # Setup groups for dynamic card generation
            self._groups = list(self._chronology.group_by_firmware_folder().items())
            self._build_dynamic_cards()
            self._update_generate_button_state()
            
        except Exception as exc:
            self._logger.exception("Failed to run initial chronology scan.")
            QMessageBox.critical(self, "Scan Error", f"Failed to scan project:\n{exc}")

    def _build_dynamic_cards(self) -> None:
        if self._cards_layout is None:
            return

        self._entry_cards.clear()

        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, (folder, entries) in enumerate(self._groups, start=1):
            if not entries:
                continue

            entry = entries[0]
            card = self._create_card(index, folder, entry)
            self._entry_cards.append(card)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card["group_box"])

        self.ui.grp_firmware_entries.setTitle(f"Detected Firmware Entries ({len(self._entry_cards)} card(s))")

    def _create_card(self, index: int, folder: Path, entry: Any) -> dict[str, Any]:
        card_box = QGroupBox(f"Chronology {index}", self._cards_container)
        form = QFormLayout(card_box)
        form.setContentsMargins(10, 10, 10, 10)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        firmware_folder_value = self._format_firmware_folder(folder)
        line_firmware_folder = self._read_only_line(firmware_folder_value)
        line_bin = self._read_only_line(entry.bin_file_name)
        line_version = self._read_only_line(entry.version)
        line_plc = self._read_only_line(entry.plc_model)
        line_bootloader = self._read_only_line(entry.bootloader_version or "")
        line_stage = self._read_only_line(entry.testing_stage)
        line_source_path = self._read_only_line(str(entry.source_code_path))

        line_reason = QLineEdit(card_box)
        line_released_by = QLineEdit(card_box)
        line_tested_by = QLineEdit(card_box)
        line_selpro_version = QLineEdit(card_box)
        line_selpro_path = QLineEdit(card_box)
        combo_ladder_release = self._yes_no_combo(card_box)
        combo_operator_modification = self._yes_no_combo(card_box)
        combo_automation_modification = self._yes_no_combo(card_box)

        form.addRow("Firmware Folder:", line_firmware_folder)
        form.addRow("BIN File Name:", line_bin)
        form.addRow("Version:", line_version)
        form.addRow("PLC Model:", line_plc)
        form.addRow("Bootloader Version:", line_bootloader)
        form.addRow("Testing Stage:", line_stage)
        form.addRow("Source Code Path:", line_source_path)

        form.addRow("Reason for Upgrade:", line_reason)
        form.addRow("Released By:", line_released_by)
        form.addRow("Tested By:", line_tested_by)
        form.addRow("Selpro Version:", line_selpro_version)
        form.addRow("Selpro Path:", line_selpro_path)
        form.addRow("Ladder Release To Production:", combo_ladder_release)
        form.addRow("Operator Procedure Modification:", combo_operator_modification)
        form.addRow("Automation Set Up Modification:", combo_automation_modification)

        line_reason.textChanged.connect(self._update_generate_button_state)
        line_released_by.textChanged.connect(self._update_generate_button_state)
        line_tested_by.textChanged.connect(self._update_generate_button_state)
        combo_ladder_release.currentTextChanged.connect(self._update_generate_button_state)
        combo_operator_modification.currentTextChanged.connect(self._update_generate_button_state)
        combo_automation_modification.currentTextChanged.connect(self._update_generate_button_state)

        return {
            "group_box": card_box,
            "folder": folder,
            "entry": entry,
            "line_firmware_folder": line_firmware_folder,
            "line_source_path": line_source_path,
            "line_reason": line_reason,
            "line_released_by": line_released_by,
            "line_tested_by": line_tested_by,
            "line_selpro_version": line_selpro_version,
            "line_selpro_path": line_selpro_path,
            "combo_ladder_release": combo_ladder_release,
            "combo_operator_modification": combo_operator_modification,
            "combo_automation_modification": combo_automation_modification,
        }

    def _format_firmware_folder(self, folder: Path) -> str:
        try:
            rel = folder.resolve().relative_to(self._project_folder.resolve())
            rel_text = rel.as_posix()
            if rel_text.startswith("2. Bin File/"):
                return rel_text[len("2. Bin File/") :]
            return rel_text
        except Exception:
            return folder.as_posix()

    @staticmethod
    def _read_only_line(value: str) -> QLineEdit:
        line = QLineEdit()
        line.setText(value)
        line.setReadOnly(True)
        line.setCursorPosition(0)
        return line

    @staticmethod
    def _yes_no_combo(parent: QWidget) -> QComboBox:
        combo = QComboBox(parent)
        combo.addItems(["Select...", "Yes", "No"])
        return combo

    def _update_generate_button_state(self) -> None:
        template_ready = bool(self.ui.line_excel_template.text().strip())
        card_ready = bool(self._entry_cards)

        for card in self._entry_cards:
            if not card["line_reason"].text().strip():
                card_ready = False
                break
            if not card["line_released_by"].text().strip():
                card_ready = False
                break
            if not card["line_tested_by"].text().strip():
                card_ready = False
                break
            if card["combo_ladder_release"].currentText() == "Select...":
                card_ready = False
                break
            if card["combo_operator_modification"].currentText() == "Select...":
                card_ready = False
                break
            if card["combo_automation_modification"].currentText() == "Select...":
                card_ready = False
                break

        self.ui.btn_generate.setEnabled(template_ready and card_ready)

    def _on_browse_template_clicked(self) -> None:
        """
        Opens file dialog to select the template and updates the UI line edit.
        """
        path = self._select_template_file()
        if path and hasattr(self.ui, "line_excel_template"):
            self.ui.line_excel_template.setText(str(path))
            self._update_generate_button_state()

    def _on_browse_output_clicked(self) -> None:
        """
        Opens file dialog to select the output destination and updates the UI line edit.
        """
        path = self._select_output_file()
        if path and hasattr(self.ui, "line_output_file"):
            self.ui.line_output_file.setText(str(path))

    def _on_generate_clicked(self) -> None:
        """
        Handles the generate/next button click. Validates inputs, updates the 
        current group's models, and advances the wizard or finishes generation.
        """
        if not self._validate_inputs():
            return

        self._update_chronology_models()

        # Fetch template path
        if hasattr(self.ui, "line_excel_template") and self.ui.line_excel_template.text().strip():
            template_path = Path(self.ui.line_excel_template.text().strip())
        else:
            template_path = self._select_template_file()
            if not template_path:
                return

        try:
            generator = ChronologyGenerator(self._project_folder, template_path)
            
            # Monkey-patch the scan_project method to inject our updated, user-edited 
            # chronology model instead of re-scanning and wiping the inputs.
            generator.scan_project = lambda: self._chronology
            
            generator.generate(output_path=None)
            
            QMessageBox.information(
                self, 
                "Success", 
                "Chronology Excel report(s) generated successfully."
            )
            self.accept()
            
        except ChronologyGenerationError as exc:
            self._logger.error(f"Chronology generation failed: {exc}")
            QMessageBox.critical(self, "Generation Error", str(exc))
        except Exception as exc:
            self._logger.exception("Unexpected error during chronology generation.")
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred:\n{exc}")

    def _validate_inputs(self) -> bool:
        """
        Validates the user input fields.

        Returns:
            True if all inputs are valid, False otherwise.
        """
        if not self._entry_cards:
            QMessageBox.warning(self, "Validation Error", "No firmware folders with BIN files were discovered.")
            return False

        if hasattr(self.ui, "line_excel_template") and not self.ui.line_excel_template.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please select an Excel Template.")
            self.ui.btn_browse_template.setFocus()
            return False

        for index, card in enumerate(self._entry_cards, start=1):
            if not card["line_reason"].text().strip():
                QMessageBox.warning(self, "Validation Error", f"Chronology {index}: 'Reason for Upgrade' cannot be empty.")
                card["line_reason"].setFocus()
                return False
            if not card["line_released_by"].text().strip():
                QMessageBox.warning(self, "Validation Error", f"Chronology {index}: 'Released By' cannot be empty.")
                card["line_released_by"].setFocus()
                return False
            if not card["line_tested_by"].text().strip():
                QMessageBox.warning(self, "Validation Error", f"Chronology {index}: 'Tested By' cannot be empty.")
                card["line_tested_by"].setFocus()
                return False
            if card["combo_ladder_release"].currentText() == "Select...":
                QMessageBox.warning(self, "Validation Error", f"Chronology {index}: select 'Ladder Release To Production'.")
                card["combo_ladder_release"].setFocus()
                return False
            if card["combo_operator_modification"].currentText() == "Select...":
                QMessageBox.warning(self, "Validation Error", f"Chronology {index}: select 'Operator Procedure Modification'.")
                card["combo_operator_modification"].setFocus()
                return False
            if card["combo_automation_modification"].currentText() == "Select...":
                QMessageBox.warning(self, "Validation Error", f"Chronology {index}: select 'Automation Set Up Modification'.")
                card["combo_automation_modification"].setFocus()
                return False

        return True

    def _select_template_file(self) -> Path | None:
        """
        Opens a file dialog to select the chronology template.

        Returns:
            The selected Path, or None if cancelled.
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Chronology Excel Template",
            str(self._project_folder),
            "Excel Files (*.xlsx *.xlsm)"
        )
        return Path(filepath) if filepath else None

    def _select_output_file(self) -> Path | None:
        """
        Opens a file dialog to specify the output destination.

        Returns:
            The selected Path, or None if cancelled.
        """
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Chronology Report",
            str(self._project_folder / DEFAULT_OUTPUT_FILENAME),
            "Excel Files (*.xlsx)"
        )
        return Path(filepath) if filepath else None

    def _update_chronology_models(self) -> None:
        if not self._chronology:
            return

        for card in self._entry_cards:
            entry = card["entry"]
            reason = card["line_reason"].text().strip()
            released_by = card["line_released_by"].text().strip()
            tested_by = card["line_tested_by"].text().strip()
            selpro_version = card["line_selpro_version"].text().strip()
            selpro_path = card["line_selpro_path"].text().strip()

            ladder_release = card["combo_ladder_release"].currentText()
            operator_mod = card["combo_operator_modification"].currentText()
            automation_mod = card["combo_automation_modification"].currentText()

            entry.reason_for_upgrade = reason
            entry.released_by = released_by
            entry.tested_by = tested_by
            entry.selpro_version = f"{selpro_version} {selpro_path}".strip()
            entry.ladder_release_to_production = ladder_release if ladder_release != "Select..." else ""
            entry.operator_procedure_modification = operator_mod if operator_mod != "Select..." else ""
            entry.automation_setup_modification = automation_mod if automation_mod != "Select..." else ""