
from slokern.contracts.enums import FeasibilityVerdict, RankingObjective
from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.core.search.candidate_id import generate_candidate_id
from slokern.core.search.rank import EvaluatedCandidate, rank_candidates


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

def test_generate_candidate_id_numeric_normalization():
    # Int and float representation of integers must yield identical candidate IDs
    id_int = generate_candidate_id("model-a", "vllm", {"tp": 1})
    id_float = generate_candidate_id("model-a", "vllm", {"tp": 1.0})
    assert id_int == id_float

    # Nested structures with numeric floats
    id_nested_float = generate_candidate_id("model-a", "vllm", {"params": {"tp": 2.0, "layers": [4.0, 8]}})
    id_nested_int = generate_candidate_id("model-a", "vllm", {"params": {"tp": 2, "layers": [4, 8.0]}})
    assert id_nested_float == id_nested_int

    # Booleans are preserved and distinct from integer 1/0
    id_bool = generate_candidate_id("model-a", "vllm", {"flag": True})
    id_one = generate_candidate_id("model-a", "vllm", {"flag": 1})
    assert id_bool != id_one

    # Fractional floats are preserved
    id_frac1 = generate_candidate_id("model-a", "vllm", {"ratio": 0.75})
    id_frac2 = generate_candidate_id("model-a", "vllm", {"ratio": 0.75})
    assert id_frac1 == id_frac2


def test_candidate_id_float_int_equivalence():
    """Explicit regression test for BLK-11 / Probe P-12: float vs int representation drift."""
    # Probe P-12: {"tensor_parallel_size": 1} vs 1.0 must produce identical candidate IDs
    id_int = generate_candidate_id("meta-llama/Llama-3-8B-Instruct", "vllm", {"tensor_parallel_size": 1})
    id_float = generate_candidate_id("meta-llama/Llama-3-8B-Instruct", "vllm", {"tensor_parallel_size": 1.0})
    assert id_int == id_float

    # Numeric keys in dictionaries must be normalized identically
    id_key_float = generate_candidate_id("model-a", "vllm", {1.0: "val"})
    id_key_int = generate_candidate_id("model-a", "vllm", {1: "val"})
    assert id_key_float == id_key_int

    # Sets must be deterministically sorted and serialized
    id_set1 = generate_candidate_id("model-a", "vllm", {"gpus": {0, 1}})
    id_set2 = generate_candidate_id("model-a", "vllm", {"gpus": {1, 0}})
    assert id_set1 == id_set2

    # Negative zero must be normalized to zero
    id_neg_zero = generate_candidate_id("model-a", "vllm", {"temp": -0.0})
    id_pos_zero = generate_candidate_id("model-a", "vllm", {"temp": 0})
    assert id_neg_zero == id_pos_zero

    # Scientific notation representation of whole numbers
    id_sci = generate_candidate_id("model-a", "vllm", {"max_tokens": 1e2})
    id_exact = generate_candidate_id("model-a", "vllm", {"max_tokens": 100})
    assert id_sci == id_exact


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
