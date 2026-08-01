from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.crc.crc_comparison_service import CRCComparisonService


class CRCComparisonServiceTests(unittest.TestCase):
    def test_calculates_crc_for_single_bin_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_file = root / "firmware.bin"
            bin_file.write_bytes(b"firmware-content")

            service = CRCComparisonService()
            result = service.calculate_for_bin(bin_file)

            self.assertEqual(result.bin_file_path, bin_file)
            self.assertEqual(result.bin_file_name, "firmware.bin")
            self.assertTrue(bool(result.crc_hex))
            self.assertGreater(result.crc_decimal, 0)

    def test_crc_is_deterministic_for_same_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_file = root / "a.bin"
            second_file = root / "b.bin"
            first_file.write_bytes(b"same-content")
            second_file.write_bytes(b"same-content")

            service = CRCComparisonService()
            first = service.calculate_for_bin(first_file)
            second = service.calculate_for_bin(second_file)

            self.assertEqual(first.crc_hex, second.crc_hex)
            self.assertEqual(first.crc_decimal, second.crc_decimal)


if __name__ == "__main__":
    unittest.main()
