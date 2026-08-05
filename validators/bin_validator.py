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

        ladders_root = context.folders.get(FOLDER_KEYS["ladders"])
        bin_root = context.folders.get(FOLDER_KEYS["bin_file"])

        if ladders_root is None:

            return self.skipped_result(
                reason="BIN validation skipped because ladder validation prerequisites are unavailable."
            )

        if bin_root is None:

            return self.skipped_result(
                reason="BIN validation skipped because folder validation failed."
            )

        failure_reasons: list[str] = []
        stage_errors: list[str] = []

        stages = [relative_path for relative_path, _ in context.discovered_paths]
        crc_records: dict[str, dict[str, str | None]] = {}

        if not stages:
            reason = "No firmware folders were discovered before BIN validation."
            self.logger.error(reason)
            stage_errors.append(reason)
            return self.fail_result(
                reason=reason,
                checked_path=bin_root,
                details={
                    "stage_errors": stage_errors,
                    "bin_crcs": crc_records,
                    "bin_files": {key: str(path) for key, path in context.bin_files.items()},
                },
            )

        for relative_path in stages:
            ladder_stage_path = ladders_root / Path(*relative_path.split("/"))
            stage_path = bin_root / Path(*relative_path.split("/"))

            if not ladder_stage_path.exists() or not ladder_stage_path.is_dir():
                reason = f"{relative_path}: Firmware folder not found in Ladders folder."
                self.logger.error(reason)
                stage_errors.append(reason)
                failure_reasons.append(reason)
                continue

            if not stage_path.exists() or not stage_path.is_dir():
                reason = f"{relative_path}: Firmware folder not found in Bin File folder."
                self.logger.error(reason)
                stage_errors.append(reason)
                failure_reasons.append(reason)
                continue

            ladder_bin_candidates = self._file_search.direct_files(ladder_stage_path, BIN_EXTENSION)
            latest_ladder_bin = self._select_latest_by_mtime(ladder_bin_candidates)

            if latest_ladder_bin is None:
                reason = f"{relative_path}: No BIN file found in Ladders folder."
                self.logger.warning(reason)
                stage_errors.append(reason)
                failure_reasons.append(reason)
                continue

            bin_candidates = self._file_search.direct_files(stage_path, BIN_EXTENSION)
            latest_bin = self._select_latest_by_mtime(bin_candidates)

            if latest_bin is None:
                reason = f"{relative_path}: No BIN file found in Bin File folder."
                self.logger.warning(reason)
                stage_errors.append(reason)
                failure_reasons.append(reason)
                continue

            context.add_bin_file(relative_path, latest_bin)

            try:
                ladder_crc_result = self._crc_service.calculate_for_bin(latest_ladder_bin)
                bin_crc_result = self._crc_service.calculate_for_bin(latest_bin)
            except CRCError as error:
                reason = f"{relative_path}: {error}"
                self.logger.error(reason)
                stage_errors.append(reason)
                failure_reasons.append(reason)
                continue

            crc_record = self._crc_to_dict(ladder_crc_result, bin_crc_result)
            crc_records[relative_path] = crc_record

            if crc_record["status"] != "PASS":
                reason = f"{relative_path}: CRC Mismatch"
                self.logger.error(reason)
                stage_errors.append(reason)
                failure_reasons.append(reason)

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
            reason="BIN CRC comparison validated successfully.",
            checked_path=bin_root,
            details={
                "bin_crcs": crc_records,
                "bin_files": {key: str(path) for key, path in context.bin_files.items()},
            },
        )

    @staticmethod
    def _crc_to_dict(
        ladder_result: BinCRCResult,
        bin_result: BinCRCResult,
    ) -> dict[str, str | None]:
        is_match = ladder_result.crc_hex == bin_result.crc_hex
        return {
            "ladder_bin_file": str(ladder_result.bin_file_path),
            "ladder_bin_name": ladder_result.bin_file_name,
            "ladder_crc": ladder_result.crc_hex,
            "bin_file": str(bin_result.bin_file_path),
            "bin_name": bin_result.bin_file_name,
            "bin_crc": bin_result.crc_hex,
            "crc": bin_result.crc_hex if is_match else None,
            "status": "PASS" if is_match else "FAILED",
            "reason": "" if is_match else "CRC Mismatch",
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