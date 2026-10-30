"""
Purpose: Unit tests for report CLI command.
Owner: Rajdeep
"""

import json

from slokern.cli.commands.report import report_command
from slokern.contracts.enums import (
    ArrivalMode,
    ExecutionStatus,
    FeasibilityVerdict,
    RankingObjective,
    VerificationState,
)
from slokern.contracts.search import CandidateSummary, SearchResult
from slokern.contracts.run import RunRecord
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
    run_dir = exp_dir / "runs" / "run-search-cand-win"
    run_dir.mkdir(parents=True)
    run_record = RunRecord(
        run_id="run-search-cand-win",
        experiment_id="exp-01",
        candidate_id="cand-winner",
        is_verification_run=False,
        execution_status=ExecutionStatus.COMPLETED,
        raw_artifact_uri="runs/run-search-cand-win/raw_measurements.jsonl",
    )
    (run_dir / "run_record.json").write_text(run_record.model_dump_json())
    (run_dir / "applied_config.json").write_text(json.dumps({
        "candidate_id": "cand-winner",
        "model_name": "demo-model",
        "runtime_name": "vllm-fake",
        "requested_settings": {},
        "effective_settings": {},
        "parameter_status": {},
        "environment_fingerprint": {"runtime_name": "vllm-fake", "is_simulated": True, "mode": "DEMO DATA"},
    }))
    (run_dir / "raw_measurements.jsonl").write_text('{"request_id":"demo-request"}\n')

    out_dir = tmp_path / "published"
    ret = report_command(str(exp_dir), output_dir=str(out_dir))
    assert ret == 0

    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.md").exists()
    report_data = json.loads((out_dir / "report.json").read_text())
    assert report_data["environment_fingerprint"]["evidence_classification"] == "DEMO DATA"
    assert report_data["selected_candidate"]["runtime_name"] == "vllm-fake"
    assert "runs/run-search-cand-win/raw_measurements.jsonl" in report_data["artifact_paths"].values()
    assert "**Evidence Classification:** **DEMO DATA**" in (out_dir / "report.md").read_text()
    out = capsys.readouterr().out
    assert "Report successfully published" in out
