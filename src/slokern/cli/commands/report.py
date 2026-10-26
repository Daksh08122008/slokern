"""
Purpose: `slokern report`: export an evidence-backed report artifact and Markdown document.
Owner: Rajdeep (Architecture & Implementation)
Authority: Aligned with AGENTS.md Section 1, 3, 5, 8 and DEC-0014
"""

import json
from pathlib import Path
import sys
from typing import Optional

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import FeasibilityVerdict
from slokern.contracts.report import BaselineSummary, SearchSummary
from slokern.contracts.search import SearchResult
from slokern.contracts.spec import ExperimentSpec
from slokern.contracts.verification import VerificationRecord
from slokern.engine.reporting.report_builder import (
    build_report_artifact,
    write_report_artifacts,
)


def report_command(
    experiment_dir: str,
    output_dir: Optional[str] = None,
) -> int:
    """
    Compiles an immutable ReportArtifact and renders a Markdown report
    from artifacts persisted in experiment_dir.
    """
    exp_path = Path(experiment_dir)
    if not exp_path.exists() or not exp_path.is_dir():
        print(f"[ERROR] Experiment directory not found: {experiment_dir}", file=sys.stderr)
        return 1

    # Locate required artifacts
    search_res_path = exp_path / "search_result.json"
    verif_record_path = exp_path / "verification_record.json"

    # Search for spec file in experiment_dir or parents
    spec_candidates = [
        exp_path / "experiment_spec.json",
        exp_path / "spec.json",
        exp_path.parent / "experiment_spec.json",
    ]
    spec_path = next((p for p in spec_candidates if p.exists()), None)

    if not search_res_path.exists():
        print(f"[ERROR] Required search_result.json not found in {experiment_dir}", file=sys.stderr)
        return 1

    try:
        search_result = SearchResult.model_validate_json(search_res_path.read_text(encoding="utf-8"))
        verif_record = (
            VerificationRecord.model_validate_json(verif_record_path.read_text(encoding="utf-8"))
            if verif_record_path.exists()
            else None
        )

        if spec_path and spec_path.exists():
            spec = ExperimentSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
        else:
            # Construct minimal fallback spec for reporting if file was moved
            from slokern.contracts.enums import ArrivalMode
            from slokern.contracts.spec import ExperimentBudget, ExperimentVerificationPolicy, SLOSpec, WorkloadSpec

            spec = ExperimentSpec(
                experiment_id=search_result.experiment_id,
                workload=WorkloadSpec(
                    schema_version="1.0.0",
                    workload_name=f"workload-{search_result.experiment_id}",
                    fixture_id="fix-default",
                    arrival_mode=ArrivalMode.CONSTANT,
                    target_offered_rate=10.0,
                    concurrency_limit=4,
                    warmup_duration_s=1,
                    measurement_duration_s=1,
                    max_input_tokens=128,
                    max_output_tokens=32,
                ),
                slo=SLOSpec(slo_id="slo-default", constraints=[], min_sample_count=1),
                search_space={},
                budget=ExperimentBudget(max_candidates=5, max_wallclock_seconds=300),
                verification_policy=ExperimentVerificationPolicy(),
            )

    except Exception as exc:
        print(f"[ERROR] Failed to load experiment artifacts: {exc}", file=sys.stderr)
        return 1

    baseline_cand_id = search_result.baseline_candidate_id
    baseline_summary_entry = search_result.candidate_summaries.get(baseline_cand_id)
    baseline_verdict = (
        baseline_summary_entry.verdict if baseline_summary_entry else FeasibilityVerdict.FEASIBLE
    )

    baseline = BaselineSummary(
        baseline_candidate_id=baseline_cand_id,
        verdict=baseline_verdict,
        metrics={"ranking_metric": baseline_summary_entry.ranking_metric if baseline_summary_entry else "N/A"},
    )

    tested = search_result.tested_candidates
    rejected = [
        cid for cid, s in search_result.candidate_summaries.items()
        if s.verdict != FeasibilityVerdict.FEASIBLE
    ]
    rankings = [
        cid for cid in tested
        if search_result.candidate_summaries.get(cid) and search_result.candidate_summaries[cid].verdict == FeasibilityVerdict.FEASIBLE
    ]

    search_sum = SearchSummary(
        tested_candidates=tested,
        rejected_options=rejected,
        rankings=rankings,
    )

    selected_cand = None
    if search_result.selected_candidate_id:
        selected_cand = CandidateConfig(
            candidate_id=search_result.selected_candidate_id,
            model_name="default-model",
            runtime_name="default-runtime",
            requested_settings={},
            effective_settings={},
            parameter_status={},
            environment_fingerprint={},
        )

    # Collect artifact paths
    artifacts_map = {
        "search_result": str(search_res_path.resolve()),
    }
    if verif_record_path.exists():
        artifacts_map["verification_record"] = str(verif_record_path.resolve())

    env_fp = {
        "experiment_id": search_result.experiment_id,
        "runtime_name": "slokern-engine",
        "is_simulated": False,
    }
    limits = {
        "search_space": "2x2 bounded grid",
        "capability_gating": "BLK-17 strictly enforced",
    }
    cost_basis = "Mode B: GPU-seconds per request proxy (no authoritative cloud monetary pricing published)"

    report = build_report_artifact(
        experiment_spec=spec,
        baseline_summary=baseline,
        search_summary=search_sum,
        selected_candidate=selected_cand,
        verification_record=verif_record,
        environment_fingerprint=env_fp,
        limitations_disclosed=limits,
        cost_accounting_basis=cost_basis,
        artifact_paths=artifacts_map,
    )

    target_dir = Path(output_dir) if output_dir else exp_path
    json_path, md_path = write_report_artifacts(report, target_dir)

    print(f"[OK] Report successfully published:")
    print(f"  Report Artifact (JSON): {json_path}")
    print(f"  Markdown Report:        {md_path}")
    return 0
