"""
Purpose: Search package exports.
Owner: Rajdeep (Historical design: Rohan)
"""

from slokern.core.search.candidate_id import generate_candidate_id
from slokern.core.search.space import (
    BOUNDED_SEARCH_SPACE_2X2,
    generate_2x2_candidates,
    validate_candidate_settings,
    get_search_space_dimensions,
)
from slokern.core.search.budget import (
    BudgetLimiter,
    ExperimentBudget,
    BudgetExhaustedError,
)
from slokern.core.search.rank import (
    EvaluatedCandidate,
    rank_candidates,
)
from slokern.core.search.grid import (
    GridSearchController,
    extract_ranking_metric,
)

__all__ = [
    "generate_candidate_id",
    "BOUNDED_SEARCH_SPACE_2X2",
    "generate_2x2_candidates",
    "validate_candidate_settings",
    "get_search_space_dimensions",
    "BudgetLimiter",
    "ExperimentBudget",
    "BudgetExhaustedError",
    "EvaluatedCandidate",
    "rank_candidates",
    "GridSearchController",
    "extract_ranking_metric",
]
