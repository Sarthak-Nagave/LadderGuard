from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from validators.chronology_validator import ChronologyValidator


class ChronologyValidatorTableParserTests(unittest.TestCase):
    def _create_pdf_with_table(self, path: Path, headers: list[str], rows: list[list[str]]) -> None:
        doc = SimpleDocTemplate(str(path), pagesize=letter)
        table = Table([headers] + rows)
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ]))
        doc.build([table])

    def test_parse_single_table_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Master" / "Initial"
            stage_folder.mkdir(parents=True, exist_ok=True)

            pdf_path = stage_folder / "chronology.pdf"
            headers = ["Testing Stage", "BIN File", "CRC", "Version", "Release Date", "Reason for Upgrade"]
            row = ["Master / Initial", "firmware_V1.00.bin", "0x1234ABCD", "V1.00", "14.05.2026", "Firmware stability improvements."]
            self._create_pdf_with_table(pdf_path, headers, [row])

            validator = ChronologyValidator(None)
            metadata = validator._extract_metadata(pdf_path)

            self.assertEqual(metadata["board"], "Master")
            self.assertEqual(metadata["stage"], "Initial")
            self.assertEqual(metadata["bin_file"], "firmware_V1.00.bin")
            self.assertEqual(metadata["crc"], "0x1234ABCD")
            self.assertEqual(metadata["version"], "V1.00")
            self.assertEqual(metadata["release_date"], "14.05.2026")
            self.assertEqual(metadata["reason_for_upgrade"], "Firmware stability improvements.")

    def test_parse_two_table_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Slave" / "Final"
            stage_folder.mkdir(parents=True, exist_ok=True)

            pdf_path = stage_folder / "chronology.pdf"
            headers = ["BIN File", "Testing Stage", "Version", "CRC", "Release Date", "Reason for Upgrade"]
            rows = [
                ["firmware_V2.00.bin", "Slave / Final", "V2.00", "1815415625", "14.05.2026", "Firmware stability improvements."],
                ["firmware_V1.00.bin", "Slave / Final", "V1.00", "1815415610", "14.03.2026", "-"]
            ]
            self._create_pdf_with_table(pdf_path, headers, rows)

            validator = ChronologyValidator(None)
            metadata = validator._extract_metadata(pdf_path)

            self.assertEqual(metadata["board"], "Slave")
            self.assertEqual(metadata["stage"], "Final")
            self.assertEqual(metadata["bin_file"], "firmware_V2.00.bin")
            self.assertEqual(metadata["crc"], "1815415625")
            self.assertEqual(metadata["version"], "V2.00")
            self.assertEqual(metadata["release_date"], "14.05.2026")
            self.assertEqual(metadata["reason_for_upgrade"], "Firmware stability improvements.")

    def test_parse_table_missing_crc(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Master" / "Initial"
            stage_folder.mkdir(parents=True, exist_ok=True)

            pdf_path = stage_folder / "chronology.pdf"
            headers = ["Testing Stage", "BIN File", "Version", "Release Date", "Reason for Upgrade"]
            row = ["Master / Initial", "firmware_V1.00.bin", "V1.00", "14.05.2026", "Firmware stability improvements."]
            self._create_pdf_with_table(pdf_path, headers, [row])

            validator = ChronologyValidator(None)
            metadata = validator._extract_metadata(pdf_path)

            self.assertEqual(metadata["crc"], None)
            self.assertEqual(metadata["bin_file"], "firmware_V1.00.bin")
            self.assertEqual(metadata["version"], "V1.00")

    def test_parse_wrapped_bin_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Slave" / "Initial"
            stage_folder.mkdir(parents=True, exist_ok=True)

            pdf_path = stage_folder / "chronology.pdf"
            headers = ["Testing Stage", "BIN File", "CRC", "Version", "Release Date", "Reason for Upgrade"]
            bin_filename = "LD_TCX03_TCX13_TCX33_TCX44_TCX38_DTCXXX-Initial_CALB_MST_MIBRX-4M_20.1-4_6_0_1_88_V1.00.bin"
            row = ["Slave / Initial", bin_filename, "1815415625", "V1.00", "14.05.2026", "Firmware stability improvements."]
            self._create_pdf_with_table(pdf_path, headers, [row])

            validator = ChronologyValidator(None)
            metadata = validator._extract_metadata(pdf_path)

            self.assertEqual(metadata["bin_file"], bin_filename)
            self.assertEqual(metadata["crc"], "1815415625")

    def test_parse_table_different_column_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chronology_folder = root / "7. Chronology"
            stage_folder = chronology_folder / "Master" / "Final"
            stage_folder.mkdir(parents=True, exist_ok=True)

            pdf_path = stage_folder / "chronology.pdf"
            headers = ["Release Date", "Reason for Upgrade", "Version", "CRC", "BIN File", "Testing Stage"]
            row = ["14.05.2026", "Firmware stability improvements.", "V1.00", "0x1234ABCD", "firmware_V1.00.bin", "Master / Final"]
            self._create_pdf_with_table(pdf_path, headers, [row])

            validator = ChronologyValidator(None)
            metadata = validator._extract_metadata(pdf_path)

            self.assertEqual(metadata["testing_stage"], "Master / Final")
            self.assertEqual(metadata["bin_file"], "firmware_V1.00.bin")
            self.assertEqual(metadata["crc"], "0x1234ABCD")
            self.assertEqual(metadata["version"], "V1.00")
            self.assertEqual(metadata["release_date"], "14.05.2026")
            self.assertEqual(metadata["reason_for_upgrade"], "Firmware stability improvements.")


if __name__ == "__main__":
    unittest.main()
