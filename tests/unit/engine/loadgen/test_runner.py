"""
Purpose: Unit tests for engine/loadgen/runner.
Owner: Rajdeep (Historical design: Adriraj)
"""

import asyncio
from pathlib import Path

import pytest

from slokern.contracts.enums import ArrivalMode
from slokern.contracts.spec import WorkloadSpec
from slokern.engine.loadgen.recorder import JSONLRecorder
from slokern.engine.loadgen.runner import LoadGeneratorResult, LoadGeneratorRunner
from slokern.engine.serving.fake import FakeServingAdapter


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
    reason='Windows Codex sandbox loopback socket constraint ([WinError 10013]) blocks ProactorEventLoop and subprocess IPC.',
)


def _build_test_workload(
    arrival_mode: ArrivalMode = ArrivalMode.CONSTANT,
    target_offered_rate: float = 10.0,
    concurrency_limit: int = 16,
    warmup_duration_s: int = 1,
    measurement_duration_s: int = 2,
    max_output_tokens: int = 8,
) -> WorkloadSpec:
    return WorkloadSpec(
        schema_version="1.0.0",
        workload_name="test_workload",
        fixture_id="fix_test",
        arrival_mode=arrival_mode,
        target_offered_rate=target_offered_rate,
        concurrency_limit=concurrency_limit,
        warmup_duration_s=warmup_duration_s,
        measurement_duration_s=measurement_duration_s,
        max_input_tokens=128,
        max_output_tokens=max_output_tokens,
    )


@requires_subprocess_socket
def test_runner_subprocess_dispatch_streaming(tmp_path: Path):
    """Verifies subprocess-isolated execution with streaming tokens against FakeServingAdapter."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=20.0,
        warmup_duration_s=1,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "subprocess_stream_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=True)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        run_id="run-sub-01",
        stream=True,
    )

    assert isinstance(result, LoadGeneratorResult)
    assert result.total_requests == 40  # 20 req/s * 2s
    assert result.warmup_requests == 20
    assert result.active_requests == 20
    assert result.completed_requests == 40
    assert result.failed_requests == 0
    assert result.generator_saturated is False

    # Trace validation: file exists and all lines strictly validate
    records = JSONLRecorder.read_records(trace_path)
    assert len(records) == 40

    for rec in records:
        assert rec.run_id == "run-sub-01"
        assert rec.http_status == 200
        assert rec.is_valid is True
        assert rec.first_token_at is not None

        # Monotonicity invariant: scheduled_at <= sent_at <= first_token_at <= completed_at
        assert rec.scheduled_at <= rec.sent_at
        assert rec.sent_at <= rec.first_token_at
        assert rec.first_token_at <= rec.completed_at


def test_runner_in_process_non_streaming(tmp_path: Path):
    """Verifies in-process execution with non-streaming agenerate."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "inprocess_nonstream_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=False)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        run_id="run-nostream-01",
        stream=False,
    )

    assert result.total_requests == 10
    assert result.active_requests == 10
    assert result.failed_requests == 0

    records = JSONLRecorder.read_records(trace_path)
    assert len(records) == 10
    for rec in records:
        assert rec.scheduled_at <= rec.sent_at <= rec.completed_at


