"""
Purpose: Unit tests for core/metrics/validity.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md Section 2.6 and contracts/metrics.py
"""

import pytest

from slokern.contracts.evidence import RawRequestMeasurement
from slokern.core.metrics.validity import detect_generator_saturation


def _make_measurement(
    scheduled_at: float,
    sent_at: float,
    completed_at: float = 100.1,
    is_warmup: bool = False,
) -> RawRequestMeasurement:
    return RawRequestMeasurement(
        request_id="req-val",
        run_id="run-val",
        scheduled_at=scheduled_at,
        sent_at=sent_at,
        first_token_at=sent_at + 0.010,
        completed_at=completed_at,
        http_status=200,
        input_tokens=10,
        output_tokens=10,
        is_warmup=is_warmup,
        is_valid=True,
    )


def test_saturation_healthy_trace():
    """Trace with low dispatch lag (2ms) and matching offered rate flags saturated = False."""
    # 10 requests over 1.0s = 10 req/s, target = 10 req/s, lag = 2ms
    records = [
        _make_measurement(scheduled_at=10.0 + i * 0.1, sent_at=10.002 + i * 0.1, completed_at=10.05 + i * 0.1)
        for i in range(10)
    ]
    saturated, mean_lag, max_lag = detect_generator_saturation(
        records,
        target_offered_rate=10.0,
        window_duration_s=1.0,
    )
    assert saturated is False
    assert pytest.approx(mean_lag, rel=1e-3) == 2.0
    assert pytest.approx(max_lag, rel=1e-3) == 2.0


def test_saturation_high_dispatch_lag():
    """Mean dispatch lag exceeding 10.0 ms triggers generator_saturated = True."""
    # 2 requests: lags 12ms and 14ms -> mean 13ms (> 10ms)
    records = [
        _make_measurement(scheduled_at=10.0, sent_at=10.012),
        _make_measurement(scheduled_at=10.1, sent_at=10.114),
    ]
    saturated, mean_lag, max_lag = detect_generator_saturation(
        records,
        target_offered_rate=None,
        window_duration_s=1.0,
    )
    assert saturated is True
    assert pytest.approx(mean_lag, rel=1e-3) == 13.0
    assert pytest.approx(max_lag, rel=1e-3) == 14.0


def test_saturation_rate_undersupply():
    """Delivered offered load falling below 90% of target rate triggers generator_saturated = True."""
    # Target = 20.0 req/s. 90% of target = 18.0 req/s.
    # We deliver only 15 requests over 1.0s -> 15.0 req/s (< 18.0 req/s).
    # Dispatch lag is tiny (1ms), but rate is insufficient.
    records = [
        _make_measurement(scheduled_at=10.0 + i * 0.05, sent_at=10.001 + i * 0.05)
        for i in range(15)
    ]
    saturated, mean_lag, _ = detect_generator_saturation(
        records,
        target_offered_rate=20.0,
        window_duration_s=1.0,
    )
    assert saturated is True
    assert pytest.approx(mean_lag, rel=1e-3) == 1.0


def test_saturation_rate_sufficient_boundary():
    """Delivered offered load exactly at or above 90% of target rate passes."""
    # Target = 10.0 req/s. 90% = 9.0 req/s.
    # Delivered = 9 requests over 1.0s = 9.0 req/s.
    records = [
        _make_measurement(scheduled_at=10.0 + i * 0.1, sent_at=10.001 + i * 0.1)
        for i in range(9)
    ]
    saturated, _, _ = detect_generator_saturation(
        records,
        target_offered_rate=10.0,
        window_duration_s=1.0,
    )
    assert saturated is False


def test_saturation_warmup_excluded():
    """Warmup records with high lag are ignored when computing active dispatch lag."""
    # Warmup request has 50ms lag, but active request has 2ms lag.
    records = [
        _make_measurement(scheduled_at=10.0, sent_at=10.050, is_warmup=True),
        _make_measurement(scheduled_at=20.0, sent_at=20.002, is_warmup=False),
    ]
    saturated, mean_lag, max_lag = detect_generator_saturation(records, window_duration_s=1.0)
    assert saturated is False
    assert pytest.approx(mean_lag, rel=1e-3) == 2.0


def test_saturation_empty_records():
    """Empty records returns safe defaults: saturated = False, mean_lag = 0.0, max_lag = 0.0."""
    saturated, mean_lag, max_lag = detect_generator_saturation([])
    assert saturated is False
    assert mean_lag == 0.0
    assert max_lag == 0.0


def test_saturation_empty_records_with_target_rate():
    """Empty records with target_offered_rate declared returns saturated = False (not contaminated)."""
    saturated, mean_lag, max_lag = detect_generator_saturation([], target_offered_rate=10.0)
    assert saturated is False
    assert mean_lag == 0.0
    assert max_lag == 0.0


def test_saturation_only_warmup_records_with_target_rate():
    """Trace with only warmup records returns saturated = False even with target rate declared."""
    warmup_records = [
        _make_measurement(scheduled_at=10.0 + i * 0.1, sent_at=10.001 + i * 0.1, is_warmup=True)
        for i in range(5)
    ]
    saturated, mean_lag, max_lag = detect_generator_saturation(
        warmup_records, target_offered_rate=10.0, window_duration_s=1.0
    )
    assert saturated is False
    assert mean_lag == 0.0
    assert max_lag == 0.0


def test_saturation_rate_sufficient_float_boundary():
    """Delivered offered load at exact 90% boundary with non-dyadic float target passes cleanly."""
    # Target = 26.0 req/s. 90% is 23.4 req/s. In IEEE 754, 0.90 * 26.0 = 23.400000000000002.
    # We deliver exactly 234 requests over 10.0s = 23.4 req/s.
    records = [
        _make_measurement(scheduled_at=100.0 + i * (10.0 / 234), sent_at=100.001 + i * (10.0 / 234))
        for i in range(234)
    ]
    saturated, _, _ = detect_generator_saturation(
        records,
        target_offered_rate=26.0,
        window_duration_s=10.0,
    )
    assert saturated is False
