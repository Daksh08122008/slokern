"""
Purpose: Independent verification protocol runner executing fresh rerun and drift audit.
Owner: Rajdeep (Historical design: Daksh)
Authority: Aligned with AGENTS.md Section 5, 7, and DEC-0014
"""

import json
import uuid
from pathlib import Path
from typing import Any, List, Optional, Sequence, Union

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
    ReasonCode,
    VerificationState,
)
from slokern.contracts.metrics import MetricSet
from slokern.contracts.run import RunRecord
from slokern.contracts.search import SearchResult
from slokern.contracts.spec import SLOSpec, WorkloadSpec
from slokern.contracts.verification import VerificationRecord
from slokern.core.evaluator.evaluate import evaluate_slo
from slokern.core.verification.compare import DriftPolicy, compare_metrics
from slokern.engine.serving.base import BaseServingAdapter


class VerificationCampaignError(ValueError):
    """Raised when a search campaign cannot be verified due to missing or invalid inputs."""


def run_independent_verification(
    original_run_id: str,
    candidate_config: CandidateConfig,
    workload: WorkloadSpec,
    slo: SLOSpec,
    experiment_id: str = "exp-default",
    original_metrics: Optional[MetricSet] = None,
    drift_policy: Optional[DriftPolicy] = None,
    adapter: Optional[BaseServingAdapter] = None,
    single_run_executor: Optional[Any] = None,
    artifacts_root: Optional[Union[str, Path]] = None,
    cancellation_token: Optional[Any] = None,
    seed: Optional[int] = 999,
    stream: bool = True,
    prompts: Optional[Union[List[str], str]] = None,
    isolate_process: bool = False,
    persist_record: bool = True,
    existing_run_ids: Optional[Sequence[str]] = None,
) -> VerificationRecord:
    """
    Reruns winning candidate configuration under a fresh, independent run ID,
    recalculates metrics and feasibility from verification evidence,
    performs drift analysis, and issues final independent verification verdict.
    """
    verification_id = f"verif-{uuid.uuid4().hex[:8]}"
    verification_run_id = f"run-verify-{uuid.uuid4().hex[:8]}"

    # Invariant: verification run ID must be distinct from original search run ID and all prior runs
    assert verification_run_id != original_run_id, "Verification run ID must be distinct from original search run ID"
    if existing_run_ids:
        assert verification_run_id not in existing_run_ids, "Verification run ID must not collide with existing campaign run IDs"

    resolved_root = Path(artifacts_root or "artifacts")

    if single_run_executor is not None:
        executor = single_run_executor
    else:
        from slokern.engine.runner.run_executor import SingleRunExecutor

        executor = SingleRunExecutor(
            artifacts_root=resolved_root,
            isolate_process=isolate_process,
        )

    run_result = executor.execute(
        candidate_config=candidate_config,
        workload=workload,
        slo=slo,
        experiment_id=experiment_id,
        run_id=verification_run_id,
        is_verification_run=True,
        adapter=adapter,
        cancellation_token=cancellation_token,
        seed=seed,
        stream=stream,
        prompts=prompts,
        raise_on_failure=False,
    )

    drift = None
    reason_codes: List[ReasonCode] = []
    feasibility: Optional[FeasibilityResult] = None

    if run_result.run_record.execution_status != ExecutionStatus.COMPLETED:
        verdict = VerificationState.VERIFICATION_INCONCLUSIVE
        reason_codes = [ReasonCode.EXECUTION_CRASHED]
        notes = f"Verification execution ended with status {run_result.run_record.execution_status.value}."
    elif run_result.metric_set is None or run_result.feasibility_result is None:
        verdict = VerificationState.VERIFICATION_INCONCLUSIVE
        reason_codes = [ReasonCode.MISSING_REQUIRED_METRIC]
        notes = "Verification run completed without required metric or feasibility evidence."
    elif run_result.feasibility_result.validity_status != EvidenceValidity.VALID:
        verdict = VerificationState.VERIFICATION_INCONCLUSIVE
        feasibility = run_result.feasibility_result
        if run_result.feasibility_result.validity_status == EvidenceValidity.CONTAMINATED:
            reason_codes = [ReasonCode.GENERATOR_SATURATED]
        else:
            reason_codes = [ReasonCode.INSUFFICIENT_SAMPLES]
        notes = f"Verification evidence validity is {run_result.feasibility_result.validity_status.value}."
    else:
        verif_metrics = run_result.metric_set
        feasibility = evaluate_slo(verif_metrics, slo)

        if original_metrics is not None:
            drift = compare_metrics(original_metrics, verif_metrics, slo, drift_policy=drift_policy)

        if feasibility.overall_verdict == FeasibilityVerdict.FEASIBLE:
            if drift is not None and (drift.slo_drift_detected or drift.drift_exceeded):
                verdict = VerificationState.VERIFICATION_FAILED
                reason_codes = [ReasonCode.VERIFICATION_DRIFT_EXCEEDED]
                notes = "Verification run exceeded accepted drift tolerance or crossed declared SLO threshold."
            else:
                verdict = VerificationState.VERIFIED
                reason_codes = [ReasonCode.HARD_CONSTRAINTS_PASSED]
                notes = "Independent verification passed: configuration confirmed against all hard constraints."
        elif feasibility.overall_verdict == FeasibilityVerdict.INFEASIBLE:
            verdict = VerificationState.VERIFICATION_FAILED
            breach_codes = [
                c.reason_code for c in feasibility.constraint_evaluations
                if not c.passed and c.reason_code is not None
            ]
            reason_codes = breach_codes if breach_codes else [ReasonCode.HARD_CONSTRAINTS_PASSED]
            notes = "Independent verification failed: rerun violated declared hard constraints."
        else:
            verdict = VerificationState.VERIFICATION_INCONCLUSIVE
            reason_codes = [ReasonCode.INSUFFICIENT_SAMPLES]
            notes = "Independent verification inconclusive: insufficient samples or invalid observations."

    record = VerificationRecord(
        verification_id=verification_id,
        experiment_id=experiment_id,
        candidate_id=candidate_config.candidate_id,
        original_run_id=original_run_id,
        verification_run_id=verification_run_id,
        verification_verdict=verdict,
        drift_analysis=drift,
        metric_set=run_result.metric_set,
        feasibility_result=feasibility if feasibility is not None else run_result.feasibility_result,
        reason_codes=reason_codes,
        final_decision_notes=notes,
    )

    if persist_record:
        exp_dir = resolved_root / "experiments" / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        record_path = exp_dir / "verification_record.json"
        record_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    return record


