"""
Purpose: Contract test suite validating fixtures, raw measurement integrity, and lifecycle invariants.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with AGENTS.md Section 4, 5, 10, 13 and docs/experiment-methodology.md
"""

import json
import math
from pathlib import Path
import pytest
from pydantic import ValidationError

from slokern.contracts.evidence import RawRequestMeasurement
from slokern.core.metrics.aggregate import calculate_metrics
from slokern.core.metrics.percentiles import calculate_percentiles


FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def test_golden_fixture_percentiles_basic():
    """Validates percentiles_basic.json fixtures against contract and recomputes statistics."""
    fixture_path = FIXTURES_DIR / "metrics_golden" / "percentiles_basic.json"
    assert fixture_path.exists(), f"Missing fixture file: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Metadata check
    assert "_meta" in data
    assert data["_meta"]["owner"] == "Rajdeep"

    # 2. Raw measurements validation against RawRequestMeasurement
    raw_measurements = data.get("raw_measurements", [])
    assert len(raw_measurements) > 0

    validated = []
    seen_ids = set()
    for raw in raw_measurements:
        m = RawRequestMeasurement.model_validate(raw)
        validated.append(m)

        # Unique request ID check
        assert m.request_id not in seen_ids, f"Duplicate request_id: {m.request_id}"
        seen_ids.add(m.request_id)

        # Finite numbers check
        assert math.isfinite(m.scheduled_at)
        assert math.isfinite(m.sent_at)
        assert math.isfinite(m.completed_at)
        if m.first_token_at is not None:
            assert math.isfinite(m.first_token_at)

        # Monotonicity invariant for successful requests:
        # scheduled_at <= sent_at <= first_token_at <= completed_at
        assert m.scheduled_at <= m.sent_at, f"Scheduling inversion in {m.request_id}"
        assert m.first_token_at is not None, f"Expected first_token_at in {m.request_id}"
        assert m.sent_at <= m.first_token_at, f"Negative TTFT in {m.request_id}"
        assert m.first_token_at <= m.completed_at, f"Completion before first token in {m.request_id}"
        assert m.http_status == 200
        assert m.is_valid is True

    # 3. Independent percentile calculation verification
    raw_values = data.get("raw_values", [])
    expected = data.get("expected_percentiles", {})
    computed = calculate_percentiles(raw_values)

    assert computed is not None
    assert round(computed.p50, 3) == round(expected["p50"], 3)
    assert round(computed.p90, 3) == round(expected["p90"], 3)
    assert round(computed.p95, 3) == round(expected["p95"], 3)
    assert round(computed.p99, 3) == round(expected["p99"], 3)
    assert round(computed.mean, 3) == round(expected["mean"], 3)
    assert round(computed.min, 3) == round(expected["min"], 3)
    assert round(computed.max, 3) == round(expected["max"], 3)


def test_golden_fixture_failed_requests():
    """Validates failed_requests.json fixture, lifecycle distinctions, and error metrics."""
    fixture_path = FIXTURES_DIR / "metrics_golden" / "failed_requests.json"
    assert fixture_path.exists(), f"Missing fixture file: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "_meta" in data
    raw_measurements = data.get("raw_measurements", [])
    assert len(raw_measurements) > 0

    validated = []
    seen_ids = set()
    for raw in raw_measurements:
        m = RawRequestMeasurement.model_validate(raw)
        validated.append(m)

        assert m.request_id not in seen_ids, f"Duplicate request_id: {m.request_id}"
        seen_ids.add(m.request_id)

        # Lifecycle distinction:
        # Successful requests have 200, valid timings, and first_token_at
        if m.http_status == 200 and m.error_type is None and m.is_valid:
            assert m.first_token_at is not None
            assert m.scheduled_at <= m.sent_at <= m.first_token_at <= m.completed_at
        else:
            # Failed requests legitimately may lack first_token_at
            assert m.sent_at <= m.completed_at
            assert not m.is_valid or m.http_status != 200 or m.error_type is not None

    # Derive metrics from fixture
    expected = data.get("expected_metrics", {})
    metrics = calculate_metrics(
        records=validated,
        run_id=expected.get("run_id", "run-failed-case-01"),
        target_offered_rate=5.0,
        measurement_duration_s=3.0,
    )
    assert metrics.sample_count == 10  # 10 valid active samples
    assert metrics.failed_request_count == 5  # 5 failed requests
    assert pytest.approx(metrics.error_rate, rel=1e-4) == 5.0 / 15.0  # 5 failed out of 15 total active


