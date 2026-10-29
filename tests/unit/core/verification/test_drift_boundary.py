"""
Purpose: Boundary and mathematical tests for verification drift comparator.
Owner: Rajdeep
Authority: AGENTS.md Section 5, 7, 10
"""


from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.contracts.spec import SLOConstraint, SLOSpec
from slokern.core.verification.compare import DriftPolicy, _compute_delta, compare_metrics


def _make_metric_set(
    run_id: str,
    ttft_p95: float = 100.0,
    throughput_rps: float = 20.0,
    error_rate: float = 0.0,
) -> MetricSet:
    return MetricSet(
        metric_version="1.0.0",
        run_id=run_id,
        sample_count=100,
        failed_request_count=int(error_rate * 100),
        offered_load_rps=20.0,
        achieved_load_rps=20.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=ttft_p95 * 0.7, p95=ttft_p95),
        itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
        request_throughput_rps=throughput_rps,
        token_throughput_tps=throughput_rps * 10.0,
        error_rate=error_rate,
    )


def test_delta_computation_near_zero_math():
    """Validates epsilon math when original or verification values are zero or near zero."""
    # 0 to 0
    assert _compute_delta(0.0, 0.0) == 0.0
    # Near zero to near zero (< 1e-6)
    assert _compute_delta(1e-7, 2e-7) == 0.0
    # Zero base to 0.005 (e.g. error rate 0.5% increase)
    assert _compute_delta(0.0, 0.005) == 0.5
    # Standard relative delta
    assert _compute_delta(100.0, 115.0) == 15.0
    assert _compute_delta(100.0, 85.0) == -15.0
    # Non-finite inputs return 0.0 safely
    assert _compute_delta(float("nan"), 100.0) == 0.0
    assert _compute_delta(100.0, float("inf")) == 0.0


def test_latency_drift_exact_boundary():
    """
    Tests exact boundary operator for latency (+15.0% tolerance):
    - +14.99% -> PASS
    - +15.00% -> PASS (strict >: 15.0 <= 15.0 is True)
    - +15.01% -> FAIL (15.01 > 15.0)
    """
    orig = _make_metric_set("run-ref", ttft_p95=100.0)

    # 1. Below tolerance: +14.99%
    verif_below = _make_metric_set("run-v1", ttft_p95=114.99)
    res_below = compare_metrics(orig, verif_below)
    ttft_comp = res_below.metric_comparisons["ttft_p95"]
    assert ttft_comp.passed is True
    assert ttft_comp.relative_drift == 14.99

    # 2. Exactly at tolerance: +15.00%
    verif_exact = _make_metric_set("run-v2", ttft_p95=115.0)
    res_exact = compare_metrics(orig, verif_exact)
    ttft_comp_exact = res_exact.metric_comparisons["ttft_p95"]
    assert ttft_comp_exact.passed is True
    assert ttft_comp_exact.relative_drift == 15.0
    assert res_exact.drift_exceeded is False

    # 3. Strictly above tolerance: +15.01%
    verif_above = _make_metric_set("run-v3", ttft_p95=115.01)
    res_above = compare_metrics(orig, verif_above)
    ttft_comp_above = res_above.metric_comparisons["ttft_p95"]
    assert ttft_comp_above.passed is False
    assert ttft_comp_above.relative_drift == 15.01
    assert "exceeds tolerance" in (ttft_comp_above.failure_reason or "")
    assert res_above.drift_exceeded is True


def test_throughput_drift_exact_boundary():
    """
    Tests exact boundary operator for throughput (-15.0% tolerance drop):
    - -14.99% drop -> PASS
    - -15.00% drop -> PASS
    - -15.01% drop -> FAIL
    """
    orig = _make_metric_set("run-ref", throughput_rps=100.0)

    # 1. Below tolerance drop: -14.99% (85.01 rps)
    verif_below = _make_metric_set("run-v1", throughput_rps=85.01)
    res_below = compare_metrics(orig, verif_below)
    tp_comp = res_below.metric_comparisons["request_throughput_rps"]
    assert tp_comp.passed is True

    # 2. Exactly at tolerance drop: -15.00% (85.0 rps)
    verif_exact = _make_metric_set("run-v2", throughput_rps=85.0)
    res_exact = compare_metrics(orig, verif_exact)
    tp_comp_exact = res_exact.metric_comparisons["request_throughput_rps"]
    assert tp_comp_exact.passed is True
    assert tp_comp_exact.relative_drift == -15.0
    assert res_exact.drift_exceeded is False

    # 3. Strictly exceeding drop: -15.01% (84.99 rps)
    verif_above = _make_metric_set("run-v3", throughput_rps=84.99)
    res_above = compare_metrics(orig, verif_above)
    tp_comp_above = res_above.metric_comparisons["request_throughput_rps"]
    assert tp_comp_above.passed is False
    assert "Throughput relative drop" in (tp_comp_above.failure_reason or "")
    assert res_above.drift_exceeded is True


