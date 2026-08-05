"""
services.logger
===============

Centralized logging configuration for the Operational Package Validator.

Author:
    Selec Controls Pvt. Ltd. - R&D
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from config import LOG_DIRECTORY, LOG_FILE_NAME


class LoggerService:
    """
    Configures and provides the application logger.

    This class should be initialized only once during application startup.
    """

    _configured: bool = False

    @classmethod
    def configure(cls) -> None:
        """Configure Loguru sinks."""

        if cls._configured:
            return

        log_dir = Path(LOG_DIRECTORY)
        log_dir.mkdir(parents=True, exist_ok=True)

        logger.remove()

        # Console output
        # In PyInstaller --windowed mode, standard streams are None.
        # We must never pass None to logger.add().
        console_sink = sys.stderr
        if console_sink is not None:
            logger.add(
                console_sink,
                level="INFO",
                colorize=True,
                enqueue=True,
                backtrace=True,
                diagnose=False,
                format=(
                    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                    "<level>{level: <8}</level> | "
                    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                    "<level>{message}</level>"
                ),
            )

        # File output
        logger.add(
            log_dir / LOG_FILE_NAME,
            level="DEBUG",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=False,
            encoding="utf-8",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
        )

        cls._configured = True

    @staticmethod
    def get_logger():
        """Return the configured logger."""
        return logger