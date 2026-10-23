"""Validate an experiment specification and its execution budget."""

import sys
from pathlib import Path

from slokern.contracts.spec import ExperimentSpec
from slokern.core.search.budget import BudgetValidationError, validate_budget


def validate_command(spec_file: str) -> int:
    """Return a process-style status code after validating a JSON spec."""
    try:
        spec = ExperimentSpec.model_validate_json(Path(spec_file).read_text())
        validate_budget(spec)
    except BudgetValidationError as exc:
        print(f"Budget validation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print("Spec and budget valid.")
    return 0
