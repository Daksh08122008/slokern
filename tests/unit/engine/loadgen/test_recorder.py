"""
Purpose: Unit tests for engine/loadgen/recorder.
Owner: Rajdeep (Historical design: Adriraj)
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from slokern.contracts.evidence import RawRequestMeasurement
from slokern.engine.loadgen.recorder import JSONLRecorder


def _sample_measurement(
    request_id: str = "req-001",
    run_id: str = "run-001",
    scheduled_at: float = 1000.0,
    sent_at: float = 1000.002,
    first_token_at: float = 1000.015,
    completed_at: float = 1000.080,
    http_status: int = 200,
    input_tokens: int = 128,
    output_tokens: int = 32,
    is_warmup: bool = False,
    is_valid: bool = True,
    error_type: str = None,
) -> RawRequestMeasurement:
    return RawRequestMeasurement(
        request_id=request_id,
        run_id=run_id,
        scheduled_at=scheduled_at,
        sent_at=sent_at,
        first_token_at=first_token_at,
        completed_at=completed_at,
        http_status=http_status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        is_warmup=is_warmup,
        is_valid=is_valid,
        error_type=error_type,
    )


def test_recorder_writes_valid_jsonl(tmp_path: Path):
    file_path = tmp_path / "measurements.jsonl"
    with JSONLRecorder(file_path=file_path) as recorder:
        m1 = _sample_measurement("req-01", is_warmup=True)
        m2 = _sample_measurement("req-02", is_warmup=False)
        recorder.record(m1)
        recorder.record(m2)

    lines = file_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    # Verify each line strictly validates against RawRequestMeasurement
    parsed1 = RawRequestMeasurement.model_validate_json(lines[0])
    parsed2 = RawRequestMeasurement.model_validate_json(lines[1])
    assert parsed1.request_id == "req-01"
    assert parsed1.is_warmup is True
    assert parsed2.request_id == "req-02"
    assert parsed2.is_warmup is False


def test_recorder_immediate_disk_flush(tmp_path: Path):
    file_path = tmp_path / "flush_test.jsonl"
    recorder = JSONLRecorder(file_path=file_path, flush_immediately=True)
    m = _sample_measurement("req-flush")
    recorder.record(m)

    # Read file from disk BEFORE closing recorder
    disk_content = file_path.read_text(encoding="utf-8").strip()
    assert disk_content != ""
    record_read = RawRequestMeasurement.model_validate_json(disk_content)
    assert record_read.request_id == "req-flush"
    recorder.close()


def test_recorder_validates_dict_input(tmp_path: Path):
    file_path = tmp_path / "dict_test.jsonl"
    with JSONLRecorder(file_path=file_path) as recorder:
        valid_dict = {
            "request_id": "req-dict-01",
            "run_id": "run-01",
            "scheduled_at": 100.0,
            "sent_at": 100.005,
            "first_token_at": 100.020,
            "completed_at": 100.050,
            "http_status": 200,
            "input_tokens": 64,
            "output_tokens": 16,
            "is_warmup": False,
            "is_valid": True,
        }
        res = recorder.record(valid_dict)
        assert isinstance(res, RawRequestMeasurement)
        assert res.request_id == "req-dict-01"


def test_recorder_rejects_invalid_schema(tmp_path: Path):
    file_path = tmp_path / "invalid_test.jsonl"
    with JSONLRecorder(file_path=file_path) as recorder:
        # Missing required field 'run_id'
        with pytest.raises(ValidationError):
            recorder.record({
                "request_id": "req-bad",
                "scheduled_at": 100.0,
                "sent_at": 100.0,
                "completed_at": 100.1,
                "input_tokens": 10,
                "output_tokens": 5,
                "is_warmup": False,
                "is_valid": True,
            })

        # Extra disallowed field (extra='forbid')
        with pytest.raises(ValidationError):
            recorder.record({
                "request_id": "req-extra",
                "run_id": "run-01",
                "scheduled_at": 100.0,
                "sent_at": 100.0,
                "completed_at": 100.1,
                "input_tokens": 10,
                "output_tokens": 5,
                "is_warmup": False,
                "is_valid": True,
                "forbidden_extra_field": "disallowed",
            })


def test_recorder_running_stats(tmp_path: Path):
    file_path = tmp_path / "stats_test.jsonl"
    with JSONLRecorder(file_path=file_path) as recorder:
        # Request 1: Warmup, lag = 2.0ms
        recorder.record(_sample_measurement("req-w1", scheduled_at=100.0, sent_at=100.002, is_warmup=True))
        # Request 2: Warmup, lag = 4.0ms
        recorder.record(_sample_measurement("req-w2", scheduled_at=100.0, sent_at=100.004, is_warmup=True))
        # Request 3: Active, lag = 6.0ms, valid
        recorder.record(_sample_measurement("req-a1", scheduled_at=100.0, sent_at=100.006, is_warmup=False, is_valid=True))
        # Request 4: Active, lag = 8.0ms, error
        recorder.record(_sample_measurement(
            "req-a2",
            scheduled_at=100.0,
            sent_at=100.008,
            is_warmup=False,
            is_valid=False,
            http_status=500,
            error_type="cuda_out_of_memory",
        ))

        stats = recorder.get_stats()
        assert stats.total_count == 4
        assert stats.warmup_count == 2
        assert stats.active_count == 2
        assert stats.valid_count == 3
        assert stats.active_valid_count == 1
        assert stats.error_count == 1
        assert stats.active_error_count == 1

        # All lags: 2, 4, 6, 8 ms -> mean = 5.0ms, max = 8.0ms, min = 2.0ms
        assert stats.mean_dispatch_lag_ms == 5.0
        assert stats.max_dispatch_lag_ms == 8.0
        assert stats.min_dispatch_lag_ms == 2.0

        # Active lags: 6, 8 ms -> active mean = 7.0ms, active max = 8.0ms
        assert stats.active_mean_dispatch_lag_ms == 7.0
        assert stats.active_max_dispatch_lag_ms == 8.0


def test_recorder_read_records(tmp_path: Path):
    file_path = tmp_path / "read_back.jsonl"
    with JSONLRecorder(file_path=file_path) as recorder:
        for i in range(5):
            recorder.record(_sample_measurement(f"req-{i}", scheduled_at=10.0 + i, sent_at=10.001 + i))

    read_back = JSONLRecorder.read_records(file_path)
    assert len(read_back) == 5
    for i, rec in enumerate(read_back):
        assert rec.request_id == f"req-{i}"
        assert isinstance(rec, RawRequestMeasurement)


def test_recorder_closed_error(tmp_path: Path):
    file_path = tmp_path / "closed.jsonl"
    recorder = JSONLRecorder(file_path=file_path)
    recorder.close()
    with pytest.raises(RuntimeError, match="Cannot record to closed"):
        recorder.record(_sample_measurement("req-fail"))


def test_recorder_concurrent_thread_writes(tmp_path: Path):
    """Verifies that concurrent writes from multiple threads are serialized safely without loss."""
    import concurrent.futures
    file_path = tmp_path / "concurrent.jsonl"

    recorder = JSONLRecorder(file_path=file_path, flush_immediately=True)
    num_threads = 8
    writes_per_thread = 25
    total_expected = num_threads * writes_per_thread

    def worker(thread_idx: int):
        for i in range(writes_per_thread):
            req_id = f"req-t{thread_idx}-{i}"
            recorder.record(_sample_measurement(req_id, scheduled_at=100.0, sent_at=100.002))

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, t) for t in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    stats = recorder.get_stats()
    assert stats.total_count == total_expected
    assert recorder.total_count == total_expected
    recorder.close()

    records = JSONLRecorder.read_records(file_path)
    assert len(records) == total_expected


def test_recorder_all_property_accessors(tmp_path: Path):
    """Verifies all direct property accessors on JSONLRecorder match get_stats()."""
    file_path = tmp_path / "props_test.jsonl"
    with JSONLRecorder(file_path=file_path) as rec:
        rec.record(_sample_measurement("req-w", scheduled_at=10.0, sent_at=10.002, is_warmup=True))
        rec.record(_sample_measurement("req-a1", scheduled_at=10.0, sent_at=10.005, is_warmup=False, is_valid=True))
        rec.record(_sample_measurement(
            "req-a2",
            scheduled_at=10.0,
            sent_at=10.010,
            is_warmup=False,
            is_valid=False,
            http_status=500,
            error_type="server_error",
        ))

        stats = rec.get_stats()
        assert rec.total_count == stats.total_count == 3
        assert rec.warmup_count == stats.warmup_count == 1
        assert rec.active_count == stats.active_count == 2
        assert rec.valid_count == stats.valid_count == 2
        assert rec.active_valid_count == stats.active_valid_count == 1
        assert rec.error_count == stats.error_count == 1
        assert rec.active_error_count == stats.active_error_count == 1
        assert rec.mean_dispatch_lag_ms == stats.mean_dispatch_lag_ms
        assert rec.max_dispatch_lag_ms == stats.max_dispatch_lag_ms
        assert rec.min_dispatch_lag_ms == stats.min_dispatch_lag_ms
        assert rec.active_mean_dispatch_lag_ms == stats.active_mean_dispatch_lag_ms
        assert rec.active_max_dispatch_lag_ms == stats.active_max_dispatch_lag_ms
