"""
Purpose: Unit tests for core/verification/protocol: verification protocol outcomes and error handling.
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
from slokern.core.verification.protocol import run_independent_verification
from slokern.engine.runner.run_executor import SingleRunResult


class MockProtocolExecutor:
    def __init__(
        self,
        default_verdict: FeasibilityVerdict = FeasibilityVerdict.FEASIBLE,
        execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
        validity_status: EvidenceValidity = EvidenceValidity.VALID,
        ttft_p95: float = 150.0,
    ):
        self.default_verdict = default_verdict
        self.execution_status = execution_status
        self.validity_status = validity_status
        self.ttft_p95 = ttft_p95
        self.call_count = 0
        self.last_run_id = None

    def execute(self, candidate_config, workload, slo, experiment_id, run_id, **kwargs):
        self.call_count += 1
        self.last_run_id = run_id
        ms = MetricSet(
            metric_version="1.0.0",
            run_id=run_id,
            sample_count=50,
            failed_request_count=0,
            offered_load_rps=10.0,
            achieved_load_rps=10.0,
            generator_saturated=False,
            ttft_ms=PercentileDistribution(p50=self.ttft_p95 * 0.7, p95=self.ttft_p95),
            itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
            e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
            request_throughput_rps=10.0,
            token_throughput_tps=200.0,
            error_rate=0.0,
        )
        feas = FeasibilityResult(
            policy_version="1.0.0",
            run_id=run_id,
            overall_verdict=self.default_verdict,
            constraint_evaluations=[],
            validity_status=self.validity_status,
            audit_notes="Mock verdict",
        )
        rec = RunRecord(
            run_id=run_id,
            experiment_id=experiment_id,
            candidate_id=candidate_config.candidate_id,
            is_verification_run=kwargs.get("is_verification_run", True),
            execution_status=self.execution_status,
            started_at="2026-10-23T00:00:00+00:00",
            completed_at="2026-10-23T00:00:01+00:00",
        )
        return SingleRunResult(
            run_record=rec,
            metric_set=ms if self.execution_status == ExecutionStatus.COMPLETED else None,
            feasibility_result=feas if self.execution_status == ExecutionStatus.COMPLETED else None,
            applied_config=candidate_config,
            raw_measurements_count=50,
            artifact_paths={},
        )


@pytest.fixture
def test_setup():
    candidate = CandidateConfig(
        candidate_id="cand-proto-01",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )
    workload = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="proto-workload",
        fixture_id="fix-proto-01",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        concurrency_limit=4,
        warmup_duration_s=1,
        measurement_duration_s=1,
        max_input_tokens=128,
        max_output_tokens=32,
    )
    slo = SLOSpec(
        slo_id="slo-proto",
        min_sample_count=2,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=500.0, unit="ms", operator="<="),
            SLOConstraint(metric_name="error_rate", statistic="mean", threshold=0.01, unit="fraction", operator="<="),
        ],
    )
    return candidate, workload, slo


def test_protocol_successful_verification(test_setup):
    """Healthy rerun yields VERIFIED verdict."""
    candidate, workload, slo = test_setup
    mock_executor = MockProtocolExecutor(default_verdict=FeasibilityVerdict.FEASIBLE, ttft_p95=150.0)

    record = run_independent_verification(
        original_run_id="run-search-100",
        candidate_config=candidate,
        workload=workload,
        slo=slo,
        single_run_executor=mock_executor,
    )

    assert record.verification_verdict == VerificationState.VERIFIED
    assert "Independent verification passed" in (record.final_decision_notes or "")


def test_protocol_failed_verification(test_setup):
    """Rerun that violates SLO constraints yields VERIFICATION_FAILED."""
    candidate, workload, slo = test_setup
    # Executor produces ttft_p95=600 which violates threshold 500
    mock_executor = MockProtocolExecutor(default_verdict=FeasibilityVerdict.INFEASIBLE, ttft_p95=600.0)

    record = run_independent_verification(
        original_run_id="run-search-100",
        candidate_config=candidate,
        workload=workload,
        slo=slo,
        single_run_executor=mock_executor,
    )

    assert record.verification_verdict == VerificationState.VERIFICATION_FAILED
    assert "violated declared hard constraints" in (record.final_decision_notes or "")


def test_protocol_inconclusive_on_adapter_failure(test_setup):
    """Rerun that crashes yields VERIFICATION_INCONCLUSIVE."""
    candidate, workload, slo = test_setup
    mock_executor = MockProtocolExecutor(execution_status=ExecutionStatus.FAILED)

    record = run_independent_verification(
        original_run_id="run-search-100",
        candidate_config=candidate,
        workload=workload,
        slo=slo,
        single_run_executor=mock_executor,
    )

    assert record.verification_verdict == VerificationState.VERIFICATION_INCONCLUSIVE
