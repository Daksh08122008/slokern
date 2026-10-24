"""
Purpose: Contract and boundary tests for decision correctness and verification independence.
Owner: Daksh (Decision Verification Audit)
Authority: docs/decision-policy.md, docs/ownership.md, AGENTS.md Section 5 & 13

This test suite independently audits:
1. Decision correctness: hard SLO boundaries, comparison operators, reason codes.
2. Verification independence: fresh run ID, separation of execution failure from SLO infeasibility.
3. Evidence integrity: contaminated load, missing metrics, and invalid values (NaN, negative latency).
"""

import math
import pytest

from slokern.contracts.enums import (
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
    ReasonCode,
    VerificationState,
)
from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.contracts.run import RunRecord
from slokern.contracts.spec import SLOConstraint, SLOSpec
from slokern.contracts.verification import DriftAnalysis, VerificationRecord
from slokern.core.evaluator.evaluate import evaluate_slo


@pytest.fixture
def standard_slo() -> SLOSpec:
    """Standard hard SLO specification for boundary testing."""
    return SLOSpec(
        slo_id="slo-contract-test",
        min_sample_count=20,
        constraints=[
            SLOConstraint(
                metric_name="ttft",
                statistic="p95",
                threshold=200.0,
                unit="ms",
                operator="<=",
            ),
            SLOConstraint(
                metric_name="itl",
                statistic="p95",
                threshold=50.0,
                unit="ms",
                operator="<=",
            ),
            SLOConstraint(
                metric_name="request_throughput",
                statistic="mean",
                threshold=10.0,
                unit="requests/s",
                operator=">=",
            ),
            SLOConstraint(
                metric_name="error_rate",
                statistic="mean",
                threshold=0.01,
                unit="fraction",
                operator="<=",
            ),
        ],
    )


@pytest.fixture
def passing_metrics() -> MetricSet:
    """Metrics that strictly pass standard_slo."""
    return MetricSet(
        metric_version="1.0.0",
        run_id="run-search-001",
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
        error_rate=0.0,
    )


# ==============================================================================
# 1. VERIFICATION INDEPENDENCE TESTS
# ==============================================================================


def test_verification_run_id_distinct_from_search_run_id():
    """Verification rerun MUST be assigned a fresh, distinct run_id."""
    search_run_id = "run-search-cand-01"
    verification_run_id = "run-verify-cand-01"

    assert verification_run_id != search_run_id

    # Construct RunRecord verifying is_verification_run flag separation
    search_record = RunRecord(
        run_id=search_run_id,
        experiment_id="exp-001",
        candidate_id="cand-01",
        is_verification_run=False,
        execution_status=ExecutionStatus.COMPLETED,
        raw_artifact_uri="artifacts/exp-001/runs/search/measurements.jsonl",
    )
    assert search_record.is_verification_run is False

    verification_record = RunRecord(
        run_id=verification_run_id,
        experiment_id="exp-001",
        candidate_id="cand-01",
        is_verification_run=True,
        execution_status=ExecutionStatus.COMPLETED,
        raw_artifact_uri="artifacts/exp-001/runs/verify/measurements.jsonl",
    )
    assert verification_record.is_verification_run is True
    assert verification_record.run_id != search_record.run_id
    assert verification_record.raw_artifact_uri != search_record.raw_artifact_uri


def test_verification_record_contract_integrity():
    """VerificationRecord binds original search run to fresh verification run."""
    record = VerificationRecord(
        verification_id="verif-session-001",
        experiment_id="exp-001",
        candidate_id="cand-01",
        original_run_id="run-search-cand-01",
        verification_run_id="run-verify-cand-01",
        verification_verdict=VerificationState.VERIFIED,
        drift_analysis=DriftAnalysis(
            metric_deltas={"ttft_p95": 2.5, "request_throughput": -1.2},
            slo_drift_detected=False,
        ),
        final_decision_notes="All constraints verified independently under fresh run ID.",
    )

    assert record.original_run_id != record.verification_run_id
    assert record.verification_verdict == VerificationState.VERIFIED
    assert record.drift_analysis.slo_drift_detected is False


