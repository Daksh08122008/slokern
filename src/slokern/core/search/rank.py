"""
Purpose: Deterministic ranking of feasible candidates by the declared objective.
Owner: Rohan
"""

from typing import List, Dict, Optional
from dataclasses import dataclass

from slokern.contracts.search import CandidateSummary, SearchResult
from slokern.contracts.enums import FeasibilityVerdict, RankingObjective
from slokern.contracts.metrics import MetricSet


@dataclass
class EvaluatedCandidate:
    candidate_id: str
    verdict: FeasibilityVerdict
    ranking_metric: Optional[float]
    metric_set: MetricSet


def rank_candidates(
    evaluated_candidates: List[EvaluatedCandidate],
    objective: RankingObjective
) -> List[EvaluatedCandidate]:
    """
    Filters feasible candidates and ranks them according to the given objective.
    Tie-breaking: if metric values are equal, sort by candidate_id to be deterministic.
    """
    feasible_candidates = [
        c for c in evaluated_candidates
        if c.verdict == FeasibilityVerdict.FEASIBLE
    ]

    # Determine sorting direction.
    # Cost and time should be minimized (ascending).
    # Throughput should be maximized (descending).
    minimize = objective in [
        RankingObjective.MONETARY_COST_PER_TOKEN,
        RankingObjective.MONETARY_COST_PER_1K_REQUESTS,
        RankingObjective.GPU_SECONDS_PER_REQUEST
    ]

    # Sort
    feasible_candidates.sort(
        key=lambda c: (
            c.ranking_metric if minimize else -c.ranking_metric if c.ranking_metric is not None else 0,
            c.candidate_id
        )
    )

    return feasible_candidates
