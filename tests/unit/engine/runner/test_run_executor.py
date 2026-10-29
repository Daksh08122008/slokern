"""
Purpose: Unit tests for engine/runner/run_executor (TASK-08).
Owner: Rajdeep (Architecture & Verification)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
    ParameterStatus,
    ReasonCode,
)
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.metrics import MetricSet
from slokern.contracts.run import RunRecord
from slokern.contracts.spec import SLOConstraint, SLOSpec, WorkloadSpec
from slokern.contracts.verdict import FeasibilityResult
from slokern.engine.loadgen.runner import LoadGeneratorResult, LoadGeneratorRunner
from slokern.engine.runner.cancel import CancellationToken, RunCancelledError
from slokern.engine.runner.run_executor import (
    RunExecutionError,
    SingleRunExecutor,
    SingleRunResult,
    sanitize_error_message,
)
from slokern.engine.serving.fake import FailureInjectionConfig, FakeServingAdapter


def _build_test_candidate_config(
    model_name: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    runtime_name: str = "vllm",
    max_num_seqs: int = 16,
    gpu_mem: float = 0.90,
) -> CandidateConfig:
    return CandidateConfig(
        candidate_id="cand-test-01",
        model_name=model_name,
        runtime_name=runtime_name,
        requested_settings={
            "max_num_seqs": max_num_seqs,
            "gpu_memory_utilization": gpu_mem,
        },
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )


def _build_test_workload(
    target_rate: float = 10.0,
    warmup_s: int = 1,
    measure_s: int = 1,
    concurrency: int = 4,
) -> WorkloadSpec:
    return WorkloadSpec(
        schema_version="1.0.0",
        workload_name="unit-test-workload",
        fixture_id="fix-001",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=target_rate,
        concurrency_limit=concurrency,
        warmup_duration_s=warmup_s,
        measurement_duration_s=measure_s,
        max_input_tokens=64,
        max_output_tokens=16,
    )


def _build_test_slo(
    ttft_threshold_ms: float = 2000.0,
    min_samples: int = 5,
) -> SLOSpec:
    return SLOSpec(
        slo_id="slo-test-01",
        constraints=[
            SLOConstraint(
                metric_name="ttft_ms",
                statistic="p95",
                threshold=ttft_threshold_ms,
                unit="ms",
                operator="<=",
            ),
            SLOConstraint(
                metric_name="error_rate",
                statistic="mean",
                threshold=0.05,
                unit="fraction",
                operator="<=",
            ),
        ],
        min_sample_count=min_samples,
    )


def test_successful_fake_serving_run(tmp_path: Path):
    """
    1. Successful fake-serving run: configuration reaches the adapter, requests are dispatched,
    raw measurements are recorded, metrics are calculated, an SLO verdict is produced,
    and artifacts are readable.
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

    cand_config = _build_test_candidate_config()
    workload = _build_test_workload(target_rate=10.0, warmup_s=1, measure_s=1, concurrency=4)
    slo = _build_test_slo(ttft_threshold_ms=5000.0, min_samples=3)

    result = executor.execute(
        candidate_config=cand_config,
        workload=workload,
        slo=slo,
        experiment_id="exp-001",
        run_id="run-001",
    )

    # 1. Result status checks
    assert isinstance(result, SingleRunResult)
    assert result.is_completed is True
    assert result.is_failed is False
    assert result.is_cancelled is False
    assert result.execution_status == ExecutionStatus.COMPLETED
    assert result.is_feasible is True

    # 2. Feasibility result checks
    assert result.feasibility_result is not None
    assert result.feasibility_result.overall_verdict == FeasibilityVerdict.FEASIBLE
    assert result.feasibility_result.validity_status == EvidenceValidity.VALID

    # 3. MetricSet checks
    assert result.metric_set is not None
    assert result.metric_set.sample_count >= 3
    assert result.metric_set.error_rate == 0.0
    assert result.metric_set.generator_saturated is False

    # 4. Read-back applied config checks
    assert result.applied_config is not None
    assert result.applied_config.parameter_status["max_num_seqs"] == ParameterStatus.APPLIED
    assert result.applied_config.environment_fingerprint["simulated"] is True

    # 5. Artifact existence & round-trip verification
    run_dir = tmp_path / "experiments" / "exp-001" / "runs" / "run-001"
    assert (run_dir / "run_record.json").exists()
    assert (run_dir / "raw_measurements.jsonl").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "feasibility.json").exists()
    assert (run_dir / "applied_config.json").exists()

    # Load and validate with Pydantic contracts
    loaded_record = RunRecord.model_validate_json((run_dir / "run_record.json").read_text())
    assert loaded_record.run_id == "run-001"
    assert loaded_record.execution_status == ExecutionStatus.COMPLETED
    assert loaded_record.raw_artifact_uri == "artifacts/experiments/exp-001/runs/run-001/raw_measurements.jsonl"
    assert loaded_record.started_at is not None
    assert loaded_record.completed_at is not None

    loaded_metrics = MetricSet.model_validate_json((run_dir / "metrics.json").read_text())
    assert loaded_metrics.run_id == "run-001"

    loaded_feasibility = FeasibilityResult.model_validate_json((run_dir / "feasibility.json").read_text())
    assert loaded_feasibility.overall_verdict == FeasibilityVerdict.FEASIBLE

    # Verify helper method loads raw measurements
    measurements = result.load_raw_measurements()
    assert len(measurements) > 0
    assert all(isinstance(m, RawRequestMeasurement) for m in measurements)


