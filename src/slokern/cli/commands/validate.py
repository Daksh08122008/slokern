import sys

from slokern.contracts.spec import ExperimentSpec
from slokern.core.search.budget import BudgetValidationError, validate_budget

# flake8: noqa: E501,F401,F811,E402,E302,E305,W293


def validate_command(spec_file: str) -> int:
    try:
        with open(spec_file, "r") as f:
            content = f.read()

        spec = ExperimentSpec.model_validate_json(content)
        validate_budget(spec)
        print("Spec and budget valid.")
        return 0
    except BudgetValidationError as e:
        print(f"Budget validation failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Validation failed: {e}", file=sys.stderr)
        return 1
