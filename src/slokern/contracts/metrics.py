"""
Purpose: Canonical derived metrics contract with explicit units and load-generator health indicators.
Owner: Adriraj (Benchmarking) & Rajdeep (Architecture)
Authority: Aligned with docs/metrics.md and docs/architecture.md Section 4
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class PercentileDistribution:
    """Summary statistics for latency observations in milliseconds."""
    p50: Optional[float] = None
    p90: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None
    mean: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None


@dataclass
class MetricSet:
    """
    Derived performance indicators calculated deterministically from valid measurement windows.
    Traceable to raw request records (RawRequestMeasurement).
    """
    metric_version: str
    run_id: str
    sample_count: int
    failed_request_count: int
    
    # Load generation metrics (critical for validity auditing)
    offered_load_rps: float
    achieved_load_rps: float
    generator_saturated: bool
    
    # Latency metric distributions (all in ms)
    ttft_ms: PercentileDistribution
    itl_ms: PercentileDistribution
    e2e_latency_ms: PercentileDistribution
    
    # Throughput and error metrics
    request_throughput_rps: float
    token_throughput_tps: float
    error_rate: float
    
    # Optional metadata / notes
    metadata: Dict[str, Any] = field(default_factory=dict)
