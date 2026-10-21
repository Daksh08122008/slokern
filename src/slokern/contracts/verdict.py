"""
Purpose: Per-constraint verdict and reason-code models.
Owner: Rajdeep
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.enums import FeasibilityVerdict, ReasonCode, EvidenceValidity


class ConstraintEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(..., description="Target metric")
    statistic: str = Field(..., description="Evaluated statistic")
    observed_value: Optional[float] = Field(None, description="Derived metric value (null if metric missing or sample insufficient)")
    required_threshold: float = Field(..., description="Threshold from SLOSpec")
    operator: str = Field(..., description="Comparison operator")
    passed: Optional[bool] = Field(None, description="Boolean or null")
    reason_code: ReasonCode = Field(..., description="Machine-readable reason code")


class FeasibilityResult(BaseModel):
    """Deterministic constraint audit result."""
    model_config = ConfigDict(extra="forbid")

    policy_version: str = Field(..., description="Version of feasibility evaluation rules")
    run_id: str = Field(..., description="Associated run identifier")
    overall_verdict: FeasibilityVerdict = Field(..., description="Enum: FEASIBLE, INFEASIBLE, INCONCLUSIVE")
    constraint_evaluations: List[ConstraintEvaluation] = Field(..., description="List of per-constraint evaluation records")
    validity_status: EvidenceValidity = Field(..., description="Enum: VALID, INVALID, CONTAMINATED")
    audit_notes: Optional[str] = Field(None, description="Structured text explaining edge cases or exclusions")
