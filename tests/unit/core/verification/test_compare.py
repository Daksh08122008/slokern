"""
Purpose: Unit tests for core/verification/compare: drift analysis, epsilon math, and threshold crossovers.
Owner: Rajdeep (Historical design: Daksh)
Authority: Aligned with AGENTS.md Section 5, 7, 10
"""

import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
    VerificationState,
)
from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.contracts.run import RunRecord
from slokern.contracts.spec import SLOConstraint, SLOSpec, WorkloadSpec
from slokern.contracts.verdict import FeasibilityResult
from slokern.core.verification.compare import _compute_delta, compare_metrics
from slokern.core.verification.protocol import run_independent_verification


def _build_test_metric_set(
    run_id: str,
    ttft_p95: float = 150.0,
    itl_p95: float = 35.0,
    e2e_p95: float = 800.0,
    throughput_rps: float = 12.0,
    throughput_tps: float = 240.0,
    error_rate: float = 0.0,
    omit_ttft: bool = False,
) -> MetricSet:
    return MetricSet(
        metric_version="1.0.0",
        run_id=run_id,
        sample_count=50,
        failed_request_count=int(error_rate * 50),
        offered_load_rps=12.0,
        achieved_load_rps=12.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution() if omit_ttft else PercentileDistribution(p50=ttft_p95 * 0.7, p95=ttft_p95),
        itl_ms=PercentileDistribution(p50=itl_p95 * 0.7, p95=itl_p95),
        e2e_latency_ms=PercentileDistribution(p50=e2e_p95 * 0.8, p95=e2e_p95),
        request_throughput_rps=throughput_rps,
        token_throughput_tps=throughput_tps,
        error_rate=error_rate,
    )


def test_compare_zero_to_zero():
    """Zero to zero delta is 0.0%."""
    delta = _compute_delta(0.0, 0.0)
    assert delta == 0.0

    orig = _build_test_metric_set("run-orig", error_rate=0.0)
    verif = _build_test_metric_set("run-verif", error_rate=0.0)
    analysis = compare_metrics(orig, verif)
    assert analysis.metric_deltas.get("error_rate") == 0.0


def test_compare_zero_to_nonzero_error_rate():
    """Error rate 0.0 to 0.005 reports absolute delta, evaluated against SLO."""
    orig = _build_test_metric_set("run-orig", error_rate=0.0)
    verif = _build_test_metric_set("run-verif", error_rate=0.005)

    slo = SLOSpec(
        slo_id="slo-error-check",
        min_sample_count=20,
        constraints=[
            SLOConstraint(metric_name="error_rate", statistic="mean", threshold=0.01, unit="fraction", operator="<=")
        ]
    )

    analysis = compare_metrics(orig, verif, slo)
    # 0.0 to 0.005 is +0.5 percentage points
    assert analysis.metric_deltas["error_rate"] == 0.5
    # 0.005 is still <= 0.01 threshold, so no threshold crossover occurred
    assert analysis.slo_drift_detected is False


def test_compare_threshold_drift_failure():
    """Crossing SLO threshold sets slo_drift_detected=True."""
    orig = _build_test_metric_set("run-orig", ttft_p95=180.0)  # Passed 200ms threshold
    verif = _build_test_metric_set("run-verif", ttft_p95=220.0)  # Failed 200ms threshold

    slo = SLOSpec(
        slo_id="slo-ttft-check",
        min_sample_count=20,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=200.0, unit="ms", operator="<=")
        ]
    )

    analysis = compare_metrics(orig, verif, slo)
    assert analysis.slo_drift_detected is True
    assert analysis.metric_deltas["ttft_p95"] > 0.0


def test_compare_missing_metric_inconclusive():
    """Missing required metric yields slo_drift_detected=True."""
    orig = _build_test_metric_set("run-orig", omit_ttft=True)
    verif = _build_test_metric_set("run-verif", ttft_p95=150.0)

    slo = SLOSpec(
        slo_id="slo-missing-metric",
        min_sample_count=20,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=200.0, unit="ms", operator="<=")
        ]
    )

    analysis = compare_metrics(orig, verif, slo)
    assert analysis.slo_drift_detected is True


