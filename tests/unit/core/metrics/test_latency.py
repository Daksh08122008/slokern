"""
Purpose: Unit tests for core/metrics/latency.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md Section 2 and contracts/evidence.py
"""

from typing import Optional
import pytest

from slokern.contracts.evidence import RawRequestMeasurement
from slokern.core.metrics.latency import (
    extract_ttft_observations,
    extract_itl_observations,
    extract_e2e_observations,
    is_valid_completed_request,
)


def _make_record(
    request_id: str = "req-01",
    run_id: str = "run-01",
    scheduled_at: float = 100.0,
    sent_at: float = 100.002,
    first_token_at: Optional[float] = 100.022,
    completed_at: float = 100.102,
    http_status: int = 200,
    input_tokens: int = 50,
    output_tokens: int = 10,
    itl_observations_ms: Optional[list] = None,
    error_type: Optional[str] = None,
    is_warmup: bool = False,
    is_valid: bool = True,
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
        itl_observations_ms=itl_observations_ms,
        error_type=error_type,
        is_warmup=is_warmup,
        is_valid=is_valid,
    )


def test_is_valid_completed_request():
    """Verifies filtering of warmup, invalid, and error requests."""
    valid = _make_record()
    assert is_valid_completed_request(valid) is True

    warmup = _make_record(is_warmup=True)
    assert is_valid_completed_request(warmup) is False

    invalid = _make_record(is_valid=False)
    assert is_valid_completed_request(invalid) is False

    error_rec = _make_record(error_type="cuda_out_of_memory", is_valid=False)
    assert is_valid_completed_request(error_rec) is False

    status_err = _make_record(http_status=500)
    assert is_valid_completed_request(status_err) is False


def test_extract_ttft_observations():
    """TTFT is extracted as (first_token_at - sent_at) * 1000 for valid requests with tokens >= 1."""
    r1 = _make_record(sent_at=10.0, first_token_at=10.025, output_tokens=5)  # 25 ms
    r2 = _make_record(sent_at=20.0, first_token_at=20.050, output_tokens=10) # 50 ms
    r_warmup = _make_record(sent_at=30.0, first_token_at=30.010, is_warmup=True)
    r_no_first_token = _make_record(sent_at=40.0, first_token_at=None, output_tokens=0)
    r_zero_output = _make_record(sent_at=50.0, first_token_at=50.020, output_tokens=0)
    r_error = _make_record(sent_at=60.0, first_token_at=60.010, http_status=500)

    records = [r1, r2, r_warmup, r_no_first_token, r_zero_output, r_error]
    ttft_obs = extract_ttft_observations(records)

    assert len(ttft_obs) == 2
    assert pytest.approx(ttft_obs[0], rel=1e-4) == 25.0
    assert pytest.approx(ttft_obs[1], rel=1e-4) == 50.0


def test_extract_itl_observations_direct_list():
    """ITL extraction uses mean(itl_observations_ms) when non-empty."""
    r1 = _make_record(
        output_tokens=4,
        itl_observations_ms=[10.0, 12.0, 14.0],
    )
    obs = extract_itl_observations([r1])
    assert len(obs) == 1
    assert pytest.approx(obs[0], rel=1e-4) == 12.0


def test_extract_itl_observations_fallback():
    """ITL extraction falls back to (completed_at - first_token_at)*1000 / (output_tokens - 1)."""
    # first_token_at = 100.0, completed_at = 100.090, output_tokens = 10 (tokens - 1 = 9)
    # total gen time = 90 ms -> ITL = 90 / 9 = 10.0 ms
    r1 = _make_record(
        first_token_at=100.0,
        completed_at=100.090,
        output_tokens=10,
        itl_observations_ms=None,
    )
    obs = extract_itl_observations([r1])
    assert len(obs) == 1
    assert pytest.approx(obs[0], rel=1e-4) == 10.0


def test_extract_itl_filters_single_token_and_warmup():
    """Requests with output_tokens < 2 or is_warmup=True are omitted from ITL."""
    r_single = _make_record(output_tokens=1, first_token_at=10.0, completed_at=10.05)
    r_warmup = _make_record(output_tokens=5, is_warmup=True)
    obs = extract_itl_observations([r_single, r_warmup])
    assert len(obs) == 0


def test_extract_e2e_observations():
    """E2E latency is (completed_at - sent_at) * 1000 for valid active requests."""
    r1 = _make_record(sent_at=100.0, completed_at=100.250) # 250 ms
    r2 = _make_record(sent_at=200.0, completed_at=200.120) # 120 ms
    r_warmup = _make_record(sent_at=300.0, completed_at=300.500, is_warmup=True)
    r_invalid = _make_record(sent_at=400.0, completed_at=400.300, is_valid=False)

    obs = extract_e2e_observations([r1, r2, r_warmup, r_invalid])
    assert len(obs) == 2
    assert pytest.approx(obs[0], rel=1e-4) == 250.0
    assert pytest.approx(obs[1], rel=1e-4) == 120.0