def test_evidence_fixtures_schema_and_provenance():
    """Validates evidence fixtures in fixtures/evidence/ adhere to schema and provenance rules."""
    evidence_dir = FIXTURES_DIR / "evidence"

    # 1. Valid pass fixture
    pass_file = evidence_dir / "valid_pass.json"
    assert pass_file.exists()
    pass_data = json.loads(pass_file.read_text(encoding="utf-8"))
    assert pass_data["_meta"]["label"] == "DEMO DATA"
    m_pass = RawRequestMeasurement.model_validate(pass_data["measurement"])
    assert m_pass.is_valid is True
    assert m_pass.scheduled_at <= m_pass.sent_at <= m_pass.first_token_at <= m_pass.completed_at

    # 2. Valid fail fixture
    fail_file = evidence_dir / "valid_fail.json"
    assert fail_file.exists()
    fail_data = json.loads(fail_file.read_text(encoding="utf-8"))
    assert fail_data["_meta"]["label"] == "DEMO DATA"
    m_fail = RawRequestMeasurement.model_validate(fail_data["measurement"])
    assert m_fail.is_valid is True
    assert m_fail.completed_at - m_fail.sent_at > 5.0  # high latency exceeding thresholds

    # 3. Invalid measurement fixture
    invalid_file = evidence_dir / "invalid_measurement.json"
    assert invalid_file.exists()
    invalid_data = json.loads(invalid_file.read_text(encoding="utf-8"))
    assert invalid_data["_meta"]["label"] == "DEMO DATA"
    m_invalid = RawRequestMeasurement.model_validate(invalid_data["measurement"])
    assert m_invalid.is_valid is False
    # Demonstrates scheduling inversion / negative latency in anomalous recording
    assert m_invalid.sent_at < m_invalid.scheduled_at or m_invalid.completed_at < m_invalid.sent_at

    # 4. Runtime failure fixture
    oom_file = evidence_dir / "runtime_failure.json"
    assert oom_file.exists()
    oom_data = json.loads(oom_file.read_text(encoding="utf-8"))
    assert oom_data["_meta"]["label"] == "DEMO DATA"
    m_oom = RawRequestMeasurement.model_validate(oom_data["measurement"])
    assert m_oom.http_status == 500
    assert m_oom.error_type == "cuda_out_of_memory"
    assert m_oom.first_token_at is None


def test_raw_request_measurement_rejects_extra_fields():
    """Verifies ConfigDict(extra='forbid') rejects unrecognized fields at contract boundary."""
    payload = {
        "request_id": "req-01",
        "run_id": "run-01",
        "scheduled_at": 100.0,
        "sent_at": 100.001,
        "completed_at": 100.050,
        "input_tokens": 10,
        "output_tokens": 10,
        "is_warmup": False,
        "is_valid": True,
        "unexpected_field": "unauthorized",
    }
    with pytest.raises(ValidationError, match="extra_forbidden"):
        RawRequestMeasurement.model_validate(payload)


def test_raw_request_measurement_rejects_missing_required_fields():
    """Verifies missing non-optional fields raise ValidationError."""
    payload = {
        "request_id": "req-01",
        "run_id": "run-01",
        # missing scheduled_at
        "sent_at": 100.001,
        "completed_at": 100.050,
        "input_tokens": 10,
        "output_tokens": 10,
        "is_warmup": False,
        "is_valid": True,
    }
    with pytest.raises(ValidationError, match="scheduled_at"):
        RawRequestMeasurement.model_validate(payload)


def test_evidence_invariants_auditor():
    """Audits timestamp monotonicity, finite numbers, and lifecycle distinctions."""
    def audit_measurement_invariants(m: RawRequestMeasurement) -> tuple[bool, str]:
        if not math.isfinite(m.scheduled_at) or not math.isfinite(m.sent_at) or not math.isfinite(m.completed_at):
            return False, "non_finite_timestamp"
        if m.scheduled_at < 0 or m.sent_at < 0 or m.completed_at < 0:
            return False, "negative_timestamp"
        if m.scheduled_at > m.sent_at:
            return False, "scheduling_inversion"
        if m.completed_at < m.sent_at:
            return False, "completion_before_sent"

        # Streaming successful request
        if m.is_valid and m.http_status == 200 and m.error_type is None:
            if m.first_token_at is not None:
                if not math.isfinite(m.first_token_at) or m.first_token_at < 0:
                    return False, "invalid_first_token_at"
                if m.first_token_at < m.sent_at:
                    return False, "first_token_before_sent"
                if m.completed_at < m.first_token_at:
                    return False, "completed_before_first_token"
        return True, "valid"

    # Valid streaming
    m_valid = RawRequestMeasurement(
        request_id="r1", run_id="run1", scheduled_at=1.0, sent_at=1.01,
        first_token_at=1.02, completed_at=1.05, http_status=200,
        input_tokens=5, output_tokens=5, is_warmup=False, is_valid=True
    )
    ok, reason = audit_measurement_invariants(m_valid)
    assert ok is True

    # Inversion: first_token_at < sent_at
    m_inv_ttft = RawRequestMeasurement(
        request_id="r2", run_id="run1", scheduled_at=1.0, sent_at=1.05,
        first_token_at=1.02, completed_at=1.06, http_status=200,
        input_tokens=5, output_tokens=5, is_warmup=False, is_valid=True
    )
    ok, reason = audit_measurement_invariants(m_inv_ttft)
    assert ok is False
    assert reason == "first_token_before_sent"

    # Non-finite timestamp
    m_nan = RawRequestMeasurement(
        request_id="r3", run_id="run1", scheduled_at=float("nan"), sent_at=1.01,
        first_token_at=1.02, completed_at=1.05, http_status=200,
        input_tokens=5, output_tokens=5, is_warmup=False, is_valid=True
    )
    ok, reason = audit_measurement_invariants(m_nan)
    assert ok is False
    assert reason == "non_finite_timestamp"
