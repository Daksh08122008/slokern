import math
import pytest

from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.contracts.spec import SLOSpec, SLOConstraint
from slokern.contracts.enums import FeasibilityVerdict, ReasonCode, EvidenceValidity
from slokern.core.evaluator.evaluate import (
    evaluate_slo,
    evaluate_constraint,
    get_observed_value,
    get_reason_code_for_failure,
)


@pytest.fixture
def base_slo() -> SLOSpec:
    return SLOSpec(
        slo_id="slo-test",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=200.0, unit="ms", operator="<="),
            SLOConstraint(metric_name="itl", statistic="p95", threshold=50.0, unit="ms", operator="<="),
            SLOConstraint(metric_name="request_throughput", statistic="mean", threshold=10.0, unit="requests/s", operator=">="),
        ]
    )


@pytest.fixture
def base_metrics() -> MetricSet:
    return MetricSet(
        metric_version="1.0.0",
        run_id="run-123",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=20.0,
        achieved_load_rps=19.9,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p95=150.0, p50=100.0),
        itl_ms=PercentileDistribution(p95=40.0, p50=20.0),
        e2e_latency_ms=PercentileDistribution(p95=1000.0, p50=800.0),
        request_throughput_rps=15.0,
        token_throughput_tps=500.0,
        error_rate=0.0
    )


def test_evaluator_feasible(base_metrics: MetricSet, base_slo: SLOSpec):
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.FEASIBLE
    assert result.validity_status == EvidenceValidity.VALID
    assert len(result.constraint_evaluations) == 3
    for c in result.constraint_evaluations:
        assert c.passed is True
        assert c.reason_code == ReasonCode.HARD_CONSTRAINTS_PASSED


