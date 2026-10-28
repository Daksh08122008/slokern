"""
Purpose: Independent verification record model.
Owner: Rajdeep
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.enums import ReasonCode, VerificationState
from slokern.contracts.metrics import MetricSet
from slokern.contracts.verdict import FeasibilityResult


class MetricDriftComparison(BaseModel):
    """Detailed drift evaluation for an individual metric."""
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(..., description="Canonical metric identifier")
    reference_value: float = Field(..., description="Reference measurement from winning search run")
    verification_value: float = Field(..., description="Fresh measurement from independent verification run")
    absolute_drift: float = Field(..., description="Absolute difference between verification and reference")
    relative_drift: Optional[float] = Field(None, description="Percentage drift relative to reference when defined")
    tolerance: float = Field(..., description="Declared drift tolerance threshold")
    comparison_method: Literal["relative_percentage", "absolute_difference"] = Field(..., description="Mathematical comparison formula applied")
    unit: str = Field(..., description="Explicit metric unit")
    passed: bool = Field(..., description="True if drift is within accepted tolerance")
    failure_reason: Optional[str] = Field(None, description="Diagnostic reason if drift failed or could not be evaluated")


class DriftAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_deltas: Dict[str, float] = Field(..., description="Percent difference between search run and verification run metrics")
    slo_drift_detected: bool = Field(..., description="Boolean indicating whether verification drifted across a threshold")
    metric_comparisons: Optional[Dict[str, MetricDriftComparison]] = Field(default=None, description="Detailed per-metric drift evaluations")
    drift_exceeded: bool = Field(default=False, description="True if any required metric exceeded its declared drift tolerance")


class VerificationRecord(BaseModel):
    """Independent verification audit record for the winning candidate."""
    model_config = ConfigDict(extra="forbid")

    verification_id: str = Field(..., description="Unique identifier for the verification session")
    experiment_id: str = Field(..., description="Associated experiment identifier")
    candidate_id: str = Field(..., description="Frozen candidate configuration tested")
    original_run_id: str = Field(..., description="Search run ID where candidate was selected")
    verification_run_id: str = Field(..., description="Fresh run ID under which rerun was conducted")
    verification_verdict: VerificationState = Field(..., description="Enum: VERIFIED, VERIFICATION_FAILED, VERIFICATION_INCONCLUSIVE")
    drift_analysis: Optional[DriftAnalysis] = Field(None, description="Drift analysis")
    metric_set: Optional[MetricSet] = Field(default=None, description="Derived metrics from the verification run")
    feasibility_result: Optional[FeasibilityResult] = Field(default=None, description="Deterministic feasibility verdict from the verification run")
    reason_codes: Optional[List[ReasonCode]] = Field(default=None, description="Machine-readable decision reason codes")
    final_decision_notes: Optional[str] = Field(None, description="Explanation of confirmation or failure")
