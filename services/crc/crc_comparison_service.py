"""Reusable BIN-file CRC calculation service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.crc.crc_generator import CRCGenerator


@dataclass(slots=True)
class BinCRCResult:
    """Result for CRC calculated from a single BIN file."""

    bin_file_path: Path
    bin_file_name: str
    crc_hex: str
    crc_decimal: int


class CRCComparisonService:
    """Small reusable service that calculates CRC for a BIN file."""

    def __init__(self, crc_generator: CRCGenerator | None = None) -> None:
        self._crc_generator = crc_generator or CRCGenerator()

    def calculate_for_bin(self, bin_file_path: Path) -> BinCRCResult:
        """Calculate CRC for a BIN file and return normalized values."""
        result = self._crc_generator.generate_from_file(bin_file_path)
        crc_hex = self._normalize_hex(result.hex_value)
        return BinCRCResult(
            bin_file_path=Path(bin_file_path),
            bin_file_name=Path(bin_file_path).name,
            crc_hex=crc_hex,
            crc_decimal=result.decimal_value,
        )

    @staticmethod
    def _normalize_hex(value: str) -> str:
        text = value.strip().upper()
        if text.startswith("0X"):
            return text[2:]
        return text
