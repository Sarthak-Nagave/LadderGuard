from pathlib import Path
from core.validation_engine import ValidationEngine

def run():
    target_dir = Path(r"c:\Users\SM 464\Desktop\Operational Package")
    engine = ValidationEngine()
    summary = engine.validate(target_dir)

    for r in summary.results:
        print(f"[{r.status.name}] {r.step.name if hasattr(r.step, 'name') else r.step}: {r.reason}")

if __name__ == "__main__":
    run()
