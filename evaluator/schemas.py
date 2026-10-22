# daksh

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class VerdictState(str, Enum):
    """The three deterministic verdict states for a benchmark run."""
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    INCONCLUSIVE = "INCONCLUSIVE"


class ReasonCode(str, Enum):
    """Explicit reason codes for failed or inconclusive runs."""
    # Infeasible Reason Codes
    TTFT_EXCEEDED = "TTFT_EXCEEDED"
    ITL_EXCEEDED = "ITL_EXCEEDED"
    HIGH_ERROR_RATE = "HIGH_ERROR_RATE"
    OOM_CRASH = "OOM_CRASH"

    # Inconclusive Reason Codes
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
    MISSING_METRICS = "MISSING_METRICS"
    RUN_CONTAMINATED = "RUN_CONTAMINATED"


class ConstraintResult(BaseModel):
    """Individual constraint pass/fail evaluation."""
    constraint_name: str
    target_value: float
    actual_value: Optional[float]
    passed: bool
    reason_code: Optional[ReasonCode] = None


class Verdict(BaseModel):
    """Final deterministic evaluation verdict for a candidate run."""
    run_id: str
    candidate_id: str
    state: VerdictState
    reasons: List[ReasonCode] = Field(default_factory=list)
    constraint_results: List[ConstraintResult] = Field(default_factory=list)
    notes: Optional[str] = None