def test_error_rate_absolute_boundary():
    """
    Tests exact boundary for error rate (+0.01 / +1.0 percentage points):
    - 0.000 -> 0.010 -> PASS
    - 0.000 -> 0.0101 -> FAIL
    """
    orig = _make_metric_set("run-ref", error_rate=0.0)

    # 1. Exact match at +0.010: PASS
    verif_exact = _make_metric_set("run-v1", error_rate=0.010)
    res_exact = compare_metrics(orig, verif_exact)
    err_comp = res_exact.metric_comparisons["error_rate"]
    assert err_comp.passed is True
    assert err_comp.absolute_drift == 0.01
    assert res_exact.drift_exceeded is False

    # 2. Strictly above +0.010: FAIL
    verif_above = _make_metric_set("run-v2", error_rate=0.0101)
    res_above = compare_metrics(orig, verif_above)
    err_comp_above = res_above.metric_comparisons["error_rate"]
    assert err_comp_above.passed is False
    assert "exceeds tolerance" in (err_comp_above.failure_reason or "")
    assert res_above.drift_exceeded is True


def test_non_finite_metrics_handling():
    """Validates that NaN and Inf do not cause unhandled errors and are flagged as failed."""
    orig = _make_metric_set("run-ref", ttft_p95=100.0)
    verif = _make_metric_set("run-v1", ttft_p95=float("nan"))

    res = compare_metrics(orig, verif)
    comp = res.metric_comparisons["ttft_p95"]
    assert comp.passed is False
    assert comp.failure_reason == "NON_FINITE_METRIC"
    assert res.drift_exceeded is True


def test_custom_drift_policy():
    """Validates overriding default tolerances with custom DriftPolicy."""
    custom_policy = DriftPolicy(
        latency_relative_tolerance=5.0,  # Strict 5% tolerance
        throughput_relative_tolerance=-5.0,
        error_rate_absolute_tolerance=0.005,
    )

    orig = _make_metric_set("run-ref", ttft_p95=100.0)
    # +8% would pass default (15%) but fails custom (5%)
    verif = _make_metric_set("run-v1", ttft_p95=108.0)

    res = compare_metrics(orig, verif, drift_policy=custom_policy)
    comp = res.metric_comparisons["ttft_p95"]
    assert comp.passed is False
    assert comp.tolerance == 5.0
    assert res.drift_exceeded is True


def test_slo_drift_detected_independent_of_tolerance():
    """
    Even if drift is within relative tolerance, crossing an SLO threshold
    must trigger slo_drift_detected = True.
    """
    # Reference: 190ms (passes 200ms threshold)
    orig = _make_metric_set("run-ref", ttft_p95=190.0)
    # Verification: 205ms (+7.9% drift is within 15% tolerance, but breaches 200ms SLO)
    verif = _make_metric_set("run-v1", ttft_p95=205.0)

    slo = SLOSpec(
        slo_id="slo-test",
        min_sample_count=20,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=200.0, unit="ms", operator="<=")
        ]
    )

    res = compare_metrics(orig, verif, slo_spec=slo)
    assert res.slo_drift_detected is True
    # In this case ttft_p95 drift was 7.89% <= 15.0%, so drift_exceeded is False,
    # but slo_drift_detected is True because threshold was breached.
    assert res.metric_comparisons["ttft_p95"].passed is True
    assert res.slo_drift_detected is True


