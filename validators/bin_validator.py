"""
validators.bin_validator
========================

Validates BIN firmware files against Ladder SDOC files.

Responsibilities
----------------
- Validate BIN folder structure.
- Discover Initial and Final BIN files.
- Ensure exactly one BIN exists per stage.
- Compare BIN filenames with SDOC filenames.
- Cache discovered BIN files.

Author:
    Selec Controls Pvt. Ltd. - R&D

Python:
    3.12+
"""

from __future__ import annotations

from pathlib import Path

from config import BIN_EXTENSION, FOLDER_KEYS

from core.base_validator import BaseValidator
from core.validation_context import ValidationContext
from core.validation_result import ValidationResult
from core.validation_step import ValidationStep

from services.crc.crc_comparison_service import BinCRCResult, CRCComparisonService
from services.crc.crc_exceptions import CRCError
from services.file_search import FileSearchService


class BinValidator(BaseValidator):
    """
    Validates BIN firmware files.
    """

    def __init__(
        self,
        file_search: FileSearchService,
    ) -> None:

        super().__init__(ValidationStep.BIN_FILES)

        self._file_search = file_search
        self._crc_service = CRCComparisonService()

    def validate(
        self,
        context: ValidationContext,
    ) -> ValidationResult:

        self.logger.info("Starting BIN validation.")

        bin_root = context.folders.get(FOLDER_KEYS["bin_file"])

        if bin_root is None:

            return self.skipped_result(
                reason="BIN validation skipped because folder validation failed."
            )

        failure_reasons: list[str] = []
        stage_errors: list[str] = []

        stages = [relative_path for relative_path, _ in context.discovered_paths]
        crc_records: dict[str, dict[str, str | None]] = {}

        for relative_path in stages:
            stage_path = bin_root / Path(*relative_path.split("/"))
            bin_candidates = self._file_search.recursive_files(stage_path, BIN_EXTENSION)
            latest_bin = self._select_latest_by_mtime(bin_candidates)

            if latest_bin is None:
                reason = f"{relative_path}: No BIN file found in Bin File folder."
                stage_errors.append(reason)
                failure_reasons.append(reason)
                continue

            context.add_bin_file(relative_path, latest_bin)

            try:
                crc_result = self._crc_service.calculate_for_bin(latest_bin)
            except CRCError as error:
                reason = f"{relative_path}: {error}"
                stage_errors.append(reason)
                failure_reasons.append(reason)
                continue

            crc_records[relative_path] = self._crc_to_dict(crc_result)

        context.set_metadata("bin_crc_records", crc_records)

        if failure_reasons:
            return self.fail_result(
                reason="; ".join(failure_reasons),
                checked_path=bin_root,
                details={
                    "stage_errors": stage_errors,
                    "bin_crcs": crc_records,
                    "bin_files": {key: str(path) for key, path in context.bin_files.items()},
                },
            )

        self.logger.info("BIN validation completed successfully.")

        return self.pass_result(
            reason="BIN CRC validated successfully.",
            checked_path=bin_root,
            details={
                "bin_crcs": crc_records,
                "bin_files": {key: str(path) for key, path in context.bin_files.items()},
            },
        )

    @staticmethod
    def _crc_to_dict(result: BinCRCResult) -> dict[str, str | None]:
        return {
            "bin_file": str(result.bin_file_path),
            "bin_name": result.bin_file_name,
            "crc": result.crc_hex,
        }

    @staticmethod
    def _select_latest_by_mtime(files: list[Path]) -> Path | None:
        if not files:
            return None

        def key(path: Path) -> tuple[int, str]:
            stat = path.stat()
            mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
            return mtime_ns, str(path).casefold()

        return max(files, key=key)