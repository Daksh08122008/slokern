"""
Purpose: Search package exports.
Owner: Rajdeep (Historical design: Rohan)
"""

from slokern.core.search.budget import (
    BudgetExhaustedError,
    BudgetLimiter,
    ExperimentBudget,
)
from slokern.core.search.candidate_id import generate_candidate_id
from slokern.core.search.grid import (
    GridSearchController,
    GridSearchOutcome,
    SearchConfigurationError,
    SearchExecutionError,
    extract_ranking_metric,
    run_grid_search,
    validate_search_capabilities,
)
from slokern.core.search.rank import (
    EvaluatedCandidate,
    rank_candidates,
)
from slokern.core.search.space import (
    BOUNDED_SEARCH_SPACE_2X2,
    generate_2x2_candidates,
    get_search_space_dimensions,
    validate_candidate_settings,
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
    "GridSearchOutcome",
    "SearchConfigurationError",
    "SearchExecutionError",
    "extract_ranking_metric",
    "run_grid_search",
    "validate_search_capabilities",
]
