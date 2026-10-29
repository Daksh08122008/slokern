"""
Purpose: Deterministic percentile computation from raw samples using linear interpolation.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md Section 3 and contracts/metrics.py
"""

import math
from typing import Optional, Sequence

from slokern.contracts.metrics import PercentileDistribution


def _interpolate_percentile(sorted_values: Sequence[float], p: float) -> Optional[float]:
    """
    Computes linearly interpolated percentile for quantile p in [0.0, 1.0].
    Formula:
        R = (N - 1) * p
        i = floor(R)
        f = R - i
        percentile = v[i] + f * (v[i + 1] - v[i])
    """
    n = len(sorted_values)
    if n == 0:
        return None
    if n == 1:
        return float(sorted_values[0])

    r = max(0.0, min(float(n - 1), (n - 1) * p))
    i = int(math.floor(r))
    f = r - i
    if i >= n - 1:
        return float(sorted_values[-1])
    return float(sorted_values[i] + f * (sorted_values[i + 1] - sorted_values[i]))


def calculate_percentiles(values: Sequence[float]) -> PercentileDistribution:
    """
    Validates, sorts, and computes linear-interpolated percentiles (p50, p90, p95, p99, mean, min, max).
    Handles empty input (all fields None) and single observation (all stats equal v0).
    """
    clean_values = [float(v) for v in values if v is not None and not math.isnan(v)]
    if not clean_values:
        return PercentileDistribution(
            p50=None,
            p90=None,
            p95=None,
            p99=None,
            mean=None,
            min=None,
            max=None,
        )

    clean_values.sort()
    n = len(clean_values)
    mean_val = float(sum(clean_values) / n)
    min_val = float(clean_values[0])
    max_val = float(clean_values[-1])

    if n == 1:
        v0 = clean_values[0]
        return PercentileDistribution(
            p50=v0,
            p90=v0,
            p95=v0,
            p99=v0,
            mean=v0,
            min=v0,
            max=v0,
        )

    p50_val = _interpolate_percentile(clean_values, 0.50)
    p90_val = _interpolate_percentile(clean_values, 0.90)
    p95_val = _interpolate_percentile(clean_values, 0.95)
    p99_val = _interpolate_percentile(clean_values, 0.99)

    return PercentileDistribution(
        p50=p50_val,
        p90=p90_val,
        p95=p95_val,
        p99=p99_val,
        mean=mean_val,
        min=min_val,
        max=max_val,
    )
