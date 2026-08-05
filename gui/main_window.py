"""
gui.main_window
===============

Main application window.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""
from __future__ import annotations

import os
import sys
import traceback
import webbrowser
from pathlib import Path
from typing import Any

from PySide6.QtGui import QAction, QCloseEvent, QColor, QGuiApplication
from PySide6.QtCore import QObject, QThread, QFileSystemWatcher, Signal, Qt
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from config import APP_NAME, APP_VERSION, COMPANY_NAME, DOCUMENT_VALIDATION_FOLDERS
from core.validation_engine import ValidationEngine
from core.validation_step import ValidationStep
from core.validation_summary import ValidationSummary
from reports.report_model import ReportDataModel
from reports.report_window import ReportWindow
from services.file_reader import FileReaderService
from services.file_search import FileSearchService
from services.folder_structure_generator import FolderStructureGenerator
from services.logger import LoggerService
from services.project_organizer import ProjectOrganizerService
from services.signature_reader import SignatureReaderService
from validators.bin_validator import BinValidator
from validators.chronology_validator import ChronologyValidator
from validators.document_validator import DocumentValidator
from validators.folder_validator import FolderValidator
from validators.ladder_validator import LadderValidator

from gui.progress_widget import ProgressWidget
from gui.result_table import ResultTable
from gui.chronology.chronology_dialog import ChronologyDialog

logger = LoggerService.get_logger()


class ValidationWorker(QObject):
    """
    Executes validation in a background thread.
    """
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, engine: ValidationEngine, project_path: Path) -> None:
        super().__init__()
        self._engine = engine
        self._project_path = project_path
        
        # Connect engine's progress callback directly to the worker's signal
        self._engine.set_progress_callback(self.progress.emit)

    def run(self) -> None:
        try:
            logger.info(f"ValidationWorker started for: {self._project_path}")
            summary = self._engine.validate(self._project_path)
            self.finished.emit(summary)
        except Exception as error:
            logger.exception(error)
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    """
    Main application window.
    """

    def __init__(self) -> None:
        super().__init__()

        self.summary: ValidationSummary | None = None
        self.project_path: Path | None = None
        self.worker: ValidationWorker | None = None
        self.report_window: ReportWindow | None = None
        self.thread: QThread | None = None
        self._filesystem_watcher: QFileSystemWatcher | None = None
        self._watched_paths: set[str] = set()
        self._project_changed_pending = False
        self._open_report_after_validation = False
        self._validation_summaries_by_project: dict[str, ValidationSummary] = {}

        self._build_ui()
        self._create_menu()
        self._connect_signals()
        self._setup_file_watcher()

    # ---------------------------------------------------------

    def _build_ui(self) -> None:
        """
        Build the main window.
        """
        self.setWindowTitle(APP_NAME)
        self.resize(1600, 900)
        self.setMinimumSize(1450, 820)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        header_frame = QFrame()
        header_frame.setObjectName("HeaderPanel")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(2)

        title_label = QLabel("Operational Package Validator")
        title_label.setObjectName("WindowTitle")
        subtitle_label = QLabel("Industrial-grade validation workspace for engineering package integrity")
        subtitle_label.setObjectName("WindowSubtitle")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)

        main_layout.addWidget(header_frame)

        self.summary_container = QFrame()
        self.summary_container.setObjectName("SummaryPanel")
        self.summary_layout = QGridLayout(self.summary_container)
        self.summary_layout.setContentsMargins(10, 10, 10, 10)
        self.summary_layout.setSpacing(6)
        self.summary_cards: dict[str, QFrame] = {}
        self.summary_value_labels: dict[str, QLabel] = {}
        self._build_summary_cards()
        main_layout.addWidget(self.summary_container)

        project_frame = QFrame()
        project_frame.setObjectName("ProjectPanel")
        project_layout = QHBoxLayout(project_frame)
        project_layout.setContentsMargins(10, 6, 10, 6)
        project_layout.setSpacing(8)

        project_label = QLabel("Project Folder")
        project_label.setObjectName("SectionLabel")
        self.project_path_label = QLabel("No project selected")
        self.project_path_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )
        self.project_path_label.setWordWrap(True)
        self.project_path_label.setMinimumHeight(24)
        self.project_path_label.setObjectName("ProjectPathLabel")
        self.browse_button = QPushButton("Browse...")

        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_path_label, 1)
        project_layout.addWidget(self.browse_button)

        main_layout.addWidget(project_frame)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        self.report_button = QPushButton("Validate & Generate Report")
        self.report_button.setEnabled(True)
        self.report_button.setObjectName("SecondaryButton")
        self.report_button.setMinimumWidth(240)
        self.generate_and_validate_button = QPushButton("Generate Folder Structure")
        self.generate_and_validate_button.setObjectName("PrimaryButton")
        self.generate_and_validate_button.setMinimumWidth(240)
        
        self.generate_chronology_button = QPushButton("Generate Chronology")
        self.generate_chronology_button.setObjectName("SecondaryButton")
        self.generate_chronology_button.setMinimumWidth(180)

        button_layout.addStretch(1)
        button_layout.addWidget(self.report_button)
        button_layout.addWidget(self.generate_and_validate_button)
        button_layout.addWidget(self.generate_chronology_button)
        button_layout.addStretch(1)

        main_layout.addLayout(button_layout)

        self.progress_widget = ProgressWidget()
        self.progress_widget.setObjectName("ProgressWidget")
        main_layout.addWidget(self.progress_widget)

        self.result_table = ResultTable()
        self.result_table.setObjectName("ResultTable")
        main_layout.addWidget(self.result_table, 1)

        self._apply_initial_geometry()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    # ---------------------------------------------------------

    def _connect_signals(self) -> None:
        """
        Connect all widget signals.
        """
        self.browse_button.clicked.connect(self._browse_project)
        self.report_button.clicked.connect(self._generate_report)
        self.generate_and_validate_button.clicked.connect(self._generate_folder_structure)
        self.generate_chronology_button.clicked.connect(self.on_generate_chronology)

    # ---------------------------------------------------------

    def _build_summary_cards(self) -> None:
        """Create the summary cards shown at the top of the dashboard."""
        cards = [
            ("pass", "PASS"),
            ("fail", "FAIL"),
            ("warning", "WARNING"),
            ("duration", "DURATION"),
        ]

        for index, (key, title) in enumerate(cards):
            card = QFrame()
            card.setObjectName("SummaryCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 6, 8, 6)
            card_layout.setSpacing(1)

            title_label = QLabel(title)
            title_label.setObjectName("SummaryTitle")
            title_label.setAlignment(Qt.AlignCenter)
            value_label = QLabel("—")
            value_label.setObjectName("SummaryValue")
            value_label.setAlignment(Qt.AlignCenter)

            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)

            card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            card.setMinimumHeight(46)
            self._apply_card_shadow(card)
            self.summary_cards[key] = card
            self.summary_value_labels[key] = value_label
            self.summary_layout.addWidget(card, 0, index)

    # ---------------------------------------------------------

    def _apply_card_shadow(self, widget: QWidget) -> None:
        """Add a subtle shadow and hover polish to dashboard cards."""
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(6)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 10))
        widget.setGraphicsEffect(shadow)

    def _apply_initial_geometry(self) -> None:
        """Center the window at a compact initial size."""
        geometry = None

        screens = QGuiApplication.screens()
        if screens:
            geometry = screens[0].availableGeometry()
        else:
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                geometry = screen.availableGeometry()

        if geometry is None:
            desktop = QApplication.desktop()
            if desktop is not None:
                geometry = desktop.availableGeometry()

        if geometry is None:
            self.resize(1600, 900)
            return

        width = min(1600, max(self.minimumWidth(), int(geometry.width() * 0.72)))
        height = min(900, max(self.minimumHeight(), int(geometry.height() * 0.72)))
        self.resize(width, height)
        self.move(
            geometry.left() + max(0, (geometry.width() - width) // 2),
            geometry.top() + max(0, (geometry.height() - height) // 2),
        )

    # ---------------------------------------------------------

    def _update_summary_cards(self, summary: ValidationSummary | None) -> None:
        """Refresh the top summary cards with the newest validation data."""
        if summary is None:
            self.summary_value_labels["pass"].setText("—")
            self.summary_value_labels["fail"].setText("—")
            self.summary_value_labels["warning"].setText("—")
            self.summary_value_labels["duration"].setText("—")
            return

        duration = "0s"
        if summary.started_at and summary.finished_at:
            elapsed = summary.finished_at - summary.started_at
            seconds = int(elapsed.total_seconds())
            duration = f"{seconds}s"

        self.summary_value_labels["pass"].setText(str(summary.passed))
        self.summary_value_labels["fail"].setText(str(summary.failed))
        self.summary_value_labels["warning"].setText(str(summary.warnings))
        self.summary_value_labels["duration"].setText(duration)

    # ---------------------------------------------------------

    def _setup_file_watcher(self) -> None:
        """Set up filesystem watching for the selected project tree."""
        self._filesystem_watcher = QFileSystemWatcher(self)
        self._filesystem_watcher.directoryChanged.connect(self._handle_path_changed)
        self._filesystem_watcher.fileChanged.connect(self._handle_path_changed)

    # ---------------------------------------------------------

    def _watch_project(self, project_path: Path | None) -> None:
        """Watch the selected project folder and its current subdirectories."""
        if self._filesystem_watcher is None:
            self._setup_file_watcher()

        if self._filesystem_watcher is None:
            return

        for watched_path in list(self._filesystem_watcher.files()) + list(self._filesystem_watcher.directories()):
            self._filesystem_watcher.removePath(watched_path)

        self._watched_paths.clear()

        if project_path is None or not project_path.exists():
            return

        self._filesystem_watcher.addPath(str(project_path))
        self._watched_paths.add(str(project_path))
        self._watch_subdirectories(project_path)

    # ---------------------------------------------------------

    def _watch_subdirectories(self, directory: Path) -> None:
        """Recursively watch current subdirectories for live changes."""
        if self._filesystem_watcher is None:
            return

        try:
            child_directories = sorted(
                path
                for path in directory.iterdir()
                if path.is_dir()
            )
        except OSError:
            return

        for child_directory in child_directories:
            path_str = str(child_directory)
            if path_str in self._watched_paths:
                continue

            self._filesystem_watcher.addPath(path_str)
            self._watched_paths.add(path_str)
            self._watch_subdirectories(child_directory)

    # ---------------------------------------------------------

    def _handle_path_changed(self, path: str) -> None:
        """Mark the current project as changed when the filesystem updates."""
        if self.project_path is None:
            return

        self._project_changed_pending = True

        if self.thread is not None and self.thread.isRunning():
            logger.info("Project files changed during validation: {}", path)
            return

        self.status_bar.showMessage("Project files have changed. Click Validate to refresh.")

    # ---------------------------------------------------------

    def _reset_validation_state(self) -> None:
        """Reset UI state and refresh flags before a new validation run."""
        self.summary = None
        self.result_table.clear_results()
        self.progress_widget.reset()
        self.report_button.setEnabled(False)
        self._project_changed_pending = False
        self._update_summary_cards(None)

    # ---------------------------------------------------------

    def _browse_project(self) -> None:
        """
        Open a folder selection dialog and validate the selection.
        """
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Project Folder",
        )

        if not directory:
            return

        selected_path = Path(directory)
        
        # Validation: Verify path exists and is a directory
        if not selected_path.exists() or not selected_path.is_dir():
            self._show_error(
                APP_NAME,
                "The selected project folder does not exist or is invalid."
            )
            return

        try:
            organizer = ProjectOrganizerService()
            selected_path = organizer.organize_if_needed(selected_path)
        except Exception as e:
            logger.error(f"Error during project organization: {e}")
            self._show_warning(APP_NAME, f"Project organization failed: {e}")

        self.project_path = selected_path
        self.project_path_label.setText(str(self.project_path))
        self._watch_project(self.project_path)

        self._reset_validation_state()
        self.report_button.setEnabled(True)
        self.status_bar.showMessage("Project selected.")
        logger.info("Project selected: {}", self.project_path)

    # ---------------------------------------------------------

    def _set_validation_running(self, running: bool) -> None:
        """
        Enable or disable controls while validation is running.
        """
        self.browse_button.setEnabled(not running)
        self.generate_and_validate_button.setEnabled(not running)
        self.report_button.setEnabled(not running)

    # ---------------------------------------------------------

    def _start_validation(self) -> None:
        """
        Start project validation.
        """
        if self.project_path is None or not self.project_path.exists():
            self._show_warning(
                APP_NAME,
                "Please select a valid project folder.",
            )
            return

        self._reset_validation_state()
        self.progress_widget.set_running()
        self.progress_widget.set_step("Starting validation...")
        self.status_bar.showMessage("Validation started...")
        self._set_validation_running(True)
        
        logger.info("Validation started for {}", self.project_path)

        self.thread = QThread(self)

        file_search = FileSearchService()
        file_reader = FileReaderService()
        signature_reader = SignatureReaderService()

        validators = [
            FolderValidator(file_search),
            LadderValidator(file_search),
            BinValidator(file_search),
            DocumentValidator(
                ValidationStep.OPERATIONAL_FLOW,
                DOCUMENT_VALIDATION_FOLDERS[0],
                file_search,
                file_reader,
                signature_reader,
            ),
            DocumentValidator(
                ValidationStep.TEST_REPORT,
                DOCUMENT_VALIDATION_FOLDERS[1],
                file_search,
                file_reader,
                signature_reader,
            ),
            DocumentValidator(
                ValidationStep.AUTOMATION_INPUT,
                DOCUMENT_VALIDATION_FOLDERS[2],
                file_search,
                file_reader,
                signature_reader,
            ),
            DocumentValidator(
                ValidationStep.LADDER_FLOW,
                DOCUMENT_VALIDATION_FOLDERS[3],
                file_search,
                file_reader,
                signature_reader,
            ),
            ChronologyValidator(file_search),
        ]

        engine = ValidationEngine(validators)
        self.worker = ValidationWorker(
            engine=engine,
            project_path=self.project_path,
        )

        self.worker.moveToThread(self.thread)

        #
        # Thread connections
        #
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._validation_finished)
        self.worker.failed.connect(self._validation_failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)

        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    # ---------------------------------------------------------

    def _validation_finished(self, summary: ValidationSummary) -> None:
        """
        Called when validation completes successfully.
        """
        summary.results = [r for r in summary.results if r.step != ValidationStep.CHRONOLOGY]
        
        self.summary = summary
        self.result_table.load_summary(summary)
        self.result_table.resize_columns()
        self._update_summary_cards(summary)

        self.progress_widget.set_success()
        self.progress_widget.set_step("Validation completed successfully.")

        if self._project_changed_pending:
            self.status_bar.showMessage("Project files have changed. Click Validate to refresh.")
            self._project_changed_pending = False
        else:
            self.status_bar.showMessage(
                f"Validation completed. "
                f"Passed: {summary.passed} | "
                f"Failed: {summary.failed} | "
                f"Warnings: {summary.warnings}"
            )

        self._set_validation_running(False)
        self.report_button.setEnabled(True)
        self._validation_summaries_by_project[self._project_key(summary.project_path)] = summary

        if self._open_report_after_validation:
            try:
                self._show_report_window(summary)
            except Exception as error:
                logger.exception("Unable to open report window after validation. Traceback:\n%s", traceback.format_exc())
                self._show_error(
                    APP_NAME,
                    f"Unable to open report window.\n\n{error}",
                )
            finally:
                self._open_report_after_validation = False

        self.thread = None
        self.worker = None

        logger.info("Validation completed successfully.")

    # ---------------------------------------------------------

    def _validation_failed(self, message: str) -> None:
        """
        Called when validation fails.
        """
        self.progress_widget.set_failure(message)
        self.status_bar.showMessage("Validation failed.")

        self._set_validation_running(False)
        self._open_report_after_validation = False

        self.thread = None
        self.worker = None

        logger.error(message)

        self._show_error(
            APP_NAME,
            message,
        )

    # ---------------------------------------------------------

    def _update_progress(self, percentage: int, step: str) -> None:
        """
        Update validation progress on the UI.
        """
        self.progress_widget.set_progress(percentage)
        self.progress_widget.set_step(step)

    # ---------------------------------------------------------

    def _show_report_window(self, summary: ValidationSummary) -> None:
        """Display the native PySide6 report window for the supplied validation summary."""
        logger.info("Entering _show_report_window()")

        if self.report_window is not None and (self.report_window.isVisible() or self.report_window.isHidden()):
            logger.info("Refreshing existing ReportWindow with latest validation summary")
            report_model = ReportDataModel.from_summary(summary)
            self.report_window.set_data_model(report_model)
            self.report_window.raise_()
            self.report_window.activateWindow()
            self.report_window.showNormal()
            self.status_bar.showMessage("Report window refreshed")
            return

        logger.info("Creating ReportDataModel...")
        report_model = ReportDataModel.from_summary(summary)
        logger.info("ReportDataModel created for project: %s", report_model.project_name)
        logger.info("Validation Summary ID: %s | Project Path: %s | Passed: %s | Failed: %s | Warnings: %s", id(summary), summary.project_path, summary.passed, summary.failed, summary.warnings)

        logger.info("Creating ReportWindow...")
        self.report_window = ReportWindow(report_model)
        self.report_window.destroyed.connect(lambda: setattr(self, "report_window", None))
        logger.info("ReportWindow created: %s | receives summary id: %s", self.report_window, id(summary))

        logger.info("Calling show()...")
        self.report_window.show()
        logger.info("show() completed. visible=%s hidden=%s geometry=%s", self.report_window.isVisible(), self.report_window.isHidden(), self.report_window.geometry())

        logger.info("Calling raise_()...")
        self.report_window.raise_()
        logger.info("Calling activateWindow()...")
        self.report_window.activateWindow()
        self.report_window.showNormal()
        logger.info("Window visible=%s hidden=%s geometry=%s", self.report_window.isVisible(), self.report_window.isHidden(), self.report_window.geometry())

        self.status_bar.showMessage("Report window opened")

    def _generate_report(self) -> None:
        """Validate the selected project and open the report window."""
        default_path = ""
        if self.project_path is not None and self.project_path.exists():
            default_path = str(self.project_path)

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Project Folder",
            default_path,
        )

        if not directory:
            return

        selected_path = Path(directory)
        if not selected_path.exists() or not selected_path.is_dir():
            self._show_warning(
                APP_NAME,
                "Please select a valid project folder.",
            )
            return

        self.project_path = selected_path
        self.project_path_label.setText(str(self.project_path))
        self._watch_project(self.project_path)

        logger.info("Validate & Generate Report requested for {}", self.project_path)
        self._open_report_after_validation = True
        self._start_validation()

    def _generate_folder_structure(self) -> None:
        """Generate the operational package folder structure only."""
        if self.project_path is None or not self.project_path.exists():
            self._show_warning(
                APP_NAME,
                "Please select a valid project folder.",
            )
            return

        try:
            generator = FolderStructureGenerator()
            generated_root = generator.generate_structure(source_project_path=self.project_path)
            self.status_bar.showMessage("Folder structure generated")
            logger.info("Folder structure successfully generated at:\n{}", generated_root)
        except PermissionError:
            logger.exception("Permission denied while generating folder structure")
            self._show_error(
                "Folder Structure Generation Failed",
                "Permission denied while creating folders.",
            )
            return
        except FileNotFoundError:
            logger.exception("Invalid path while generating folder structure")
            self._show_error(
                "Folder Structure Generation Failed",
                "The target path is invalid.",
            )
            return
        except OSError as error:
            logger.exception("Unexpected filesystem error while generating folder structure: {}", error)
            self._show_error(
                "Folder Structure Generation Failed",
                "An unexpected filesystem error occurred.",
            )
            return
        except Exception as error:
            logger.exception("Unexpected error while generating folder structure: {}", error)
            self._show_error(
                "Folder Structure Generation Failed",
                str(error),
            )
            return

        # Auto-select the generated folder as the project and start validation
        self.project_path = generated_root
        self.project_path_label.setText(str(generated_root))
        self._watch_project(generated_root)
        self._reset_validation_state()
        self.report_button.setEnabled(True)
        logger.info("Auto-selected generated folder as project: {}", generated_root)
        self.status_bar.showMessage("Folder structure generated. Click Validate & Generate Report.")

        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Information)
        message_box.setWindowTitle("Generation Completed")
        message_box.setText(
            "Operational Package Structure has been generated successfully.\n\n"
            f"Location:\n{generated_root.resolve()}"
        )

        open_folder_button = message_box.addButton("Open Folder", QMessageBox.ActionRole)
        message_box.addButton(QMessageBox.Ok)
        message_box.exec()

        if message_box.clickedButton() == open_folder_button:
            try:
                os.startfile(generated_root)
            except Exception:
                logger.exception("Unable to open generated folder.")

    # ---------------------------------------------------------

    def on_generate_chronology(self) -> None:
        """
        Open the Chronology Generation dialog for the selected project.
        """
        if self.project_path is None or not self.project_path.exists():
            QMessageBox.warning(
                self,
                APP_NAME,
                "Project folder not selected."
            )
            return

        validation_summary = self._validation_summaries_by_project.get(self._project_key(self.project_path))
        if validation_summary is None:
            QMessageBox.information(
                self,
                "Validation Required",
                "Please validate the generated Operational Package before generating the Chronology.",
            )
            return

        bin_records = self._extract_bin_crc_records(validation_summary)
        pass_records = {
            stage: record
            for stage, record in bin_records.items()
            if isinstance(record, dict) and str(record.get("status") or "").upper() == "PASS"
        }

        if not pass_records:
            QMessageBox.information(
                self,
                "No Chronology Generated",
                "All firmware folders failed CRC validation.",
            )
            return

        logger.info("Chronology generation started.")
        logger.info("Chronology dialog opened.")

        dialog = ChronologyDialog(
            project_folder=self.project_path,
            parent=self,
            validation_bin_crc_records=bin_records,
        )
        dialog.exec()

        logger.info("Chronology generation completed.")

    # ---------------------------------------------------------

    @staticmethod
    def _open_report(report_path: Path) -> None:
        """
        Open the generated report using the
        operating system's default browser.
        """
        try:
            if os.name == "nt":
                os.startfile(report_path)
                return
            webbrowser.open(report_path.as_uri())
        except Exception:
            logger.exception("Unable to open report.")

    # ---------------------------------------------------------

    def _create_menu(self) -> None:
        """
        Create the application menu.
        """
        file_menu = self.menuBar().addMenu("&File")

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("&Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ---------------------------------------------------------

    def _show_about(self) -> None:
        """
        Display application information.
        """
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            (
                f"<h3>{APP_NAME}</h3>"
                f"<p>Version {APP_VERSION}</p>"
                f"<p>{COMPANY_NAME}</p>"
                "<hr>"
                f"<p>Running on Python {python_version}</p>"
            ),
        )

    # ---------------------------------------------------------

    def _cleanup_thread(self) -> None:
        """
        Release thread resources safely.
        """
        if self.thread is not None:
            logger.info("Cleaning up background thread...")
            if self.thread.isRunning():
                self.thread.quit()
                self.thread.wait(3000)
                
        self.worker = None
        self.thread = None
        logger.info("Thread cleanup completed.")

    # ---------------------------------------------------------

    def reset_application(self) -> None:
        """
        Reset the application state.
        """
        self._cleanup_thread()
        
        self.summary = None
        self.project_path = None
        
        self.project_path_label.setText("No project selected")
        self.progress_widget.reset()
        self.result_table.clear_results()
        self._update_summary_cards(None)
        
        self.report_button.setEnabled(True)
        
        self.status_bar.showMessage("Ready")

    # ---------------------------------------------------------

    def _show_error(self, title: str, message: str) -> None:
        """
        Display an error dialog.
        """
        QMessageBox.critical(self, title, message)

    # ---------------------------------------------------------

    def _show_information(self, title: str, message: str) -> None:
        """
        Display an information dialog.
        """
        QMessageBox.information(self, title, message)

    # ---------------------------------------------------------

    def _show_warning(self, title: str, message: str) -> None:
        """
        Display a warning dialog.
        """
        QMessageBox.warning(self, title, message)

    def _project_key(self, project_path: Path) -> str:
        return str(project_path.resolve()).casefold()

    @staticmethod
    def _extract_bin_crc_records(summary: ValidationSummary) -> dict[str, dict[str, Any]]:
        for result in summary.results:
            if result.step != ValidationStep.BIN_FILES:
                continue
            bin_crcs = result.details.get("bin_crcs")
            if isinstance(bin_crcs, dict):
                return {
                    str(stage): value
                    for stage, value in bin_crcs.items()
                    if isinstance(value, dict)
                }
        return {}

    # ---------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handle application exit.
        """
        if self.thread is not None and self.thread.isRunning():
            reply = QMessageBox.question(
                self,
                APP_NAME,
                (
                    "Validation is still running.\n\n"
                    "Do you really want to exit?"
                ),
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply != QMessageBox.Yes:
                event.ignore()
                return

            self._cleanup_thread()

        logger.info("Application closed.")
        event.accept()