import pytest
from slokern.core.search.space import validate_candidate_settings
from slokern.core.search.rank import rank_candidates, EvaluatedCandidate
from slokern.contracts.enums import FeasibilityVerdict, RankingObjective

def test_validate_candidate_settings():
    assert validate_candidate_settings({"batch_size": 32}, ["batch_size", "gpu_memory_utilization"]) is True
    assert validate_candidate_settings({"invalid": 1}, ["batch_size"]) is False

def test_rank_candidates_with_none_metric_minimize():
    c1 = EvaluatedCandidate("c1", FeasibilityVerdict.FEASIBLE, None, None)
    c2 = EvaluatedCandidate("c2", FeasibilityVerdict.FEASIBLE, 10.0, None)

    ranked = rank_candidates([c1, c2], RankingObjective.MONETARY_COST_PER_TOKEN)
    assert ranked[0].candidate_id == "c2"
    assert ranked[1].candidate_id == "c1"

def test_rank_candidates_with_none_metric_maximize():
    c1 = EvaluatedCandidate("c1", FeasibilityVerdict.FEASIBLE, None, None)
    c2 = EvaluatedCandidate("c2", FeasibilityVerdict.FEASIBLE, 10.0, None)

    ranked = rank_candidates([c1, c2], RankingObjective.MAX_THROUGHPUT_UNDER_SLO)
    assert ranked[0].candidate_id == "c2"
    assert ranked[1].candidate_id == "c1"
