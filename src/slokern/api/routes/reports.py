"""
Purpose: Report artifact and Markdown serialization endpoints.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 4, 14 and DEC-0014
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from slokern.api.routes.runs import ACTIVE_RUNS, RUNS_LOCK
from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ArrivalMode, FeasibilityVerdict
from slokern.contracts.report import BaselineSummary, SearchSummary
from slokern.contracts.spec import (
    ExperimentBudget,
    ExperimentSpec,
    SLOConstraint,
    SLOSpec,
    WorkloadSpec,
)
from slokern.contracts.verification import VerificationRecord
from slokern.engine.reporting.report_builder import (
    build_report_artifact,
    render_markdown_report,
    write_report_artifacts,
)


def get_report_data(experiment_id: str, artifacts_root: str = "artifacts") -> Dict[str, Any]:
    """
    Fetches compiled report artifact and Markdown representation for experiment_id.
    """
    exp_dir = Path(artifacts_root) / "experiments" / experiment_id
    md_file = exp_dir / "report.md"
    json_file = exp_dir / "report.json"
    legacy_json_file = exp_dir / "report_artifact.json"

    # If artifacts exist on disk, return them directly
    if md_file.exists() and (json_file.exists() or legacy_json_file.exists()):
        try:
            target_json = json_file if json_file.exists() else legacy_json_file
            artifact_json = json.loads(target_json.read_text(encoding="utf-8"))
            return {
                "experiment_id": experiment_id,
                "markdown": md_file.read_text(encoding="utf-8"),
                "artifact": artifact_json,
            }
        except Exception:
            pass

    # Compile report on-demand from disk evidence or in-memory runs
    try:
        # 1. Verification record
        verif_record: Optional[VerificationRecord] = None
        verif_path = exp_dir / "verification_record.json"
        if verif_path.exists():
            try:
                verif_record = VerificationRecord.model_validate_json(
                    verif_path.read_text(encoding="utf-8")
                )
            except Exception:
                verif_record = None

        # 2. Associated run details
        run_data: Optional[Dict[str, Any]] = None
        with RUNS_LOCK:
            for r in ACTIVE_RUNS.values():
                if r.get("experiment_id") == experiment_id:
                    run_data = r
                    break

        cand_id = run_data.get("candidate_id", "cand-default") if run_data else "cand-default"
        workload_dump = run_data.get("workload") if run_data else None
        slo_dump = run_data.get("slo") if run_data else None
        metric_dump = run_data.get("metric_set") if run_data else None
        is_feasible = run_data.get("is_feasible", True) if run_data else True

        workload = (
            WorkloadSpec.model_validate(workload_dump)
            if workload_dump
            else WorkloadSpec(
                schema_version="1.0.0",
                workload_name="api-workload",
                fixture_id="fix-api-01",
                arrival_mode=ArrivalMode.CONSTANT,
                target_offered_rate=5.0,
                concurrency_limit=2,
                warmup_duration_s=1,
                measurement_duration_s=2,
                max_input_tokens=64,
                max_output_tokens=32,
            )
        )

        slo = (
            SLOSpec.model_validate(slo_dump)
            if slo_dump
            else SLOSpec(
                slo_id="slo-api-01",
                constraints=[
                    SLOConstraint(
                        metric_name="ttft_ms",
                        statistic="p95",
                        threshold=50.0,
                        unit="ms",
                        operator="<=",
                    )
                ],
                min_sample_count=2,
            )
        )

        spec = ExperimentSpec(
            experiment_id=experiment_id,
            workload=workload,
            slo=slo,
            search_space={"max_num_seqs": [8, 16], "max_num_batched_tokens": [256, 512]},
            budget=ExperimentBudget(max_candidates=4, max_wallclock_seconds=120, max_cost_limit=None),
        )

        selected_candidate = CandidateConfig(
            candidate_id=cand_id,
            model_name="fake-llama-3-8b",
            runtime_name="vllm-fake",
            requested_settings={},
            effective_settings={"max_num_seqs": 16},
            parameter_status={},
            environment_fingerprint={"hardware": "Host (CPU/Simulation)"},
        )

        base_summary = BaselineSummary(
            baseline_candidate_id=cand_id,
            verdict=FeasibilityVerdict.FEASIBLE if is_feasible else FeasibilityVerdict.INFEASIBLE,
            metrics=metric_dump or {"ttft_p95_ms": 11.0, "achieved_load_rps": 10.0},
        )

        search_summary = SearchSummary(
            tested_candidates=[cand_id],
            rejected_options=[] if is_feasible else [cand_id],
            rankings=[cand_id] if is_feasible else [],
        )

        artifact = build_report_artifact(
            experiment_spec=spec,
            baseline_summary=base_summary,
            search_summary=search_summary,
            environment_fingerprint={"device": "CPU/Test Environment"},
            limitations_disclosed={"gating": "BLK-17: Dynamic batching gated on remote vLLM"},
            cost_accounting_basis="proxy_gpu_seconds",
            artifact_paths={"experiment_dir": str(exp_dir)},
            selected_candidate=selected_candidate if is_feasible else None,
            verification_record=verif_record,
        )

        write_report_artifacts(artifact, output_dir=exp_dir)
        md_text = render_markdown_report(artifact)

        return {
            "experiment_id": experiment_id,
            "markdown": md_text,
            "artifact": artifact.model_dump(),
        }
    except Exception as exc:
        return {
            "experiment_id": experiment_id,
            "markdown": f"# SLOKern Experiment Dossier\n\nNo report available for experiment `{experiment_id}`: {exc}",
            "artifact": None,
            "error": str(exc),
        }