@requires_subprocess_socket
def test_runner_handles_injected_server_errors(tmp_path: Path):
    """Verifies runner records errors into JSONL when adapter fails, without crashing."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    adapter.inject_oom(True)  # Forces CUDA OOM failure

    trace_path = tmp_path / "oom_trace.jsonl"
    runner = LoadGeneratorRunner(isolate_process=True)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        run_id="run-oom-01",
    )

    assert result.total_requests == 10
    assert result.failed_requests == 10
    assert result.completed_requests == 0

    records = JSONLRecorder.read_records(trace_path)
    assert len(records) == 10
    for rec in records:
        assert rec.is_valid is False
        assert rec.error_type == "cuda_out_of_memory"
        assert rec.http_status == 500
        # Injected error before first token must yield null first_token_at and 0 output tokens
        assert rec.first_token_at is None
        assert rec.output_tokens == 0
        assert rec.scheduled_at <= rec.sent_at <= rec.completed_at


def test_saturation_triggered_by_artificial_dispatch_delay(tmp_path: Path):
    """Verifies generator_saturated = True triggers when dispatch latency exceeds 10ms."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "saturated_delay_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=False)
    # Inject 15ms artificial delay before socket write
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        artificial_dispatch_delay_ms=15.0,
    )

    assert result.mean_dispatch_lag_ms >= 12.0
    assert result.mean_dispatch_skew_ms >= 12.0
    assert result.generator_saturated is True


def test_saturation_healthy_run(tmp_path: Path):
    """Verifies generator_saturated = False when dispatch latency and rate are within limits."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "healthy_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=False)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        artificial_dispatch_delay_ms=0.0,
    )

    assert result.mean_dispatch_lag_ms < 10.0
    assert result.generator_saturated is False


@requires_subprocess_socket
def test_runner_poisson_arrival_execution(tmp_path: Path):
    """Verifies execution under Poisson arrival distribution."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=15.0,
        warmup_duration_s=1,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "poisson_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=True)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        seed=42,
    )

    assert result.total_requests > 0
    assert result.failed_requests == 0
    records = JSONLRecorder.read_records(trace_path)
    assert len(records) == result.total_requests
    for rec in records:
        assert rec.scheduled_at <= rec.sent_at <= rec.first_token_at <= rec.completed_at


@requires_subprocess_socket
def test_runner_arun_async_wrapper(tmp_path: Path):
    """Verifies arun() asynchronous dispatch wrapper."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=5.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "async_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=True)
    result = asyncio.run(runner.arun(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        run_id="run-async-01",
    ))

    assert result.total_requests == 5
    assert result.completed_requests == 5


class _PartialFailureServingAdapter(FakeServingAdapter):
    """Emits 2 valid tokens and then yields an error chunk."""
    def stream_generate(self, request):
        from slokern.engine.serving.base import TokenChunk
        yield TokenChunk(token="token1", token_id=1, index=0, timestamp_ms=10.0, latency_ms=10.0, is_last=False)
        yield TokenChunk(token="token2", token_id=2, index=1, timestamp_ms=20.0, latency_ms=10.0, is_last=False)
        yield TokenChunk(
            token="", token_id=0, index=2, timestamp_ms=25.0, latency_ms=5.0, is_last=True,
            error="Connection reset by peer",
            metadata={"status_code": 502, "failure_injected": "network_reset"},
        )


@requires_subprocess_socket
def test_runner_streaming_partial_failure(tmp_path: Path):
    """Verifies streaming handles mid-stream failures, preserving tokens generated prior to error."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=5.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    adapter = _PartialFailureServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "partial_fail_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=True)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        run_id="run-part-01",
    )

    assert result.total_requests == 5
    assert result.failed_requests == 5
    assert result.completed_requests == 0

    records = JSONLRecorder.read_records(trace_path)
    assert len(records) == 5
    for rec in records:
        assert rec.is_valid is False
        assert rec.output_tokens == 2
        assert rec.first_token_at is not None
        assert rec.http_status == 502
        assert rec.error_type == "network_reset"
        assert rec.scheduled_at <= rec.sent_at <= rec.first_token_at <= rec.completed_at


