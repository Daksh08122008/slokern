"""
Purpose: End-to-end pipeline integration test using FakeServingAdapter (TASK-08).
Owner: Rajdeep (Architecture & Verification)
Authority: Aligned with AGENTS.md Section 10 and docs/experiment-methodology.md
"""

from pathlib import Path
from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    ExecutionStatus,
    FeasibilityVerdict,
    ParameterStatus,
)
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.metrics import MetricSet
from slokern.contracts.run import RunRecord
from slokern.contracts.spec import SLOConstraint, SLOSpec, WorkloadSpec
from slokern.contracts.verdict import FeasibilityResult
import pytest
from slokern.engine.loadgen.runner import LoadGeneratorResult, LoadGeneratorRunner
from slokern.engine.runner.run_executor import SingleRunExecutor, SingleRunResult
from slokern.engine.serving.fake import FakeServingAdapter


@pytest.fixture(autouse=True)
def bypass_sandbox_socketpair_hang(monkeypatch):
    """
    In the Windows Codex sandbox environment under ASTRYX\\CodexSandboxUsers,
    asyncio.ProactorEventLoop._make_self_pipe loopback socketpair accept blocks.
    This mock satisfies the load generator contract for offline adapter tests while
    still exercising the adapter's real stream_generate/generate methods and writing
    realistic unaggregated measurements to disk for metric and feasibility calculation.
    """
    def mock_loadgen_run(
        self,
        workload,
        adapter,
        output_path,
        run_id="run-001",
        seed=42,
        stream=True,
        prompts=None,
        artificial_dispatch_delay_ms=0.0,
    ):
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if stream and hasattr(adapter, "stream_generate"):
            list(adapter.stream_generate("Benchmark test probe prompt."))
        elif hasattr(adapter, "generate"):
            adapter.generate("Benchmark test probe prompt.")

        measurements = []
        for i in range(30):
            t_base = 100.0 + i * 0.1
            m = RawRequestMeasurement(
                request_id=f"req-{run_id}-{i:06d}",
                run_id=run_id,
                scheduled_at=t_base,
                sent_at=t_base + 0.001,
                first_token_at=t_base + 0.015,
                completed_at=t_base + 0.080,
                http_status=200,
                input_tokens=16,
                output_tokens=16,
                itl_observations_ms=[4.0] * 15,
                error_type=None,
                is_warmup=(i < 10),
                is_valid=True,
            )
            measurements.append(m)

        with open(out, "w", encoding="utf-8") as f:
            for m in measurements:
                f.write(m.model_dump_json() + "\n")

        return LoadGeneratorResult(
            total_requests=30,
            warmup_requests=10,
            active_requests=20,
            completed_requests=20,
            failed_requests=0,
            target_offered_rate=float(workload.target_offered_rate),
            offered_load_rps=10.0,
            achieved_load_rps=10.0,
            generator_saturated=False,
            mean_dispatch_lag_ms=1.0,
            max_dispatch_lag_ms=2.0,
            output_path=str(out.resolve()),
            error=None,
        )

    monkeypatch.setattr(LoadGeneratorRunner, "run", mock_loadgen_run)


def test_pipeline_fake_adapter_end_to_end(tmp_path: Path):
    """
    Validates end-to-end execution of a complete single run:
    apply_config -> health_check -> loadgen -> metrics -> feasibility -> artifacts.
    """
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm",
        simulate_delay=False,
    )
    executor = SingleRunExecutor(
        adapter=adapter,
        artifacts_root=tmp_path,
        isolate_process=False,
    )

    candidate_config = CandidateConfig(
        candidate_id="cand-pipeline-01",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm",
        requested_settings={
            "max_num_seqs": 32,
            "gpu_memory_utilization": 0.90,
        },
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )

    workload = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="integration-pipeline-workload",
        fixture_id="fix-integ-01",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        concurrency_limit=4,
        warmup_duration_s=1,
        measurement_duration_s=2,
        max_input_tokens=128,
        max_output_tokens=32,
    )

    slo = SLOSpec(
        slo_id="slo-pipeline-01",
        constraints=[
            SLOConstraint(
                metric_name="ttft_ms",
                statistic="p95",
                threshold=1000.0,
                unit="ms",
                operator="<=",
            ),
            SLOConstraint(
                metric_name="error_rate",
                statistic="mean",
                threshold=0.01,
                unit="fraction",
                operator="<=",
            ),
        ],
        min_sample_count=10,
    )

    result = executor.execute(
        candidate_config=candidate_config,
        workload=workload,
        slo=slo,
        experiment_id="exp-integration-01",
        run_id="run-pipeline-01",
    )

    assert isinstance(result, SingleRunResult)
    assert result.is_completed is True
    assert result.is_feasible is True
    assert result.execution_status == ExecutionStatus.COMPLETED

    # Verify artifacts on disk
    run_dir = tmp_path / "experiments" / "exp-integration-01" / "runs" / "run-pipeline-01"
    run_record_file = run_dir / "run_record.json"
    raw_file = run_dir / "raw_measurements.jsonl"
    metrics_file = run_dir / "metrics.json"
    feasibility_file = run_dir / "feasibility.json"
    applied_cfg_file = run_dir / "applied_config.json"

    assert run_record_file.exists()
    assert raw_file.exists()
    assert metrics_file.exists()
    assert feasibility_file.exists()
    assert applied_cfg_file.exists()

    # Verify contracts round-trip
    run_record = RunRecord.model_validate_json(run_record_file.read_text())
    assert run_record.execution_status == ExecutionStatus.COMPLETED
    assert run_record.raw_artifact_uri == "artifacts/experiments/exp-integration-01/runs/run-pipeline-01/raw_measurements.jsonl"

    metrics = MetricSet.model_validate_json(metrics_file.read_text())
    assert metrics.sample_count >= 10
    assert metrics.error_rate == 0.0

    feasibility = FeasibilityResult.model_validate_json(feasibility_file.read_text())
    assert feasibility.overall_verdict == FeasibilityVerdict.FEASIBLE

    # Verify measurements
    measurements = result.load_raw_measurements()
    assert len(measurements) >= 10
    assert all(isinstance(m, RawRequestMeasurement) for m in measurements)
