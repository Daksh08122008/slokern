"""
Purpose: Independent verification record model.
Owner: Rajdeep
"""

from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.enums import VerificationState


class DriftAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_deltas: Dict[str, float] = Field(..., description="Percent difference between search run and verification run metrics")
    slo_drift_detected: bool = Field(..., description="Boolean indicating whether verification drifted across a threshold")


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
    final_decision_notes: Optional[str] = Field(None, description="Explanation of confirmation or failure")
