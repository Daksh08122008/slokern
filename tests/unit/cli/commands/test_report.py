"""
Purpose: Unit tests for report CLI command.
Owner: Rajdeep
"""

from slokern.cli.commands.report import report_command
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


def test_report_missing_directory(capsys):
    ret = report_command("nonexistent_dir")
    assert ret == 1
    assert "Experiment directory not found" in capsys.readouterr().err


def test_report_missing_search_result(tmp_path, capsys):
    ret = report_command(str(tmp_path))
    assert ret == 1
    assert "Required search_result.json not found" in capsys.readouterr().err


def test_report_success_generation(tmp_path, capsys):
    exp_dir = tmp_path / "exp-01"
    exp_dir.mkdir()

    spec = ExperimentSpec(
        experiment_id="exp-01",
        workload=WorkloadSpec(
            schema_version="1.0.0",
            workload_name="rep-workload",
            fixture_id="fix-rep-01",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=5.0,
            concurrency_limit=2,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=16,
            max_output_tokens=16,
        ),
        slo=SLOSpec(slo_id="slo-rep", constraints=[], min_sample_count=1),
        search_space={},
        budget=ExperimentBudget(max_candidates=4, max_wallclock_seconds=60),
        verification_policy=ExperimentVerificationPolicy(),
    )
    result = SearchResult(
        experiment_id="exp-01",
        baseline_candidate_id="cand-base",
        selected_candidate_id="cand-winner",
        selection_rationale="Lowest cost feasible candidate",
        stopping_reason="space_exhausted",
        tested_candidates=["cand-base", "cand-winner"],
        candidate_summaries={
            "cand-base": CandidateSummary(verdict=FeasibilityVerdict.FEASIBLE, ranking_metric=10.0),
            "cand-winner": CandidateSummary(verdict=FeasibilityVerdict.FEASIBLE, ranking_metric=20.0),
        },
        ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
    )
    verif = VerificationRecord(
        verification_id="verif-01",
        experiment_id="exp-01",
        candidate_id="cand-winner",
        original_run_id="run-search-cand-win",
        verification_run_id="run-verify-cand-win",
        verification_verdict=VerificationState.VERIFIED,
        final_decision_notes="Verification succeeded.",
    )

    (exp_dir / "experiment_spec.json").write_text(spec.model_dump_json())
    (exp_dir / "search_result.json").write_text(result.model_dump_json())
    (exp_dir / "verification_record.json").write_text(verif.model_dump_json())

    out_dir = tmp_path / "published"
    ret = report_command(str(exp_dir), output_dir=str(out_dir))
    assert ret == 0

    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.md").exists()
    out = capsys.readouterr().out
    assert "Report successfully published" in out
