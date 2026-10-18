import pytest

from slokern.core.search.candidate_id import generate_candidate_id
from slokern.core.search.rank import EvaluatedCandidate, rank_candidates
from slokern.contracts.enums import FeasibilityVerdict, RankingObjective
from slokern.contracts.metrics import MetricSet, PercentileDistribution

def create_mock_metric_set(run_id: str):
    return MetricSet(
        metric_version="1.0.0",
        run_id=run_id,
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(),
        itl_ms=PercentileDistribution(),
        e2e_latency_ms=PercentileDistribution(),
        request_throughput_rps=10.0,
        token_throughput_tps=50.0,
        error_rate=0.0
    )

def test_generate_candidate_id_deterministic():
    id1 = generate_candidate_id("model-a", "vllm", {"batch_size": 32})
    id2 = generate_candidate_id("model-a", "vllm", {"batch_size": 32})
    assert id1 == id2

def test_generate_candidate_id_differs():
    id1 = generate_candidate_id("model-a", "vllm", {"batch_size": 32})
    id2 = generate_candidate_id("model-a", "vllm", {"batch_size": 64})
    assert id1 != id2

def test_rank_candidates_filters_infeasible():
    candidates = [
        EvaluatedCandidate("c1", FeasibilityVerdict.FEASIBLE, 10.0, create_mock_metric_set("r1")),
        EvaluatedCandidate("c2", FeasibilityVerdict.INFEASIBLE, 5.0, create_mock_metric_set("r2")),
        EvaluatedCandidate("c3", FeasibilityVerdict.INCONCLUSIVE, 1.0, create_mock_metric_set("r3")),
    ]
    ranked = rank_candidates(candidates, RankingObjective.MONETARY_COST_PER_TOKEN)
    assert len(ranked) == 1
    assert ranked[0].candidate_id == "c1"

def test_rank_candidates_minimize_cost():
    candidates = [
        EvaluatedCandidate("c1", FeasibilityVerdict.FEASIBLE, 10.0, create_mock_metric_set("r1")),
        EvaluatedCandidate("c2", FeasibilityVerdict.FEASIBLE, 5.0, create_mock_metric_set("r2")),
    ]
    ranked = rank_candidates(candidates, RankingObjective.MONETARY_COST_PER_TOKEN)
    assert ranked[0].candidate_id == "c2"

def test_rank_candidates_maximize_throughput():
    candidates = [
        EvaluatedCandidate("c1", FeasibilityVerdict.FEASIBLE, 10.0, create_mock_metric_set("r1")),
        EvaluatedCandidate("c2", FeasibilityVerdict.FEASIBLE, 5.0, create_mock_metric_set("r2")),
    ]
    ranked = rank_candidates(candidates, RankingObjective.MAX_THROUGHPUT_UNDER_SLO)
    assert ranked[0].candidate_id == "c1"

def test_rank_candidates_tie_breaking():
    # c2 and c1 have same metric. "c1" < "c2" alphabetically
    candidates = [
        EvaluatedCandidate("c2", FeasibilityVerdict.FEASIBLE, 10.0, create_mock_metric_set("r2")),
        EvaluatedCandidate("c1", FeasibilityVerdict.FEASIBLE, 10.0, create_mock_metric_set("r1")),
    ]
    ranked = rank_candidates(candidates, RankingObjective.MONETARY_COST_PER_TOKEN)
    assert ranked[0].candidate_id == "c1"
