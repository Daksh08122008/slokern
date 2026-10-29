"""
Purpose: Deterministic ranking of feasible candidates by the declared objective.
Owner: Rajdeep (Historical design: Rohan)
"""

import math
from dataclasses import dataclass
from typing import List, Optional

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
    feasible_candidates = []
    for candidate in evaluated_candidates:
        if candidate.verdict != FeasibilityVerdict.FEASIBLE:
            continue
        value = candidate.ranking_metric
        if (
            value is None
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            continue
        try:
            if not math.isfinite(value) or value < 0:
                continue
        except OverflowError:
            continue
        feasible_candidates.append(candidate)

    # Determine sorting direction.
    # Cost and time should be minimized (ascending).
    # Throughput should be maximized (descending).
    minimize = objective in [
        RankingObjective.MONETARY_COST_PER_TOKEN,
        RankingObjective.MONETARY_COST_PER_1K_REQUESTS,
        RankingObjective.GPU_SECONDS_PER_REQUEST
    ]

    feasible_candidates.sort(
        key=lambda c: (
            c.ranking_metric if minimize else -c.ranking_metric,
            c.candidate_id
        )
    )

    return feasible_candidates
