"""
Purpose: Unit tests for core/metrics/throughput.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md Section 2.4-2.7 and contracts/metrics.py
"""

import pytest

from slokern.contracts.evidence import RawRequestMeasurement
from slokern.core.metrics.throughput import (
    calculate_throughputs,
    resolve_window_duration,
)


def _make_measurement(
    request_id: str = "req-01",
    sent_at: float = 100.0,
    completed_at: float = 100.050,
    output_tokens: int = 20,
    is_warmup: bool = False,
    is_valid: bool = True,
    http_status: int = 200,
    error_type: str = None,
) -> RawRequestMeasurement:
    return RawRequestMeasurement(
        request_id=request_id,
        run_id="run-tps",
        scheduled_at=sent_at - 0.001,
        sent_at=sent_at,
        first_token_at=sent_at + 0.010,
        completed_at=completed_at,
        http_status=http_status,
        input_tokens=50,
        output_tokens=output_tokens,
        is_warmup=is_warmup,
        is_valid=is_valid,
        error_type=error_type,
    )


def test_resolve_window_duration_declared():
    """Explicit measurement_duration_s takes precedence over empirical timestamps."""
    records = [
        _make_measurement(sent_at=10.0, completed_at=12.0),
    ]
    dur = resolve_window_duration(records, measurement_duration_s=5.0)
    assert dur == 5.0


def test_resolve_window_duration_empirical_fallback():
    """Omitting measurement_duration_s falls back to max(completed_at) - min(sent_at) across active records."""
    records = [
        _make_measurement(sent_at=10.0, completed_at=10.5, is_warmup=True),  # excluded warmup
        _make_measurement(sent_at=20.0, completed_at=20.2, is_warmup=False),
        _make_measurement(sent_at=21.0, completed_at=23.5, is_warmup=False),
    ]
    # Active span = 23.5 - 20.0 = 3.5s
    dur = resolve_window_duration(records, measurement_duration_s=None)
    assert pytest.approx(dur, rel=1e-4) == 3.5


def test_resolve_window_duration_zero_and_empty():
    """Empty records or 0-duration clamped to >= 1e-6 to prevent division by zero."""
    dur_empty = resolve_window_duration([], measurement_duration_s=None)
    assert dur_empty >= 1e-6

    record_instant = [_make_measurement(sent_at=10.0, completed_at=10.0)]
    dur_instant = resolve_window_duration(record_instant, measurement_duration_s=0.0)
    assert dur_instant >= 1e-6


def test_calculate_throughputs_rates_and_loads():
    """Tests request throughput, token throughput, offered load, achieved load, and error rate."""
    # 4 active requests over 2.0s:
    # 3 valid completed, 1 failed (500 error)
    # output tokens: 10, 20, 30 = 60 tokens from valid requests
    r1 = _make_measurement("r1", output_tokens=10)
    r2 = _make_measurement("r2", output_tokens=20)
    r3 = _make_measurement("r3", output_tokens=30)
    r4_fail = _make_measurement("r4", http_status=500, error_type="server_error", is_valid=False)
    r_warmup = _make_measurement("rw", is_warmup=True, output_tokens=100)

    records = [r1, r2, r3, r4_fail, r_warmup]
    window_s = 2.0

    (
        req_tps,
        tok_tps,
        offered_load,
        achieved_load,
        error_rate,
    ) = calculate_throughputs(records, window_s)

    # 3 valid completed / 2.0s = 1.5 req/s
    assert pytest.approx(req_tps, rel=1e-4) == 1.5
    # 60 tokens / 2.0s = 30.0 tok/s
    assert pytest.approx(tok_tps, rel=1e-4) == 30.0
    # 4 active offered / 2.0s = 2.0 req/s
    assert pytest.approx(offered_load, rel=1e-4) == 2.0
    # 3 valid achieved / 2.0s = 1.5 req/s
    assert pytest.approx(achieved_load, rel=1e-4) == 1.5
    # 1 failed / 4 active = 0.25 (25% error rate)
    assert pytest.approx(error_rate, rel=1e-4) == 0.25


def test_calculate_throughputs_empty_records():
    """Empty records yields 0.0 for all throughputs and error rate without zero-division error."""
    req_tps, tok_tps, offered, achieved, err = calculate_throughputs([], 2.0)
    assert req_tps == 0.0
    assert tok_tps == 0.0
    assert offered == 0.0
    assert achieved == 0.0
    assert err == 0.0


def test_resolve_window_duration_all_warmup_fallback():
    """Trace containing only warmup records returns 1e-6 without leaking warmup span."""
    warmup_records = [
        _make_measurement(sent_at=10.0, completed_at=15.0, is_warmup=True),
        _make_measurement(sent_at=12.0, completed_at=18.0, is_warmup=True),
    ]
    dur = resolve_window_duration(warmup_records, measurement_duration_s=None)
    assert dur == 1e-6
