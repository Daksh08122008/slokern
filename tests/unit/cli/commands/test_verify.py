"""
Purpose: Unit tests for verify CLI command.
Owner: Rajdeep (Historical design: Daksh)
"""

from unittest.mock import MagicMock, patch

from slokern.cli.commands.verify import verify_command
from slokern.contracts.enums import ArrivalMode, FeasibilityVerdict, RankingObjective, VerificationState
from slokern.contracts.search import CandidateSummary, SearchResult
from slokern.contracts.spec import (
    ExperimentBudget,
    ExperimentSpec,
    ExperimentVerificationPolicy,
    SLOSpec,
    WorkloadSpec,
)
from slokern.contracts.verification import VerificationRecord


def make_spec_and_result(winner_id="cand-winner-01"):
    spec = ExperimentSpec(
        experiment_id="exp-verif-test",
        workload=WorkloadSpec(
            schema_version="1.0.0",
            workload_name="verif-workload",
            fixture_id="fix-verif-01",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=5.0,
            concurrency_limit=2,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=16,
            max_output_tokens=16,
        ),
        slo=SLOSpec(slo_id="slo-verif", constraints=[], min_sample_count=1),
        search_space={},
        budget=ExperimentBudget(max_candidates=4, max_wallclock_seconds=60),
        verification_policy=ExperimentVerificationPolicy(),
    )
    result = SearchResult(
        experiment_id="exp-verif-test",
        baseline_candidate_id="cand-base",
        selected_candidate_id=winner_id,
        selection_rationale="Lowest cost feasible candidate",
        stopping_reason="budget_exhausted",
        tested_candidates=["cand-base", winner_id] if winner_id else ["cand-base"],
        candidate_summaries={
            "cand-base": CandidateSummary(verdict=FeasibilityVerdict.FEASIBLE, ranking_metric=10.0),
        },
        ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
    )
    return spec, result


def test_verify_missing_files(tmp_path, capsys):
    ret = verify_command("nonexistent_spec.json", "nonexistent_result.json")
    assert ret == 1
    assert "Specification file not found" in capsys.readouterr().err


def test_verify_no_winner(tmp_path, capsys):
    spec, result = make_spec_and_result(winner_id=None)
    spec_path = tmp_path / "spec.json"
    result_path = tmp_path / "result.json"
    spec_path.write_text(spec.model_dump_json())
    result_path.write_text(result.model_dump_json())

    ret = verify_command(str(spec_path), str(result_path))
    assert ret == 1
    assert "Search result contains no selected candidate" in capsys.readouterr().err


def test_verify_success(tmp_path, capsys):
    spec, result = make_spec_and_result()
    spec_path = tmp_path / "spec.json"
    result_path = tmp_path / "result.json"
    spec_path.write_text(spec.model_dump_json())
    result_path.write_text(result.model_dump_json())

    mock_record = VerificationRecord(
        verification_id="verif-1234",
        experiment_id="exp-verif-test",
        candidate_id="cand-winner-01",
        original_run_id="run-search-cand-win",
        verification_run_id="run-verify-5678",
        verification_verdict=VerificationState.VERIFIED,
        final_decision_notes="Independent verification passed all SLO constraints.",
    )

    with patch("slokern.cli.commands.verify.run_independent_verification", return_value=mock_record):
        ret = verify_command(str(spec_path), str(result_path), adapter="fake", output_dir=str(tmp_path))
        assert ret == 0
        out = capsys.readouterr().out
        assert "Configuration successfully verified" in out
        assert "Final Verdict:       VERIFIED" in out


def test_verify_failed_verdict(tmp_path, capsys):
    spec, result = make_spec_and_result()
    spec_path = tmp_path / "spec.json"
    result_path = tmp_path / "result.json"
    spec_path.write_text(spec.model_dump_json())
    result_path.write_text(result.model_dump_json())

    mock_record = VerificationRecord(
        verification_id="verif-1234",
        experiment_id="exp-verif-test",
        candidate_id="cand-winner-01",
        original_run_id="run-search-cand-win",
        verification_run_id="run-verify-5678",
        verification_verdict=VerificationState.VERIFICATION_FAILED,
        final_decision_notes="Candidate violated hard SLO constraints during rerun.",
    )

    with patch("slokern.cli.commands.verify.run_independent_verification", return_value=mock_record):
        ret = verify_command(str(spec_path), str(result_path), adapter="fake", output_dir=str(tmp_path))
        assert ret == 1
        err = capsys.readouterr().err
        assert "Configuration verification failed or inconclusive" in err
