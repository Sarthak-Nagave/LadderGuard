"""CRC algorithm implementations and base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property


class CRCAlgorithm(ABC):
    """Base class for CRC algorithms."""

    name: str
    width: int
    polynomial: int
    initial_value: int
    final_xor: int
    reflect_input: bool
    reflect_output: bool

    def __init__(self) -> None:
        self._crc = self.initial_value

    @cached_property
    def _mask(self) -> int:
        return (1 << self.width) - 1

    @cached_property
    def _lookup_table(self) -> tuple[int, ...]:
        table: list[int] = []
        if self.reflect_input:
            for byte in range(256):
                crc = byte
                for _ in range(8):
                    if crc & 1:
                        crc = (crc >> 1) ^ self.polynomial
                    else:
                        crc >>= 1
                table.append(crc & self._mask)
        else:
            top_bit = 1 << (self.width - 1)
            for byte in range(256):
                crc = byte << (self.width - 8)
                for _ in range(8):
                    if crc & top_bit:
                        crc = ((crc << 1) ^ self.polynomial) & self._mask
                    else:
                        crc = (crc << 1) & self._mask
                table.append(crc)
        return tuple(table)

    def reset(self) -> None:
        self._crc = self.initial_value

    def update(self, data: bytes) -> None:
        if self.reflect_input:
            for byte in data:
                index = (self._crc ^ byte) & 0xFF
                self._crc = (self._crc >> 8) ^ self._lookup_table[index]
        else:
            shift = self.width - 8
            for byte in data:
                index = ((self._crc >> shift) ^ byte) & 0xFF
                self._crc = ((self._crc << 8) & self._mask) ^ self._lookup_table[index]

    def finalize(self) -> int:
        return (self._crc ^ self.final_xor) & self._mask

    def compute(self, data: bytes) -> int:
        self.reset()
        self.update(data)
        return self.finalize()


class CRC16Algorithm(CRCAlgorithm):
    name = "CRC16"
    width = 16
    polynomial = 0x1021
    initial_value = 0xFFFF
    final_xor = 0x0000
    reflect_input = False
    reflect_output = False


class CRC32Algorithm(CRCAlgorithm):
    name = "CRC32"
    width = 32
    polynomial = 0xEDB88320
    initial_value = 0xFFFFFFFF
    final_xor = 0xFFFFFFFF
    reflect_input = True
    reflect_output = True


class CRC32CAlgorithm(CRCAlgorithm):
    name = "CRC32C"
    width = 32
    polynomial = 0x82F63B78
    initial_value = 0xFFFFFFFF
    final_xor = 0xFFFFFFFF
    reflect_input = True
    reflect_output = True


class CRC64Algorithm(CRCAlgorithm):
    name = "CRC64"
    width = 64
    polynomial = 0x42F0E1EBA9EA3693
    initial_value = 0xFFFFFFFFFFFFFFFF
    final_xor = 0xFFFFFFFFFFFFFFFF
    reflect_input = False
    reflect_output = False