def test_evaluator_infeasible_ttft(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.ttft_ms.p95 = 250.0
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert result.validity_status == EvidenceValidity.VALID

    ttft_eval = next(c for c in result.constraint_evaluations if c.metric_name == "ttft")
    assert ttft_eval.passed is False
    assert ttft_eval.reason_code == ReasonCode.TTFT_P95_EXCEEDED


def test_evaluator_infeasible_throughput(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.request_throughput_rps = 5.0
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert result.validity_status == EvidenceValidity.VALID

    tp_eval = next(c for c in result.constraint_evaluations if c.metric_name == "request_throughput")
    assert tp_eval.passed is False
    assert tp_eval.reason_code == ReasonCode.THROUGHPUT_DEFICIT


def test_evaluator_inconclusive_generator_saturated(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.generator_saturated = True
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.CONTAMINATED
    for c in result.constraint_evaluations:
        assert c.reason_code == ReasonCode.GENERATOR_SATURATED


def test_evaluator_inconclusive_insufficient_samples(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.sample_count = 5
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.VALID
    for c in result.constraint_evaluations:
        assert c.reason_code == ReasonCode.INSUFFICIENT_SAMPLES


def test_evaluator_inconclusive_missing_metric(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.ttft_ms.p95 = None
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.VALID

    ttft_eval = next(c for c in result.constraint_evaluations if c.metric_name == "ttft")
    assert ttft_eval.passed is None
    assert ttft_eval.reason_code == ReasonCode.MISSING_REQUIRED_METRIC


def test_evaluator_boundary_exact_match(base_metrics: MetricSet, base_slo: SLOSpec):
    # threshold is 200.0, operator <=
    base_metrics.ttft_ms.p95 = 200.0
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.FEASIBLE
    ttft_eval = next(c for c in result.constraint_evaluations if c.metric_name == "ttft")
    assert ttft_eval.passed is True


def test_evaluator_inconclusive_nan_latency(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.ttft_ms.p95 = float("nan")
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.INVALID
    ttft_eval = next(c for c in result.constraint_evaluations if c.metric_name == "ttft")
    assert ttft_eval.passed is None
    assert ttft_eval.reason_code == ReasonCode.MISSING_REQUIRED_METRIC
    assert result.audit_notes is not None
    assert "Invalid observation" in result.audit_notes


def test_evaluator_inconclusive_negative_latency(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.ttft_ms.p95 = -10.0
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.INVALID
    ttft_eval = next(c for c in result.constraint_evaluations if c.metric_name == "ttft")
    assert ttft_eval.passed is None
    assert ttft_eval.reason_code == ReasonCode.MISSING_REQUIRED_METRIC
    assert result.audit_notes is not None
    assert "Invalid observation" in result.audit_notes


def test_evaluator_inconclusive_nan_with_generator_saturated(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.generator_saturated = True
    base_metrics.ttft_ms.p95 = float("nan")
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.CONTAMINATED
    for c in result.constraint_evaluations:
        assert c.reason_code == ReasonCode.GENERATOR_SATURATED


def test_evaluator_token_throughput_pass(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-tps-pass",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="token_throughput", statistic="mean", threshold=400.0, unit="requests/s", operator=">="),
        ],
    )
    base_metrics.token_throughput_tps = 500.0
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.FEASIBLE
    assert result.validity_status == EvidenceValidity.VALID
    tps_eval = result.constraint_evaluations[0]
    assert tps_eval.observed_value == 500.0
    assert tps_eval.passed is True
    assert tps_eval.reason_code == ReasonCode.HARD_CONSTRAINTS_PASSED


def test_evaluator_token_throughput_fail(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-tps-fail",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="token_throughput", statistic="mean", threshold=600.0, unit="requests/s", operator=">="),
        ],
    )
    base_metrics.token_throughput_tps = 500.0
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert result.validity_status == EvidenceValidity.VALID
    tps_eval = result.constraint_evaluations[0]
    assert tps_eval.observed_value == 500.0
    assert tps_eval.passed is False
    assert tps_eval.reason_code == ReasonCode.THROUGHPUT_DEFICIT
    assert "token_throughput mean >= 600.0" in result.audit_notes


def test_evaluator_token_throughput_boundary_match(base_metrics: MetricSet):
    slo_ge = SLOSpec(
        slo_id="slo-tps-ge",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="token_throughput", statistic="mean", threshold=500.0, unit="requests/s", operator=">="),
        ],
    )
    base_metrics.token_throughput_tps = 500.0
    result_ge = evaluate_slo(base_metrics, slo_ge)
    assert result_ge.overall_verdict == FeasibilityVerdict.FEASIBLE
    assert result_ge.constraint_evaluations[0].passed is True

    slo_gt = SLOSpec(
        slo_id="slo-tps-gt",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="token_throughput", statistic="mean", threshold=500.0, unit="requests/s", operator=">"),
        ],
    )
    result_gt = evaluate_slo(base_metrics, slo_gt)
    assert result_gt.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert result_gt.constraint_evaluations[0].passed is False
    assert result_gt.constraint_evaluations[0].reason_code == ReasonCode.THROUGHPUT_DEFICIT


def test_evaluator_itl_p50_failure_reason_code(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-itl-p50",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="itl", statistic="p50", threshold=15.0, unit="ms", operator="<="),
        ],
    )
    base_metrics.itl_ms.p50 = 20.0
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.INFEASIBLE
    itl_eval = result.constraint_evaluations[0]
    assert itl_eval.passed is False
    assert itl_eval.reason_code == ReasonCode.ITL_P95_EXCEEDED
    assert "itl p50 <= 15.0" in result.audit_notes


def test_evaluator_itl_p50_pass(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-itl-p50-pass",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="itl", statistic="p50", threshold=25.0, unit="ms", operator="<="),
        ],
    )
    base_metrics.itl_ms.p50 = 20.0
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.FEASIBLE
    itl_eval = result.constraint_evaluations[0]
    assert itl_eval.passed is True
    assert itl_eval.reason_code == ReasonCode.HARD_CONSTRAINTS_PASSED


def test_evaluator_unconstrained_dropped_requests_audited(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.failed_request_count = 5
    base_metrics.error_rate = 0.05
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.FEASIBLE
    assert result.audit_notes is not None
    assert result.audit_notes != "All hard constraints satisfied."
    assert "5" in result.audit_notes
    assert "unconstrained" in result.audit_notes.lower()
    assert "dropped" in result.audit_notes.lower() or "failed" in result.audit_notes.lower()


def test_evaluator_constrained_error_rate_failure(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-err-fail",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="error_rate", statistic="mean", threshold=0.01, unit="fraction", operator="<="),
        ],
    )
    base_metrics.failed_request_count = 2
    base_metrics.error_rate = 0.02
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.INFEASIBLE
    err_eval = result.constraint_evaluations[0]
    assert err_eval.passed is False
    assert err_eval.reason_code == ReasonCode.ERROR_RATE_EXCEEDED


