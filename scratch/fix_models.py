import pathlib

with open('services/chronology_generator/models.py', 'r', encoding='utf-8') as f:
    text = f.read()

replacement = """
@dataclass(slots=True)
class ProductInfo:
    source_pdf: Path | None = None
    mode: str = "Single"
    series_name: str | None = None
    single_product: str | None = None
    products: list[str] = field(default_factory=list)
    page_number: int = -1
    parse_status: str = "Pending"
    warning: str = ""

@dataclass(slots=True)
class ChronologyEntry:
"""

text = text.replace("@dataclass(slots=True)\nclass ChronologyEntry:", replacement)
text = text.replace('automation_setup_modification: str = ""', 'automation_setup_modification: str = ""\n    test_report_path: Path | None = None')

with open('services/chronology_generator/models.py', 'w', encoding='utf-8') as f:
    f.write(text)
