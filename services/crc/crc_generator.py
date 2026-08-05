"""CRC generation engine for BIN files."""

from __future__ import annotations

import time
from pathlib import Path

from config import CRC_ALGORITHM
from services.crc.crc_exceptions import (
    CRCEmptyFileError,
    CRCMissingFileError,
    CRCPermissionError,
    CRCReadError,
)
from services.crc.crc_factory import CRCFactory
from services.crc.crc_result import CRCResult
from services.logger import LoggerService

logger = LoggerService.get_logger()


class CRCGenerator:
    """Generate CRC values for binary data and BIN files."""

    def __init__(self, algorithm_name: str | None = None) -> None:
        self.algorithm_name = algorithm_name or CRC_ALGORITHM

    def generate_from_file(self, file_path: Path) -> CRCResult:
        file_path = Path(file_path)
        logger.info("Starting CRC generation for file %s using %s", file_path, self.algorithm_name)

        if not file_path.exists():
            logger.error("CRC generation failed: missing file %s", file_path)
            raise CRCMissingFileError(f"BIN file not found: {file_path}")

        if not file_path.is_file():
            logger.error("CRC generation failed: path is not a file %s", file_path)
            raise CRCReadError(f"Expected a file, but found: {file_path}")

        try:
            file_size = file_path.stat().st_size
        except PermissionError as error:
            logger.exception("Permission denied while accessing file %s", file_path)
            raise CRCPermissionError(str(error)) from error
        except OSError as error:
            logger.exception("Unable to inspect file %s", file_path)
            raise CRCReadError(str(error)) from error

        if file_size == 0:
            logger.error("CRC generation failed: empty file %s", file_path)
            raise CRCEmptyFileError(f"BIN file is empty: {file_path}")

        algorithm = CRCFactory.get_algorithm(self.algorithm_name)
        start_time = time.perf_counter()

        try:
            with file_path.open("rb") as handle:
                while chunk := handle.read(8192):
                    algorithm.update(chunk)
        except PermissionError as error:
            logger.exception("Permission denied while reading file %s", file_path)
            raise CRCPermissionError(str(error)) from error
        except OSError as error:
            logger.exception("Failed to read file %s", file_path)
            raise CRCReadError(str(error)) from error
        except Exception as error:
            logger.exception("Unexpected error while generating CRC for %s: %s", file_path, error)
            raise CRCReadError(str(error)) from error

        processing_time = time.perf_counter() - start_time
        crc_value = algorithm.finalize()

        result = CRCResult(
            algorithm=algorithm.name,
            crc_value=crc_value,
            hex_value=f"0x{crc_value:0{algorithm.width // 4}X}",
            decimal_value=crc_value,
            file_size=file_size,
            processing_time=processing_time,
            success=True,
            error_message=None,
        )

        logger.info(
            "CRC generated for %s: algorithm=%s file_size=%d processing_time=%.6fs crc=%s",
            file_path,
            result.algorithm,
            result.file_size,
            result.processing_time,
            result.hex_value,
        )

        return result

    def generate_from_data(self, data: bytes, algorithm_name: str | None = None) -> CRCResult:
        algorithm_name = algorithm_name or self.algorithm_name
        algorithm = CRCFactory.get_algorithm(algorithm_name)

        start_time = time.perf_counter()
        algorithm.update(data)
        processing_time = time.perf_counter() - start_time
        crc_value = algorithm.finalize()

        return CRCResult(
            algorithm=algorithm.name,
            crc_value=crc_value,
            hex_value=f"0x{crc_value:0{algorithm.width // 4}X}",
            decimal_value=crc_value,
            file_size=len(data),
            processing_time=processing_time,
            success=True,
            error_message=None,
        )
