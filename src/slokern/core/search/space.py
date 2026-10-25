"""
Purpose: Candidate input, config validation logic, and 2x2 bounded search space definition.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, Section 6, and ROADMAP.md TASK-10
"""

from typing import Dict, Any, List
from slokern.contracts.config import CandidateConfig
from slokern.core.search.candidate_id import generate_candidate_id


BOUNDED_SEARCH_SPACE_2X2: Dict[str, List[int]] = {
    "max_num_batched_tokens": [1024, 2048],
    "max_num_seqs": [16, 64],
}


def validate_candidate_settings(
    settings: Dict[str, Any],
    allowed_keys: List[str]
) -> bool:
    """
    Validates that a candidate only contains allowed settings.
    """
    for key in settings:
        if key not in allowed_keys:
            return False
    return True


def get_search_space_dimensions() -> Dict[str, List[int]]:
    """Returns the declared legal 2x2 bounded parameter ranges."""
    return {k: list(v) for k, v in BOUNDED_SEARCH_SPACE_2X2.items()}


def generate_2x2_candidates(model_name: str, runtime_name: str) -> List[CandidateConfig]:
    """
    Generates the canonical 2x2 parameter matrix:
    max_num_batched_tokens in {1024, 2048} x max_num_seqs in {16, 64} (4 legal candidates total).
    Assigns stable canonical candidate IDs via generate_candidate_id().
    """
    candidates: List[CandidateConfig] = []

    # Deterministic ordered grid iteration
    for batched_tokens in BOUNDED_SEARCH_SPACE_2X2["max_num_batched_tokens"]:
        for max_seqs in BOUNDED_SEARCH_SPACE_2X2["max_num_seqs"]:
            settings = {
                "max_num_batched_tokens": int(batched_tokens),
                "max_num_seqs": int(max_seqs),
            }
            cand_id = generate_candidate_id(
                model_name=model_name,
                runtime_name=runtime_name,
                requested_settings=settings
            )
            candidate = CandidateConfig(
                candidate_id=cand_id,
                model_name=model_name,
                runtime_name=runtime_name,
                requested_settings=settings,
                effective_settings={},
                parameter_status={},
                environment_fingerprint={},
            )
            candidates.append(candidate)

    return candidates