def test_slo_infeasible_run(tmp_path: Path):
    """
    2. SLO-infeasible run: execution completes successfully but the verdict is INFEASIBLE.
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

    cand_config = _build_test_candidate_config()
    workload = _build_test_workload(target_rate=10.0, warmup_s=1, measure_s=1, concurrency=4)
    # Impossible TTFT threshold: 0.0001 ms -> Must trigger INFEASIBLE
    slo = _build_test_slo(ttft_threshold_ms=0.0001, min_samples=3)

    result = executor.execute(
        candidate_config=cand_config,
        workload=workload,
        slo=slo,
        experiment_id="exp-infeasible",
        run_id="run-inf-01",
    )

    assert result.is_completed is True
    assert result.execution_status == ExecutionStatus.COMPLETED
    assert result.is_feasible is False
    assert result.feasibility_result is not None
    assert result.feasibility_result.overall_verdict == FeasibilityVerdict.INFEASIBLE

    # Check reason code for breach
    eval_ttft = [e for e in result.feasibility_result.constraint_evaluations if "ttft" in e.metric_name][0]
    assert eval_ttft.passed is False
    assert eval_ttft.reason_code == ReasonCode.TTFT_P95_EXCEEDED

    # Artifacts must still be persisted and valid
    run_dir = tmp_path / "experiments" / "exp-infeasible" / "runs" / "run-inf-01"
    assert (run_dir / "feasibility.json").exists()
    assert (run_dir / "run_record.json").exists()


def test_health_check_failure(tmp_path: Path):
    """
    3. Health-check failure: adapter reports unhealthy -> run marked FAILED before loadgen.
    """
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm",
        failure_config=FailureInjectionConfig(health_status=False),
        simulate_delay=False,
    )
    executor = SingleRunExecutor(
        adapter=adapter,
        artifacts_root=tmp_path,
        isolate_process=False,
    )

    cand_config = _build_test_candidate_config()
    workload = _build_test_workload()
    slo = _build_test_slo()

    result = executor.execute(
        candidate_config=cand_config,
        workload=workload,
        slo=slo,
        experiment_id="exp-health-fail",
        run_id="run-hf-01",
    )

    assert result.is_completed is False
    assert result.is_failed is True
    assert result.execution_status == ExecutionStatus.FAILED
    assert result.is_feasible is False
    assert result.metric_set is None
    assert result.feasibility_result is None

    assert result.run_record.execution_error is not None
    assert result.run_record.execution_error["stage"] == "health_check"

    # run_record.json must be persisted on disk
    record_path = tmp_path / "experiments" / "exp-health-fail" / "runs" / "run-hf-01" / "run_record.json"
    assert record_path.exists()
    saved = RunRecord.model_validate_json(record_path.read_text())
    assert saved.execution_status == ExecutionStatus.FAILED


def test_adapter_configuration_failure(tmp_path: Path):
    """
    4. Adapter/configuration failure: unsupported model or parameters rejected in strict mode.
    """
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm",
        simulate_delay=False,
    )
    executor = SingleRunExecutor(
        adapter=adapter,
        artifacts_root=tmp_path,
        strict_config=True,
    )

    # max_num_seqs: 99999 exceeds runtime limit (max_value=256) -> rejected
    cand_config = _build_test_candidate_config(max_num_seqs=99999)
    workload = _build_test_workload()
    slo = _build_test_slo()

    result = executor.execute(
        candidate_config=cand_config,
        workload=workload,
        slo=slo,
        experiment_id="exp-cfg-fail",
        run_id="run-cf-01",
    )

    assert result.is_completed is False
    assert result.is_failed is True
    assert result.execution_status == ExecutionStatus.FAILED
    assert result.run_record.execution_error["stage"] == "apply_config"

    record_path = tmp_path / "experiments" / "exp-cfg-fail" / "runs" / "run-cf-01" / "run_record.json"
    assert record_path.exists()


def test_load_generator_execution_failure(tmp_path: Path):
    """
    5. Load-generator execution failure: runner raises exception during dispatch.
    """
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm",
        simulate_delay=False,
    )

    mock_runner = MagicMock(spec=LoadGeneratorRunner)
    mock_runner.run.side_effect = RuntimeError("Simulated process crash in generator")

    executor = SingleRunExecutor(
        adapter=adapter,
        artifacts_root=tmp_path,
        load_generator_runner=mock_runner,
    )

    cand_config = _build_test_candidate_config()
    workload = _build_test_workload()
    slo = _build_test_slo()

    result = executor.execute(
        candidate_config=cand_config,
        workload=workload,
        slo=slo,
        experiment_id="exp-loadgen-fail",
        run_id="run-lg-01",
    )

    assert result.is_failed is True
    assert result.execution_status == ExecutionStatus.FAILED
    assert result.run_record.execution_error["stage"] == "load_generation"
    assert "Simulated process crash" in result.run_record.execution_error["message"]


def test_cancellation_before_execution(tmp_path: Path):
    """
    6a. Cancellation prior to run execution: marked CANCELLED immediately.
    """
    adapter = FakeServingAdapter(model_name="meta-llama/Meta-Llama-3-8B-Instruct", runtime_name="vllm")
    executor = SingleRunExecutor(adapter=adapter, artifacts_root=tmp_path)

    token = CancellationToken()
    token.cancel()

    result = executor.execute(
        candidate_config=_build_test_candidate_config(),
        workload=_build_test_workload(),
        slo=_build_test_slo(),
        experiment_id="exp-cancel-pre",
        run_id="run-cn-01",
        cancellation_token=token,
    )

    assert result.is_cancelled is True
    assert result.execution_status == ExecutionStatus.CANCELLED
    assert result.is_completed is False
    assert result.is_feasible is False

    record_path = tmp_path / "experiments" / "exp-cancel-pre" / "runs" / "run-cn-01" / "run_record.json"
    assert record_path.exists()
    saved = RunRecord.model_validate_json(record_path.read_text())
    assert saved.execution_status == ExecutionStatus.CANCELLED


def test_cancellation_during_loadgen(tmp_path: Path):
    """
    6b. Cancellation during load generation triggers runner.cancel and registers CANCELLED.
    """
    adapter = FakeServingAdapter(model_name="meta-llama/Meta-Llama-3-8B-Instruct", runtime_name="vllm")
    token = CancellationToken()

    mock_runner = MagicMock(spec=LoadGeneratorRunner)

    def side_effect_run(*args, **kwargs):
        token.cancel()
        raise RunCancelledError("Execution was cancelled")

    mock_runner.run.side_effect = side_effect_run

    executor = SingleRunExecutor(
        adapter=adapter,
        artifacts_root=tmp_path,
        load_generator_runner=mock_runner,
    )

    result = executor.execute(
        candidate_config=_build_test_candidate_config(),
        workload=_build_test_workload(),
        slo=_build_test_slo(),
        experiment_id="exp-cancel-during",
        run_id="run-cn-02",
        cancellation_token=token,
    )

    assert result.is_cancelled is True
    assert result.execution_status == ExecutionStatus.CANCELLED
    assert result.is_completed is False


def test_insufficient_samples_yields_inconclusive(tmp_path: Path):
    """
    7a. Insufficient measurements: sample count < min_sample_count yields INCONCLUSIVE.
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

    # 1 second at 5 req/s will deliver ~5 samples
    workload = _build_test_workload(target_rate=5.0, warmup_s=0, measure_s=1, concurrency=2)
    # Require 50 minimum samples -> must trigger INSUFFICIENT_SAMPLES
    slo = _build_test_slo(ttft_threshold_ms=5000.0, min_samples=50)

    result = executor.execute(
        candidate_config=_build_test_candidate_config(),
        workload=workload,
        slo=slo,
        experiment_id="exp-insufficient",
        run_id="run-ins-01",
    )

    assert result.is_completed is True
    assert result.execution_status == ExecutionStatus.COMPLETED
    assert result.is_feasible is False
    assert result.feasibility_result is not None
    assert result.feasibility_result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE

    # Constraint evaluation reason must be INSUFFICIENT_SAMPLES
    for ce in result.feasibility_result.constraint_evaluations:
        assert ce.reason_code == ReasonCode.INSUFFICIENT_SAMPLES
        assert ce.passed is None


