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
from slokern.engine.runner.run_executor import SingleRunExecutor, SingleRunResult
from slokern.engine.serving.fake import FakeServingAdapter


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
