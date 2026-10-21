"""
Purpose: Deterministic evaluation of evidence against an SLO into a verdict.
Owner: Daksh
"""

import math
from typing import List

from slokern.contracts.metrics import MetricSet
from slokern.contracts.spec import SLOSpec
from slokern.contracts.verdict import FeasibilityResult, ConstraintEvaluation
from slokern.contracts.enums import FeasibilityVerdict, ReasonCode, EvidenceValidity
from slokern.contracts.versions import POLICY_VERSION


def get_observed_value(metric_set: MetricSet, metric_name: str, statistic: str) -> float | None:
    """Extract observed metric value from MetricSet by metric name and statistic."""
    if metric_name == "request_throughput":
        return metric_set.request_throughput_rps
    if metric_name in ("token_throughput", "token_throughput_tps"):
        return metric_set.token_throughput_tps
    if metric_name == "error_rate":
        return metric_set.error_rate

    # Check if metric_name refers to a percentile distribution attribute
    dist_map = {
        "ttft": metric_set.ttft_ms,
        "itl": metric_set.itl_ms,
        "e2e_latency": metric_set.e2e_latency_ms
    }

    if metric_name in dist_map:
        dist = dist_map[metric_name]
        return getattr(dist, statistic, None)

    return None

def evaluate_constraint(observed_value: float | None, threshold: float, operator: str) -> bool | None:
    """
    Evaluate an observed metric value against a declared threshold and operator.

    Returns True/False on successful comparison, or None if the observation, threshold,
    or operator is missing, NaN, negative, or unsupported.
    """
    if observed_value is None:
        return None
    if math.isnan(observed_value) or observed_value < 0:
        return None
    if math.isnan(threshold):
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

    if metric_name == "ttft" and statistic == "p95":
        return ReasonCode.TTFT_P95_EXCEEDED
    if metric_name == "ttft" and statistic == "p50":
        return ReasonCode.TTFT_P50_EXCEEDED
    if metric_name == "itl" and statistic in ("p95", "p50"):
        return ReasonCode.ITL_P95_EXCEEDED
    if metric_name == "itl":
        return ReasonCode.ITL_P95_EXCEEDED
    if metric_name == "e2e_latency":
        return ReasonCode.E2E_LATENCY_EXCEEDED
    if metric_name == "error_rate":
        return ReasonCode.ERROR_RATE_EXCEEDED
    if metric_name in ("request_throughput", "token_throughput", "token_throughput_tps"):
        return ReasonCode.THROUGHPUT_DEFICIT

    return ReasonCode.MISSING_REQUIRED_METRIC