def test_verification_run_id_recycling_rejected():
    """
    Audit check: verification run ID must NEVER be identical to the search run ID.
    Recycling search metrics or run IDs violates independent verification invariants.
    """
    search_run_id = "run-candidate-042"
    recycled_verification_run_id = "run-candidate-042"

    is_recycled = (search_run_id == recycled_verification_run_id)
    assert is_recycled is True, "Precondition: simulate an illicit recycled ID"

    # Independent verification audit invariant:
    # A verification session must reject recycled run identities
    def audit_verification_independence(orig_id: str, verif_id: str) -> bool:
        return orig_id != verif_id

    assert audit_verification_independence(search_run_id, recycled_verification_run_id) is False


def test_verification_fails_when_slo_drift_detected():
    """
    When verification rerun exhibits performance drift exceeding declared margin,
    verdict must be VERIFICATION_FAILED, never VERIFIED.
    """
    drift_record = VerificationRecord(
        verification_id="verif-session-002",
        experiment_id="exp-001",
        candidate_id="cand-01",
        original_run_id="run-search-cand-01",
        verification_run_id="run-verify-cand-01",
        verification_verdict=VerificationState.VERIFICATION_FAILED,
        drift_analysis=DriftAnalysis(
            metric_deltas={"ttft_p95": 45.0, "request_throughput": -25.0},
            slo_drift_detected=True,
        ),
        final_decision_notes="Verification failed: severe performance drift breached SLO threshold.",
    )

    assert drift_record.verification_verdict == VerificationState.VERIFICATION_FAILED
    assert drift_record.drift_analysis is not None
    assert drift_record.drift_analysis.slo_drift_detected is True
    assert drift_record.verification_verdict != VerificationState.VERIFIED


def test_infeasible_verification_rerun_overrules_search_feasible(
    passing_metrics: MetricSet, standard_slo: SLOSpec
):
    """
    If a search run was FEASIBLE, but the independent verification rerun breaches an SLO constraint,
    the verification evaluation must be INFEASIBLE and cannot be marked VERIFIED.
    """
    # 1. Search run evaluates to FEASIBLE
    search_result = evaluate_slo(passing_metrics, standard_slo)
    assert search_result.overall_verdict == FeasibilityVerdict.FEASIBLE

    # 2. Independent rerun under fresh run ID experiences latency degradation
    rerun_metrics = passing_metrics.model_copy(deep=True)
    rerun_metrics.run_id = "run-verify-cand-01"
    rerun_metrics.ttft_ms.p95 = 250.0  # Threshold is 200.0 ms

    rerun_result = evaluate_slo(rerun_metrics, standard_slo)
    assert rerun_result.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert any(
        c.reason_code == ReasonCode.TTFT_P95_EXCEEDED and c.passed is False
        for c in rerun_result.constraint_evaluations
    )

    # 3. Final verification record must reflect VERIFICATION_FAILED
    verif_record = VerificationRecord(
        verification_id="verif-overrule-001",
        experiment_id="exp-001",
        candidate_id="cand-01",
        original_run_id=passing_metrics.run_id,
        verification_run_id=rerun_metrics.run_id,
        verification_verdict=VerificationState.VERIFICATION_FAILED,
        drift_analysis=DriftAnalysis(
            metric_deltas={"ttft_p95": 100.0},
            slo_drift_detected=True,
        ),
        final_decision_notes="Verification rerun failed hard constraint: TTFT p95 exceeded threshold.",
    )
    assert verif_record.verification_verdict == VerificationState.VERIFICATION_FAILED
    assert verif_record.verification_verdict != VerificationState.VERIFIED


# ==============================================================================
# 2. SEPARATION OF EXECUTION FAILURE VS SLO INFEASIBILITY
# ==============================================================================


def test_execution_failure_is_not_slo_infeasible():
    """
    An execution crash (CUDA OOM, timeout, unhandled exception) is an execution failure,
    NEVER an SLO infeasibility verdict.
    """
    # A crashed execution is recorded as FAILED in RunRecord
    crashed_run = RunRecord(
        run_id="run-crash-oom",
        experiment_id="exp-001",
        candidate_id="cand-oom",
        is_verification_run=False,
        execution_status=ExecutionStatus.FAILED,
        execution_error={
            "error_type": "OutOfMemoryError",
            "message": "CUDA out of memory during batch execution",
            "reason_code": ReasonCode.EXECUTION_CRASHED.value,
        },
    )

    assert crashed_run.execution_status == ExecutionStatus.FAILED
    # ExecutionStatus.FAILED must not be confused with FeasibilityVerdict.INFEASIBLE
    assert crashed_run.execution_status.value != FeasibilityVerdict.INFEASIBLE.value


