"""
Purpose: Unit tests for core/search/budget: validate_budget, BudgetLimiter, and 6-run budget enforcement.
Owner: Rajdeep (Historical design: Rohan)
"""

import math
import time

import pytest

from slokern.contracts.enums import ArrivalMode
from slokern.contracts.spec import (
    ExperimentBudget as ContractExperimentBudget,
)
from slokern.contracts.spec import (
    ExperimentSpec,
    ExperimentVerificationPolicy,
    SLOSpec,
    WorkloadSpec,
)
from slokern.core.search.budget import (
    BudgetExhaustedError,
    BudgetLimiter,
    BudgetValidationError,
    ExperimentBudget,
    validate_budget,
)


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
        budget=ContractExperimentBudget(
            max_candidates=max_candidates,
            max_wallclock_seconds=max_wallclock_seconds,
            max_cost_limit=max_cost_limit,
        ),
        verification_policy=ExperimentVerificationPolicy(
            repetitions=repetitions,
            duration_multiplier=duration_multiplier,
        ),
    )


# --- Preflight Validation Tests (origin/main) ---


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


# --- Runtime BudgetLimiter Tests (origin/2x2) ---


def test_budget_limiter_defaults():
    limiter = BudgetLimiter()
    assert limiter.max_total_runs == 6
    assert limiter.max_search_runs == 5
    assert limiter.max_verification_runs == 1
    assert limiter.runs_executed == 0
    assert limiter.search_runs_executed == 0
    assert limiter.verification_runs_executed == 0
    assert limiter.remaining_total_runs == 6
    assert limiter.remaining_search_runs == 5
    assert limiter.remaining_verification_runs == 1
    assert limiter.is_exhausted() is False
    assert limiter.is_search_exhausted() is False
    assert limiter.can_execute_search_run() is True
    assert limiter.can_execute_verification_run() is True


def test_budget_limiter_invalid_bounds():
    with pytest.raises(ValueError):
        BudgetLimiter(max_total_runs=5, max_search_runs=5, max_verification_runs=1)


def test_budget_limiter_search_run_progression():
    limiter = BudgetLimiter(max_total_runs=6, max_search_runs=5, max_verification_runs=1)

    # Execute 5 search runs (1 baseline + 4 candidates)
    for i in range(5):
        assert limiter.can_execute_search_run() is True
        limiter.record_search_run()
        assert limiter.search_runs_executed == i + 1
        assert limiter.runs_executed == i + 1

    # Search phase must be strictly exhausted now
    assert limiter.search_runs_executed == 5
    assert limiter.runs_executed == 5
    assert limiter.is_search_exhausted() is True
    assert limiter.can_execute_search_run() is False
    assert limiter.remaining_search_runs == 0

    # Attempting a 6th search run must fail with BudgetExhaustedError
    with pytest.raises(BudgetExhaustedError):
        limiter.record_search_run()

    # Invariant: exactly 1 run budget remains for independent verification!
    assert limiter.remaining_total_runs == 1
    assert limiter.remaining_verification_runs == 1
    assert limiter.can_execute_verification_run() is True

    # Record the 1 verification run
    limiter.record_verification_run()
    assert limiter.verification_runs_executed == 1
    assert limiter.runs_executed == 6
    assert limiter.is_exhausted() is True
    assert limiter.can_execute_verification_run() is False

    # Attempting another verification run must fail
    with pytest.raises(BudgetExhaustedError):
        limiter.record_verification_run()


def test_budget_limiter_alias_experiment_budget():
    budget = ExperimentBudget(max_total_runs=4, max_search_runs=3, max_verification_runs=1)
    assert isinstance(budget, BudgetLimiter)
    assert budget.max_total_runs == 4
    assert budget.max_search_runs == 3


def test_budget_limiter_stopping_reason():
    limiter = BudgetLimiter()

    # Default before running
    assert limiter.get_stopping_reason(space_exhausted=True) == "space_exhausted"

    # Cancellation precedence
    assert limiter.get_stopping_reason(cancelled=True) == "cancelled"

    # Early convergence
    assert limiter.get_stopping_reason(early_convergence=True) == "early_convergence"

    # When search budget is exhausted
    for _ in range(5):
        limiter.record_search_run()
    assert limiter.get_stopping_reason() == "budget_exhausted"


def test_budget_limiter_timeout():
    # Timeout of 0.05 seconds
    limiter = BudgetLimiter(timeout_seconds=0.05)
    assert limiter.is_timed_out() is False
    assert limiter.can_execute_search_run() is True

    time.sleep(0.08)
    assert limiter.is_timed_out() is True
    assert limiter.can_execute_search_run() is False
    assert limiter.can_execute_verification_run() is False

    with pytest.raises(BudgetExhaustedError) as exc_info:
        limiter.record_search_run()
    assert "timed out" in str(exc_info.value)
    assert limiter.get_stopping_reason() == "timeout"