def test_malformed_measurements_yields_inconclusive(tmp_path: Path):
    """
    7b. Malformed measurements: corrupted JSONL trace yields INCONCLUSIVE verdict with INVALID validity.
    """
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm",
        simulate_delay=False,
    )

    mock_runner = MagicMock(spec=LoadGeneratorRunner)

    def side_effect_corrupt(output_path, *args, **kwargs):
        # Write corrupted JSON to the output path
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text('{"request_id": "r1", valid_json: false,\n', encoding="utf-8")
        return LoadGeneratorResult(
            total_requests=1,
            warmup_requests=0,
            active_requests=1,
            completed_requests=1,
            failed_requests=0,
            target_offered_rate=10.0,
            offered_load_rps=10.0,
            achieved_load_rps=10.0,
            generator_saturated=False,
            mean_dispatch_lag_ms=1.0,
            max_dispatch_lag_ms=2.0,
            output_path=str(out),
            error=None,
        )

    mock_runner.run.side_effect = side_effect_corrupt

    executor = SingleRunExecutor(
        adapter=adapter,
        artifacts_root=tmp_path,
        load_generator_runner=mock_runner,
    )

    result = executor.execute(
        candidate_config=_build_test_candidate_config(),
        workload=_build_test_workload(),
        slo=_build_test_slo(),
        experiment_id="exp-malformed",
        run_id="run-mal-01",
    )

    assert result.is_failed is True
    assert result.execution_status == ExecutionStatus.FAILED
    assert result.is_feasible is False
    assert result.feasibility_result is not None
    assert result.feasibility_result.overall_verdict == FeasibilityVerdict.INCONCLUSIVE
    assert result.feasibility_result.validity_status == EvidenceValidity.INVALID
    assert "Malformed JSONL record" in result.run_record.execution_error["message"]


