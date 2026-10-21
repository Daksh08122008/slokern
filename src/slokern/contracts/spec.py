"""
Purpose: Workload, SLO, search-space, budget and experiment-spec models.
Owner: Rajdeep
"""

from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.enums import ArrivalMode


class WorkloadSpec(BaseModel):
    """Defines the offered traffic profile to ensure benchmark repeatability."""
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., description="String version identifier (e.g., '1.0.0')")
    workload_name: str = Field(..., description="Identifier for the workload profile")
    fixture_id: str = Field(..., description="Hash or path of the versioned prompt dataset")
    arrival_mode: ArrivalMode = Field(..., description="Arrival process")
    target_offered_rate: float = Field(..., description="Intended requests per second (float, requests/s)")
    concurrency_limit: int = Field(..., description="Maximum concurrent requests in flight")
    warmup_duration_s: int = Field(..., description="Warm-up window duration in seconds")
    measurement_duration_s: int = Field(..., description="Active measurement window in seconds")
    max_input_tokens: int = Field(..., description="Upper bound on input prompt length")
    max_output_tokens: int = Field(..., description="Maximum generated token limit")


class SLOConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(..., description="Target metric")
    statistic: Literal["p50", "p90", "p95", "p99", "mean", "max"] = Field(..., description="Declared statistic")
    threshold: float = Field(..., description="Numeric threshold value")
    unit: Literal["ms", "s", "requests/s", "fraction"] = Field(..., description="Explicit unit")
    operator: Literal["<=", "<", ">=", ">"] = Field(..., description="Comparison operator")


class SLOSpec(BaseModel):
    """Specifies the non-negotiable service-level objectives against which candidates are evaluated."""
    model_config = ConfigDict(extra="forbid")

    slo_id: str = Field(..., description="Unique identifier for the SLO declaration")
    constraints: List[SLOConstraint] = Field(..., description="List of hard constraint rules")
    min_sample_count: int = Field(..., description="Minimum required valid requests to allow an authoritative verdict")


class ExperimentBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_candidates: int = Field(..., description="Hard upper limit on candidate configurations tested")
    max_wallclock_seconds: int = Field(..., description="Maximum total experiment duration")
    max_cost_limit: Optional[float] = Field(None, description="Optional expenditure ceiling")


class ExperimentVerificationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repetitions: int = Field(default=1, description="Number of verification repetitions")
    duration_multiplier: float = Field(default=1.0, description="Multiplier for measurement duration during verification")


class ExperimentSpec(BaseModel):
    """The root document defining an entire optimization experiment."""
    model_config = ConfigDict(extra="forbid")

    experiment_id: str = Field(..., description="Unique identifier for the experiment session")
    workload: WorkloadSpec = Field(..., description="Embedded WorkloadSpec")
    slo: SLOSpec = Field(..., description="Embedded SLOSpec")
    search_space: Dict[str, Any] = Field(..., description="Declared legal parameter ranges and candidate generation rules")
    budget: ExperimentBudget = Field(..., description="Experiment budget")
    verification_policy: ExperimentVerificationPolicy = Field(
        default_factory=ExperimentVerificationPolicy,
        description="Rules governing the independent verification rerun"
    )
