with open("tests/unit/engine/loadgen/test_runner.py", "r", encoding="utf-8") as f:
    text = f.read()

header_snippet = """def _can_bind_and_connect_loopback() -> bool:
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
"""

if "requires_subprocess_socket" not in text:
    text = text.replace("from slokern.engine.serving.fake import FakeServingAdapter\n", "from slokern.engine.serving.fake import FakeServingAdapter\n\n" + header_snippet)

subprocess_funcs = [
    "test_runner_subprocess_dispatch_streaming",
    "test_runner_handles_injected_server_errors",
    "test_runner_poisson_arrival_execution",
    "test_runner_arun_async_wrapper",
    "test_runner_streaming_partial_failure",
    "test_runner_subprocess_abrupt_crash_handling",
    "test_runner_subprocess_timeout",
    "test_runner_arun_cancellation",
    "test_runner_cancel_noop_when_not_running",
    "test_runner_trace_end_to_end_metrics_compatibility",
]

for func in subprocess_funcs:
    target = f"def {func}("
    replacement = f"@requires_subprocess_socket\ndef {func}("
    if replacement not in text:
        text = text.replace(target, replacement)

platform_fallback_test = """
def test_sync_dispatch_platform_fallback(tmp_path: Path):
    \"\"\"Verifies the synchronous in-process platform fallback executes streaming workload against FakeServingAdapter.\"\"\"
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
"""

if "test_sync_dispatch_platform_fallback" not in text:
    text += platform_fallback_test

with open("tests/unit/engine/loadgen/test_runner.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(text)

print("Successfully updated test_runner.py")

