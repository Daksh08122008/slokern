"""Validation for the declared experiment budget and verification policy."""

import math

from slokern.contracts.spec import ExperimentSpec


class BudgetValidationError(ValueError):
    """Raised when an experiment budget cannot safely be executed."""


def validate_budget(spec: ExperimentSpec) -> None:
    """Validate finite, positive limits before any experiment run starts.

    The optional cost ceiling is validated here but cannot be enforced by the
    current Mode B search controller without an authoritative price source.
    The controller therefore rejects a configured cost ceiling before running.
    """
    budget = spec.budget
    if budget.max_candidates < 1:
        raise BudgetValidationError(
            f"budget.max_candidates must be >= 1, got {budget.max_candidates}"
        )
    if budget.max_wallclock_seconds < 1:
        raise BudgetValidationError(
            "budget.max_wallclock_seconds must be >= 1, "
            f"got {budget.max_wallclock_seconds}"
        )
    if budget.max_cost_limit is not None:
        if not math.isfinite(budget.max_cost_limit) or budget.max_cost_limit <= 0:
            raise BudgetValidationError(
                "budget.max_cost_limit must be finite and > 0 when provided, "
                f"got {budget.max_cost_limit}"
            )

    policy = spec.verification_policy
    if policy.repetitions < 1:
        raise BudgetValidationError(
            "verification_policy.repetitions must be >= 1, "
            f"got {policy.repetitions}"
        )
    if (
        not math.isfinite(policy.duration_multiplier)
        or policy.duration_multiplier <= 0
    ):
        raise BudgetValidationError(
            "verification_policy.duration_multiplier must be finite and > 0, "
            f"got {policy.duration_multiplier}"
        )
