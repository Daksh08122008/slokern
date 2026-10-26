"""
Purpose: Independent verification protocol runner executing fresh rerun and drift audit.
Owner: Rajdeep (Historical design: Daksh)
Authority: Aligned with AGENTS.md Section 5, 7 and DEC-0014
"""

from pathlib import Path
from typing import Any, List, Optional, Union
import uuid

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
    VerificationState,
)
from slokern.contracts.metrics import MetricSet
from slokern.contracts.spec import SLOSpec, WorkloadSpec
from slokern.contracts.verification import VerificationRecord
from slokern.core.evaluator.evaluate import evaluate_slo
from slokern.core.verification.compare import compare_metrics
from slokern.engine.serving.base import BaseServingAdapter


def run_independent_verification(
    original_run_id: str,
    candidate_config: CandidateConfig,
    workload: WorkloadSpec,
    slo: SLOSpec,
    experiment_id: str = "exp-default",
    original_metrics: Optional[MetricSet] = None,
    adapter: Optional[BaseServingAdapter] = None,
    single_run_executor: Optional[Any] = None,
    artifacts_root: Optional[Union[str, Path]] = None,
    cancellation_token: Optional[Any] = None,
    seed: Optional[int] = 999,
    stream: bool = True,
    prompts: Optional[Union[List[str], str]] = None,
    isolate_process: bool = False,
) -> VerificationRecord:
    """
    Reruns winning candidate configuration under a fresh, independent run ID,
    recalculates metrics and feasibility from verification evidence,
    performs drift analysis, and issues final independent verification verdict.
    """
    verification_id = f"verif-{uuid.uuid4().hex[:8]}"
    verification_run_id = f"run-verify-{uuid.uuid4().hex[:8]}"

    # Enforce distinct verification run ID invariant
    assert verification_run_id != original_run_id, "Verification run ID must be distinct from original search run ID"

    if single_run_executor is not None:
        executor = single_run_executor
    else:
        from slokern.engine.runner.run_executor import SingleRunExecutor

        executor = SingleRunExecutor(
            artifacts_root=artifacts_root or "artifacts",
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

    if run_result.run_record.execution_status != ExecutionStatus.COMPLETED:
        verdict = VerificationState.VERIFICATION_INCONCLUSIVE
        notes = f"Verification execution ended with status {run_result.run_record.execution_status.value}."
    elif run_result.metric_set is None or run_result.feasibility_result is None:
        verdict = VerificationState.VERIFICATION_INCONCLUSIVE
        notes = "Verification run completed without required metric or feasibility evidence."
    elif run_result.feasibility_result.validity_status != EvidenceValidity.VALID:
        verdict = VerificationState.VERIFICATION_INCONCLUSIVE
        notes = f"Verification evidence validity is {run_result.feasibility_result.validity_status.value}."
    else:
        verif_metrics = run_result.metric_set
        feasibility = evaluate_slo(verif_metrics, slo)

        if original_metrics is not None:
            drift = compare_metrics(original_metrics, verif_metrics, slo)

        if feasibility.overall_verdict == FeasibilityVerdict.FEASIBLE:
            if drift is not None and drift.slo_drift_detected:
                verdict = VerificationState.VERIFICATION_FAILED
                notes = "Verification run drifted across a declared hard SLO threshold."
            else:
                verdict = VerificationState.VERIFIED
                notes = "Independent verification passed: configuration confirmed against all hard constraints."
        elif feasibility.overall_verdict == FeasibilityVerdict.INFEASIBLE:
            verdict = VerificationState.VERIFICATION_FAILED
            notes = "Independent verification failed: rerun violated declared hard constraints."
        else:
            verdict = VerificationState.VERIFICATION_INCONCLUSIVE
            notes = "Independent verification inconclusive: insufficient samples or invalid observations."

    return VerificationRecord(
        verification_id=verification_id,
        experiment_id=experiment_id,
        candidate_id=candidate_config.candidate_id,
        original_run_id=original_run_id,
        verification_run_id=verification_run_id,
        verification_verdict=verdict,
        drift_analysis=drift,
        final_decision_notes=notes,
    )
