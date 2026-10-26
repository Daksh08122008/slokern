"""
Purpose: Unit tests for optimize CLI command.
Owner: Rajdeep
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from slokern.cli.commands.optimize import optimize_command
from slokern.contracts.enums import ArrivalMode, FeasibilityVerdict, RankingObjective
from slokern.contracts.search import CandidateSummary, SearchResult
from slokern.core.search.grid import GridSearchOutcome
from slokern.contracts.spec import (
    ExperimentBudget,
    ExperimentSpec,
    ExperimentVerificationPolicy,
    SLOSpec,
    WorkloadSpec,
)


def make_valid_spec():
    return ExperimentSpec(
        experiment_id="exp-opt-test",
        workload=WorkloadSpec(
            schema_version="1.0.0",
            workload_name="opt-workload",
            fixture_id="fix-opt-01",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=5.0,
            concurrency_limit=2,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=16,
            max_output_tokens=16,
        ),
        slo=SLOSpec(slo_id="slo-opt", constraints=[], min_sample_count=1),
        search_space={"max_num_batched_tokens": [256, 512]},
        budget=ExperimentBudget(max_candidates=4, max_wallclock_seconds=60),
        verification_policy=ExperimentVerificationPolicy(),
    )


def test_optimize_missing_spec_file(capsys):
    ret = optimize_command("nonexistent_spec.json")
    assert ret == 1
    assert "Specification file not found" in capsys.readouterr().err


def test_optimize_invalid_objective(tmp_path, capsys):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(make_valid_spec().model_dump_json())

    ret = optimize_command(str(spec_path), adapter="fake", objective="unsupported_objective")
    assert ret == 1
    assert "Invalid ranking objective" in capsys.readouterr().err


def test_optimize_capability_gating_halts(tmp_path, capsys):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(make_valid_spec().model_dump_json())

    # local adapter does not support max_num_batched_tokens dynamically
    ret = optimize_command(str(spec_path), adapter="local")
    assert ret == 1
    err = capsys.readouterr().err
    assert "Optimization campaign halted per BLK-17" in err


def test_optimize_fake_adapter_success(tmp_path, capsys):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(make_valid_spec().model_dump_json())

    mock_search_result = SearchResult(
        experiment_id="exp-opt-test",
        baseline_candidate_id="cand-base",
        selected_candidate_id="cand-winner",
        selection_rationale="Lowest cost feasible candidate",
        stopping_reason="budget_exhausted",
        tested_candidates=["cand-base", "cand-winner"],
        candidate_summaries={
            "cand-winner": CandidateSummary(
                verdict=FeasibilityVerdict.FEASIBLE,
                ranking_metric=0.05,
            )
        },
        ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
    )
    mock_outcome = GridSearchOutcome(
        search_result=mock_search_result,
        run_results=[],
    )

    with patch("slokern.cli.commands.optimize.GridSearchController.run", return_value=mock_outcome):
        ret = optimize_command(
            str(spec_path),
            adapter="fake",
            objective="max_throughput_under_slo",
            output_dir=str(tmp_path),
        )
        assert ret == 0
        out = capsys.readouterr().out
        assert "Optimization campaign completed successfully" in out
        assert "Selected Winner ID:   cand-winner" in out