def test_saturation_triggered_by_concurrency_bottleneck(tmp_path: Path):
    """Verifies generator_saturated = True triggers when client concurrency limit causes queueing delays."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=20.0,  # 20 req/s = new request every 50ms
        concurrency_limit=1,       # Only 1 concurrent request allowed
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    # Simulate 80ms processing delay per request to force queue backup
    adapter = FakeServingAdapter(simulate_delay=True, base_ttft_ms=40.0, base_itl_ms=10.0, default_output_tokens=5)
    trace_path = tmp_path / "bottleneck_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=False)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
    )

    # Concurrency bottleneck should cause dispatch lag to accumulate well beyond 10ms threshold
    assert result.mean_dispatch_lag_ms > 10.0
    assert result.generator_saturated is True


class _CrashingServingAdapter(FakeServingAdapter):
    """Simulates hard subprocess abort via os._exit."""
    def stream_generate(self, request):
        import os
        os._exit(42)
        yield from []


@requires_subprocess_socket
def test_runner_subprocess_abrupt_crash_handling(tmp_path: Path):
    """Verifies that an abrupt crash (e.g. exit code 42) in the child process is caught and cleaned up."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=5.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    adapter = _CrashingServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "crash_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=True)
    with pytest.raises(RuntimeError, match="exited abnormally with code 42"):
        runner.run(
            workload=workload,
            adapter=adapter,
            output_path=trace_path,
        )


@requires_subprocess_socket
def test_runner_subprocess_timeout(tmp_path: Path):
    """Verifies that a subprocess exceeding spawn_timeout_s is cleanly terminated and raises TimeoutError."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=5.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    # Simulate a slow adapter taking 200ms per request
    adapter = FakeServingAdapter(simulate_delay=True, base_ttft_ms=200.0)
    trace_path = tmp_path / "timeout_trace.jsonl"

    # Set extremely short timeout to guarantee timeout
    runner = LoadGeneratorRunner(isolate_process=True, spawn_timeout_s=0.05)
    with pytest.raises(TimeoutError, match="timed out"):
        runner.run(
            workload=workload,
            adapter=adapter,
            output_path=trace_path,
        )


def test_runner_multiple_prompts_round_robin(tmp_path: Path):
    """Verifies round-robin prompt dispatching across multiple prompts."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=4.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "multi_prompt_trace.jsonl"

    prompts = ["prompt alpha", "prompt beta long question text", "prompt gamma"]
    runner = LoadGeneratorRunner(isolate_process=False)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        prompts=prompts,
    )

    assert result.total_requests == 4
    records = JSONLRecorder.read_records(trace_path)
    assert len(records) == 4
    # Prompt token counts should vary according to the rotating prompts
    assert records[0].input_tokens != records[1].input_tokens


def test_runner_in_process_timeout(tmp_path: Path):
    """Verifies that isolate_process=False enforces spawn_timeout_s and raises TimeoutError."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=5.0,
        warmup_duration_s=0,
        measurement_duration_s=1,
    )
    # Slow adapter simulating 200ms per request
    adapter = FakeServingAdapter(simulate_delay=True, base_ttft_ms=200.0)
    trace_path = tmp_path / "inprocess_timeout_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=False, spawn_timeout_s=0.05)
    with pytest.raises(TimeoutError):
        runner.run(
            workload=workload,
            adapter=adapter,
            output_path=trace_path,
        )


def test_runner_zero_duration_workload(tmp_path: Path):
    """Verifies degenerate zero-duration workloads complete cleanly without errors."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        warmup_duration_s=0,
        measurement_duration_s=0,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "zero_dur_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=False)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
    )

    assert result.total_requests == 0
    assert result.completed_requests == 0
    assert result.generator_saturated is True  # Rate deficit: 0 rps < 0.90 * 10
    assert trace_path.exists()
    assert JSONLRecorder.read_records(trace_path) == []


