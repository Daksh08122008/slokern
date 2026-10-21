import pytest

from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.contracts.spec import SLOSpec, SLOConstraint
from slokern.contracts.enums import FeasibilityVerdict, ReasonCode, EvidenceValidity
from slokern.core.evaluator.evaluate import evaluate_slo


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
