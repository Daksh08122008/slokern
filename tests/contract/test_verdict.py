import pytest
from pydantic import ValidationError

from slokern.contracts.enums import EvidenceValidity, FeasibilityVerdict, ReasonCode
from slokern.contracts.verdict import ConstraintEvaluation, FeasibilityResult


def test_constraint_evaluation_valid() -> None:
    eval = ConstraintEvaluation(
        metric_name="ttft",
        statistic="p95",
        observed_value=250.0,
        required_threshold=200.0,
        operator="<=",
        passed=False,
        reason_code=ReasonCode.TTFT_P95_EXCEEDED,
    )
    assert eval.metric_name == "ttft"
    assert eval.statistic == "p95"
    assert eval.observed_value == 250.0
    assert eval.required_threshold == 200.0
    assert eval.operator == "<="
    assert eval.passed is False
    assert eval.reason_code == ReasonCode.TTFT_P95_EXCEEDED

def test_constraint_evaluation_valid_optional() -> None:
    eval = ConstraintEvaluation(
        metric_name="ttft",
        statistic="p95",
        required_threshold=200.0,
        operator="<=",
        reason_code=ReasonCode.INSUFFICIENT_SAMPLES,
    )
    assert eval.observed_value is None
    assert eval.passed is None

def test_constraint_evaluation_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        ConstraintEvaluation(
            metric_name="ttft",
            statistic="p95",
            required_threshold=200.0,
            operator="<=",
            reason_code=ReasonCode.INSUFFICIENT_SAMPLES,
            extra_field="should fail",
        )

def test_feasibility_result_valid() -> None:
    eval = ConstraintEvaluation(
        metric_name="ttft",
        statistic="p95",
        observed_value=250.0,
        required_threshold=200.0,
        operator="<=",
        passed=False,
        reason_code=ReasonCode.TTFT_P95_EXCEEDED,
    )
    res = FeasibilityResult(
        policy_version="1.0.0",
        run_id="run-1",
        overall_verdict=FeasibilityVerdict.INFEASIBLE,
        constraint_evaluations=[eval],
        validity_status=EvidenceValidity.VALID,
    )
    assert res.policy_version == "1.0.0"
    assert res.run_id == "run-1"
    assert res.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert len(res.constraint_evaluations) == 1
    assert res.validity_status == EvidenceValidity.VALID
    assert res.audit_notes is None

def test_feasibility_result_valid_optional() -> None:
    res = FeasibilityResult(
        policy_version="1.0.0",
        run_id="run-1",
        overall_verdict=FeasibilityVerdict.INCONCLUSIVE,
        constraint_evaluations=[],
        validity_status=EvidenceValidity.CONTAMINATED,
        audit_notes="Load generator saturated",
    )
    assert res.audit_notes == "Load generator saturated"

def test_feasibility_result_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        FeasibilityResult(
            policy_version="1.0.0",
            run_id="run-1",
            overall_verdict=FeasibilityVerdict.INFEASIBLE,
            constraint_evaluations=[],
            validity_status=EvidenceValidity.VALID,
            extra_field="should fail",
        )
