"""
Purpose: Combines raw evidence into canonical, unit-explicit MetricSet.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md and contracts/metrics.py
"""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.metrics import MetricSet
from slokern.core.metrics.latency import (
    _ensure_measurement,
    extract_e2e_observations,
    extract_itl_observations,
    extract_ttft_observations,
    is_valid_completed_request,
)
from slokern.core.metrics.percentiles import calculate_percentiles
from slokern.core.metrics.throughput import (
    calculate_throughputs,
    resolve_window_duration,
)
from slokern.core.metrics.validity import detect_generator_saturation


def calculate_metrics(
    records: Union[Iterable[Union[RawRequestMeasurement, Dict[str, Any]]], str, Path],
    run_id: Optional[str] = None,
    target_offered_rate: Optional[float] = None,
    measurement_duration_s: Optional[float] = None,
    metric_version: str = "1.0.0",
    metadata: Optional[Dict[str, Any]] = None,
) -> MetricSet:
    """
    Deterministically computes a canonical MetricSet from raw request measurements.

    1. Filters out warm-up records (is_warmup == True).
    2. Derives linear-interpolated percentiles for TTFT, ITL, and E2E latencies.
    3. Computes throughputs, offered vs achieved load, and error rate.
    4. Audits client generator queue health (mean lag > 10ms or load < 90% target rate).
    5. Returns fully validated MetricSet.
    """
    parsed_records: List[RawRequestMeasurement] = []

    if isinstance(records, (str, Path)):
        trace_path = Path(records)
        if not trace_path.exists():
            raise FileNotFoundError(f"Trace file does not exist: {trace_path}")
        with open(trace_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                stripped = line.strip()
                if stripped:
                    try:
                        parsed_records.append(RawRequestMeasurement.model_validate_json(stripped))
                    except Exception as exc:
                        raise ValueError(
                            f"Malformed JSONL record on line {line_no} in trace file '{trace_path}': {exc}"
                        ) from exc
    else:
        for r in records:
            parsed_records.append(_ensure_measurement(r))

    resolved_run_id = run_id
    if resolved_run_id is None:
        if parsed_records:
            resolved_run_id = parsed_records[0].run_id
        else:
            resolved_run_id = "unknown"

    active_records = [r for r in parsed_records if not r.is_warmup]

    failed_records = [
        r for r in active_records
        if (r.error_type is not None or (r.http_status is not None and r.http_status != 200))
    ]
    valid_completed_records = [r for r in active_records if is_valid_completed_request(r)]

    sample_count = len(valid_completed_records)
    failed_request_count = len(failed_records)

    eff_duration_s = resolve_window_duration(active_records, measurement_duration_s)

    (
        request_throughput_rps,
        token_throughput_tps,
        offered_load_rps,
        achieved_load_rps,
        error_rate,
    ) = calculate_throughputs(active_records, eff_duration_s)

    (
        generator_saturated,
        _mean_lag_ms,
        _max_lag_ms,
    ) = detect_generator_saturation(active_records, target_offered_rate, eff_duration_s)

    ttft_obs = extract_ttft_observations(active_records)
    ttft_dist = calculate_percentiles(ttft_obs)

    itl_obs = extract_itl_observations(active_records)
    itl_dist = calculate_percentiles(itl_obs)

    e2e_obs = extract_e2e_observations(active_records)
    e2e_dist = calculate_percentiles(e2e_obs)

    final_metadata = dict(metadata) if metadata is not None else {}

    return MetricSet(
        metric_version=metric_version,
        run_id=resolved_run_id,
        sample_count=sample_count,
        failed_request_count=failed_request_count,
        offered_load_rps=offered_load_rps,
        achieved_load_rps=achieved_load_rps,
        generator_saturated=generator_saturated,
        ttft_ms=ttft_dist,
        itl_ms=itl_dist,
        e2e_latency_ms=e2e_dist,
        request_throughput_rps=request_throughput_rps,
        token_throughput_tps=token_throughput_tps,
        error_rate=error_rate,
        metadata=final_metadata,
    )