@requires_subprocess_socket
def test_runner_arun_cancellation(tmp_path: Path):
    """Verifies cancelling arun() triggers cancel() and raises CancelledError cleanly."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=2.0,
        warmup_duration_s=0,
        measurement_duration_s=5,
    )
    adapter = FakeServingAdapter(simulate_delay=True, base_ttft_ms=500.0)
    trace_path = tmp_path / "cancel_trace.jsonl"

    async def _run_and_cancel():
        runner = LoadGeneratorRunner(isolate_process=True)
        task = asyncio.create_task(
            runner.arun(
                workload=workload,
                adapter=adapter,
                output_path=trace_path,
            )
        )
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # Child process must not remain alive
        assert runner._current_proc is None or not runner._current_proc.is_alive()

    asyncio.run(_run_and_cancel())


@requires_subprocess_socket
def test_runner_arun_cancellation_in_process(tmp_path: Path):
    """Verifies cancelling arun() in in-process mode (isolate_process=False) raises CancelledError cleanly."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=2.0,
        warmup_duration_s=0,
        measurement_duration_s=5,
    )
    adapter = FakeServingAdapter(simulate_delay=True, base_ttft_ms=500.0)
    trace_path = tmp_path / "inprocess_cancel_trace.jsonl"

    async def _run_and_cancel_in_process():
        runner = LoadGeneratorRunner(isolate_process=False)
        task = asyncio.create_task(
            runner.arun(
                workload=workload,
                adapter=adapter,
                output_path=trace_path,
            )
        )
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_run_and_cancel_in_process())


@requires_subprocess_socket
def test_runner_cancel_noop_when_not_running():
    """Verifies cancel() is a safe noop when no execution is active."""
    runner = LoadGeneratorRunner(isolate_process=True)
    # Calling cancel before any run
    runner.cancel()
    assert runner._current_proc is None


@requires_subprocess_socket
def test_runner_trace_end_to_end_metrics_compatibility(tmp_path: Path):
    """Verifies that the generated trace can be ingested directly by calculate_metrics()."""
    from slokern.core.metrics.aggregate import calculate_metrics

    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        warmup_duration_s=1,
        measurement_duration_s=2,
        max_output_tokens=8,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "e2e_metrics_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=True)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        run_id="run-e2e-01",
        stream=True,
    )

    assert result.total_requests == 30
    assert result.warmup_requests == 10
    assert result.active_requests == 20

    # Calculate metrics from the generated trace file
    metrics = calculate_metrics(
        records=trace_path,
        run_id="run-e2e-01",
        target_offered_rate=10.0,
        measurement_duration_s=2.0,
    )

    assert metrics.run_id == "run-e2e-01"
    assert metrics.sample_count == 20
    assert metrics.failed_request_count == 0
    assert metrics.generator_saturated is False
    assert metrics.request_throughput_rps == pytest.approx(10.0, rel=0.01)
    assert metrics.achieved_load_rps == pytest.approx(10.0, rel=0.01)
    assert metrics.offered_load_rps == pytest.approx(10.0, rel=0.01)
    assert metrics.token_throughput_tps == pytest.approx(80.0, rel=0.01)
    assert metrics.error_rate == 0.0
    assert metrics.ttft_ms.mean is not None
    assert metrics.itl_ms.mean is not None

def test_sync_dispatch_platform_fallback(tmp_path: Path):
    """Verifies the synchronous in-process platform fallback executes streaming workload against FakeServingAdapter."""
    workload = _build_test_workload(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=20.0,
        warmup_duration_s=1,
        measurement_duration_s=1,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    trace_path = tmp_path / "sync_fallback_trace.jsonl"

    runner = LoadGeneratorRunner(isolate_process=False)
    result = runner.run(
        workload=workload,
        adapter=adapter,
        output_path=trace_path,
        run_id="run-sync-01",
        stream=True,
    )

    assert isinstance(result, LoadGeneratorResult)
    assert result.total_requests == 40
    assert result.completed_requests == 40
    assert result.failed_requests == 0
    assert trace_path.exists()

    records = JSONLRecorder.read_records(trace_path)
    assert len(records) == 40
    for rec in records:
        assert rec.is_valid is True
        assert rec.first_token_at is not None
        assert rec.scheduled_at <= rec.sent_at <= rec.first_token_at <= rec.completed_at
