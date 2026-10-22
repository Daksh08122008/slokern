from typing import Dict, Any, List
from evaluator.schemas import Verdict, VerdictState, ReasonCode, ConstraintResult


def evaluate_run(
    run_id: str,
    candidate_id: str,
    metrics: Dict[str, Any],
    slo_spec: Dict[str, Any]
) -> Verdict:
    """
    Evaluates a benchmark run against defined SLO requirements using 
    strict deterministic precedence:
    1. Data Integrity / Inconclusive checks (missing data, low samples)
    2. Threshold Constraints (TTFT, error rate) -> Infeasible
    3. Success -> Feasible
    """
    constraint_results: List[ConstraintResult] = []
    reasons: List[ReasonCode] = []

    # -------------------------------------------------------------
    # STEP 1: Data Integrity & Inconclusive Checks
    # -------------------------------------------------------------
    sample_count = metrics.get("sample_count", 0)
    min_samples = slo_spec.get("min_samples", 10)

    if sample_count < min_samples:
        reasons.append(ReasonCode.INSUFFICIENT_SAMPLES)
        return Verdict(
            run_id=run_id,
            candidate_id=candidate_id,
            state=VerdictState.INCONCLUSIVE,
            reasons=reasons,
            notes=f"Sample count ({sample_count}) is below minimum required ({min_samples})."
        )

    # Check for missing required metrics
    required_keys = ["ttft_p90", "error_rate"]
    for key in required_keys:
        if key not in metrics or metrics[key] is None:
            reasons.append(ReasonCode.MISSING_METRICS)
            return Verdict(
                run_id=run_id,
                candidate_id=candidate_id,
                state=VerdictState.INCONCLUSIVE,
                reasons=reasons,
                notes=f"Required metric '{key}' is missing from benchmark artifact."
            )

    # Check for Out-Of-Memory flag
    if metrics.get("oom_occurred", False):
        reasons.append(ReasonCode.OOM_CRASH)
        return Verdict(
            run_id=run_id,
            candidate_id=candidate_id,
            state=VerdictState.INFEASIBLE,
            reasons=reasons,
            notes="GPU Out-Of-Memory error detected during execution."
        )

    # -------------------------------------------------------------
    # STEP 2: Threshold Evaluations (Hard Constraints)
    # -------------------------------------------------------------
    
    # 1. TTFT Check (Inclusive boundary: <= target)
    target_ttft = slo_spec.get("max_ttft_ms", 200.0)
    actual_ttft = metrics["ttft_p90"]
    ttft_passed = actual_ttft <= target_ttft
    
    if not ttft_passed:
        reasons.append(ReasonCode.TTFT_EXCEEDED)

    constraint_results.append(
        ConstraintResult(
            constraint_name="ttft_p90",
            target_value=target_ttft,
            actual_value=actual_ttft,
            passed=ttft_passed,
            reason_code=ReasonCode.TTFT_EXCEEDED if not ttft_passed else None
        )
    )

    # 2. Error Rate Check (Inclusive boundary: <= max error rate)
    max_error_rate = slo_spec.get("max_error_rate", 0.0)
    actual_error_rate = metrics["error_rate"]
    error_passed = actual_error_rate <= max_error_rate

    if not error_passed:
        reasons.append(ReasonCode.HIGH_ERROR_RATE)

    constraint_results.append(
        ConstraintResult(
            constraint_name="error_rate",
            target_value=max_error_rate,
            actual_value=actual_error_rate,
            passed=error_passed,
            reason_code=ReasonCode.HIGH_ERROR_RATE if not error_passed else None
        )
    )

    # -------------------------------------------------------------
    # STEP 3: Final Verdict Decision
    # -------------------------------------------------------------
    if reasons:
        final_state = VerdictState.INFEASIBLE
        notes = "One or more hard constraints failed."
    else:
        final_state = VerdictState.FEASIBLE
        notes = "All hard constraints passed successfully."

    return Verdict(
        run_id=run_id,
        candidate_id=candidate_id,
        state=final_state,
        reasons=reasons,
        constraint_results=constraint_results,
        notes=notes
    )