def test_compare_measurement_variability_tolerated():
    """Natural 10% tail latency variance does not fail if within SLO."""
    orig = _build_test_metric_set("run-orig", ttft_p95=150.0)
    verif = _build_test_metric_set("run-verif", ttft_p95=165.0)  # +10%

    slo = SLOSpec(
        slo_id="slo-variance-check",
        min_sample_count=20,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=200.0, unit="ms", operator="<=")
        ]
    )

    analysis = compare_metrics(orig, verif, slo)
    assert analysis.slo_drift_detected is False
    assert abs(analysis.metric_deltas["ttft_p95"] - 10.0) < 0.1


class MockVerificationExecutor:
    def __init__(self, metric_set=None, default_verdict=FeasibilityVerdict.FEASIBLE):
        self.metric_set = metric_set
        self.default_verdict = default_verdict
        self.call_count = 0
        self.last_run_id = None

    def execute(self, candidate_config, workload, slo, experiment_id, run_id, **kwargs):
        self.call_count += 1
        self.last_run_id = run_id
        ms = self.metric_set or _build_test_metric_set(run_id, ttft_p95=15.0)
        feas = FeasibilityResult(
            policy_version="1.0.0",
            run_id=run_id,
            overall_verdict=self.default_verdict,
            constraint_evaluations=[],
            validity_status=EvidenceValidity.VALID,
            audit_notes="Mock verdict",
        )
        rec = RunRecord(
            run_id=run_id,
            experiment_id=experiment_id,
            candidate_id=candidate_config.candidate_id,
            is_verification_run=kwargs.get("is_verification_run", True),
            execution_status=ExecutionStatus.COMPLETED,
            started_at="2026-10-23T00:00:00+00:00",
            completed_at="2026-10-23T00:00:01+00:00",
        )
        from slokern.engine.runner.run_executor import SingleRunResult
        return SingleRunResult(
            run_record=rec,
            metric_set=ms,
            feasibility_result=feas,
            applied_config=candidate_config,
            raw_measurements_count=50,
            artifact_paths={},
        )


def test_verification_protocol_fresh_run_id():
    """Verification run ID is distinct from search run ID."""
    candidate = CandidateConfig(
        candidate_id="cand-verif-test",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )

    workload = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="verif-workload",
        fixture_id="fix-001",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        concurrency_limit=4,
        warmup_duration_s=1,
        measurement_duration_s=1,
        max_input_tokens=128,
        max_output_tokens=32,
    )
    slo = SLOSpec(
        slo_id="slo-verif",
        min_sample_count=2,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=500.0, unit="ms", operator="<="),
            SLOConstraint(metric_name="error_rate", statistic="mean", threshold=0.1, unit="fraction", operator="<="),
        ],
    )

    search_run_id = "run-search-original-001"
    orig_metrics = _build_test_metric_set(search_run_id, ttft_p95=15.0)
    mock_executor = MockVerificationExecutor()

    record = run_independent_verification(
        original_run_id=search_run_id,
        candidate_config=candidate,
        workload=workload,
        slo=slo,
        original_metrics=orig_metrics,
        single_run_executor=mock_executor,
    )

    assert record.original_run_id == search_run_id
    assert record.verification_run_id != search_run_id
    assert record.verification_run_id.startswith("run-verify-")
    assert record.verification_verdict == VerificationState.VERIFIED
    assert record.drift_analysis is not None
    assert record.metric_set is not None
    assert record.feasibility_result is not None
    assert mock_executor.call_count == 1
    assert mock_executor.last_run_id == record.verification_run_id