def verify_search_campaign(
    experiment_id: str,
    artifacts_root: Union[str, Path] = "artifacts",
    search_result: Optional[SearchResult] = None,
    workload: Optional[WorkloadSpec] = None,
    slo: Optional[SLOSpec] = None,
    drift_policy: Optional[DriftPolicy] = None,
    adapter: Optional[BaseServingAdapter] = None,
    single_run_executor: Optional[Any] = None,
    cancellation_token: Optional[Any] = None,
    seed: Optional[int] = 999,
    isolate_process: bool = False,
) -> VerificationRecord:
    """
    End-to-end verification of an audited search campaign:
    1. Loads or accepts the SearchResult for the experiment.
    2. Identifies and validates the top-ranked FEASIBLE winner.
    3. Locates the winning candidate's original search run artifacts (applied_config, metrics).
    4. Executes a fresh independent rerun under a distinct verification_run_id.
    5. Re-evaluates hard SLOs and computes metric drift.
    6. Emits and persists the canonical VerificationRecord.
    """
    resolved_root = Path(artifacts_root)
    exp_dir = resolved_root / "experiments" / experiment_id

    if not exp_dir.is_dir():
        raise VerificationCampaignError(f"Experiment directory {exp_dir} does not exist.")

    # 1. Load or validate SearchResult
    if search_result is None:
        sr_path = exp_dir / "search_result.json"
        if not sr_path.is_file():
            raise VerificationCampaignError(f"No search_result.json found in {exp_dir}.")
        search_result = SearchResult.model_validate_json(sr_path.read_text(encoding="utf-8"))

    winner_id = search_result.selected_candidate_id
    if not winner_id:
        raise VerificationCampaignError(
            f"Search campaign '{experiment_id}' has no selected winning candidate to verify."
        )

    summary = search_result.candidate_summaries.get(winner_id)
    if summary is None or summary.verdict != FeasibilityVerdict.FEASIBLE:
        raise VerificationCampaignError(
            f"Winning candidate '{winner_id}' has non-feasible verdict "
            f"'{summary.verdict.value if summary else 'MISSING'}'; verification aborted."
        )

    # 2. Locate the winning candidate's search run folder and load reference artifacts
    runs_dir = exp_dir / "runs"
    if not runs_dir.is_dir():
        raise VerificationCampaignError(f"Runs directory {runs_dir} does not exist.")

    winning_run_dir: Optional[Path] = None
    winning_run_record: Optional[RunRecord] = None
    existing_run_ids: List[str] = []

    for run_path in sorted(runs_dir.iterdir()):
        if not run_path.is_dir():
            continue
        rec_path = run_path / "run_record.json"
        if rec_path.is_file():
            try:
                rec = RunRecord.model_validate_json(rec_path.read_text(encoding="utf-8"))
                existing_run_ids.append(rec.run_id)
                # Match winning search run (not a previous verification run)
                if rec.candidate_id == winner_id and not rec.is_verification_run:
                    winning_run_dir = run_path
                    winning_run_record = rec
            except Exception:
                continue

    if winning_run_dir is None or winning_run_record is None:
        raise VerificationCampaignError(
            f"Could not locate original search run artifacts for winning candidate '{winner_id}' in {runs_dir}."
        )

    # Load applied candidate config
    config_path = winning_run_dir / "applied_config.json"
    if not config_path.is_file():
        raise VerificationCampaignError(f"Missing applied_config.json in {winning_run_dir}.")
    candidate_config = CandidateConfig.model_validate_json(config_path.read_text(encoding="utf-8"))

    # Load reference metrics
    metrics_path = winning_run_dir / "metrics.json"
    if not metrics_path.is_file():
        raise VerificationCampaignError(f"Missing metrics.json in {winning_run_dir}.")
    reference_metrics = MetricSet.model_validate_json(metrics_path.read_text(encoding="utf-8"))

    # 3. Resolve WorkloadSpec and SLOSpec
    resolved_workload = workload
    resolved_slo = slo

    if resolved_workload is None or resolved_slo is None:
        # Check report.json or spec.json for workload and slo
        report_path = exp_dir / "report.json"
        if report_path.is_file():
            try:
                report_data = json.loads(report_path.read_text(encoding="utf-8"))
                exp_spec = report_data.get("experiment_spec", {})
                if resolved_workload is None and "workload" in exp_spec:
                    resolved_workload = WorkloadSpec.model_validate(exp_spec["workload"])
                if resolved_slo is None and "slo" in exp_spec:
                    resolved_slo = SLOSpec.model_validate(exp_spec["slo"])
            except Exception:
                pass

    if resolved_workload is None or resolved_slo is None:
        raise VerificationCampaignError(
            f"WorkloadSpec and SLOSpec must be provided or discoverable in report.json for campaign {experiment_id}."
        )

    # 4. Execute verification rerun
    return run_independent_verification(
        original_run_id=winning_run_record.run_id,
        candidate_config=candidate_config,
        workload=resolved_workload,
        slo=resolved_slo,
        experiment_id=experiment_id,
        original_metrics=reference_metrics,
        drift_policy=drift_policy,
        adapter=adapter,
        single_run_executor=single_run_executor,
        artifacts_root=resolved_root,
        cancellation_token=cancellation_token,
        seed=seed,
        isolate_process=isolate_process,
        persist_record=True,
        existing_run_ids=existing_run_ids,
    )
