"""
Purpose: Unit tests for core/search/space: 2x2 bounded search space definition and candidate generation.
Owner: Rajdeep (Historical design: Rohan)
"""

from slokern.contracts.config import CandidateConfig
from slokern.core.search.candidate_id import generate_candidate_id
from slokern.core.search.space import (
    generate_2x2_candidates,
    get_search_space_dimensions,
    validate_candidate_settings,
)


def test_bounded_search_space_dimensions():
    dims = get_search_space_dimensions()
    assert "max_num_batched_tokens" in dims
    assert "max_num_seqs" in dims
    assert dims["max_num_batched_tokens"] == [1024, 2048]
    assert dims["max_num_seqs"] == [16, 64]


def test_generate_2x2_candidates_count_and_types():
    model = "meta-llama/Meta-Llama-3-8B-Instruct"
    runtime = "vllm"

    candidates = generate_2x2_candidates(model, runtime)
    assert len(candidates) == 4

    seen_ids = set()
    seen_settings = set()

    for cand in candidates:
        assert isinstance(cand, CandidateConfig)
        assert cand.model_name == model
        assert cand.runtime_name == runtime
        assert len(cand.candidate_id) == 12

        # Assert candidate_id matches deterministic canonical hash
        expected_id = generate_candidate_id(model, runtime, cand.requested_settings)
        assert cand.candidate_id == expected_id

        seen_ids.add(cand.candidate_id)
        seen_settings.add(
            (
                cand.requested_settings["max_num_batched_tokens"],
                cand.requested_settings["max_num_seqs"],
            )
        )

    # All candidate IDs must be strictly unique
    assert len(seen_ids) == 4
    # All combinations must match declared matrix
    expected_combinations = {
        (1024, 16),
        (1024, 64),
        (2048, 16),
        (2048, 64),
    }
    assert seen_settings == expected_combinations


def test_generate_2x2_candidates_deterministic():
    model = "meta-llama/Meta-Llama-3-8B-Instruct"
    runtime = "vllm"

    run1 = generate_2x2_candidates(model, runtime)
    run2 = generate_2x2_candidates(model, runtime)

    assert [c.candidate_id for c in run1] == [c.candidate_id for c in run2]
    assert [c.requested_settings for c in run1] == [c.requested_settings for c in run2]


def test_validate_candidate_settings():
    allowed = ["max_num_batched_tokens", "max_num_seqs"]

    assert validate_candidate_settings({"max_num_batched_tokens": 1024}, allowed) is True
    assert validate_candidate_settings({"max_num_batched_tokens": 1024, "max_num_seqs": 16}, allowed) is True
    assert validate_candidate_settings({"unsupported_param": 123}, allowed) is False
    assert validate_candidate_settings({"max_num_batched_tokens": 1024, "unknown": True}, allowed) is False
    assert validate_candidate_settings({}, allowed) is True