def test_persistence_failure_handling(tmp_path: Path):
    """
    8. Persistence failure: writing artifacts to a non-writable destination records failure cleanly.
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

    with patch.object(Path, "write_text", side_effect=OSError("Disk write failed: No space left on device")):
        result = executor.execute(
            candidate_config=_build_test_candidate_config(),
            workload=_build_test_workload(),
            slo=_build_test_slo(),
            experiment_id="exp-persist-fail",
            run_id="run-pf-01",
        )

    assert result.is_failed is True
    assert result.execution_status == ExecutionStatus.FAILED
    assert result.run_record.execution_error["stage"] == "persist_artifacts"
    assert "No space left on device" in result.run_record.execution_error["message"]


def test_input_validation_failure(tmp_path: Path):
    """
    Input validation: invalid workload durations trigger validation failure.
    """
    adapter = FakeServingAdapter(model_name="meta-llama/Meta-Llama-3-8B-Instruct", runtime_name="vllm")
    executor = SingleRunExecutor(adapter=adapter, artifacts_root=tmp_path)

    # Durations total 0 -> invalid
    workload = _build_test_workload(warmup_s=0, measure_s=0)
    slo = _build_test_slo()

    result = executor.execute(
        candidate_config=_build_test_candidate_config(),
        workload=workload,
        slo=slo,
        experiment_id="exp-val-fail",
        run_id="run-vf-01",
    )

    assert result.is_failed is True
    assert result.execution_status == ExecutionStatus.FAILED
    assert result.run_record.execution_error["stage"] == "validation"


def test_raise_on_failure_modes(tmp_path: Path):
    """
    raise_on_failure=True raises RunExecutionError or RunCancelledError.
    """
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm",
        failure_config=FailureInjectionConfig(health_status=False),
    )
    executor = SingleRunExecutor(adapter=adapter, artifacts_root=tmp_path)

    with pytest.raises(RunExecutionError) as exc_info:
        executor.execute(
            candidate_config=_build_test_candidate_config(),
            workload=_build_test_workload(),
            slo=_build_test_slo(),
            experiment_id="exp-raise-fail",
            run_id="run-rf-01",
            raise_on_failure=True,
        )
    assert exc_info.value.stage == "health_check"

    # Test cancellation raise
    token = CancellationToken()
    token.cancel()
    with pytest.raises(RunCancelledError):
        executor.execute(
            candidate_config=_build_test_candidate_config(),
            workload=_build_test_workload(),
            slo=_build_test_slo(),
            experiment_id="exp-raise-cancel",
            run_id="run-rc-01",
            cancellation_token=token,
            raise_on_failure=True,
        )


def test_secret_redaction_in_errors():
    """
    Secret redaction helper sanitizes Bearer tokens, API keys, and private IPs.
    """
    raw_msg = (
        "Connection failed to endpoint http://192.168.1.100:8000/v1 "
        "with Authorization: Bearer sk-secret-nebius-token-123456789. "
        "Internal host: 10.0.4.12, api_key='secret-key-99999999'."
    )
    sanitized = sanitize_error_message(raw_msg)

    assert "sk-secret-nebius-token" not in sanitized
    assert "Bearer ***" in sanitized
    assert "192.168.x.x" in sanitized
    assert "10.x.x.x" in sanitized
    assert "secret-key-99999999" not in sanitized


def _can_bind_and_connect_loopback() -> bool:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        port = s.getsockname()[1]
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.settimeout(0.1)
        s2.connect(('127.0.0.1', port))
        s2.close()
        s.close()
        return True
    except OSError:
        return False

requires_subprocess_socket = pytest.mark.skipif(
    not _can_bind_and_connect_loopback(),
    reason='Windows Codex sandbox forbids loopback socket connections ([WinError 10013]), blocking ProactorEventLoop and multiprocessing pipe IPC.',
)

@requires_subprocess_socket
def test_subprocess_isolated_run(tmp_path: Path):
    """
    Subprocess-isolated run: tests true multiprocessing dispatch with isolate_process=True.
    """
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm",
        simulate_delay=False,
    )
    executor = SingleRunExecutor(
        adapter=adapter,
        artifacts_root=tmp_path,
        isolate_process=True,
    )

    cand_config = _build_test_candidate_config()
    workload = _build_test_workload(target_rate=10.0, warmup_s=1, measure_s=1, concurrency=2)
    slo = _build_test_slo(ttft_threshold_ms=5000.0, min_samples=3)

    result = executor.execute(
        candidate_config=cand_config,
        workload=workload,
        slo=slo,
        experiment_id="exp-subprocess",
        run_id="run-sub-01",
    )

    assert result.is_completed is True
    assert result.execution_status == ExecutionStatus.COMPLETED
    assert result.is_feasible is True
    assert (tmp_path / "experiments" / "exp-subprocess" / "runs" / "run-sub-01" / "metrics.json").exists()
