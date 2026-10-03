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

from PySide6.QtCore import QFileSystemWatcher, QObject, Qt, QThread, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from reports.report_model import ReportDataModel
from reports.report_window import ReportWindow

from config import (
    APP_NAME,
    APP_VERSION,
    COMPANY_NAME,
    DOCUMENT_VALIDATION_FOLDERS,
    GUI_MESSAGES,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
)
from core.validation_engine import ValidationEngine
from core.validation_step import ValidationStep
from core.validation_summary import ValidationSummary
from gui.chronology.chronology_dialog import ChronologyDialog
from gui.progress_widget import ProgressWidget
from gui.result_table import ResultTable
from gui.ui_dialogs import show_action_dialog, show_styled_message
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
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_frame = QFrame()
        header_frame.setObjectName("HeaderPanel")
        header_frame.setMinimumHeight(70)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(2)

        title_label = QLabel(APP_NAME)
        title_label.setObjectName("WindowTitle")
        subtitle_label = QLabel(f"Version {APP_VERSION}")
        subtitle_label.setObjectName("WindowSubtitle")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)

        main_layout.addWidget(header_frame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 12, 16, 16)
        content_layout.setSpacing(10)
        main_layout.addWidget(content_widget, 1)

        self.summary_container = QFrame()
        self.summary_container.setObjectName("SummaryPanel")
        self.summary_layout = QGridLayout(self.summary_container)
        self.summary_layout.setContentsMargins(10, 10, 10, 10)
        self.summary_layout.setSpacing(8)
        self.summary_cards: dict[str, QFrame] = {}
        self.summary_value_labels: dict[str, QLabel] = {}
        self._build_summary_cards()
        content_layout.addWidget(self.summary_container)

        project_frame = QFrame()
        project_frame.setObjectName("ProjectPanel")
        project_layout = QHBoxLayout(project_frame)
        project_layout.setContentsMargins(10, 8, 10, 8)
        project_layout.setSpacing(8)

        project_label = QLabel("Project Folder")
        project_label.setObjectName("SectionLabel")
        self.project_path_label = QLabel("No project selected")
        self.project_path_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )
        self.project_path_label.setWordWrap(False)
        self.project_path_label.setMinimumHeight(24)
        self.project_path_label.setObjectName("ProjectPathLabel")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setObjectName("BrowseButton")
        self.browse_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))

        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_path_label, 1)
        project_layout.addWidget(self.browse_button)

        content_layout.addWidget(project_frame)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        self.report_button = QPushButton("Validate & Generate Report")
        self.report_button.setEnabled(True)
        self.report_button.setObjectName("SecondaryButton")
        self.report_button.setMinimumWidth(220)
        self.report_button.setMinimumHeight(38)
        self.report_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.report_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.generate_and_validate_button = QPushButton("Ladder Release Structure")
        self.generate_and_validate_button.setObjectName("PrimaryButton")
        self.generate_and_validate_button.setMinimumWidth(220)
        self.generate_and_validate_button.setMinimumHeight(38)
        self.generate_and_validate_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.generate_and_validate_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        
        self.generate_chronology_button = QPushButton("Generate Chronology")
        self.generate_chronology_button.setObjectName("SecondaryButton")
        self.generate_chronology_button.setMinimumWidth(220)
        self.generate_chronology_button.setMinimumHeight(38)
        self.generate_chronology_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.generate_chronology_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))

        button_layout.addWidget(self.report_button, 1)
        button_layout.addWidget(self.generate_and_validate_button, 1)
        button_layout.addWidget(self.generate_chronology_button, 1)

        content_layout.addLayout(button_layout)

        self.progress_widget = ProgressWidget()
        self.progress_widget.setObjectName("ProgressWidget")
        content_layout.addWidget(self.progress_widget)

        self.result_table = ResultTable()
        self.result_table.setObjectName("ResultTable")
        content_layout.addWidget(self.result_table, 1)

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
            ("pass", "PASS", "\u2713"),
            ("fail", "FAIL", "\u2715"),
            ("warning", "WARNING", "!"),
            ("duration", "DURATION", "\u23F1"),
        ]

        for index, (key, title, icon_text) in enumerate(cards):
            card = QFrame()
            card.setObjectName("SummaryCard")
            card.setProperty("cardType", key)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(2)

            icon_label = QLabel(icon_text)
            icon_label.setObjectName("SummaryIcon")
            icon_label.setAlignment(Qt.AlignCenter)

            title_label = QLabel(title)
            title_label.setObjectName("SummaryTitle")
            title_label.setAlignment(Qt.AlignCenter)
            value_label = QLabel("—")
            value_label.setObjectName("SummaryValue")
            value_label.setAlignment(Qt.AlignCenter)

            card_layout.addWidget(icon_label)
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)

            card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            card.setMinimumHeight(80)
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
            self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
            return

        # Safely clamp the minimum size to the available screen geometry
        safe_min_width = min(MIN_WINDOW_WIDTH, geometry.width())
        safe_min_height = min(MIN_WINDOW_HEIGHT, geometry.height())
        self.setMinimumSize(safe_min_width, safe_min_height)

        # Calculate desired startup size, clamped to available screen
        desired_width = min(WINDOW_WIDTH, geometry.width())
        desired_height = min(WINDOW_HEIGHT, geometry.height())

        self.resize(desired_width, desired_height)
        self.move(
            geometry.left() + max(0, (geometry.width() - desired_width) // 2),
            geometry.top() + max(0, (geometry.height() - desired_height) // 2),
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

    def _set_project_path_label(self, path: Path | None) -> None:
        if path is None:
            self.project_path_label.setText("No project selected")
            self.project_path_label.setToolTip("")
            return

        metrics = self.project_path_label.fontMetrics()
        width = max(120, self.project_path_label.width() - 16)
        text = str(path)
        self.project_path_label.setText(metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, width))
        self.project_path_label.setToolTip(text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._set_project_path_label(self.project_path)

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
        self._set_project_path_label(self.project_path)
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
        self._set_project_path_label(self.project_path)
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
        self._set_project_path_label(generated_root)
        self._watch_project(generated_root)
        self._reset_validation_state()
        self.report_button.setEnabled(True)
        logger.info("Auto-selected generated folder as project: {}", generated_root)
        self.status_bar.showMessage("Folder structure generated. Click Validate & Generate Report.")

        choice = show_action_dialog(
            self,
            title=GUI_MESSAGES.get("generation_completed", "Generation Completed"),
            subtitle="Folder Structure Generated Successfully",
            description=f"Location:\n{generated_root.resolve()}",
            accent="success",
            actions=[("Open Folder", "open_folder"), ("Close", "close")],
        )

        if choice == "open_folder":
            try:
                os.startfile(generated_root)
            except Exception:
                logger.exception("Unable to open generated folder.")

    # ---------------------------------------------------------

    def check_chronology_prerequisites(self) -> dict:
        """
        Evaluate if chronology generation is allowed.
        Returns a dict with structured information about the prerequisite state.
        """
        if self.project_path is None or not self.project_path.exists():
            return {
                "allowed": False,
                "validation_completed": False,
                "passed_count": 0,
                "total_count": 7,
                "crc_completed": False,
                "crc_passed": False,
                "reason": "Validation has not been completed.\nPlease run validation first."
            }

        validation_summary = self._validation_summaries_by_project.get(self._project_key(self.project_path))
        if validation_summary is None:
            return {
                "allowed": False,
                "validation_completed": False,
                "passed_count": 0,
                "total_count": 7,
                "crc_completed": False,
                "crc_passed": False,
                "reason": "Validation has not been completed.\nPlease run validation first."
            }
        
        passed_count = validation_summary.passed
        total_count = 7  # Exactly 7 steps as per requirements

        bin_records = self._extract_bin_crc_records(validation_summary)
        
        # Check CRC records presence and pass state
        crc_completed = bool(bin_records)
        pass_records = {
            stage: record
            for stage, record in bin_records.items()
            if isinstance(record, dict) and str(record.get("status") or "").upper() == "PASS"
        }
        fail_records = {
            stage: record
            for stage, record in bin_records.items()
            if isinstance(record, dict) and str(record.get("status") or "").upper() == "FAIL"
        }

        # The project considers CRC complete if there are BIN records.
        # It considers CRC PASS only if there are pass records and no fail records, or just any pass records?
        # Actually, if there is a FAIL, the status is FAIL. 
        # But wait, existing code used: `if not pass_records:` block. 
        # User said "CRC = PASS" is the condition, and differentiate between NOT RUN and FAIL.
        # If crc_completed is False, it's NOT RUN.
        # If there are fail records or NO pass records (while completed), it's FAIL.
        if crc_completed:
            # We have records. If any is PASS and none are FAIL, it's PASS. But maybe there's a mix.
            # Let's say it's PASS if `bool(pass_records)` is true, consistent with existing logic which blocked `if not pass_records`.
            # Actually, existing logic blocked if there were NO pass records. So if there's at least one PASS record, it generated.
            crc_passed = bool(pass_records)
        else:
            crc_passed = False

        if passed_count < 6:
            if not crc_passed:
                crc_status_text = "FAIL" if crc_completed else "Not completed"
                reason = (f"Validation result: {passed_count}/{total_count}\n"
                          f"Required: 6/7 or 7/7\n\n"
                          f"CRC status: {crc_status_text}\n\n"
                          f"Both chronology prerequisites must be satisfied.")
            else:
                reason = (f"Validation result: {passed_count}/{total_count}\n"
                          f"Required: 6/7 or 7/7\n\n"
                          f"Please resolve the failed validation steps before generating chronology.")
            return {
                "allowed": False,
                "validation_completed": True,
                "passed_count": passed_count,
                "total_count": total_count,
                "crc_completed": crc_completed,
                "crc_passed": crc_passed,
                "reason": reason
            }
        
        if not crc_passed:
            crc_status_text = "FAIL" if crc_completed else "Not completed"
            pass_word = "PASS" if crc_completed else "pass"
            reason = (f"Validation result: {passed_count}/{total_count}\n"
                      f"CRC status: {crc_status_text}\n\n"
                      f"CRC validation must {pass_word} before chronology can be generated.")
            return {
                "allowed": False,
                "validation_completed": True,
                "passed_count": passed_count,
                "total_count": total_count,
                "crc_completed": crc_completed,
                "crc_passed": crc_passed,
                "reason": reason
            }
            
        return {
            "allowed": True,
            "validation_completed": True,
            "passed_count": passed_count,
            "total_count": total_count,
            "crc_completed": True,
            "crc_passed": True,
            "reason": "Prerequisites satisfied."
        }

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

        prereqs = self.check_chronology_prerequisites()
        logger.info(
            f"Chronology prerequisite check: Validation={prereqs['passed_count']}/{prereqs['total_count']}, "
            f"CRC={'PASS' if prereqs['crc_passed'] else ('FAIL' if prereqs['crc_completed'] else 'NOT RUN')}, "
            f"Allowed={prereqs['allowed']}"
        )

        if not prereqs["allowed"]:
            logger.info(f"Chronology Generation Blocked: {prereqs['reason'].replace(chr(10), ' ')}")
            QMessageBox.information(
                self,
                "Chronology Generation Blocked",
                prereqs["reason"]
            )
            return

        validation_summary = self._validation_summaries_by_project.get(self._project_key(self.project_path))
        bin_records = self._extract_bin_crc_records(validation_summary)

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
        
        self._set_project_path_label(None)
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
        show_styled_message(self, title, message, variant="error")

    # ---------------------------------------------------------

    def _show_information(self, title: str, message: str) -> None:
        """
        Display an information dialog.
        """
        show_styled_message(self, title, message, variant="info")

    # ---------------------------------------------------------

    def _show_warning(self, title: str, message: str) -> None:
        """
        Display a warning dialog.
        """
        show_styled_message(self, title, message, variant="warning")

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