def test_evaluator_zero_dropped_requests_clean_audit(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.failed_request_count = 0
    base_metrics.error_rate = 0.0
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.FEASIBLE
    assert result.audit_notes == "All hard constraints satisfied."


def test_evaluate_constraint_operators_and_edges():
    assert evaluate_constraint(None, 10.0, "<=") is None
    assert evaluate_constraint(10.0, None, "<=") is None
    assert evaluate_constraint(math.nan, 10.0, "<=") is None
    assert evaluate_constraint(-0.01, 10.0, "<=") is None
    assert evaluate_constraint(10.0, math.nan, "<=") is None
    assert evaluate_constraint(10.0, -5.0, "<=") is None
    assert evaluate_constraint(float("inf"), 10.0, "<=") is None
    assert evaluate_constraint(10.0, float("inf"), "<=") is None
    assert evaluate_constraint(0.0, 10.0, ">=") is False
    assert evaluate_constraint(0.0, 10.0, "<=") is True
    assert evaluate_constraint(10.0, 10.0, "<=") is True
    assert evaluate_constraint(10.0, 10.0, "<") is False
    assert evaluate_constraint(10.0, 10.0, ">=") is True
    assert evaluate_constraint(10.0, 10.0, ">") is False
    assert evaluate_constraint(5.0, 10.0, "==") is None


def test_get_observed_value_mappings(base_metrics: MetricSet):
    assert get_observed_value(base_metrics, "request_throughput", "mean") == 15.0
    assert get_observed_value(base_metrics, "request_throughput_rps", "mean") == 15.0
    assert get_observed_value(base_metrics, "token_throughput", "mean") == 500.0
    assert get_observed_value(base_metrics, "token_throughput_tps", "mean") == 500.0
    assert get_observed_value(base_metrics, "error_rate", "mean") == 0.0
    assert get_observed_value(base_metrics, "ttft", "p95") == 150.0
    assert get_observed_value(base_metrics, "ttft_ms", "p95") == 150.0
    assert get_observed_value(base_metrics, "itl", "p50") == 20.0
    assert get_observed_value(base_metrics, "itl_ms", "p50") == 20.0
    assert get_observed_value(base_metrics, "e2e_latency", "p95") == 1000.0
    assert get_observed_value(base_metrics, "e2e_latency_ms", "p95") == 1000.0
    assert get_observed_value(base_metrics, "nonexistent", "mean") is None


def test_get_reason_code_for_failure_mappings():
    assert get_reason_code_for_failure("ttft", "p95", "<=") == ReasonCode.TTFT_P95_EXCEEDED
    assert get_reason_code_for_failure("ttft", "p50", "<=") == ReasonCode.TTFT_P50_EXCEEDED
    assert get_reason_code_for_failure("ttft", "p90", "<=") == ReasonCode.TTFT_P95_EXCEEDED
    assert get_reason_code_for_failure("ttft", "p99", "<=") == ReasonCode.TTFT_P95_EXCEEDED
    assert get_reason_code_for_failure("ttft", "mean", "<=") == ReasonCode.TTFT_P95_EXCEEDED
    assert get_reason_code_for_failure("ttft_ms", "p95", "<=") == ReasonCode.TTFT_P95_EXCEEDED
    assert get_reason_code_for_failure("itl", "p95", "<=") == ReasonCode.ITL_P95_EXCEEDED
    assert get_reason_code_for_failure("itl", "p50", "<=") == ReasonCode.ITL_P95_EXCEEDED
    assert get_reason_code_for_failure("itl_ms", "p95", "<=") == ReasonCode.ITL_P95_EXCEEDED
    assert get_reason_code_for_failure("e2e_latency", "p99", "<=") == ReasonCode.E2E_LATENCY_EXCEEDED
    assert get_reason_code_for_failure("e2e_latency_ms", "p99", "<=") == ReasonCode.E2E_LATENCY_EXCEEDED
    assert get_reason_code_for_failure("error_rate", "mean", "<=") == ReasonCode.ERROR_RATE_EXCEEDED
    assert get_reason_code_for_failure("request_throughput", "mean", ">=") == ReasonCode.THROUGHPUT_DEFICIT
    assert get_reason_code_for_failure("request_throughput_rps", "mean", ">=") == ReasonCode.THROUGHPUT_DEFICIT
    assert get_reason_code_for_failure("token_throughput", "mean", ">=") == ReasonCode.THROUGHPUT_DEFICIT
    assert get_reason_code_for_failure("token_throughput_tps", "mean", ">=") == ReasonCode.THROUGHPUT_DEFICIT
    assert get_reason_code_for_failure("ttft", "p95", "INVALID") == ReasonCode.UNSUPPORTED_OPERATOR
    assert get_reason_code_for_failure("unknown", "mean", "<=") == ReasonCode.MISSING_REQUIRED_METRIC


def test_evaluator_inconclusive_nan_threshold(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-nan-thresh",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=float("nan"), unit="ms", operator="<="),
        ],
    )
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.INVALID
    assert result.constraint_evaluations[0].passed is None
    assert result.constraint_evaluations[0].reason_code == ReasonCode.MISSING_REQUIRED_METRIC
    assert "Invalid threshold for ttft: nan" in result.audit_notes


