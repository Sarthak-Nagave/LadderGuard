from __future__ import annotations

from pathlib import Path

from services.crc.crc_exceptions import (
    CRCEmptyFileError,
    CRCMissingFileError,
    CRCUnsupportedAlgorithmError,
)
from services.crc.crc_factory import CRCFactory
from services.crc.crc_generator import CRCGenerator


def test_crc_factory_returns_known_algorithms() -> None:
    available = CRCFactory.available_algorithms()
    assert "crc32" in available
    assert "crc16" in available
    assert "crc32c" in available
    assert "crc64" in available


def test_generate_crc_from_data_matches_expected_crc32() -> None:
    generator = CRCGenerator("CRC32")
    result = generator.generate_from_data(b"Selec Controls")

    assert result.algorithm == "CRC32"
    assert result.success is True
    assert result.file_size == len(b"Selec Controls")
    assert result.decimal_value == int(result.hex_value, 16)


def test_generate_crc_from_file_raises_missing_file(tmp_path: Path) -> None:
    generator = CRCGenerator()
    missing_file = tmp_path / "missing.bin"

    try:
        generator.generate_from_file(missing_file)
        assert False, "Expected CRCMissingFileError"
    except CRCMissingFileError:
        pass


def test_generate_crc_from_file_raises_for_empty_file(tmp_path: Path) -> None:
    generator = CRCGenerator()
    empty_file = tmp_path / "empty.bin"
    empty_file.write_bytes(b"")

    try:
        generator.generate_from_file(empty_file)
        assert False, "Expected CRCEmptyFileError"
    except CRCEmptyFileError:
        pass


def test_generate_crc_with_unsupported_algorithm_raises() -> None:
    try:
        CRCGenerator("UNKNOWN").generate_from_data(b"data")
        assert False, "Expected CRCUnsupportedAlgorithmError"
    except CRCUnsupportedAlgorithmError:
        pass
