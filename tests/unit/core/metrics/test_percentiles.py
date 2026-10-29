"""
Purpose: Unit tests for core/metrics/percentiles.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md Section 3 and contracts/metrics.py
"""

import json
from pathlib import Path

import pytest

from slokern.contracts.metrics import PercentileDistribution
from slokern.core.metrics.percentiles import calculate_percentiles


def test_percentiles_empty():
    """Empty list returns PercentileDistribution with all fields set to None."""
    dist = calculate_percentiles([])
    assert isinstance(dist, PercentileDistribution)
    assert dist.p50 is None
    assert dist.p90 is None
    assert dist.p95 is None
    assert dist.p99 is None
    assert dist.mean is None
    assert dist.min is None
    assert dist.max is None


def test_percentiles_single_element():
    """Single element returns that exact element for min, max, mean, and all percentiles."""
    val = 42.5
    dist = calculate_percentiles([val])
    assert dist.p50 == val
    assert dist.p90 == val
    assert dist.p95 == val
    assert dist.p99 == val
    assert dist.mean == val
    assert dist.min == val
    assert dist.max == val


def test_percentiles_two_elements():
    """Two-element list tests basic linear interpolation."""
    # N = 2: v0 = 10.0, v1 = 20.0
    # p = 0.50 -> R = (2-1)*0.5 = 0.5 -> 10 + 0.5*(20-10) = 15.0
    # p = 0.90 -> R = 0.9 -> 10 + 0.9*10 = 19.0
    # p = 0.95 -> R = 0.95 -> 10 + 0.95*10 = 19.5
    # p = 0.99 -> R = 0.99 -> 10 + 0.99*10 = 19.9
    dist = calculate_percentiles([10.0, 20.0])
    assert pytest.approx(dist.p50, rel=1e-4) == 15.0
    assert pytest.approx(dist.p90, rel=1e-4) == 19.0
    assert pytest.approx(dist.p95, rel=1e-4) == 19.5
    assert pytest.approx(dist.p99, rel=1e-4) == 19.9
    assert pytest.approx(dist.mean, rel=1e-4) == 15.0
    assert dist.min == 10.0
    assert dist.max == 20.0


def test_percentiles_eleven_elements_golden_fixture():
    """11-element vector against golden fixture matches expected percentiles to 3 decimal places."""
    fixture_path = Path("fixtures/metrics_golden/percentiles_basic.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_values = data["raw_values"]
    expected = data["expected_percentiles"]

    dist = calculate_percentiles(raw_values)
    assert round(dist.p50, 3) == round(expected["p50"], 3)
    assert round(dist.p90, 3) == round(expected["p90"], 3)
    assert round(dist.p95, 3) == round(expected["p95"], 3)
    assert round(dist.p99, 3) == round(expected["p99"], 3)
    assert round(dist.mean, 3) == round(expected["mean"], 3)
    assert round(dist.min, 3) == round(expected["min"], 3)
    assert round(dist.max, 3) == round(expected["max"], 3)


def test_percentiles_unsorted_input():
    """Unsorted input produces identical results as sorted input."""
    raw = [50.0, 10.0, 40.0, 20.0, 30.0]
    dist_unsorted = calculate_percentiles(raw)
    dist_sorted = calculate_percentiles(sorted(raw))

    assert dist_unsorted.p50 == dist_sorted.p50
    assert dist_unsorted.p90 == dist_sorted.p90
    assert dist_unsorted.p95 == dist_sorted.p95
    assert dist_unsorted.p99 == dist_sorted.p99
    assert dist_unsorted.mean == dist_sorted.mean
    assert dist_unsorted.min == dist_sorted.min
    assert dist_unsorted.max == dist_sorted.max


def test_percentiles_handles_nans_and_nones():
    """NaNs and Nones are filtered out before computing percentiles."""
    values = [10.0, float("nan"), 20.0, 30.0]
    dist = calculate_percentiles(values)
    assert dist.p50 == 20.0
    assert dist.min == 10.0
    assert dist.max == 30.0
    assert dist.mean == 20.0

    all_nan = [float("nan"), float("nan")]
    dist_nan = calculate_percentiles(all_nan)
    assert dist_nan.p50 is None


def test_interpolate_percentile_clamps_out_of_bounds():
    """Quantiles outside [0.0, 1.0] are safely clamped without negative index wraparound."""
    from slokern.core.metrics.percentiles import _interpolate_percentile

    values = [10.0, 20.0, 30.0]
    # Negative quantile clamped to index 0 (10.0) rather than wrapping around to index -1 (30.0)
    assert _interpolate_percentile(values, -0.5) == 10.0
    # Over 1.0 clamped to index -1 (30.0)
    assert _interpolate_percentile(values, 1.5) == 30.0


def test_percentiles_with_generator_input():
    """calculate_percentiles accepts generators and iterables."""
    gen = (x * 10.0 for x in range(1, 4))  # 10.0, 20.0, 30.0
    dist = calculate_percentiles(gen)
    assert dist.p50 == 20.0
    assert dist.min == 10.0
    assert dist.max == 30.0
    assert dist.mean == 20.0
