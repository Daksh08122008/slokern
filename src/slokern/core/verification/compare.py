"""
Purpose: Compares search evidence with verification evidence, implementing epsilon near-zero math and drift auditing.
Owner: Rajdeep (Historical design: Daksh)
Authority: Aligned with AGENTS.md Section 5, 7, and DEC-0014
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional, Tuple

from slokern.contracts.metrics import MetricSet
from slokern.contracts.spec import SLOSpec
from slokern.contracts.verification import DriftAnalysis, MetricDriftComparison
from slokern.core.evaluator.evaluate import evaluate_constraint, get_observed_value

EPSILON = 1e-6


@dataclass(frozen=True)
class DriftPolicy:
    """
    Declarative tolerance specification for independent verification drift auditing.
    Default policy:
    - Latency percentiles (TTFT, ITL, E2E): max +15.0% relative degradation.
    - Throughput (RPS, TPS): max -15.0% relative drop.
    - Error rate: max +0.01 (+1.0 percentage point) absolute increase.
    - Boundary evaluation: strict '>' triggers failure (drift > tolerance).
    """

    latency_relative_tolerance: float = 15.0
    throughput_relative_tolerance: float = -15.0
    error_rate_absolute_tolerance: float = 0.01
    custom_metric_tolerances: Dict[str, float] = field(default_factory=dict)

    def get_tolerance(self, metric_label: str) -> Tuple[float, Literal["relative_percentage", "absolute_difference"], str]:
        """Returns (tolerance_value, comparison_method, unit) for a given metric label."""
        if metric_label in self.custom_metric_tolerances:
            tol = self.custom_metric_tolerances[metric_label]
            method: Literal["relative_percentage", "absolute_difference"] = (
                "absolute_difference" if "error_rate" in metric_label else "relative_percentage"
            )
            unit = "fraction" if "error_rate" in metric_label else ("ms" if "latency" in metric_label or "ttft" in metric_label or "itl" in metric_label else "requests/s")
            return tol, method, unit

        if "error_rate" in metric_label:
            return self.error_rate_absolute_tolerance, "absolute_difference", "fraction"
        if "throughput" in metric_label:
            unit = "tokens/s" if "tps" in metric_label or "token" in metric_label else "requests/s"
            return self.throughput_relative_tolerance, "relative_percentage", unit

        # Latency metrics default to relative percentage in ms
        return self.latency_relative_tolerance, "relative_percentage", "ms"


def _compute_delta(orig: float, verif: float) -> float:
    """
    Computes percentage delta between original search metric and verification metric.
    Safely handles orig near zero via epsilon math.
    """
    if not math.isfinite(orig) or not math.isfinite(verif):
        return 0.0

    if abs(orig) < EPSILON:
        if abs(verif) < EPSILON:
            return 0.0
        # For base 0 (e.g., error rate 0.0 -> 0.005), report absolute change scaled to percent
        return round((verif - orig) * 100.0, 4)

    return round(((verif - orig) / orig) * 100.0, 4)


def _evaluate_single_metric_drift(
    label: str,
    orig_val: Optional[float],
    verif_val: Optional[float],
    policy: DriftPolicy,
) -> Tuple[Optional[float], MetricDriftComparison]:
    """
    Evaluates drift for a single metric against the declared DriftPolicy.
    Returns (delta_value, comparison_record).
    """
    tolerance, method, unit = policy.get_tolerance(label)

    if orig_val is None or verif_val is None:
        delta = None
        return delta, MetricDriftComparison(
            metric_name=label,
            reference_value=0.0 if orig_val is None else orig_val,
            verification_value=0.0 if verif_val is None else verif_val,
            absolute_drift=0.0,
            relative_drift=None,
            tolerance=tolerance,
            comparison_method=method,
            unit=unit,
            passed=False,
            failure_reason="MISSING_METRIC_VALUE",
        )

    if not math.isfinite(orig_val) or not math.isfinite(verif_val):
        return 0.0, MetricDriftComparison(
            metric_name=label,
            reference_value=orig_val if math.isfinite(orig_val) else 0.0,
            verification_value=verif_val if math.isfinite(verif_val) else 0.0,
            absolute_drift=0.0,
            relative_drift=None,
            tolerance=tolerance,
            comparison_method=method,
            unit=unit,
            passed=False,
            failure_reason="NON_FINITE_METRIC",
        )

    abs_drift = round(abs(verif_val - orig_val), 6)
    delta = _compute_delta(orig_val, verif_val)

    if method == "absolute_difference":
        # For error rate, directional increase is verif - orig
        signed_abs_diff = round(verif_val - orig_val, 6)
        # Strict '>' boundary: failure if signed_abs_diff > tolerance
        passed = signed_abs_diff <= tolerance
        failure_reason = None if passed else f"Absolute drift {signed_abs_diff:g} exceeds tolerance {tolerance:g}"
        return delta, MetricDriftComparison(
            metric_name=label,
            reference_value=round(orig_val, 6),
            verification_value=round(verif_val, 6),
            absolute_drift=abs_drift,
            relative_drift=delta,
            tolerance=tolerance,
            comparison_method=method,
            unit=unit,
            passed=passed,
            failure_reason=failure_reason,
        )

    # Relative percentage evaluation
    rel_drift = delta
    if "throughput" in label:
        # Throughput drop: delta < tolerance (e.g. -16.0% < -15.0% fails)
        # Strict boundary: delta < tolerance is a failure; delta == tolerance passes.
        passed = rel_drift >= tolerance
        failure_reason = None if passed else f"Throughput relative drop {rel_drift:g}% exceeds tolerance {tolerance:g}%"
    else:
        # Latency degradation: delta > tolerance (e.g. +16.0% > +15.0% fails)
        # Strict boundary: delta > tolerance is a failure; delta == tolerance passes.
        passed = rel_drift <= tolerance
        failure_reason = None if passed else f"Latency relative increase {rel_drift:g}% exceeds tolerance {tolerance:g}%"

    return delta, MetricDriftComparison(
        metric_name=label,
        reference_value=round(orig_val, 6),
        verification_value=round(verif_val, 6),
        absolute_drift=abs_drift,
        relative_drift=rel_drift,
        tolerance=tolerance,
        comparison_method=method,
        unit=unit,
        passed=passed,
        failure_reason=failure_reason,
    )


def compare_metrics(
    original_metrics: MetricSet,
    verification_metrics: MetricSet,
    slo_spec: Optional[SLOSpec] = None,
    drift_policy: Optional[DriftPolicy] = None,
) -> DriftAnalysis:
    """
    Computes metric deltas and detailed drift comparisons between original search run and verification run.
    Evaluates whether:
    1. Any declared hard SLO threshold was crossed (slo_drift_detected = True).
    2. Any metric exceeded its declared drift tolerance under DriftPolicy (drift_exceeded = True).
    """
    policy = drift_policy or DriftPolicy()
    metric_deltas: Dict[str, float] = {}
    metric_comparisons: Dict[str, MetricDriftComparison] = {}
    slo_drift_detected = False

    # Standard metric comparison points
    standard_checks = [
        ("ttft_ms", "p95", "ttft_p95"),
        ("ttft_ms", "p50", "ttft_p50"),
        ("itl_ms", "p95", "itl_p95"),
        ("itl_ms", "p50", "itl_p50"),
        ("e2e_latency_ms", "p95", "e2e_latency_p95"),
        ("e2e_latency_ms", "p50", "e2e_latency_p50"),
        ("request_throughput", "mean", "request_throughput_rps"),
        ("token_throughput", "mean", "token_throughput_tps"),
        ("error_rate", "mean", "error_rate"),
    ]

    for m_name, stat, label in standard_checks:
        orig_val = get_observed_value(original_metrics, m_name, stat)
        verif_val = get_observed_value(verification_metrics, m_name, stat)
        if "throughput" in label:
            if original_metrics.sample_count == 0:
                orig_val = None
            if verification_metrics.sample_count == 0:
                verif_val = None
        elif label == "error_rate":
            if (original_metrics.sample_count + original_metrics.failed_request_count) == 0:
                orig_val = None
            if (verification_metrics.sample_count + verification_metrics.failed_request_count) == 0:
                verif_val = None
        delta, comp = _evaluate_single_metric_drift(label, orig_val, verif_val, policy)
        if delta is not None:
            metric_deltas[label] = delta
        metric_comparisons[label] = comp

    # If SLO specification is provided, evaluate hard threshold crossovers
    if slo_spec is not None:
        for constraint in slo_spec.constraints:
            key = f"{constraint.metric_name}_{constraint.statistic}"
            orig_val = get_observed_value(original_metrics, constraint.metric_name, constraint.statistic)
            verif_val = get_observed_value(verification_metrics, constraint.metric_name, constraint.statistic)
            if "throughput" in constraint.metric_name:
                if original_metrics.sample_count == 0:
                    orig_val = None
                if verification_metrics.sample_count == 0:
                    verif_val = None
            elif constraint.metric_name == "error_rate":
                if (original_metrics.sample_count + original_metrics.failed_request_count) == 0:
                    orig_val = None
                if (verification_metrics.sample_count + verification_metrics.failed_request_count) == 0:
                    verif_val = None

            if orig_val is not None and verif_val is not None:
                if key not in metric_deltas:
                    delta, comp = _evaluate_single_metric_drift(key, orig_val, verif_val, policy)
                    if delta is not None:
                        metric_deltas[key] = delta
                    metric_comparisons[key] = comp

                orig_pass = evaluate_constraint(orig_val, constraint.threshold, constraint.operator)
                verif_pass = evaluate_constraint(verif_val, constraint.threshold, constraint.operator)

                if orig_pass is None or verif_pass is None or not verif_pass or orig_pass != verif_pass:
                    slo_drift_detected = True
            else:
                # Missing required metric for declared constraint
                slo_drift_detected = True
                if key not in metric_comparisons:
                    _, comp = _evaluate_single_metric_drift(key, orig_val, verif_val, policy)
                    metric_comparisons[key] = comp

    both_datasets_valid = (
        original_metrics.sample_count > 0 and verification_metrics.sample_count > 0
    )
    comparable_comparisons = [
        comp for comp in metric_comparisons.values()
        if comp.failure_reason != "MISSING_METRIC_VALUE"
    ]
    drift_exceeded = (
        both_datasets_valid
        and bool(comparable_comparisons)
        and any(not comp.passed for comp in comparable_comparisons)
    )

    return DriftAnalysis(
        metric_deltas=metric_deltas,
        slo_drift_detected=slo_drift_detected,
        metric_comparisons=metric_comparisons,
        drift_exceeded=drift_exceeded,
    )
