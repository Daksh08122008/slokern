"""
Purpose: Deterministic evaluation of evidence against an SLO into a verdict.
Owner: Rajdeep (Architecture & Implementation); Decision Verification Audit: Daksh (active Oct 24)
Authority: docs/decision-policy.md, docs/metrics.md, AGENTS.md Section 5 & 13
"""

import math
from typing import List

from slokern.contracts.metrics import MetricSet
from slokern.contracts.spec import SLOSpec
from slokern.contracts.verdict import FeasibilityResult, ConstraintEvaluation
from slokern.contracts.enums import FeasibilityVerdict, ReasonCode, EvidenceValidity
from slokern.contracts.versions import POLICY_VERSION


def get_observed_value(metric_set: MetricSet, metric_name: str, statistic: str) -> float | None:
    """
    Extract observed metric value from MetricSet by metric name and statistic.

    Supports canonical metric names and explicit unit-suffixed aliases.
    """
    if metric_name in ("request_throughput", "request_throughput_rps"):
        return metric_set.request_throughput_rps
    if metric_name in ("token_throughput", "token_throughput_tps"):
        return metric_set.token_throughput_tps
    if metric_name == "error_rate":
        return metric_set.error_rate

    # Check if metric_name refers to a percentile distribution attribute
    dist_map = {
        "ttft": metric_set.ttft_ms,
        "ttft_ms": metric_set.ttft_ms,
        "itl": metric_set.itl_ms,
        "itl_ms": metric_set.itl_ms,
        "e2e_latency": metric_set.e2e_latency_ms,
        "e2e_latency_ms": metric_set.e2e_latency_ms,
    }

    if metric_name in dist_map:
        dist = dist_map[metric_name]
        if dist is None:
            return None
        return getattr(dist, statistic, None)

    return None


def evaluate_constraint(observed_value: float | None, threshold: float, operator: str) -> bool | None:
    """
    Evaluate an observed metric value against a declared threshold and operator.

    Returns True/False on successful comparison, or None if the observation, threshold,
    or operator is missing, non-finite (NaN/inf), negative (for non-negative domains),
    or unsupported.
    """
    if observed_value is None or threshold is None:
        return None
    if not math.isfinite(observed_value) or observed_value < 0:
        return None
    if not math.isfinite(threshold) or threshold < 0:
        return None
    if operator == "<=":
        return observed_value <= threshold
    if operator == "<":
        return observed_value < threshold
    if operator == ">=":
        return observed_value >= threshold
    if operator == ">":
        return observed_value > threshold
    return None


def get_reason_code_for_failure(metric_name: str, statistic: str, operator: str) -> ReasonCode:
    """Map a violated constraint or invalid operator to its canonical ReasonCode."""
    if operator not in ["<=", "<", ">=", ">"]:
        return ReasonCode.UNSUPPORTED_OPERATOR

    if metric_name in ("ttft", "ttft_ms"):
        if statistic == "p50":
            return ReasonCode.TTFT_P50_EXCEEDED
        return ReasonCode.TTFT_P95_EXCEEDED

    if metric_name in ("itl", "itl_ms"):
        return ReasonCode.ITL_P95_EXCEEDED

    if metric_name in ("e2e_latency", "e2e_latency_ms"):
        return ReasonCode.E2E_LATENCY_EXCEEDED

    if metric_name == "error_rate":
        return ReasonCode.ERROR_RATE_EXCEEDED

    if metric_name in ("request_throughput", "request_throughput_rps", "token_throughput", "token_throughput_tps"):
        return ReasonCode.THROUGHPUT_DEFICIT

    return ReasonCode.MISSING_REQUIRED_METRIC


