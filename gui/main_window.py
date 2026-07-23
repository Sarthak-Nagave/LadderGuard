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
import webbrowser
from pathlib import Path

from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
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

from config import APP_NAME, APP_VERSION, COMPANY_NAME
from core.validation_engine import ValidationEngine
from core.validation_step import ValidationStep
from core.validation_summary import ValidationSummary
from reports.report_generator import ReportGenerator
from services.file_reader import FileReaderService
from services.file_search import FileSearchService
from services.logger import LoggerService
from services.signature_reader import SignatureReaderService
from validators.bin_validator import BinValidator
from validators.chronology_validator import ChronologyValidator
from validators.document_validator import DocumentValidator
from validators.folder_validator import FolderValidator
from validators.ladder_validator import LadderValidator

from gui.progress_widget import ProgressWidget
from gui.result_table import ResultTable

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
        self.thread: QThread | None = None

        self._build_ui()
        self._create_menu()
        self._connect_signals()

    # ---------------------------------------------------------

    def _build_ui(self) -> None:
        """
        Build the main window.
        """
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        #
        # -----------------------------------------------------
        # Project Selection
        # -----------------------------------------------------
        #
        project_layout = QHBoxLayout()
        project_label = QLabel("Project Folder")
        self.project_path_label = QLabel("No project selected")
        self.project_path_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )
        self.project_path_label.setWordWrap(True)
        self.browse_button = QPushButton("Browse...")

        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_path_label, 1)
        project_layout.addWidget(self.browse_button)

        main_layout.addLayout(project_layout)

        #
        # -----------------------------------------------------
        # Action Buttons
        # -----------------------------------------------------
        #
        button_layout = QHBoxLayout()
        self.validate_button = QPushButton("Validate Project")
        self.validate_button.setEnabled(False)
        self.report_button = QPushButton("Generate Report")
        self.report_button.setEnabled(False)

        button_layout.addWidget(self.validate_button)
        button_layout.addWidget(self.report_button)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        #
        # -----------------------------------------------------
        # Progress Widget
        # -----------------------------------------------------
        #
        self.progress_widget = ProgressWidget()
        main_layout.addWidget(self.progress_widget)

        #
        # -----------------------------------------------------
        # Results Table
        # -----------------------------------------------------
        #
        self.result_table = ResultTable()
        main_layout.addWidget(self.result_table, 1)

        #
        # -----------------------------------------------------
        # Status Bar
        # -----------------------------------------------------
        #
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    # ---------------------------------------------------------

    def _connect_signals(self) -> None:
        """
        Connect all widget signals.
        """
        self.browse_button.clicked.connect(self._browse_project)
        self.validate_button.clicked.connect(self._start_validation)
        self.report_button.clicked.connect(self._generate_report)

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

        self.project_path = selected_path
        self.project_path_label.setText(str(self.project_path))

        self.validate_button.setEnabled(True)
        self.report_button.setEnabled(False)
        self.result_table.clear_results()
        self.progress_widget.reset()
        self.summary = None

        self.status_bar.showMessage("Project selected.")
        logger.info("Project selected: {}", self.project_path)

    # ---------------------------------------------------------

    def _set_validation_running(self, running: bool) -> None:
        """
        Enable or disable controls while validation is running.
        """
        self.browse_button.setEnabled(not running)
        self.validate_button.setEnabled(not running)
        self.report_button.setEnabled(not running and self.summary is not None)

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

        self.summary = None
        self.result_table.clear_results()
        self.progress_widget.reset()
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
                "3. Operational Flow",
                file_search,
                file_reader,
                signature_reader,
            ),
            DocumentValidator(
                ValidationStep.TEST_REPORT,
                "4. Test Report",
                file_search,
                file_reader,
                signature_reader,
            ),
            DocumentValidator(
                ValidationStep.AUTOMATION_INPUT,
                "5. Automation Input Doc",
                file_search,
                file_reader,
                signature_reader,
            ),
            DocumentValidator(
                ValidationStep.LADDER_FLOW,
                "6. Ladder Flow",
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
        self.summary = summary
        self.result_table.load_summary(summary)
        self.result_table.resize_columns()

        self.progress_widget.set_success()
        self.progress_widget.set_step("Validation completed successfully.")

        self.status_bar.showMessage(
            f"Validation completed. "
            f"Passed: {summary.passed} | "
            f"Failed: {summary.failed} | "
            f"Warnings: {summary.warnings}"
        )

        self._set_validation_running(False)
        self.report_button.setEnabled(True)  # Strictly enforce enablement on success

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

    def _generate_report(self) -> None:
        """
        Generate the HTML validation report.
        """
        if self.summary is None:
            self._show_information(
                APP_NAME,
                "Run validation before generating a report.",
            )
            return

        try:
            logger.info("Generating report...")
            report_path = ReportGenerator.generate(self.summary)
            
            self.status_bar.showMessage(f"Report generated: {report_path.name}")
            logger.info("Report generated: {}", report_path)
            
            self._open_report(report_path)

        except Exception as error:
            logger.exception("Unable to generate report: {}", error)
            self._show_error(
                APP_NAME,
                f"Unable to generate report.\n\n{error}",
            )

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
        
        self.validate_button.setEnabled(False)
        self.report_button.setEnabled(False)
        
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