"""
Purpose: Unit tests for core/metrics/aggregate.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md and contracts/metrics.py
"""

import json
from pathlib import Path
import pytest

from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.metrics import MetricSet
from slokern.core.metrics.aggregate import calculate_metrics


def test_calculate_metrics_in_memory_golden_fixture():
    """End-to-end calculate_metrics with in-memory records matches percentiles_basic.json expected metrics."""
    fixture_path = Path("fixtures/metrics_golden/percentiles_basic.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_measurements = [
        RawRequestMeasurement.model_validate(r) for r in data["raw_measurements"]
    ]
    expected = data["expected_metrics"]

    metrics = calculate_metrics(
        records=raw_measurements,
        run_id=expected["run_id"],
        target_offered_rate=10.0,
        measurement_duration_s=2.0,
        metric_version=expected["metric_version"],
    )

    assert isinstance(metrics, MetricSet)
    assert metrics.run_id == expected["run_id"]
    assert metrics.metric_version == expected["metric_version"]
    assert metrics.sample_count == expected["sample_count"]
    assert metrics.failed_request_count == expected["failed_request_count"]
    assert pytest.approx(metrics.offered_load_rps, rel=1e-3) == expected["offered_load_rps"]
    assert pytest.approx(metrics.achieved_load_rps, rel=1e-3) == expected["achieved_load_rps"]
    assert metrics.generator_saturated == expected["generator_saturated"]

    # Latencies
    assert pytest.approx(metrics.ttft_ms.p50, rel=1e-3) == expected["ttft_ms"]["p50"]
    assert pytest.approx(metrics.ttft_ms.p90, rel=1e-3) == expected["ttft_ms"]["p90"]
    assert pytest.approx(metrics.ttft_ms.p95, rel=1e-3) == expected["ttft_ms"]["p95"]
    assert pytest.approx(metrics.ttft_ms.p99, rel=1e-3) == expected["ttft_ms"]["p99"]
    assert pytest.approx(metrics.ttft_ms.mean, rel=1e-3) == expected["ttft_ms"]["mean"]

    assert pytest.approx(metrics.itl_ms.p50, rel=1e-3) == expected["itl_ms"]["p50"]
    assert pytest.approx(metrics.itl_ms.p90, rel=1e-3) == expected["itl_ms"]["p90"]
    assert pytest.approx(metrics.itl_ms.p95, rel=1e-3) == expected["itl_ms"]["p95"]
    assert pytest.approx(metrics.itl_ms.p99, rel=1e-3) == expected["itl_ms"]["p99"]
    assert pytest.approx(metrics.itl_ms.mean, rel=1e-3) == expected["itl_ms"]["mean"]

    assert pytest.approx(metrics.e2e_latency_ms.p50, rel=1e-3) == expected["e2e_latency_ms"]["p50"]
    assert pytest.approx(metrics.e2e_latency_ms.p90, rel=1e-3) == expected["e2e_latency_ms"]["p90"]
    assert pytest.approx(metrics.e2e_latency_ms.p95, rel=1e-3) == expected["e2e_latency_ms"]["p95"]
    assert pytest.approx(metrics.e2e_latency_ms.p99, rel=1e-3) == expected["e2e_latency_ms"]["p99"]
    assert pytest.approx(metrics.e2e_latency_ms.mean, rel=1e-3) == expected["e2e_latency_ms"]["mean"]

    # Throughputs
    assert pytest.approx(metrics.request_throughput_rps, rel=1e-3) == expected["request_throughput_rps"]
    assert pytest.approx(metrics.token_throughput_tps, rel=1e-3) == expected["token_throughput_tps"]
    assert pytest.approx(metrics.error_rate, rel=1e-3) == expected["error_rate"]


