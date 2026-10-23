"""Candidate input and objective-evidence validation tests."""

from slokern.contracts.enums import FeasibilityVerdict, RankingObjective
from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.core.search.rank import EvaluatedCandidate, rank_candidates
from slokern.core.search.space import validate_candidate_settings


def make_metrics():
    return MetricSet(
        metric_version="1.0",
        run_id="run-test",
        sample_count=1,
        failed_request_count=0,
        offered_load_rps=1.0,
        achieved_load_rps=1.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(),
        itl_ms=PercentileDistribution(),
        e2e_latency_ms=PercentileDistribution(),
        request_throughput_rps=1.0,
        token_throughput_tps=10.0,
        error_rate=0.0,
    )


def candidate(candidate_id, ranking_metric, verdict=FeasibilityVerdict.FEASIBLE):
    return EvaluatedCandidate(candidate_id, verdict, ranking_metric, make_metrics())


def test_validate_candidate_settings():
    assert validate_candidate_settings(
        {"batch_size": 32}, ["batch_size", "gpu_memory_utilization"]
    ) is True
    assert validate_candidate_settings({"invalid": 1}, ["batch_size"]) is False


def test_rank_candidates_filters_missing_and_non_finite_metrics():
    candidates = [
        candidate("missing", None),
        candidate("nan", float("nan")),
        candidate("infinity", float("inf")),
        candidate("valid", 10.0),
    ]
    ranked = rank_candidates(candidates, RankingObjective.MONETARY_COST_PER_TOKEN)
    assert [item.candidate_id for item in ranked] == ["valid"]


def test_rank_candidates_filters_string_and_boolean_metrics():
    candidates = [candidate("string", "10.0"), candidate("bool", True)]
    assert rank_candidates(
        candidates, RankingObjective.MAX_THROUGHPUT_UNDER_SLO
    ) == []


def test_rank_candidates_filters_negative_metrics():
    assert rank_candidates(
        [candidate("negative", -1.0)],
        RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
    ) == []


def test_rank_candidates_filters_non_feasible_candidates():
    candidates = [
        candidate("feasible", 3.0),
        candidate("infeasible", 100.0, FeasibilityVerdict.INFEASIBLE),
        candidate("inconclusive", 200.0, FeasibilityVerdict.INCONCLUSIVE),
    ]
    ranked = rank_candidates(
        candidates, RankingObjective.MAX_THROUGHPUT_UNDER_SLO
    )
    assert [item.candidate_id for item in ranked] == ["feasible"]


def test_rank_candidates_uses_candidate_id_for_ties():
    candidates = [candidate("candidate-b", 10.0), candidate("candidate-a", 10.0)]
    ranked = rank_candidates(
        candidates, RankingObjective.MAX_THROUGHPUT_UNDER_SLO
    )
    assert [item.candidate_id for item in ranked] == ["candidate-a", "candidate-b"]
