"""
Purpose: Run validity, queue health, and load-generator saturation detection.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md Section 2.6 and contracts/metrics.py
"""

from typing import Dict, Optional, Sequence, Tuple, Union, Any
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.core.metrics.latency import _ensure_measurement
from slokern.core.metrics.throughput import resolve_window_duration


def detect_generator_saturation(
    records: Sequence[Union[RawRequestMeasurement, Dict[str, Any]]],
    target_offered_rate: Optional[float] = None,
    window_duration_s: Optional[float] = None,
) -> Tuple[bool, float, float]:
    """
    Detects whether the client load generator experienced saturation or queue delays.
    Saturation triggers if:
    1. Mean dispatch lag (sent_at - scheduled_at) exceeds 10.0 ms.
    2. Offered load falls below 90% of target offered rate (when target_offered_rate is specified).

    Returns:
        (generator_saturated, mean_lag_ms, max_lag_ms)
    """
    parsed = [_ensure_measurement(r) for r in records]
    active_records = [r for r in parsed if not r.is_warmup]

    if not active_records:
        return (False, 0.0, 0.0)

    lags = [
        max(0.0, (r.sent_at - r.scheduled_at) * 1000.0)
        for r in active_records
    ]

    mean_lag_ms = float(sum(lags) / len(lags))
    max_lag_ms = float(max(lags))

    is_lag_saturated = mean_lag_ms > 10.0

    is_rate_undersupplied = False
    if target_offered_rate is not None and target_offered_rate > 0:
        eff_duration = (
            window_duration_s
            if (window_duration_s is not None and window_duration_s > 0)
            else resolve_window_duration(active_records)
        )
        eff_duration = max(eff_duration, 1e-6)
        offered_load = len(active_records) / eff_duration
        # Apply floating point epsilon tolerance (1e-7) so non-dyadic float products
        # at the exact 90% boundary do not trigger false positive saturation.
        if offered_load < (0.90 * target_offered_rate) - 1e-7:
            is_rate_undersupplied = True

    generator_saturated = is_lag_saturated or is_rate_undersupplied

    return (generator_saturated, mean_lag_ms, max_lag_ms)
