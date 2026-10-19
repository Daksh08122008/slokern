"""
Purpose: Deterministic evaluation of evidence against an SLO into a verdict.
Owner: Daksh
"""

from typing import List

from slokern.contracts.metrics import MetricSet
from slokern.contracts.spec import SLOSpec
from slokern.contracts.verdict import FeasibilityResult, ConstraintEvaluation
from slokern.contracts.enums import FeasibilityVerdict, ReasonCode, EvidenceValidity
from slokern.contracts.versions import POLICY_VERSION


def get_observed_value(metric_set: MetricSet, metric_name: str, statistic: str) -> float | None:
    if metric_name == "request_throughput":
        return metric_set.request_throughput_rps
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
    if observed_value is None:
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
    if operator not in ["<=", "<", ">=", ">"]:
        return ReasonCode.UNSUPPORTED_OPERATOR

    if metric_name == "ttft" and statistic == "p95":
        return ReasonCode.TTFT_P95_EXCEEDED
    if metric_name == "ttft" and statistic == "p50":
        return ReasonCode.TTFT_P50_EXCEEDED
    if metric_name == "itl" and statistic == "p95":
        return ReasonCode.ITL_P95_EXCEEDED
    if metric_name == "e2e_latency":
        return ReasonCode.E2E_LATENCY_EXCEEDED
    if metric_name == "error_rate":
        return ReasonCode.ERROR_RATE_EXCEEDED
    if metric_name == "request_throughput":
        return ReasonCode.THROUGHPUT_DEFICIT

    return ReasonCode.MISSING_REQUIRED_METRIC

def evaluate_slo(metric_set: MetricSet, slo_spec: SLOSpec) -> FeasibilityResult:
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
            else:
                 reason_code = ReasonCode.UNSUPPORTED_OPERATOR

            if overall_verdict != FeasibilityVerdict.INCONCLUSIVE:
                overall_verdict = FeasibilityVerdict.INCONCLUSIVE

        elif passed is False:
            reason_code = get_reason_code_for_failure(
                constraint.metric_name, constraint.statistic, constraint.operator
            )
            if overall_verdict == FeasibilityVerdict.FEASIBLE:
                overall_verdict = FeasibilityVerdict.INFEASIBLE
                audit_notes = f"Constraint failed: {constraint.metric_name} {constraint.statistic} {constraint.operator} {constraint.threshold}"

        evaluations.append(ConstraintEvaluation(
            metric_name=constraint.metric_name,
            statistic=constraint.statistic,
            observed_value=obs_val,
            required_threshold=constraint.threshold,
            operator=constraint.operator,
            passed=passed,
            reason_code=reason_code
        ))

    return FeasibilityResult(
        policy_version=POLICY_VERSION,
        run_id=metric_set.run_id,
        overall_verdict=overall_verdict,
        constraint_evaluations=evaluations,
        validity_status=validity_status,
        audit_notes=audit_notes
    )