def evaluate_slo(metric_set: MetricSet, slo_spec: SLOSpec) -> FeasibilityResult:
    """
    Deterministically evaluate a MetricSet against declared hard SLO constraints.

    Returns a FeasibilityResult containing per-constraint evaluations, overall verdict,
    evidence validity status, and auditable diagnostic notes.
    """
    evaluations: List[ConstraintEvaluation] = []

    # Validity status priority: CONTAMINATED > INVALID > VALID
    if metric_set.generator_saturated:
        validity_status = EvidenceValidity.CONTAMINATED
    else:
        validity_status = EvidenceValidity.VALID

    # Diagnostic messages categorized for audit logging
    failure_notes: List[str] = []
    invalid_notes: List[str] = []
    missing_notes: List[str] = []
    unsupported_notes: List[str] = []

    for constraint in slo_spec.constraints:
        obs_val = get_observed_value(metric_set, constraint.metric_name, constraint.statistic)

        if metric_set.generator_saturated:
            passed = None
            reason_code = ReasonCode.GENERATOR_SATURATED
        elif metric_set.sample_count < slo_spec.min_sample_count:
            passed = None
            reason_code = ReasonCode.INSUFFICIENT_SAMPLES
        else:
            # Check reasons for invalid/missing observation or threshold before evaluation
            if obs_val is None:
                passed = None
                reason_code = ReasonCode.MISSING_REQUIRED_METRIC
                missing_notes.append(f"Missing required metric: {constraint.metric_name}")
            elif not math.isfinite(obs_val) or obs_val < 0:
                passed = None
                reason_code = ReasonCode.MISSING_REQUIRED_METRIC
                if validity_status != EvidenceValidity.CONTAMINATED:
                    validity_status = EvidenceValidity.INVALID
                invalid_notes.append(f"Invalid observation for {constraint.metric_name}: {obs_val}")
            elif constraint.threshold is None or not math.isfinite(constraint.threshold) or constraint.threshold < 0:
                passed = None
                reason_code = ReasonCode.MISSING_REQUIRED_METRIC
                if validity_status != EvidenceValidity.CONTAMINATED:
                    validity_status = EvidenceValidity.INVALID
                invalid_notes.append(f"Invalid threshold for {constraint.metric_name}: {constraint.threshold}")
            elif constraint.operator not in ["<=", "<", ">=", ">"]:
                passed = None
                reason_code = ReasonCode.UNSUPPORTED_OPERATOR
                unsupported_notes.append(f"Unsupported operator: {constraint.operator}")
            else:
                passed = evaluate_constraint(obs_val, constraint.threshold, constraint.operator)
                if passed is True:
                    reason_code = ReasonCode.HARD_CONSTRAINTS_PASSED
                else:
                    reason_code = get_reason_code_for_failure(
                        constraint.metric_name, constraint.statistic, constraint.operator
                    )
                    failure_notes.append(
                        f"Constraint failed: {constraint.metric_name} {constraint.statistic} {constraint.operator} {constraint.threshold}"
                    )

        evaluations.append(ConstraintEvaluation(
            metric_name=constraint.metric_name,
            statistic=constraint.statistic,
            observed_value=obs_val,
            required_threshold=constraint.threshold,
            operator=constraint.operator,
            passed=passed,
            reason_code=reason_code
        ))

    # Determine overall verdict based on deterministic precedence:
    # INCONCLUSIVE (contaminated/insufficient/invalid/missing) > INFEASIBLE (failed constraints) > FEASIBLE
    if metric_set.generator_saturated or metric_set.sample_count < slo_spec.min_sample_count:
        overall_verdict = FeasibilityVerdict.INCONCLUSIVE
    elif invalid_notes or missing_notes or unsupported_notes:
        overall_verdict = FeasibilityVerdict.INCONCLUSIVE
    elif failure_notes:
        overall_verdict = FeasibilityVerdict.INFEASIBLE
    else:
        overall_verdict = FeasibilityVerdict.FEASIBLE

    # Assemble diagnostic audit notes deterministically
    all_issue_notes: List[str] = []
    if metric_set.generator_saturated:
        all_issue_notes.append("Generator saturated, workload profile was not maintained.")
    elif metric_set.sample_count < slo_spec.min_sample_count:
        all_issue_notes.append("Insufficient valid samples.")

    # Include constraint-level diagnostic issues
    all_issue_notes.extend(invalid_notes)
    all_issue_notes.extend(missing_notes)
    all_issue_notes.extend(unsupported_notes)
    all_issue_notes.extend(failure_notes)

    # Audit dropped requests when error_rate was not constrained or failed requests occurred
    dropped_warning = None
    if metric_set.failed_request_count > 0:
        has_error_rate_constraint = any(c.metric_name == "error_rate" for c in slo_spec.constraints)
        if not has_error_rate_constraint:
            dropped_warning = (
                f"Warning: {metric_set.failed_request_count} unconstrained "
                f"dropped/failed request(s) observed (error_rate={metric_set.error_rate})."
            )

    if overall_verdict == FeasibilityVerdict.FEASIBLE:
        if dropped_warning:
            audit_notes = (
                f"All hard constraints satisfied, but {metric_set.failed_request_count} "
                f"dropped/failed request(s) observed (error_rate={metric_set.error_rate}) unconstrained by SLO."
            )
        else:
            audit_notes = "All hard constraints satisfied."
    else:
        if dropped_warning:
            all_issue_notes.append(dropped_warning)
        audit_notes = "; ".join(all_issue_notes)

    return FeasibilityResult(
        policy_version=POLICY_VERSION,
        run_id=metric_set.run_id,
        overall_verdict=overall_verdict,
        constraint_evaluations=evaluations,
        validity_status=validity_status,
        audit_notes=audit_notes
    )
