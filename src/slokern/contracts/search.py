"""
Purpose: Search and candidate ranking result models.
Owner: Rajdeep
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.enums import FeasibilityVerdict, RankingObjective


class CandidateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: FeasibilityVerdict
    ranking_metric: Optional[float] = None


class SearchResult(BaseModel):
    """Bounded search exploration history and candidate ranking."""
    model_config = ConfigDict(extra="forbid")

    experiment_id: str = Field(..., description="Parent experiment identifier")
    baseline_candidate_id: str = Field(..., description="ID of baseline configuration")
    tested_candidates: List[str] = Field(..., description="List of tested candidate IDs in execution order")
    candidate_summaries: Dict[str, CandidateSummary] = Field(..., description="Map of candidate ID to feasibility verdict and ranking metric")
    ranking_objective: RankingObjective = Field(..., description="Declared objective function")
    selected_candidate_id: Optional[str] = Field(None, description="Winning feasible candidate ID (null if no candidate was feasible)")
    selection_rationale: str = Field(..., description="Deterministic justification for the winning choice")
    stopping_reason: str = Field(..., description="Reason search halted ('budget_exhausted', 'space_exhausted', 'early_convergence', 'timeout')")
