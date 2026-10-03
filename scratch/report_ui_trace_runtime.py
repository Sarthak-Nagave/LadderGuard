from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.validation_engine import ValidationEngine
from reports.report_model import ReportDataModel
from reports.report_window import ReportWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])

    project = Path("../mock_e2e_project").resolve()
    summary = ValidationEngine().validate(project)
    model = ReportDataModel.from_summary(summary)

    print(f"MODEL sections={len(model.sections)}")
    for index, section in enumerate(model.sections):
        print(f"SECTION {index} title={section.title!r} details={len(section.details)} reason={section.reason!r}")
        for card_index, card in enumerate(section.details):
            print(f"  CARD {card_index} title={card.title!r} rows={len(card.rows)} children={len(card.children)}")
            for row_index, row in enumerate(card.rows):
                print(f"    ROW {row_index} label={row.label!r} value={row.value!r}")

    window = ReportWindow(model)
    print(f"SECTIONS_LAYOUT_COUNT={window._sections_layout.count()}")


if __name__ == "__main__":
    main()