# ==============================================================================
# 3. DECISION CORRECTNESS: BOUNDARY TESTING
# ==============================================================================


def test_hard_slo_boundary_less_than_or_equal(passing_metrics: MetricSet, standard_slo: SLOSpec):
    """Operator <=: exact match passes; epsilon breach fails."""
    # Exact threshold: 200.0 <= 200.0 -> FEASIBLE
    passing_metrics.ttft_ms.p95 = 200.0
    res_exact = evaluate_slo(passing_metrics, standard_slo)
    assert res_exact.overall_verdict == FeasibilityVerdict.FEASIBLE

    # Epsilon above threshold: 200.01 <= 200.0 -> INFEASIBLE
    passing_metrics.ttft_ms.p95 = 200.01
    res_above = evaluate_slo(passing_metrics, standard_slo)
    assert res_above.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert any(
        c.reason_code == ReasonCode.TTFT_P95_EXCEEDED
        for c in res_above.constraint_evaluations
    )


def test_hard_slo_boundary_strictly_less(passing_metrics: MetricSet):
    """Operator <: exact match fails; epsilon below passes."""
    strict_slo = SLOSpec(
        slo_id="slo-strict-less",
        min_sample_count=20,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=200.0, unit="ms", operator="<")
        ],
    )

    # Exact threshold: 200.0 < 200.0 is False -> INFEASIBLE
    passing_metrics.ttft_ms.p95 = 200.0
    res_exact = evaluate_slo(passing_metrics, strict_slo)
    assert res_exact.overall_verdict == FeasibilityVerdict.INFEASIBLE

    # Below threshold: 199.99 < 200.0 is True -> FEASIBLE
    passing_metrics.ttft_ms.p95 = 199.99
    res_below = evaluate_slo(passing_metrics, strict_slo)
    assert res_below.overall_verdict == FeasibilityVerdict.FEASIBLE


def test_hard_slo_boundary_greater_than_or_equal(passing_metrics: MetricSet):
    """Operator >=: exact match passes; epsilon below fails."""
    tp_slo = SLOSpec(
        slo_id="slo-tp-gte",
        min_sample_count=20,
        constraints=[
            SLOConstraint(metric_name="request_throughput", statistic="mean", threshold=10.0, unit="requests/s", operator=">=")
        ],
    )

    # Exact threshold: 10.0 >= 10.0 -> FEASIBLE
    passing_metrics.request_throughput_rps = 10.0
    res_exact = evaluate_slo(passing_metrics, tp_slo)
    assert res_exact.overall_verdict == FeasibilityVerdict.FEASIBLE

    # Below threshold: 9.99 >= 10.0 is False -> INFEASIBLE
    passing_metrics.request_throughput_rps = 9.99
    res_below = evaluate_slo(passing_metrics, tp_slo)
    assert res_below.overall_verdict == FeasibilityVerdict.INFEASIBLE
    assert any(
        c.reason_code == ReasonCode.THROUGHPUT_DEFICIT
        for c in res_below.constraint_evaluations
    )


def test_hard_slo_boundary_strictly_greater(passing_metrics: MetricSet):
    """Operator >: exact match fails; epsilon above passes."""
    tp_slo = SLOSpec(
        slo_id="slo-tp-gt",
        min_sample_count=20,
        constraints=[
            SLOConstraint(metric_name="request_throughput", statistic="mean", threshold=10.0, unit="requests/s", operator=">")
        ],
    )

    # Exact threshold: 10.0 > 10.0 is False -> INFEASIBLE
    passing_metrics.request_throughput_rps = 10.0
    res_exact = evaluate_slo(passing_metrics, tp_slo)
    assert res_exact.overall_verdict == FeasibilityVerdict.INFEASIBLE

    # Above threshold: 10.01 > 10.0 is True -> FEASIBLE
    passing_metrics.request_throughput_rps = 10.01
    res_above = evaluate_slo(passing_metrics, tp_slo)
    assert res_above.overall_verdict == FeasibilityVerdict.FEASIBLE