def test_compare_empty_trace_does_not_exceed_drift():
    """Validates that an empty verification trace does not falsely mark drift_exceeded=True."""
    from slokern.core.metrics.aggregate import calculate_metrics

    orig = _build_test_metric_set("run-orig", ttft_p95=100.0, throughput_rps=20.0, error_rate=0.0)
    verif = calculate_metrics([], run_id="run-verif-empty")
    assert verif.sample_count == 0

    analysis = compare_metrics(orig, verif)
    assert analysis.drift_exceeded is False
    assert analysis.metric_comparisons["ttft_p95"].failure_reason == "MISSING_METRIC_VALUE"
    assert analysis.metric_comparisons["request_throughput_rps"].failure_reason == "MISSING_METRIC_VALUE"
    assert analysis.metric_comparisons["error_rate"].failure_reason == "MISSING_METRIC_VALUE"


def test_compare_invalid_trace_does_not_exceed_drift():
    """Validates that an invalid verification trace with 0 valid samples does not mark drift_exceeded=True."""
    from slokern.contracts.evidence import RawRequestMeasurement
    from slokern.core.metrics.aggregate import calculate_metrics

    orig = _build_test_metric_set("run-orig", ttft_p95=100.0, throughput_rps=20.0, error_rate=0.0)
    invalid_records = [
        RawRequestMeasurement(
            request_id=f"r-{i}",
            run_id="run-invalid",
            scheduled_at=100.0 + i * 0.1,
            sent_at=100.0 + i * 0.1,
            first_token_at=None,
            completed_at=100.5 + i * 0.1,
            http_status=500,
            input_tokens=10,
            output_tokens=0,
            itl_observations_ms=[],
            error_type="HTTP_500",
            is_warmup=False,
            is_valid=False,
        )
        for i in range(10)
    ]
    verif = calculate_metrics(invalid_records, run_id="run-invalid")
    assert verif.sample_count == 0

    analysis = compare_metrics(orig, verif)
    assert analysis.drift_exceeded is False
    assert analysis.metric_comparisons["ttft_p95"].failure_reason == "MISSING_METRIC_VALUE"
    assert analysis.metric_comparisons["request_throughput_rps"].failure_reason == "MISSING_METRIC_VALUE"


def test_compare_valid_fresh_verification_trace_evaluates_drift():
    """Validates that drift is evaluated when both datasets contain valid comparable metrics."""
    from slokern.contracts.evidence import RawRequestMeasurement
    from slokern.core.metrics.aggregate import calculate_metrics

    fresh_records = [
        RawRequestMeasurement(
            request_id=f"r-{i}",
            run_id="run-valid-fresh",
            scheduled_at=100.0 + i * 0.1,
            sent_at=100.0 + i * 0.1,
            first_token_at=100.1 + i * 0.1,
            completed_at=100.5 + i * 0.1,
            http_status=200,
            input_tokens=10,
            output_tokens=20,
            itl_observations_ms=[20.0] * 19,
            error_type=None,
            is_warmup=False,
            is_valid=True,
        )
        for i in range(20)
    ]
    verif = calculate_metrics(fresh_records, run_id="run-valid-fresh", measurement_duration_s=2.0)
    assert verif.sample_count == 20
    assert verif.ttft_ms.p95 is not None

    # Reference with matching metrics -> drift within tolerance
    orig_matching = MetricSet(
        metric_version="1.0.0",
        run_id="run-orig-match",
        sample_count=20,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=100.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=20.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=500.0, p95=500.0),
        request_throughput_rps=10.0,
        token_throughput_tps=200.0,
        error_rate=0.0,
    )
    res_pass = compare_metrics(orig_matching, verif)
    assert res_pass.drift_exceeded is False

    # Reference with much lower TTFT (50.0 ms) -> TTFT drift is (100 - 50)/50 = +100% -> drift exceeded (> 15%)
    orig_divergent = MetricSet(
        metric_version="1.0.0",
        run_id="run-orig-divergent",
        sample_count=20,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=50.0, p95=50.0),
        itl_ms=PercentileDistribution(p50=20.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=500.0, p95=500.0),
        request_throughput_rps=10.0,
        token_throughput_tps=200.0,
        error_rate=0.0,
    )
    res_fail = compare_metrics(orig_divergent, verif)
    assert res_fail.drift_exceeded is True
    assert res_fail.metric_comparisons["ttft_p95"].passed is False