def test_calculate_metrics_from_jsonl_file(tmp_path: Path):
    """calculate_metrics successfully streams from a .jsonl trace file on disk."""
    fixture_path = Path("fixtures/metrics_golden/percentiles_basic.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    jsonl_file = tmp_path / "test_trace.jsonl"
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for r in data["raw_measurements"]:
            m = RawRequestMeasurement.model_validate(r)
            f.write(m.model_dump_json() + "\n")

    metrics = calculate_metrics(
        records=jsonl_file,
        target_offered_rate=10.0,
        measurement_duration_s=2.0,
    )
    assert metrics.sample_count == 20
    assert metrics.run_id == "run-golden-01"
    assert metrics.generator_saturated is False


def test_calculate_metrics_with_failed_requests_fixture():
    """calculate_metrics with failed_requests.json correctly computes sample counts and error rates."""
    fixture_path = Path("fixtures/metrics_golden/failed_requests.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_measurements = [
        RawRequestMeasurement.model_validate(r) for r in data["raw_measurements"]
    ]
    expected = data["expected_metrics"]

    metrics = calculate_metrics(
        records=raw_measurements,
        run_id=expected["run_id"],
        target_offered_rate=5.0,
        measurement_duration_s=3.0,
    )

    assert metrics.sample_count == 10
    assert metrics.failed_request_count == 5
    assert pytest.approx(metrics.error_rate, rel=1e-4) == 5.0 / 15.0
    assert pytest.approx(metrics.offered_load_rps, rel=1e-4) == 5.0
    assert pytest.approx(metrics.achieved_load_rps, rel=1e-4) == 10.0 / 3.0
    assert pytest.approx(metrics.request_throughput_rps, rel=1e-4) == 10.0 / 3.0
    assert pytest.approx(metrics.token_throughput_tps, rel=1e-4) == 160.0 / 3.0
    assert metrics.generator_saturated is False


def test_calculate_metrics_100_percent_failed():
    """100% failed request run produces valid MetricSet with 0 samples, 1.0 error rate, and None percentiles."""
    failed_records = [
        RawRequestMeasurement(
            request_id=f"req-f-{i}",
            run_id="run-all-fail",
            scheduled_at=10.0 + i * 0.1,
            sent_at=10.001 + i * 0.1,
            first_token_at=None,
            completed_at=10.010 + i * 0.1,
            http_status=500,
            input_tokens=10,
            output_tokens=0,
            is_warmup=False,
            is_valid=False,
            error_type="connection_refused",
        )
        for i in range(5)
    ]

    metrics = calculate_metrics(
        records=failed_records,
        measurement_duration_s=1.0,
    )

    assert metrics.sample_count == 0
    assert metrics.failed_request_count == 5
    assert metrics.error_rate == 1.0
    assert metrics.request_throughput_rps == 0.0
    assert metrics.token_throughput_tps == 0.0
    assert metrics.achieved_load_rps == 0.0
    assert metrics.offered_load_rps == 5.0

    # All percentiles must be None
    assert metrics.ttft_ms.p50 is None
    assert metrics.itl_ms.p50 is None
    assert metrics.e2e_latency_ms.p50 is None


def test_calculate_metrics_warmup_strictly_excluded():
    """Warmup samples are strictly excluded from all counts and latency percentiles."""
    records = [
        RawRequestMeasurement(
            request_id="req-warmup",
            run_id="run-warmup-test",
            scheduled_at=10.0,
            sent_at=10.001,
            first_token_at=10.020,
            completed_at=10.100,
            http_status=200,
            input_tokens=10,
            output_tokens=10,
            is_warmup=True,
            is_valid=True,
        ),
        RawRequestMeasurement(
            request_id="req-active",
            run_id="run-warmup-test",
            scheduled_at=20.0,
            sent_at=20.001,
            first_token_at=20.035, # TTFT = 34ms
            completed_at=20.150,   # E2E = 149ms
            http_status=200,
            input_tokens=10,
            output_tokens=10,
            is_warmup=False,
            is_valid=True,
        ),
    ]

    metrics = calculate_metrics(records, measurement_duration_s=1.0)
    assert metrics.sample_count == 1
    assert metrics.failed_request_count == 0
    assert metrics.offered_load_rps == 1.0
    assert pytest.approx(metrics.ttft_ms.p50, rel=1e-3) == 34.0
    assert pytest.approx(metrics.e2e_latency_ms.p50, rel=1e-3) == 149.0


def test_calculate_metrics_empty_records():
    """Empty list of records produces valid MetricSet with 0 counts and None percentiles."""
    metrics = calculate_metrics([], run_id="run-empty")
    assert metrics.run_id == "run-empty"
    assert metrics.sample_count == 0
    assert metrics.failed_request_count == 0
    assert metrics.offered_load_rps == 0.0
    assert metrics.achieved_load_rps == 0.0
    assert metrics.generator_saturated is False
    assert metrics.ttft_ms.p50 is None
    assert metrics.itl_ms.p50 is None
    assert metrics.e2e_latency_ms.p50 is None


def test_calculate_metrics_dict_records():
    """calculate_metrics accepts dictionaries conforming to RawRequestMeasurement schema."""
    dict_records = [
        {
            "request_id": "req-d1",
            "run_id": "run-dict",
            "scheduled_at": 10.0,
            "sent_at": 10.002,
            "first_token_at": 10.022,
            "completed_at": 10.102,
            "http_status": 200,
            "input_tokens": 10,
            "output_tokens": 10,
            "is_warmup": False,
            "is_valid": True,
        }
    ]
    metrics = calculate_metrics(dict_records, measurement_duration_s=1.0)
    assert metrics.sample_count == 1
    assert metrics.run_id == "run-dict"
    assert pytest.approx(metrics.ttft_ms.p50, rel=1e-3) == 20.0


def test_calculate_metrics_nonexistent_file():
    """Nonexistent trace file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        calculate_metrics(Path("/tmp/nonexistent_slokern_trace.jsonl"))


def test_calculate_metrics_only_warmup_records():
    """If all records are warmup, active count is 0 and all percentiles are None."""
    warmup_only = [
        RawRequestMeasurement(
            request_id="req-w1",
            run_id="run-warmup-only",
            scheduled_at=10.0,
            sent_at=10.001,
            first_token_at=10.020,
            completed_at=10.100,
            http_status=200,
            input_tokens=10,
            output_tokens=10,
            is_warmup=True,
            is_valid=True,
        )
    ]
    metrics = calculate_metrics(warmup_only, measurement_duration_s=1.0)
    assert metrics.sample_count == 0
    assert metrics.failed_request_count == 0
    assert metrics.offered_load_rps == 0.0
    assert metrics.ttft_ms.p50 is None


def test_calculate_metrics_metadata_preservation():
    """Custom metadata dictionary passed into calculate_metrics is preserved in MetricSet."""
    custom_meta = {"trace_source": "synthetic_load", "operator": "ci_pipeline"}
    metrics = calculate_metrics([], run_id="run-meta", metadata=custom_meta)
    assert metrics.metadata == custom_meta


def test_calculate_metrics_empty_with_target_rate():
    """Empty records with target_offered_rate does not falsely trigger generator_saturated = True."""
    metrics = calculate_metrics([], run_id="run-empty-target", target_offered_rate=10.0)
    assert metrics.generator_saturated is False
    assert metrics.sample_count == 0
    assert metrics.failed_request_count == 0


def test_calculate_metrics_malformed_jsonl(tmp_path: Path):
    """Corrupted line in a .jsonl file raises ValueError indicating the exact line number."""
    bad_file = tmp_path / "corrupted_trace.jsonl"
    with open(bad_file, "w", encoding="utf-8") as f:
        # Line 1: valid
        f.write('{"request_id":"r1","run_id":"run-1","scheduled_at":10.0,"sent_at":10.001,"completed_at":10.05,"input_tokens":10,"output_tokens":10,"is_warmup":false,"is_valid":true}\n')
        # Line 2: broken JSON
        f.write('{"request_id":"r2", broken_json\n')

    with pytest.raises(ValueError, match="Malformed JSONL record on line 2 in trace file"):
        calculate_metrics(bad_file)


def test_calculate_metrics_with_generator_stream():
    """calculate_metrics accepts an unexhausted generator stream of records."""
    rec = RawRequestMeasurement(
        request_id="req-gen-1",
        run_id="run-gen",
        scheduled_at=10.0,
        sent_at=10.001,
        first_token_at=10.021,
        completed_at=10.101,
        http_status=200,
        input_tokens=10,
        output_tokens=10,
        is_warmup=False,
        is_valid=True,
    )
    generator_input = (r for r in [rec])
    metrics = calculate_metrics(generator_input, measurement_duration_s=1.0)
    assert metrics.sample_count == 1
    assert metrics.run_id == "run-gen"
    assert pytest.approx(metrics.ttft_ms.p50, rel=1e-3) == 20.0
