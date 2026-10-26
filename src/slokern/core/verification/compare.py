"""
Purpose: Compares search evidence with verification evidence, implementing epsilon near-zero math.
Owner: Rajdeep (Architecture & Implementation); Decision Verification Audit: Daksh (active Oct 24)
Authority: Aligned with AGENTS.md Section 5, 7 and DEC-0014
"""

import math
from typing import Dict, Optional

from slokern.contracts.metrics import MetricSet
from slokern.contracts.spec import SLOSpec
from slokern.contracts.verification import DriftAnalysis
from slokern.core.evaluator.evaluate import evaluate_constraint, get_observed_value

EPSILON = 1e-6


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


def compare_metrics(
    original_metrics: MetricSet,
    verification_metrics: MetricSet,
    slo_spec: Optional[SLOSpec] = None,
) -> DriftAnalysis:
    """
    Computes metric deltas between original search run and verification run.
    Detects whether verification drifted across any hard SLO threshold.
    """
    metric_deltas: Dict[str, float] = {}
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
        if orig_val is not None and verif_val is not None:
            metric_deltas[label] = _compute_delta(orig_val, verif_val)

    # If SLO specification is provided, evaluate hard threshold crossovers
    if slo_spec is not None:
        for constraint in slo_spec.constraints:
            key = f"{constraint.metric_name}_{constraint.statistic}"
            orig_val = get_observed_value(original_metrics, constraint.metric_name, constraint.statistic)
            verif_val = get_observed_value(verification_metrics, constraint.metric_name, constraint.statistic)

            if orig_val is not None and verif_val is not None:
                if key not in metric_deltas:
                    metric_deltas[key] = _compute_delta(orig_val, verif_val)

                orig_pass = evaluate_constraint(orig_val, constraint.threshold, constraint.operator)
                verif_pass = evaluate_constraint(verif_val, constraint.threshold, constraint.operator)

                if orig_pass is None or verif_pass is None or not verif_pass or orig_pass != verif_pass:
                    slo_drift_detected = True
            else:
                # Missing required metric for declared constraint
                slo_drift_detected = True

    return DriftAnalysis(
        metric_deltas=metric_deltas,
        slo_drift_detected=slo_drift_detected,
    )
