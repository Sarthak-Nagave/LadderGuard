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

from config import DEFAULT_OUTPUT_FILENAME
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QTableWidgetItem,
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
        self._groups: list[tuple[Path, list]] = []
        self._current_group_index: int = 0

        # Standard PySide6 UI setup
        self.ui = Ui_ChronologyDialog()
        self.ui.setupUi(self)

        self._configure_ui()
        self._connect_signals()
        self._run_initial_scan()

    def _configure_ui(self) -> None:
        """
        Configures the initial state of the table headers and combo boxes.
        """
        self.setWindowTitle("Generate Ladder Chronology")
        self.resize(900, 600)

        # Set project folder path in the read-only field
        if hasattr(self.ui, "line_project_folder"):
            self.ui.line_project_folder.setText(str(self._project_folder))

        # Configure Table
        headers = [
            "BIN File", 
            "Version", 
            "PLC Model", 
            "CRC", 
            "Testing Stage", 
            "Reason For Upgrade"
        ]
        self.ui.table_chronology.setColumnCount(len(headers))
        self.ui.table_chronology.setHorizontalHeaderLabels(headers)
        self.ui.table_chronology.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Configure ComboBoxes
        combo_options = ["Select...", "Yes", "No"]
        
        self.ui.combo_ladder_release.clear()
        self.ui.combo_ladder_release.addItems(combo_options)
        
        self.ui.combo_operator_modification.clear()
        self.ui.combo_operator_modification.addItems(combo_options)
        
        self.ui.combo_automation_modification.clear()
        self.ui.combo_automation_modification.addItems(combo_options)
        
        # Hide output file UI elements since paths are now automatic
        if hasattr(self.ui, "lbl_output_file"):
            self.ui.lbl_output_file.hide()
        if hasattr(self.ui, "line_output_file"):
            self.ui.line_output_file.hide()
        if hasattr(self.ui, "btn_browse_output"):
            self.ui.btn_browse_output.hide()

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
            
            # Setup groups for the wizard
            self._groups = list(self._chronology.group_by_firmware_folder().items())
            self._current_group_index = 0
            
            if self._groups:
                self._load_current_group()
            else:
                self._populate_table([])
            
        except Exception as exc:
            self._logger.exception("Failed to run initial chronology scan.")
            QMessageBox.critical(self, "Scan Error", f"Failed to scan project:\n{exc}")

    def _load_current_group(self) -> None:
        """
        Loads the UI state for the current firmware group in the wizard flow.
        """
        if not self._groups:
            return
            
        folder, entries = self._groups[self._current_group_index]
        
        # Clear inputs for the new group
        self.ui.line_released_by.clear()
        self.ui.line_tested_by.clear()
        self.ui.combo_ladder_release.setCurrentIndex(0)
        self.ui.combo_operator_modification.setCurrentIndex(0)
        self.ui.combo_automation_modification.setCurrentIndex(0)
        
        # Update labels and button text
        total = len(self._groups)
        current = self._current_group_index + 1
        folder_name = folder.relative_to(self._project_folder) if self._project_folder in folder.parents else folder.name
        self.ui.grp_firmware_entries.setTitle(f"Detected Firmware Entries - Group {current}/{total} ({folder_name})")
        
        if self._current_group_index < total - 1:
            self.ui.btn_generate.setText("Next Group")
        else:
            self.ui.btn_generate.setText("Generate Excel")
            
        self._populate_table(entries)

    def _populate_table(self, entries: list) -> None:
        """
        Populates the QTableWidget with the provided chronology entries.
        """
        self.ui.table_chronology.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            # Read-only items
            item_bin = QTableWidgetItem(entry.bin_file_name or "")
            item_bin.setFlags(item_bin.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_version = QTableWidgetItem(entry.version or "")
            item_version.setFlags(item_version.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_model = QTableWidgetItem(entry.plc_model or "")
            item_model.setFlags(item_model.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_crc = QTableWidgetItem(str(entry.crc))
            item_crc.setFlags(item_crc.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_stage = QTableWidgetItem(entry.testing_stage or "")
            item_stage.setFlags(item_stage.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Editable item
            item_reason = QTableWidgetItem(entry.reason_for_upgrade or "")
            # Default flags include ItemIsEditable

            self.ui.table_chronology.setItem(row, 0, item_bin)
            self.ui.table_chronology.setItem(row, 1, item_version)
            self.ui.table_chronology.setItem(row, 2, item_model)
            self.ui.table_chronology.setItem(row, 3, item_crc)
            self.ui.table_chronology.setItem(row, 4, item_stage)
            self.ui.table_chronology.setItem(row, 5, item_reason)

    def _on_browse_template_clicked(self) -> None:
        """
        Opens file dialog to select the template and updates the UI line edit.
        """
        path = self._select_template_file()
        if path and hasattr(self.ui, "line_excel_template"):
            self.ui.line_excel_template.setText(str(path))

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
        
        # Advance wizard if more groups remain
        if self._current_group_index < len(self._groups) - 1:
            self._current_group_index += 1
            self._load_current_group()
            return

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
        if not self.ui.line_released_by.text().strip():
            QMessageBox.warning(self, "Validation Error", "'Released By' cannot be empty.")
            self.ui.line_released_by.setFocus()
            return False

        if not self.ui.line_tested_by.text().strip():
            QMessageBox.warning(self, "Validation Error", "'Tested By' cannot be empty.")
            self.ui.line_tested_by.setFocus()
            return False

        if self.ui.combo_ladder_release.currentText() == "Select...":
            QMessageBox.warning(self, "Validation Error", "Please select an option for 'Ladder Release To Production'.")
            self.ui.combo_ladder_release.setFocus()
            return False

        if self.ui.combo_operator_modification.currentText() == "Select...":
            QMessageBox.warning(self, "Validation Error", "Please select an option for 'Operator Procedure Modification'.")
            self.ui.combo_operator_modification.setFocus()
            return False

        if self.ui.combo_automation_modification.currentText() == "Select...":
            QMessageBox.warning(self, "Validation Error", "Please select an option for 'Automation Set Up Modification'.")
            self.ui.combo_automation_modification.setFocus()
            return False

        # Validate that paths are selected if the user didn't use the browse buttons yet
        if hasattr(self.ui, "line_excel_template") and not self.ui.line_excel_template.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please select an Excel Template.")
            self.ui.btn_browse_template.setFocus()
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
        """
        Transfers the user-entered data from the UI into the underlying
        ChronologyEntry models.
        """
        if not self._chronology:
            return

        released_by = self.ui.line_released_by.text().strip()
        tested_by = self.ui.line_tested_by.text().strip()
        ladder_release = self.ui.combo_ladder_release.currentText()
        operator_mod = self.ui.combo_operator_modification.currentText()
        automation_mod = self.ui.combo_automation_modification.currentText()

        # Update only the entries in the current group
        if not self._groups:
            return
            
        entries = self._groups[self._current_group_index][1]

        for row, entry in enumerate(entries):
            # Capture the potentially edited reason for upgrade directly from the table
            reason_item = self.ui.table_chronology.item(row, 5)
            if reason_item:
                entry.reason_for_upgrade = reason_item.text().strip()

            # Apply global metadata to every entry
            entry.released_by = released_by
            entry.tested_by = tested_by
            entry.ladder_release_to_production = ladder_release
            entry.operator_procedure_modification = operator_mod
            entry.automation_setup_modification = automation_mod