def test_evaluator_inconclusive_negative_threshold(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-neg-thresh",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=-50.0, unit="ms", operator="<="),
        ],
    )
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.INVALID
    assert result.constraint_evaluations[0].passed is None
    assert "Invalid threshold for ttft: -50.0" in result.audit_notes


def test_evaluator_inconclusive_inf_latency(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.ttft_ms.p95 = float("inf")
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.INVALID
    ttft_eval = next(c for c in result.constraint_evaluations if c.metric_name == "ttft")
    assert ttft_eval.passed is None
    assert ttft_eval.reason_code == ReasonCode.MISSING_REQUIRED_METRIC
    assert "Invalid observation for ttft: inf" in result.audit_notes


def test_evaluator_inconclusive_inf_throughput(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-inf-tp",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="token_throughput", statistic="mean", threshold=100.0, unit="requests/s", operator=">="),
        ],
    )
    base_metrics.token_throughput_tps = float("inf")
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.INVALID
    assert result.constraint_evaluations[0].passed is None
    assert "Invalid observation for token_throughput: inf" in result.audit_notes


def test_evaluator_multiple_issues_audit_notes_preservation(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-multi-issues",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=100.0, unit="ms", operator="<="),  # fails (150 > 100)
            SLOConstraint(metric_name="itl", statistic="p95", threshold=50.0, unit="ms", operator="<="),   # invalid (NaN)
            SLOConstraint(metric_name="nonexistent", statistic="mean", threshold=1.0, unit="ms", operator="<="),  # missing (None)
        ],
    )
    base_metrics.itl_ms.p95 = float("nan")
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.INVALID
    assert "Constraint failed: ttft p95 <= 100.0" in result.audit_notes
    assert "Invalid observation for itl: nan" in result.audit_notes
    assert "Missing required metric: nonexistent" in result.audit_notes


def test_evaluator_unconstrained_dropped_requests_with_infeasible_verdict(base_metrics: MetricSet, base_slo: SLOSpec):
    base_metrics.ttft_ms.p95 = 300.0  # fails
    base_metrics.failed_request_count = 7
    base_metrics.error_rate = 0.07
    result = evaluate_slo(base_metrics, base_slo)

    assert result.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert "Constraint failed: ttft p95 <= 200.0" in result.audit_notes
    assert "7 unconstrained dropped/failed request(s)" in result.audit_notes


def test_evaluator_unsupported_operator_inconclusive(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-bad-op",
        min_sample_count=10,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=200.0, unit="ms", operator="<="),
        ],
    )
    object.__setattr__(slo.constraints[0], "operator", "~=")
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.constraint_evaluations[0].passed is None
    assert result.constraint_evaluations[0].reason_code == ReasonCode.UNSUPPORTED_OPERATOR
    assert "Unsupported operator: ~=" in result.audit_notes


def test_evaluator_empty_constraints(base_metrics: MetricSet):
    slo = SLOSpec(
        slo_id="slo-empty",
        min_sample_count=10,
        constraints=[],
    )
    result = evaluate_slo(base_metrics, slo)

    assert result.overall_verdict == FeasibilityVerdict.FEASIBLE
    assert result.validity_status == EvidenceValidity.VALID
    assert result.audit_notes == "All hard constraints satisfied."
    assert len(result.constraint_evaluations) == 0


def test_evaluate_constraint_boolean_rejected():
    assert evaluate_constraint(True, 10.0, '<=') is None
    assert evaluate_constraint(False, 10.0, '<=') is None
    assert evaluate_constraint(10.0, True, '<=') is None
    assert evaluate_constraint(10.0, False, '<=') is None
