"""Structured CRC result model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CRCResult:
    algorithm: str
    crc_value: int
    hex_value: str
    decimal_value: int
    file_size: int
    processing_time: float
    success: bool
    error_message: str | None = None

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return (
            f"CRCResult(algorithm={self.algorithm}, status={status}, "
            f"crc_value={self.hex_value}, file_size={self.file_size}, "
            f"processing_time={self.processing_time:.6f}s)"
        )
