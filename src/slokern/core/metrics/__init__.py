"""
Purpose: Metrics package exports.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md and contracts/metrics.py
"""

from slokern.core.metrics.percentiles import calculate_percentiles
from slokern.core.metrics.latency import (
    extract_ttft_observations,
    extract_itl_observations,
    extract_e2e_observations,
    is_valid_completed_request,
)
from slokern.core.metrics.throughput import (
    calculate_throughputs,
    resolve_window_duration,
)
from slokern.core.metrics.validity import detect_generator_saturation
from slokern.core.metrics.aggregate import calculate_metrics

__all__ = [
    "calculate_metrics",
    "calculate_percentiles",
    "extract_ttft_observations",
    "extract_itl_observations",
    "extract_e2e_observations",
    "detect_generator_saturation",
    "calculate_throughputs",
    "resolve_window_duration",
    "is_valid_completed_request",
]
