from pathlib import Path

from core.validation_step import ValidationStep
from services.signature_reader import SignatureReaderService
from validators.document_validator import DocumentValidator
from services.file_search import FileSearchService
from services.file_reader import FileReaderService


def inspect(doc_path: str, step: ValidationStep, folder_name: str) -> None:
    validator = DocumentValidator(step, folder_name, FileSearchService(), FileReaderService(), SignatureReaderService())
    snapshots = SignatureReaderService.read_page_snapshots(Path(doc_path))
    specs = validator._section_specs_for_folder()
    print("\n===", Path(doc_path).name, "===")
    for snapshot in snapshots:
        anchors = []
        for section in specs:
            aliases = [str(a) for a in section["aliases"]]
            anchor = validator._find_section_anchor(snapshot.words, snapshot.text_blocks, aliases)
            anchors.append(anchor)
        for idx, section in enumerate(specs):
            anchor = anchors[idx]
            if anchor is None:
                continue
            region = validator._build_role_region(anchor, anchors, snapshot.page_width, snapshot.page_height)
            print(f"page={snapshot.page_number} role={section['section']} anchor={anchor.rect} region={region}")
            for rect in snapshot.vector_rects:
                if validator._rect_intersects(region, rect):
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    print("  vector", rect, "w", round(w, 1), "h", round(h, 1))


def main() -> None:
    inspect(
        "C:/Users/SM 464/Desktop/Operational Package/6. Ladder Flow/LRPS480 SERIES_Ladder flow-sgn.pdf",
        ValidationStep.LADDER_FLOW,
        "6. Ladder Flow",
    )
    inspect(
        "C:/Users/SM 464/Desktop/Operational Package/4. Test Report/Slave/Final/S-final_Functional validation report_JIG-sgn.pdf",
        ValidationStep.TEST_REPORT,
        "4. Test Report",
    )


if __name__ == "__main__":
    main()
