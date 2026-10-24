"""Budget boundary tests for search preflight validation."""

import math

import pytest

from slokern.contracts.enums import ArrivalMode
from slokern.contracts.spec import (
    ExperimentBudget,
    ExperimentSpec,
    ExperimentVerificationPolicy,
    SLOSpec,
    WorkloadSpec,
)
from slokern.core.search.budget import BudgetValidationError, validate_budget


def make_spec(
    *,
    max_candidates=4,
    max_wallclock_seconds=300,
    max_cost_limit=None,
    repetitions=1,
    duration_multiplier=1.0,
):
    return ExperimentSpec(
        experiment_id="test-budget",
        workload=WorkloadSpec(
            schema_version="1.0.0",
            workload_name="test",
            fixture_id="fixture",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=1.0,
            concurrency_limit=1,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=8,
            max_output_tokens=8,
        ),
        slo=SLOSpec(slo_id="slo", constraints=[], min_sample_count=1),
        search_space={},
        budget=ExperimentBudget(
            max_candidates=max_candidates,
            max_wallclock_seconds=max_wallclock_seconds,
            max_cost_limit=max_cost_limit,
        ),
        verification_policy=ExperimentVerificationPolicy(
            repetitions=repetitions,
            duration_multiplier=duration_multiplier,
        ),
    )


def test_validate_budget_accepts_positive_limits():
    validate_budget(make_spec(max_cost_limit=10.0))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("max_candidates", 0, "max_candidates must be >= 1"),
        ("max_wallclock_seconds", 0, "max_wallclock_seconds must be >= 1"),
        ("max_cost_limit", 0.0, "max_cost_limit must be finite and > 0"),
        ("max_cost_limit", -1.0, "max_cost_limit must be finite and > 0"),
        ("max_cost_limit", math.inf, "max_cost_limit must be finite and > 0"),
        ("repetitions", 0, "repetitions must be >= 1"),
        ("duration_multiplier", 0.0, "duration_multiplier must be finite and > 0"),
        ("duration_multiplier", math.nan, "duration_multiplier must be finite and > 0"),
    ],
)
def test_validate_budget_rejects_invalid_limits(field, value, message):
    kwargs = {field: value}
    with pytest.raises(BudgetValidationError, match=message):
        validate_budget(make_spec(**kwargs))
