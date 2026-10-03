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
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, QCoreApplication

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from config import DEFAULT_OUTPUT_FILENAME, FOLDER_KEYS, GUI_MESSAGES
from services.chronology_generator.excel_writer import (
    ChronologyExcelWriter,
    ChronologyTemplateError,
)
from services.chronology_generator.models import ChronologyEntry, ProjectChronology
from services.chronology_generator.parsers import FilenameParser
from gui.ui_dialogs import show_action_dialog, show_styled_message

from .ui_chronology_dialog import Ui_ChronologyDialog


class ChronologyWorker(QObject):
    """
    Executes chronology generation (Excel/PDF) in a background thread.
    """
    # Signals to communicate with the GUI thread
    # target_path, pdf_path, pdf_succeeded, export_message
    finished = Signal(Path, Path, bool, str)
    failed = Signal(str)

    def __init__(
        self,
        chronology: ProjectChronology,
        template_path: Path,
        target_path: Path,
    ) -> None:
        super().__init__()
        self._chronology = chronology
        self._template_path = template_path
        self._target_path = target_path

    def run(self) -> None:
        try:
            writer = ChronologyExcelWriter(self._template_path)
            writer.write(self._chronology, self._target_path)

            pdf_path = writer.last_pdf_path or self._target_path.with_suffix(".pdf")
            pdf_succeeded = writer.last_pdf_export_succeeded
            export_message = writer.last_pdf_export_message or ""

            self.finished.emit(self._target_path, pdf_path, pdf_succeeded, export_message)
        except Exception as error:
            import traceback
            traceback.print_exc()
            self.failed.emit(str(error))