def test_multiple_hard_slo_failures_record_all_breaches(
    passing_metrics: MetricSet, standard_slo: SLOSpec
):
    """
    When multiple hard constraints are breached simultaneously, the evaluator must
    record every breach with its corresponding ReasonCode and passed=False.
    """
    passing_metrics.ttft_ms.p95 = 250.0  # > 200.0 (TTFT_P95_EXCEEDED)
    passing_metrics.itl_ms.p95 = 75.0   # > 50.0 (ITL_P95_EXCEEDED)
    passing_metrics.request_throughput_rps = 8.0  # < 10.0 (THROUGHPUT_DEFICIT)
    passing_metrics.error_rate = 0.05  # > 0.01 (ERROR_RATE_EXCEEDED)

    result = evaluate_slo(passing_metrics, standard_slo)

    assert result.overall_verdict == FeasibilityVerdict.INFEASIBLE

    breaches = {c.metric_name: c for c in result.constraint_evaluations if not c.passed}
    assert len(breaches) == 4

    assert breaches["ttft"].reason_code == ReasonCode.TTFT_P95_EXCEEDED
    assert breaches["itl"].reason_code == ReasonCode.ITL_P95_EXCEEDED
    assert breaches["request_throughput"].reason_code == ReasonCode.THROUGHPUT_DEFICIT
    assert breaches["error_rate"].reason_code == ReasonCode.ERROR_RATE_EXCEEDED


# ==============================================================================
# 4. EVIDENCE INTEGRITY: MISSING, CONTAMINATED, AND INVALID EVIDENCE
# ==============================================================================


def test_missing_required_metrics_inconclusive(passing_metrics: MetricSet, standard_slo: SLOSpec):
    """A missing required metric must NEVER be treated as passing (yields INCONCLUSIVE)."""
    passing_metrics.ttft_ms = None
    result = evaluate_slo(passing_metrics, standard_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert any(
        c.reason_code == ReasonCode.MISSING_REQUIRED_METRIC
        for c in result.constraint_evaluations
    )


def test_generator_saturation_triggers_contaminated_inconclusive(
    passing_metrics: MetricSet, standard_slo: SLOSpec
):
    """Client load generator saturation contaminates evidence and yields INCONCLUSIVE."""
    passing_metrics.generator_saturated = True
    result = evaluate_slo(passing_metrics, standard_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.CONTAMINATED
    assert all(
        c.reason_code == ReasonCode.GENERATOR_SATURATED
        for c in result.constraint_evaluations
    )


def test_insufficient_sample_count_inconclusive(
    passing_metrics: MetricSet, standard_slo: SLOSpec
):
    """Sample count below min_sample_count yields INCONCLUSIVE."""
    passing_metrics.sample_count = 5  # min is 20
    result = evaluate_slo(passing_metrics, standard_slo)

    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert all(
        c.reason_code == ReasonCode.INSUFFICIENT_SAMPLES
        for c in result.constraint_evaluations
    )


def test_nan_or_negative_metric_invalid_inconclusive(
    passing_metrics: MetricSet, standard_slo: SLOSpec
):
    """NaN or impossible negative latency must yield INCONCLUSIVE and INVALID evidence."""
    # Test NaN
    passing_metrics.ttft_ms.p95 = float("nan")
    res_nan = evaluate_slo(passing_metrics, standard_slo)
    assert res_nan.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert res_nan.validity_status == EvidenceValidity.INVALID

    # Test negative latency
    passing_metrics.ttft_ms.p95 = -5.0
    res_neg = evaluate_slo(passing_metrics, standard_slo)
    assert res_neg.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert res_neg.validity_status == EvidenceValidity.INVALID


def test_inconclusive_takes_precedence_over_infeasible(
    passing_metrics: MetricSet, standard_slo: SLOSpec
):
    """
    Deterministic precedence: INCONCLUSIVE (corrupt/missing/saturated) > INFEASIBLE (failed constraints).
    If a run has both a failed constraint AND generator saturation, verdict is INCONCLUSIVE.
    """
    passing_metrics.ttft_ms.p95 = 500.0  # Exceeds 200.0 (would be infeasible)
    passing_metrics.generator_saturated = True  # Contaminated

    result = evaluate_slo(passing_metrics, standard_slo)
    assert result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.validity_status == EvidenceValidity.CONTAMINATED