def test_directional_improvement_semantics():
    """
    Validates directional semantics:
    - Latency decrease (improvement) must pass.
    - Throughput increase (improvement) must pass.
    - Error rate decrease (improvement) must pass.
    """
    orig = _make_metric_set("run-ref", ttft_p95=100.0, throughput_rps=50.0, error_rate=0.02)
    # Verification improves on all three metrics: lower latency (80ms), higher throughput (65 rps), lower error rate (0.005)
    verif = _make_metric_set("run-v1", ttft_p95=80.0, throughput_rps=65.0, error_rate=0.005)

    res = compare_metrics(orig, verif)

    # 1. Latency -20.0% is <= +15.0% tolerance -> PASS
    ttft_comp = res.metric_comparisons["ttft_p95"]
    assert ttft_comp.passed is True
    assert ttft_comp.relative_drift == -20.0

    # 2. Throughput +30.0% is >= -15.0% tolerance -> PASS
    tp_comp = res.metric_comparisons["request_throughput_rps"]
    assert tp_comp.passed is True
    assert tp_comp.relative_drift == 30.0

    # 3. Error rate -0.015 is <= +0.01 tolerance -> PASS
    err_comp = res.metric_comparisons["error_rate"]
    assert err_comp.passed is True
    assert err_comp.absolute_drift == 0.015

    assert res.drift_exceeded is False


def test_error_rate_just_inside_boundary():
    """
    Validates error rate just inside (+0.0099) vs exact (+0.010) vs just outside (+0.0101).
    """
    orig = _make_metric_set("run-ref", error_rate=0.0)

    # Just inside (+0.0099 / +0.99 percentage point)
    verif_inside = _make_metric_set("run-v1", error_rate=0.0099)
    res_inside = compare_metrics(orig, verif_inside)
    comp_inside = res_inside.metric_comparisons["error_rate"]
    assert comp_inside.passed is True
    assert comp_inside.absolute_drift == 0.0099
    assert res_inside.drift_exceeded is False


def test_token_throughput_exact_boundary_and_just_outside():
    """
    Validates exact boundary and just-outside semantics for token throughput:
    Tolerance: max -15.0% relative drop.
    - -14.99% drop -> PASS (just inside)
    - -15.00% drop -> PASS (exact boundary)
    - -15.01% drop -> FAIL (just outside)
    - +25.00% increase -> PASS (improvement)
    """
    orig = _make_metric_set("run-ref", throughput_rps=10.0)  # token throughput = 100.0 tps

    # 1. Just inside: -14.99% (85.01 tps)
    verif_inside = MetricSet(
        metric_version="1.0.0",
        run_id="run-v1",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=70.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
        request_throughput_rps=10.0,
        token_throughput_tps=85.01,
        error_rate=0.0,
    )
    res_inside = compare_metrics(orig, verif_inside)
    comp_inside = res_inside.metric_comparisons["token_throughput_tps"]
    assert comp_inside.passed is True
    assert comp_inside.relative_drift == -14.99
    assert res_inside.drift_exceeded is False

    # 2. Exact boundary: -15.00% (85.0 tps)
    verif_exact = MetricSet(
        metric_version="1.0.0",
        run_id="run-v2",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=70.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
        request_throughput_rps=10.0,
        token_throughput_tps=85.0,
        error_rate=0.0,
    )
    res_exact = compare_metrics(orig, verif_exact)
    comp_exact = res_exact.metric_comparisons["token_throughput_tps"]
    assert comp_exact.passed is True
    assert comp_exact.relative_drift == -15.0
    assert res_exact.drift_exceeded is False

    # 3. Just outside: -15.01% (84.99 tps)
    verif_outside = MetricSet(
        metric_version="1.0.0",
        run_id="run-v3",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=70.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
        request_throughput_rps=10.0,
        token_throughput_tps=84.99,
        error_rate=0.0,
    )
    res_outside = compare_metrics(orig, verif_outside)
    comp_outside = res_outside.metric_comparisons["token_throughput_tps"]
    assert comp_outside.passed is False
    assert comp_outside.relative_drift == -15.01
    assert "Throughput relative drop" in (comp_outside.failure_reason or "")
    assert res_outside.drift_exceeded is True

    # 4. Improvement: +25.0% (125.0 tps)
    verif_improve = MetricSet(
        metric_version="1.0.0",
        run_id="run-v4",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=70.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
        request_throughput_rps=10.0,
        token_throughput_tps=125.0,
        error_rate=0.0,
    )
    res_improve = compare_metrics(orig, verif_improve)
    comp_improve = res_improve.metric_comparisons["token_throughput_tps"]
    assert comp_improve.passed is True
    assert comp_improve.relative_drift == 25.0
    assert res_improve.drift_exceeded is False