class ChronologyDialog(QDialog):
    """
    Dialog for configuring and generating the Project Chronology report.
    """

    def __init__(
        self,
        project_folder: Path,
        parent: QWidget | None = None,
        validation_bin_crc_records: dict[str, dict[str, Any]] | None = None,
    ) -> None:
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
        self._combo_type: QComboBox | None = None
        self._combo_stage: QComboBox | None = None
        self._stacked_cards: QStackedWidget | None = None
        self._card_map: dict[str, dict[str, Any]] = {}
        self._validation_bin_crc_records = validation_bin_crc_records or {}
        self._skipped_firmware: list[dict[str, str]] = []

        self._chronology_thread: QThread | None = None
        self._chronology_worker: ChronologyWorker | None = None

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
        self.setWindowTitle(GUI_MESSAGES.get("chronology_window_title", "Generate Ladder Chronology"))
        self.resize(900, 600)

        # Set project folder path in the read-only field
        if hasattr(self.ui, "line_project_folder"):
            self.ui.line_project_folder.setText(str(self._project_folder))

        # The legacy single-template control is no longer part of the workflow.
        if hasattr(self.ui, "lbl_excel_template"):
            self.ui.lbl_excel_template.hide()
        if hasattr(self.ui, "line_excel_template"):
            self.ui.line_excel_template.hide()
        if hasattr(self.ui, "btn_browse_template"):
            self.ui.btn_browse_template.hide()

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
        self._cards_layout.setContentsMargins(10, 10, 10, 10)
        self._cards_layout.setSpacing(12)

        # Dropdowns Layout
        dropdown_layout = QHBoxLayout()
        dropdown_layout.addWidget(QLabel("Testing Type:"))
        self._combo_type = QComboBox()
        dropdown_layout.addWidget(self._combo_type)
        dropdown_layout.addWidget(QLabel("Testing Stage:"))
        self._combo_stage = QComboBox()
        dropdown_layout.addWidget(self._combo_stage)
        dropdown_layout.addStretch(1)
        self._cards_layout.addLayout(dropdown_layout)

        # Stacked Widget for Cards
        self._stacked_cards = QStackedWidget()
        self._cards_layout.addWidget(self._stacked_cards)
        
        self._cards_layout.addStretch(1)

        self._cards_scroll_area.setWidget(self._cards_container)
        self.ui.verticalLayoutFirmware.addWidget(self._cards_scroll_area)
        
        self._combo_type.currentTextChanged.connect(self._on_type_changed)
        self._combo_stage.currentTextChanged.connect(self._on_stage_changed)

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
        Builds chronology cards from validated firmware folders.
        """
        try:
            self._chronology = ProjectChronology(project_root=self._project_folder)
            self._skipped_firmware.clear()

            for relative_path, crc_record in sorted(self._validation_bin_crc_records.items()):
                if not isinstance(crc_record, dict):
                    continue

                status = str(crc_record.get("status") or "").upper()
                if status != "PASS":
                    self._skipped_firmware.append(
                        {
                            "firmware_folder": self._format_firmware_folder(Path(relative_path)),
                            "reason": str(crc_record.get("reason") or "CRC Mismatch"),
                        }
                    )
                    continue

                entry = self._build_entry_from_validation_record(relative_path, crc_record)
                if entry is None:
                    self._skipped_firmware.append(
                        {
                            "firmware_folder": self._format_firmware_folder(Path(relative_path)),
                            "reason": "Invalid validation record.",
                        }
                    )
                    continue

                self._chronology.add_entry(entry)

            self._groups = list(self._chronology.group_by_firmware_folder().items())
            self._build_dynamic_cards()
            self._update_generate_button_state()
            
        except Exception as exc:
            self._logger.exception("Failed to run initial chronology scan.")
            self._show_error(GUI_MESSAGES.get("scan_error", "Scan Error"), f"Failed to scan project:\n{exc}")

    def _build_entry_from_validation_record(self, relative_path: str, crc_record: dict[str, Any]) -> ChronologyEntry | None:
        selected_bin_file = crc_record.get("bin_file")
        selected_bin_name = crc_record.get("bin_name")
        selected_bin_crc = str(
            crc_record.get("bin_crc")
            or crc_record.get("crc")
            or crc_record.get("ladder_crc")
            or ""
        )

        if not isinstance(selected_bin_file, str) or not selected_bin_file.strip():
            return None

        selected_bin_path = Path(selected_bin_file)
        try:
            selected_bin_path = selected_bin_path.resolve()
        except Exception:
            pass

        bin_name = selected_bin_name or selected_bin_path.name

        try:
            version = FilenameParser.extract_version(bin_name)
        except Exception:
            version = "Unknown"

        try:
            plc_model = FilenameParser.extract_plc_model(bin_name)
        except Exception:
            plc_model = "Unknown"

        try:
            bootloader_version = FilenameParser.extract_bootloader_version(bin_name)
        except Exception:
            bootloader_version = ""

        test_report_path = self._find_signed_test_report_for_relative_path(relative_path)

        return ChronologyEntry(
            source_code_path=selected_bin_path,
            bin_file_path=selected_bin_path,
            sdoc_file_path=None,
            bin_file_name=bin_name,
            sdoc_file_name=None,
            version=version,
            plc_model=plc_model,
            selpro_version="",
            bootloader_version=bootloader_version,
            crc=selected_bin_crc,
            testing_stage=relative_path.replace("/", " "),
            release_date="",
            reason_for_upgrade="",
            test_report_path=test_report_path,
        )

    def _find_signed_test_report_for_relative_path(self, relative_path: str) -> Path | None:
        """Resolve signed test report for a firmware path key like Master/Initial."""
        report_root = self._project_folder / FOLDER_KEYS.get("test_report", "4. Test Report")
        stage_path = report_root / Path(relative_path)
        if stage_path.exists():
            matches = sorted(stage_path.glob("*-sgn.pdf"))
            if matches:
                return matches[0]

        # Backward-compatible fallback: allow one-level stage folders.
        flat_stage = report_root / Path(relative_path).parts[0]
        if flat_stage.exists():
            matches = sorted(flat_stage.glob("*-sgn.pdf"))
            if matches:
                return matches[0]

        return None

    def _build_dynamic_cards(self) -> None:
        if self._stacked_cards is None:
            return

        self._entry_cards.clear()
        self._card_map.clear()

        while self._stacked_cards.count() > 0:
            widget = self._stacked_cards.widget(0)
            self._stacked_cards.removeWidget(widget)
            widget.deleteLater()

        types = set()
        
        for index, (folder, entries) in enumerate(self._groups, start=1):
            for relative_path, crc_record in sorted(self._validation_bin_crc_records.items()):
                continue

            entry = entries[0]
            card = self._create_card(index, folder, entry)
            self._entry_cards.append(card)
            self._stacked_cards.addWidget(card["group_box"])
            
            fw_folder_str = self._format_firmware_folder(folder)
            self._card_map[fw_folder_str] = card
            t, _ = self._split_fw_key(fw_folder_str)
            types.add(t)

        self.ui.grp_firmware_entries.setTitle("Detected Firmware Entries")
        
        self._combo_type.blockSignals(True)
        self._combo_type.clear()
        self._combo_type.addItems(sorted(list(types)))
        self._combo_type.blockSignals(False)
        
        if self._combo_type.count() > 0:
            self._on_type_changed(self._combo_type.currentText())
    def _on_type_changed(self, fw_type: str) -> None:
        if not self._combo_stage:
            return
        self._combo_stage.blockSignals(True)
        self._combo_stage.clear()
        
        stages = []
        for key in self._card_map:
            t, s = self._split_fw_key(key)
            if t == fw_type and s not in stages:
                stages.append(s)
                
        self._combo_stage.addItems(sorted(stages))
        self._combo_stage.blockSignals(False)
        if stages:
            self._on_stage_changed(self._combo_stage.currentText())

    def _on_stage_changed(self, fw_stage: str) -> None:
        fw_type = self._combo_type.currentText()
        if not fw_type:
            return
            
        key = f"{fw_type}/{fw_stage}" if fw_stage and fw_stage != "(Root)" else fw_type
        if key in self._card_map:
            card = self._card_map[key]
            self._stacked_cards.setCurrentWidget(card["group_box"])
        self._update_generate_button_state()
        
    def _split_fw_key(self, key: str) -> tuple[str, str]:
        parts = key.split("/")
        if len(parts) == 1:
            return parts[0], "(Root)"
        return parts[0], "/".join(parts[1:])


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
        
        line_source_path = QLineEdit(card_box)
        line_source_path.setText("")
        
        source_widget = QWidget(card_box)
        source_layout = QHBoxLayout(source_widget)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(6)
        source_layout.addWidget(line_source_path)
        btn_browse_source = QPushButton("Browse...", card_box)
        source_layout.addWidget(btn_browse_source)

        line_template_path = self._read_only_line("")

        template_widget = QWidget(card_box)
        template_layout = QHBoxLayout(template_widget)
        template_layout.setContentsMargins(0, 0, 0, 0)
        template_layout.setSpacing(6)
        template_layout.addWidget(line_template_path)

        btn_browse_template = QPushButton("Browse Template", card_box)
        template_layout.addWidget(btn_browse_template)

        line_reason = QLineEdit(card_box)
        line_released_by = QLineEdit(card_box)
        line_tested_by = QLineEdit(card_box)
        line_selpro_version = QLineEdit(card_box)
        line_selpro_path = QLineEdit(card_box)
        combo_ladder_release = self._yes_no_combo(card_box)
        combo_operator_modification = self._yes_no_combo(card_box)
        combo_automation_modification = self._yes_no_combo(card_box)
        combo_prepared_by = self._personnel_combo(card_box)
        combo_checked_by = self._personnel_combo(card_box)
        combo_approved_by = self._personnel_combo(card_box)

        form.addRow("Folder:", line_firmware_folder)
        form.addRow("BIN File Name:", line_bin)
        form.addRow("Version:", line_version)
        form.addRow("PLC Model:", line_plc)
        form.addRow("Bootloader Version:", line_bootloader)
        form.addRow("Testing Stage:", line_stage)
        form.addRow("Source Code Path:", source_widget)
        form.addRow("Chronology Template:", template_widget)

        form.addRow("Reason for Upgrade:", line_reason)
        form.addRow("Released By:", line_released_by)
        form.addRow("Tested By:", line_tested_by)
        form.addRow("Selpro Version:", line_selpro_version)
        form.addRow("Selpro Path:", line_selpro_path)
        form.addRow("Ladder Release To Production:", combo_ladder_release)
        form.addRow("Operator Procedure Modification:", combo_operator_modification)
        form.addRow("Automation Set Up Modification:", combo_automation_modification)
        form.addRow("Prepared By:", combo_prepared_by)
        form.addRow("Checked By:", combo_checked_by)
        form.addRow("Approved By:", combo_approved_by)

        line_reason.textChanged.connect(self._update_generate_button_state)
        line_released_by.textChanged.connect(self._update_generate_button_state)
        line_tested_by.textChanged.connect(self._update_generate_button_state)
        combo_ladder_release.currentTextChanged.connect(self._update_generate_button_state)
        combo_operator_modification.currentTextChanged.connect(self._update_generate_button_state)
        combo_automation_modification.currentTextChanged.connect(self._update_generate_button_state)
        combo_prepared_by.currentTextChanged.connect(self._update_generate_button_state)
        combo_checked_by.currentTextChanged.connect(self._update_generate_button_state)
        combo_approved_by.currentTextChanged.connect(self._update_generate_button_state)
        btn_browse_template.clicked.connect(lambda _checked=False, card=None: self._on_browse_template_clicked(card or card_data))
        btn_browse_source.clicked.connect(lambda _checked=False, card=None: self._on_browse_source_clicked(card or card_data))

        card_data = {
            "group_box": card_box,
            "folder": folder,
            "entry": entry,
            "line_firmware_folder": line_firmware_folder,
            "line_source_path": line_source_path,
            "line_template_path": line_template_path,
            "btn_browse_template": btn_browse_template,
            "line_reason": line_reason,
            "line_released_by": line_released_by,
            "line_tested_by": line_tested_by,
            "line_selpro_version": line_selpro_version,
            "line_selpro_path": line_selpro_path,
            "combo_ladder_release": combo_ladder_release,
            "combo_operator_modification": combo_operator_modification,
            "combo_automation_modification": combo_automation_modification,
            "combo_prepared_by": combo_prepared_by,
            "combo_checked_by": combo_checked_by,
            "combo_approved_by": combo_approved_by,
        }

        return card_data

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

    @staticmethod
    def _personnel_combo(parent: QWidget) -> QComboBox:
        combo = QComboBox(parent)
        combo.setEditable(True)
        combo.setPlaceholderText("Select or enter person")
        combo.addItems(["Select or enter person"])
        return combo

    def _update_generate_button_state(self) -> None:
        if not self._stacked_cards or self._stacked_cards.count() == 0:
            self.ui.btn_generate.setEnabled(False)
            return

        active_widget = self._stacked_cards.currentWidget()
        card_ready = False
        
        for card in self._entry_cards:
            if card["group_box"] == active_widget:
                card_ready = True
                if not card["line_reason"].text().strip():
                    card_ready = False
                if not card["line_released_by"].text().strip():
                    card_ready = False
                if not card["line_tested_by"].text().strip():
                    card_ready = False
                if card["combo_ladder_release"].currentText() == "Select...":
                    card_ready = False
                if card["combo_operator_modification"].currentText() == "Select...":
                    card_ready = False
                if card["combo_automation_modification"].currentText() == "Select...":
                    card_ready = False
                if not card["combo_prepared_by"].currentText().strip() or card["combo_prepared_by"].currentText() == "Select or enter person":
                    card_ready = False
                if not card["combo_checked_by"].currentText().strip() or card["combo_checked_by"].currentText() == "Select or enter person":
                    card_ready = False
                if not card["combo_approved_by"].currentText().strip() or card["combo_approved_by"].currentText() == "Select or enter person":
                    card_ready = False
                break

        self.ui.btn_generate.setEnabled(card_ready)

    def _on_browse_template_clicked(self, card: dict[str, Any] | None = None) -> None:
        """
        Opens file dialog to select the template and updates the matching line edit.
        """
        if card is None:
            path = self._select_template_file()
            if path and hasattr(self.ui, "line_excel_template"):
                self.ui.line_excel_template.setText(str(path))
                self._update_generate_button_state()
            return

        path = self._select_template_file_for_folder(card["line_firmware_folder"].text())
        if path is not None:
            card["line_template_path"].setText(str(path))
            self._update_generate_button_state()


    def _on_browse_source_clicked(self, card: dict[str, Any]) -> None:
        filepath = QFileDialog.getExistingDirectory(
            self,
            "Select Source Code Folder",
            str(self._project_folder)
        )
        if filepath:
            card["line_source_path"].setText(filepath)
    def _on_browse_output_clicked(self) -> None:
        """
        Opens file dialog to select the output destination and updates the UI line edit.
        """
        path = self._select_output_file()
        if path and hasattr(self.ui, "line_output_file"):
            self.ui.line_output_file.setText(str(path))

    def _on_generate_clicked(self) -> None:
        if self._chronology_thread is not None and self._chronology_thread.isRunning():
            return

        if not self._validate_inputs():
            return

        self._update_chronology_models()

        try:
            active_widget = self._stacked_cards.currentWidget()
            card = None
            for c in self._entry_cards:
                if c["group_box"] == active_widget:
                    card = c
                    break
            
            if not card:
                return

            entry = card["entry"]
            print("\n================================================")
            print("1.\nChronologyDialog._on_generate_clicked()\nentered\n")
            print(f"2.\nEntry selected\nFirmware: {entry.plc_model}\nStage: {entry.testing_stage}\n")
            print(f"3.\nentry.test_report_path: {entry.test_report_path}\n")

            target_path = self._resolve_chronology_output_path(entry.bin_file_path.parent)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if target_path.exists():
                template_path = target_path
            else:
                template_path = self._selected_template_path_for_card(card)
                if template_path is None:
                    self._show_warning(
                        GUI_MESSAGES.get("validation_error", "Validation Error"),
                        f"Please select a chronology template for\n{card['line_firmware_folder'].text()}",
                    )
                    return

            chronology = ProjectChronology(project_root=self._project_folder, entries=[entry])

            self.ui.btn_generate.setEnabled(False)
            self.ui.btn_generate.setText(QCoreApplication.translate("ChronologyDialog", "Generating...", None))

            self._chronology_thread = QThread(self)
            self._chronology_worker = ChronologyWorker(chronology, template_path, target_path)
            self._chronology_worker.moveToThread(self._chronology_thread)

            self._chronology_thread.started.connect(self._chronology_worker.run)
            self._chronology_worker.finished.connect(self._on_generation_finished)
            self._chronology_worker.failed.connect(self._on_generation_failed)

            # Cleanup
            self._chronology_worker.finished.connect(self._chronology_thread.quit)
            self._chronology_worker.failed.connect(self._chronology_thread.quit)
            self._chronology_thread.finished.connect(self._chronology_worker.deleteLater)
            self._chronology_thread.finished.connect(self._chronology_thread.deleteLater)
            self._chronology_thread.finished.connect(self._cleanup_generation_thread)

            self._chronology_thread.start()

        except Exception as exc:
            self._logger.exception("Unexpected error during chronology generation startup.")
            self._show_error(GUI_MESSAGES.get("unexpected_error", "Unexpected Error"), f"An unexpected error occurred:\n{exc}")
            self._cleanup_generation_thread()

    def _cleanup_generation_thread(self) -> None:
        self._chronology_worker = None
        self._chronology_thread = None
        self.ui.btn_generate.setEnabled(True)
        self.ui.btn_generate.setText(QCoreApplication.translate("ChronologyDialog", "Generate", None))

    def _on_generation_finished(self, target_path: Path, pdf_path: Path, pdf_succeeded: bool, export_message: str) -> None:
        if pdf_succeeded:
            text = (
                "Chronology Generated Successfully\n\n"
                "Generated Files\n\n"
                f"\u2713 {target_path.name}\n"
                f"\u2713 {pdf_path.name}"
            )
            choice = show_action_dialog(
                self,
                title=GUI_MESSAGES.get("chronology_generation_completed", "Chronology Generation Completed"),
                subtitle="Chronology Generated Successfully",
                description=text,
                accent="success",
                actions=[("View Excel", "excel"), ("View PDF", "pdf"), ("Close", "close")],
            )
        else:
            export_message = export_message or "PDF export failed. Please check logs for details."
            text = (
                "Chronology Excel generated successfully.\n\n"
                f"{export_message}\n\n"
                "Generated Files\n\n"
                f"\u2713 {target_path.name}"
            )
            choice = show_action_dialog(
                self,
                title=GUI_MESSAGES.get("chronology_generation_completed", "Chronology Generation Completed"),
                subtitle="Chronology Generated with Warnings",
                description=text,
                accent="warning",
                actions=[("View Excel", "excel"), ("View PDF", "pdf"), ("Close", "close")],
            )

        if choice == "excel":
            if not target_path.exists():
                self._show_warning("File Not Found", "Generated Excel file could not be found.")
                self.accept()
                return
            try:
                os.startfile(str(target_path))
            except Exception:
                self._logger.exception("Failed to open chronology Excel.")
                self._show_warning(
                    "Error",
                    f"Failed to open the Excel file. It might not be associated with any application.\n\nFile: {target_path}"
                )
        elif choice == "pdf":
            if not pdf_path.exists():
                self._show_warning("File Not Found", "Generated PDF file could not be found.")
                self.accept()
                return
            try:
                os.startfile(str(pdf_path))
            except Exception:
                self._logger.exception("Failed to open chronology PDF.")
                self._show_warning(
                    "Error",
                    f"Failed to open the PDF file. It might not be associated with any application.\n\nFile: {pdf_path}"
                )
        
        self.accept()

    def _on_generation_failed(self, error_message: str) -> None:
        self._show_error(GUI_MESSAGES.get("unexpected_error", "Unexpected Error"), f"An unexpected error occurred:\n{error_message}")

    def _validate_inputs(self) -> bool:
        if not self._stacked_cards or self._stacked_cards.count() == 0:
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), GUI_MESSAGES.get("chronology_no_crc", "No validated firmware folders with CRC PASS were discovered."))
            return False

        active_widget = self._stacked_cards.currentWidget()
        card = None
        for c in self._entry_cards:
            if c["group_box"] == active_widget:
                card = c
                break
                
        if not card:
            return False

        if not card["line_reason"].text().strip():
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), GUI_MESSAGES.get("chronology_reason_empty", "'Reason for Upgrade' cannot be empty."))
            card["line_reason"].setFocus()
            return False
        if not card["line_released_by"].text().strip():
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), GUI_MESSAGES.get("chronology_released_by_empty", "'Released By' cannot be empty."))
            card["line_released_by"].setFocus()
            return False
        if not card["line_tested_by"].text().strip():
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), GUI_MESSAGES.get("chronology_tested_by_empty", "'Tested By' cannot be empty."))
            card["line_tested_by"].setFocus()
            return False
        if card["combo_ladder_release"].currentText() == "Select...":
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), GUI_MESSAGES.get("chronology_ladder_release_empty", "select 'Ladder Release To Production'."))
            card["combo_ladder_release"].setFocus()
            return False
        if card["combo_operator_modification"].currentText() == "Select...":
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), GUI_MESSAGES.get("chronology_operator_mod_empty", "select 'Operator Procedure Modification'."))
            card["combo_operator_modification"].setFocus()
            return False
        if card["combo_automation_modification"].currentText() == "Select...":
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), GUI_MESSAGES.get("chronology_automation_mod_empty", "select 'Automation Set Up Modification'."))
            card["combo_automation_modification"].setFocus()
            return False
        
        personnel_msg = "Please select or enter Prepared By, Checked By, and Approved By."
        if not card["combo_prepared_by"].currentText().strip() or card["combo_prepared_by"].currentText() == "Select or enter person":
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), personnel_msg)
            card["combo_prepared_by"].setFocus()
            return False
        if not card["combo_checked_by"].currentText().strip() or card["combo_checked_by"].currentText() == "Select or enter person":
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), personnel_msg)
            card["combo_checked_by"].setFocus()
            return False
        if not card["combo_approved_by"].currentText().strip() or card["combo_approved_by"].currentText() == "Select or enter person":
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), personnel_msg)
            card["combo_approved_by"].setFocus()
            return False
        if not self._is_template_selected_for_card(card):
            self._show_warning(GUI_MESSAGES.get("validation_error", "Validation Error"), f"Please select a chronology template for\n{card['line_firmware_folder'].text()}")
            card["btn_browse_template"].setFocus()
            return False

        return True

    def _select_template_file(self) -> Path | None:
        """
        Opens a file dialog to select the chronology template.

        Returns:
            The selected Path, or None if cancelled.
        """
        return self._select_template_file_for_folder(None)

    def _select_template_file_for_folder(self, firmware_folder: str | None) -> Path | None:
        """
        Opens a file dialog to select the chronology template for a firmware folder.
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            (
                f"Select Chronology Excel Template for {firmware_folder}"
                if firmware_folder
                else "Select Chronology Excel Template"
            ),
            str(self._project_folder),
            "Excel Files (*.xlsx *.xlsm)"
        )
        return Path(filepath) if filepath else None

    def _selected_template_path(self) -> Path | None:
        if hasattr(self.ui, "line_excel_template"):
            value = self.ui.line_excel_template.text().strip()
            if value:
                path = Path(value)
                if path.exists():
                    return path
        return None

    def _selected_template_path_for_card(self, card: dict[str, Any]) -> Path | None:
        value = card["line_template_path"].text().strip()
        if not value:
            return None

        path = Path(value)
        if path.exists():
            return path
        return None

    def _is_template_selected_for_card(self, card: dict[str, Any]) -> bool:
        target_path = self._resolve_chronology_output_path(card["folder"])
        if target_path.exists():
            return True
        return self._selected_template_path_for_card(card) is not None

    def _resolve_chronology_output_path(self, firmware_folder: Path) -> Path:
        bin_root = self._project_folder / FOLDER_KEYS["bin_file"]
        chronology_root = self._project_folder / FOLDER_KEYS["chronology"]
        try:
            relative_folder = firmware_folder.resolve().relative_to(bin_root.resolve())
        except Exception:
            relative_folder = Path(firmware_folder.name)
        return chronology_root / relative_folder / "Ladder_Chronology.xlsx"

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
            
            if card["line_source_path"].text().strip():
                entry.source_code_path = Path(card["line_source_path"].text().strip())
                
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

            prep = card["combo_prepared_by"].currentText().strip()
            chk = card["combo_checked_by"].currentText().strip()
            app = card["combo_approved_by"].currentText().strip()

            entry.prepared_by = prep if prep != "Select or enter person" else ""
            entry.checked_by = chk if chk != "Select or enter person" else ""
            entry.approved_by = app if app != "Select or enter person" else ""

    def _show_error(self, title: str, message: str) -> None:
        show_styled_message(self, title, message, variant="error")

    def _show_warning(self, title: str, message: str) -> None:
        show_styled_message(self, title, message, variant="warning")