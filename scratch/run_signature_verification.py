from pathlib import Path

from core.validation_engine import ValidationEngine
from core.validation_step import ValidationStep


def main() -> None:
    project = Path("C:/Users/SM 464/Desktop/Operational Package")
    summary = ValidationEngine().validate(project)
    print("OVERALL", summary.overall_status.name, "passed", summary.passed, "failed", summary.failed, "warnings", summary.warnings)
    for result in summary.results:
        if result.step in {
            ValidationStep.OPERATIONAL_FLOW,
            ValidationStep.TEST_REPORT,
            ValidationStep.AUTOMATION_INPUT,
            ValidationStep.LADDER_FLOW,
        }:
            print(result.step.name, result.status.name, "|", result.reason)


if __name__ == "__main__":
    main()