def test_error_rate_non_zero_reference_boundary():
    """
    Validates absolute drift boundary for error rate when reference is non-zero (base = 0.02 / 2%):
    Tolerance: max +0.01 (+1.0 percentage points absolute increase).
    - 0.02 -> 0.0299 (+0.0099) -> PASS (just inside)
    - 0.02 -> 0.0300 (+0.0100) -> PASS (exact boundary)
    - 0.02 -> 0.0301 (+0.0101) -> FAIL (just outside)
    - 0.02 -> 0.0050 (-0.0150) -> PASS (improvement)
    """
    orig = _make_metric_set("run-ref", error_rate=0.02)

    # 1. Just inside: +0.0099 increase (verif = 0.0299)
    verif_inside = _make_metric_set("run-v1", error_rate=0.0299)
    res_inside = compare_metrics(orig, verif_inside)
    comp_inside = res_inside.metric_comparisons["error_rate"]
    assert comp_inside.passed is True
    assert comp_inside.absolute_drift == 0.0099
    assert res_inside.drift_exceeded is False

    # 2. Exact boundary: +0.0100 increase (verif = 0.0300)
    verif_exact = _make_metric_set("run-v2", error_rate=0.0300)
    res_exact = compare_metrics(orig, verif_exact)
    comp_exact = res_exact.metric_comparisons["error_rate"]
    assert comp_exact.passed is True
    assert comp_exact.absolute_drift == 0.01
    assert res_exact.drift_exceeded is False

    # 3. Just outside: +0.0101 increase (verif = 0.0301)
    verif_outside = _make_metric_set("run-v3", error_rate=0.0301)
    res_outside = compare_metrics(orig, verif_outside)
    comp_outside = res_outside.metric_comparisons["error_rate"]
    assert comp_outside.passed is False
    assert comp_outside.absolute_drift == 0.0101
    assert "exceeds tolerance" in (comp_outside.failure_reason or "")
    assert res_outside.drift_exceeded is True

    # 4. Improvement: -0.0150 reduction (verif = 0.0050)
    verif_improve = _make_metric_set("run-v4", error_rate=0.0050)
    res_improve = compare_metrics(orig, verif_improve)
    comp_improve = res_improve.metric_comparisons["error_rate"]
    assert comp_improve.passed is True
    assert comp_improve.absolute_drift == 0.015
    assert res_improve.drift_exceeded is False


def test_itl_and_e2e_latency_exact_boundary():
    """
    Validates exact boundary and just-outside semantics for ITL and E2E latency percentiles (+15.0% tolerance).
    """
    orig = _make_metric_set("run-ref", ttft_p95=100.0)

    # ITL p95 exact boundary: 20.0ms -> 23.0ms (+15.0%) -> PASS
    verif_itl_exact = MetricSet(
        metric_version="1.0.0",
        run_id="run-v1",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=20.0,
        achieved_load_rps=20.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=70.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=10.0, p95=23.0),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
        request_throughput_rps=20.0,
        token_throughput_tps=200.0,
        error_rate=0.0,
    )
    res_itl = compare_metrics(orig, verif_itl_exact)
    itl_comp = res_itl.metric_comparisons["itl_p95"]
    assert itl_comp.passed is True
    assert itl_comp.relative_drift == 15.0
    assert res_itl.drift_exceeded is False

    # ITL p95 just outside: 20.0ms -> 23.02ms (+15.1%) -> FAIL
    verif_itl_outside = MetricSet(
        metric_version="1.0.0",
        run_id="run-v2",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=20.0,
        achieved_load_rps=20.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=70.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=10.0, p95=23.02),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
        request_throughput_rps=20.0,
        token_throughput_tps=200.0,
        error_rate=0.0,
    )
    res_itl_out = compare_metrics(orig, verif_itl_outside)
    itl_comp_out = res_itl_out.metric_comparisons["itl_p95"]
    assert itl_comp_out.passed is False
    assert itl_comp_out.relative_drift == 15.1
    assert res_itl_out.drift_exceeded is True

    # E2E p95 exact boundary: 200.0ms -> 230.0ms (+15.0%) -> PASS
    verif_e2e_exact = MetricSet(
        metric_version="1.0.0",
        run_id="run-v3",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=20.0,
        achieved_load_rps=20.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=70.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=230.0),
        request_throughput_rps=20.0,
        token_throughput_tps=200.0,
        error_rate=0.0,
    )
    res_e2e = compare_metrics(orig, verif_e2e_exact)
    e2e_comp = res_e2e.metric_comparisons["e2e_latency_p95"]
    assert e2e_comp.passed is True
    assert e2e_comp.relative_drift == 15.0
    assert res_e2e.drift_exceeded is False


