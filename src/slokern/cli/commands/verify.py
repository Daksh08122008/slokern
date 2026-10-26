"""
Purpose: `slokern verify`: independently rerun and audit the winning candidate under a fresh run ID.
Owner: Rajdeep (Historical design: Daksh)
Authority: Aligned with AGENTS.md Section 1, 5, 7 and DEC-0014
"""

from pathlib import Path
import sys
from typing import Optional

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import VerificationState
from slokern.contracts.search import SearchResult
from slokern.contracts.spec import ExperimentSpec
from slokern.core.search.candidate_id import generate_candidate_id
from slokern.core.verification.protocol import run_independent_verification
from slokern.engine.serving.base import ConfigurationError
from slokern.engine.serving.factory import create_serving_adapter


def verify_command(
    spec_file: str,
    search_result_file: str,
    adapter: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> int:
    """
    Reruns the selected candidate from a completed search experiment under a fresh run ID,
    computes drift metrics against hard SLO constraints, and issues an independent verdict.
    """
    spec_path = Path(spec_file)
    result_path = Path(search_result_file)

    if not spec_path.exists():
        print(f"[ERROR] Specification file not found: {spec_file}", file=sys.stderr)
        return 1
    if not result_path.exists():
        print(f"[ERROR] Search result file not found: {search_result_file}", file=sys.stderr)
        return 1

    try:
        spec = ExperimentSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
        search_result = SearchResult.model_validate_json(result_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[ERROR] Failed to parse input files: {exc}", file=sys.stderr)
        return 1

    winner_id = search_result.selected_candidate_id
    if not winner_id:
        print(
            f"[ERROR] Search result contains no selected candidate. "
            f"Rationale: {search_result.selection_rationale}",
            file=sys.stderr,
        )
        return 1

    # Instantiate serving adapter
    try:
        serving_adapter = create_serving_adapter(backend=adapter)
    except ConfigurationError as exc:
        print(f"[ERROR] Serving adapter configuration failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    # Reconstruct candidate configuration
    requested_settings = {}
    effective_settings = {}
    runs_dir = result_path.parent / "runs"
    if runs_dir.exists():
        for run_dir in runs_dir.iterdir():
            cfg_file = run_dir / "applied_config.json"
            if cfg_file.exists():
                try:
                    saved_cfg = CandidateConfig.model_validate_json(cfg_file.read_text(encoding="utf-8"))
                    if saved_cfg.candidate_id == winner_id:
                        requested_settings = saved_cfg.requested_settings
                        effective_settings = saved_cfg.effective_settings
                        break
                except Exception:
                    pass

    candidate_config = CandidateConfig(
        candidate_id=winner_id,
        model_name=serving_adapter.model_name,
        runtime_name=serving_adapter.runtime_name,
        requested_settings=requested_settings,
        effective_settings=effective_settings,
        parameter_status={},
        environment_fingerprint={},
    )

    print(f"[SLOKern Independent Verification]")
    print(f"  Experiment ID:        {spec.experiment_id}")
    print(f"  Selected Winner ID:   {winner_id}")
    print(f"  Serving Adapter:      {serving_adapter.runtime_name} ({serving_adapter.model_name})")

    resolved_out_dir = Path(output_dir or "artifacts") / "experiments" / spec.experiment_id
    resolved_out_dir.mkdir(parents=True, exist_ok=True)

    try:
        record = run_independent_verification(
            original_run_id=f"run-search-{winner_id[:8]}",
            candidate_config=candidate_config,
            workload=spec.workload,
            slo=spec.slo,
            experiment_id=spec.experiment_id,
            adapter=serving_adapter,
            artifacts_root=output_dir or "artifacts",
            isolate_process=False,
        )

        record_path = resolved_out_dir / "verification_record.json"
        record_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

        print("\n[Verification Complete]")
        print(f"  Verification ID:     {record.verification_id}")
        print(f"  Original Run ID:     {record.original_run_id}")
        print(f"  Fresh Verify Run ID: {record.verification_run_id}")
        print(f"  Final Verdict:       {record.verification_verdict.value}")
        print(f"  Decision Notes:      {record.final_decision_notes}")
        if record.drift_analysis:
            print(f"  SLO Drift Detected:  {record.drift_analysis.slo_drift_detected}")

        if record.verification_verdict == VerificationState.VERIFIED:
            print("\n[OK] Configuration successfully verified.")
            return 0
        else:
            print("\n[FAIL] Configuration verification failed or inconclusive.", file=sys.stderr)
            return 1

    except Exception as exc:
        print(f"[ERROR] Verification rerun failed: {exc}", file=sys.stderr)
        return 1
