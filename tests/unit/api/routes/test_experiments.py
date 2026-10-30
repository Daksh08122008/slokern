"""Unit tests for artifact-backed experiment summaries."""

import json
from pathlib import Path

from slokern.api.routes.experiments import (
    _find_campaign_spec,
    get_experiment_candidates,
    get_experiment_verification,
    list_experiments,
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_selected_infeasible_candidate_is_not_returned_as_winner(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    campaign = artifacts / "audit-offline-validation" / "experiments" / "exp-test"
    run_id = "run-selected"
    run_dir = campaign / "runs" / run_id
    _write_json(
        campaign / "search_result.json",
        {
            "tested_candidates": ["candidate-a"],
            "candidate_summaries": {"candidate-a": {"verdict": "INFEASIBLE", "ranking_metric": None}},
            "selected_candidate_id": "candidate-a",
        },
    )
    _write_json(
        run_dir / "run_record.json",
        {
            "run_id": run_id,
            "experiment_id": "exp-test",
            "candidate_id": "candidate-a",
            "is_verification_run": False,
            "execution_status": "COMPLETED",
            "started_at": "2026-10-30T00:00:00Z",
        },
    )
    _write_json(
        run_dir / "metrics.json",
        {
            "ttft_ms": {"p95": 12.5},
            "itl_ms": {"p95": 8.1},
            "e2e_latency_ms": {"p95": 518.0},
            "token_throughput_tps": 160.0,
            "error_rate": 0.0,
        },
    )
    _write_json(
        run_dir / "feasibility.json",
        {
            "overall_verdict": "INFEASIBLE",
            "validity_status": "VALID",
            "audit_notes": "Constraint failed: e2e_latency_ms p95 <= 500.0",
            "constraint_evaluations": [
                {"metric_name": "e2e_latency_ms", "statistic": "p95", "observed_value": 518.0,
                 "required_threshold": 500.0, "passed": False, "reason_code": "E2E_LATENCY_EXCEEDED"}
            ],
        },
    )
    _write_json(run_dir / "applied_config.json", {"effective_settings": {"max_num_seqs": 16}})
    (run_dir / "raw_measurements.jsonl").write_text("{}\n", encoding="utf-8")

    candidates = get_experiment_candidates("exp-test", artifacts_root=str(artifacts))

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["feasibilityVerdict"] == "INFEASIBLE"
    assert candidate["feasible"] is False
    assert candidate["tag"] == "INFEASIBLE"
    assert candidate["reason"].startswith("Constraint failed")
    assert candidate["e2eP95"] == 518.0
    assert candidate["p95"] == 12.5
    assert candidate["p50"] is None
    assert candidate["reasonCodes"] == ["E2E_LATENCY_EXCEEDED"]
    summary = next(item for item in list_experiments(artifacts_root=str(artifacts)) if item["id"] == "exp-test")
    assert summary["feasibility"] == "Infeasible"
    assert summary["run"] == run_id
    verification = get_experiment_verification("exp-test", artifacts_root=str(artifacts))
    assert verification["original_run_id"] == run_id
    assert verification["verification_run_id"] is None


def test_campaign_spec_is_loaded_by_experiment_id(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "campaign.json",
        {
            "experiment_id": "exp-test",
            "workload": {"arrival_mode": "constant", "target_offered_rate": 10.0},
        },
    )

    spec = _find_campaign_spec("exp-test", fixtures_root=str(tmp_path))

    assert spec is not None
    assert spec["workload"]["arrival_mode"] == "constant"
    assert spec["workload"]["target_offered_rate"] == 10.0


def test_experiment_summary_uses_fixture_arrival_and_baseline_plus_grid_count(tmp_path: Path) -> None:
    campaign = tmp_path / "audit-offline-validation" / "experiments" / "exp-audit-offline-campaign"
    _write_json(
        campaign / "search_result.json",
        {
            "tested_candidates": ["baseline", "grid-1", "grid-2", "grid-3", "grid-4"],
            "candidate_summaries": {
                "baseline": {"verdict": "FEASIBLE"},
            },
            "selected_candidate_id": "baseline",
            "stopping_reason": "space_exhausted",
            "ranking_objective": "max_throughput_under_slo",
        },
    )

    summary = next(
        item for item in list_experiments(artifacts_root=str(tmp_path))
        if item["id"] == "exp-audit-offline-campaign"
    )

    assert summary["arrivalMode"] == "constant"
    assert summary["targetOfferedRateRps"] == 10.0
    assert summary["verificationDurationMultiplier"] == 1.0
    assert summary["candidateEvaluationsCount"] == 5
    assert summary["candidateBudget"] == 5
    assert summary["searchSpaceCandidateCount"] == 4
    assert summary["stopping_reason"] == "space_exhausted"
    assert summary["rankingObjective"] == "max_throughput_under_slo"
    assert [item["metric_name"] for item in summary["sloConstraints"]] == [
        "ttft_ms", "itl_ms", "error_rate"
    ]