def evaluate_slo(metric_set: MetricSet, slo_spec: SLOSpec) -> FeasibilityResult:
    """
    Deterministically evaluate a MetricSet against declared hard SLO constraints.

    Returns a FeasibilityResult containing per-constraint evaluations, overall verdict,
    evidence validity status, and auditable diagnostic notes.
    """
    evaluations: List[ConstraintEvaluation] = []

    if metric_set.generator_saturated:
        validity_status = EvidenceValidity.CONTAMINATED
        overall_verdict = FeasibilityVerdict.INCONCLUSIVE
        audit_notes = "Generator saturated, workload profile was not maintained."
    elif metric_set.sample_count < slo_spec.min_sample_count:
        validity_status = EvidenceValidity.VALID
        overall_verdict = FeasibilityVerdict.INCONCLUSIVE
        audit_notes = "Insufficient valid samples."
    else:
        validity_status = EvidenceValidity.VALID
        overall_verdict = FeasibilityVerdict.FEASIBLE
        audit_notes = "All hard constraints satisfied."

    for constraint in slo_spec.constraints:
        obs_val = get_observed_value(metric_set, constraint.metric_name, constraint.statistic)

        # Override passed status and reason code if inconclusive at root level
        if metric_set.generator_saturated:
            passed = None
            reason_code = ReasonCode.GENERATOR_SATURATED
        elif metric_set.sample_count < slo_spec.min_sample_count:
            passed = None
            reason_code = ReasonCode.INSUFFICIENT_SAMPLES
        else:
            passed = evaluate_constraint(obs_val, constraint.threshold, constraint.operator)
            reason_code = ReasonCode.HARD_CONSTRAINTS_PASSED

        if passed is None and not (metric_set.generator_saturated or metric_set.sample_count < slo_spec.min_sample_count):
            if obs_val is None:
                reason_code = ReasonCode.MISSING_REQUIRED_METRIC
                if overall_verdict != FeasibilityVerdict.INCONCLUSIVE:
                    overall_verdict = FeasibilityVerdict.INCONCLUSIVE
                    audit_notes = f"Missing required metric: {constraint.metric_name}"
            elif math.isnan(obs_val) or obs_val < 0:
                reason_code = ReasonCode.MISSING_REQUIRED_METRIC
                if validity_status != EvidenceValidity.CONTAMINATED:
                    validity_status = EvidenceValidity.INVALID
                if overall_verdict != FeasibilityVerdict.INCONCLUSIVE:
                    overall_verdict = FeasibilityVerdict.INCONCLUSIVE
                    audit_notes = f"Invalid observation for {constraint.metric_name}: {obs_val}"
                else:
                    audit_notes += f"; Invalid observation for {constraint.metric_name}: {obs_val}"
            elif constraint.operator not in ["<=", "<", ">=", ">"]:
                reason_code = ReasonCode.UNSUPPORTED_OPERATOR
                if overall_verdict != FeasibilityVerdict.INCONCLUSIVE:
                    overall_verdict = FeasibilityVerdict.INCONCLUSIVE
                    audit_notes = f"Unsupported operator: {constraint.operator}"
                else:
                    audit_notes += f"; Unsupported operator: {constraint.operator}"
            else:
                reason_code = ReasonCode.MISSING_REQUIRED_METRIC
                if overall_verdict != FeasibilityVerdict.INCONCLUSIVE:
                    overall_verdict = FeasibilityVerdict.INCONCLUSIVE

        elif passed is False:
            reason_code = get_reason_code_for_failure(
                constraint.metric_name, constraint.statistic, constraint.operator
            )
            if overall_verdict == FeasibilityVerdict.FEASIBLE:
                overall_verdict = FeasibilityVerdict.INFEASIBLE
                audit_notes = f"Constraint failed: {constraint.metric_name} {constraint.statistic} {constraint.operator} {constraint.threshold}"
            elif overall_verdict == FeasibilityVerdict.INFEASIBLE:
                audit_notes += f"; Constraint failed: {constraint.metric_name} {constraint.statistic} {constraint.operator} {constraint.threshold}"

        evaluations.append(ConstraintEvaluation(
            metric_name=constraint.metric_name,
            statistic=constraint.statistic,
            observed_value=obs_val,
            required_threshold=constraint.threshold,
            operator=constraint.operator,
            passed=passed,
            reason_code=reason_code
        ))

    # Audit dropped requests when error_rate was not constrained or failed requests occurred
    if metric_set.failed_request_count > 0:
        has_error_rate_constraint = any(c.metric_name == "error_rate" for c in slo_spec.constraints)
        if not has_error_rate_constraint:
            note = f"Warning: {metric_set.failed_request_count} unconstrained dropped/failed request(s) observed (error_rate={metric_set.error_rate})."
            if overall_verdict == FeasibilityVerdict.FEASIBLE:
                audit_notes = (
                    f"All hard constraints satisfied, but {metric_set.failed_request_count} "
                    f"dropped/failed request(s) observed (error_rate={metric_set.error_rate}) unconstrained by SLO."
                )
            elif audit_notes:
                audit_notes += f"; {note}"
            else:
                audit_notes = note

    return FeasibilityResult(
        policy_version=POLICY_VERSION,
        run_id=metric_set.run_id,
        overall_verdict=overall_verdict,
        constraint_evaluations=evaluations,
        validity_status=validity_status,
        audit_notes=audit_notes
    )
