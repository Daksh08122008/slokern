"""
Purpose: Report and summary models.
Owner: Rajdeep
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import FeasibilityVerdict
from slokern.contracts.spec import ExperimentSpec
from slokern.contracts.verification import VerificationRecord


class BaselineSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_candidate_id: str
    verdict: FeasibilityVerdict
    metrics: Dict[str, Any]


class SearchSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tested_candidates: List[str]
    rejected_options: List[str]
    rankings: List[str]


class ReportArtifact(BaseModel):
    """Self-contained, inspectable artifact published for users and hackathon judges."""
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="Unique report identifier")
    created_at: str = Field(..., description="UTC ISO timestamp")
    experiment_spec: ExperimentSpec = Field(..., description="Complete immutable specification")
    environment_fingerprint: Dict[str, Any] = Field(..., description="Full hardware/runtime environment documentation")
    baseline_summary: BaselineSummary = Field(..., description="Baseline metrics and verdict")
    search_summary: SearchSummary = Field(..., description="Candidate table, rankings, and rejected options")
    selected_candidate: Optional[CandidateConfig] = Field(None, description="Detailed configuration of the winning candidate")
    verification_record: Optional[VerificationRecord] = Field(None, description="Complete verification audit")
    limitations_disclosed: Dict[str, Any] = Field(..., description="Tested search space bounds and known environment constraints")
    cost_accounting_basis: str = Field(..., description="Explicit source of pricing data or declaration of unavailable")
    artifact_paths: Dict[str, str] = Field(..., description="References to raw measurement files and logs")
