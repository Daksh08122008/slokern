"""
Purpose: Canonical derived metrics contract with explicit units and load-generator health indicators.
Owner: Adriraj (Benchmarking) & Rajdeep (Architecture)
Authority: Aligned with docs/metrics.md and docs/architecture.md Section 4
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class PercentileDistribution(BaseModel):
    """Summary statistics for latency observations in milliseconds."""
    p50: Optional[float] = None
    p90: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None
    mean: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None


class MetricSet(BaseModel):
    """
    Derived performance indicators calculated deterministically from valid measurement windows.
    Traceable to raw request records (RawRequestMeasurement).
    """
    metric_version: str = Field(..., description="Version of metric calculation policy")
    run_id: str = Field(..., description="Associated run identifier")
    sample_count: int = Field(..., description="Count of completed valid requests analyzed")
    failed_request_count: int = Field(..., description="Count of failed or aborted requests")
    
    # Load generation metrics (critical for validity auditing)
    offered_load_rps: float = Field(..., description="Actual rate at which client scheduled requests")
    achieved_load_rps: float = Field(..., description="Actual completed request throughput over the measurement window")
    generator_saturated: bool = Field(..., description="Boolean flag indicating whether client load generator saturated")
    
    # Latency metric distributions (all in ms)
    ttft_ms: PercentileDistribution = Field(..., description="Object containing p50, p90, p95, p99, mean, min, max")
    itl_ms: PercentileDistribution = Field(..., description="Object containing p50, p90, p95, p99, mean (with documented aggregation)")
    e2e_latency_ms: PercentileDistribution = Field(..., description="Percentiles and summary of total request durations")
    
    # Throughput and error metrics
    request_throughput_rps: float = Field(..., description="Achieved completed requests per second")
    token_throughput_tps: float = Field(..., description="Total output tokens generated per second")
    error_rate: float = Field(..., description="Ratio of failed requests to total offered requests")
    
    # Optional metadata / notes
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")
