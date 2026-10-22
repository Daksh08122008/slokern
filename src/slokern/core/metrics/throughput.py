"""
Purpose: Request and token throughput, offered vs achieved load.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md Section 2.4-2.7 and contracts/metrics.py
"""

from typing import Dict, Optional, Sequence, Tuple, Union, Any
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.core.metrics.latency import is_valid_completed_request, _ensure_measurement


def resolve_window_duration(
    records: Sequence[Union[RawRequestMeasurement, Dict[str, Any]]],
    measurement_duration_s: Optional[float] = None,
) -> float:
    """
    Determines effective measurement duration (seconds).
    Uses declared measurement_duration_s if positive;
    otherwise computes empirical span max(completed_at) - min(sent_at) across active records,
    clamped to >= 1e-6 seconds.
    """
    if measurement_duration_s is not None and measurement_duration_s > 0:
        return float(measurement_duration_s)

    parsed = [_ensure_measurement(r) for r in records]
    active_records = [r for r in parsed if not r.is_warmup]
    if not active_records:
        return 1e-6

    min_sent = min(r.sent_at for r in active_records)
    max_completed = max(r.completed_at for r in active_records)
    span = max_completed - min_sent
    return float(max(span, 1e-6))


def calculate_throughputs(
    records: Sequence[Union[RawRequestMeasurement, Dict[str, Any]]],
    window_duration_s: float,
) -> Tuple[float, float, float, float, float]:
    """
    Computes throughputs and traffic rates over the specified measurement window duration:
    - request_throughput_rps: Completed valid requests / duration
    - token_throughput_tps: Generated output tokens / duration
    - offered_load_rps: Dispatched requests / duration
    - achieved_load_rps: Completed valid requests / duration
    - error_rate: Failed requests / total offered requests (0.0 to 1.0)

    Returns:
        (request_throughput_rps, token_throughput_tps, offered_load_rps, achieved_load_rps, error_rate)
    """
    dur = max(float(window_duration_s), 1e-6)

    parsed = [_ensure_measurement(r) for r in records]
    active_records = [r for r in parsed if not r.is_warmup]

    total_offered = len(active_records)

    failed_records = [
        r for r in active_records
        if (r.error_type is not None or (r.http_status is not None and r.http_status != 200))
    ]

    valid_completed = [r for r in active_records if is_valid_completed_request(r)]

    request_throughput_rps = float(len(valid_completed) / dur)
    total_tokens = sum(r.output_tokens for r in valid_completed)
    token_throughput_tps = float(total_tokens / dur)
    offered_load_rps = float(total_offered / dur)
    achieved_load_rps = float(len(valid_completed) / dur)
    error_rate = float(len(failed_records) / total_offered) if total_offered > 0 else 0.0

    return (
        request_throughput_rps,
        token_throughput_tps,
        offered_load_rps,
        achieved_load_rps,
        error_rate,
    )
