"""
Purpose: Unit tests for engine/loadgen/arrival.
Owner: Rajdeep (Historical design: Adriraj)
"""

import math
import pytest

from slokern.contracts.enums import ArrivalMode
from slokern.contracts.spec import WorkloadSpec
from slokern.engine.loadgen.arrival import ArrivalSchedule, ArrivalSlot


def test_constant_arrival_slots_count_and_intervals():
    # 10 req/s, 1s warmup, 2s measurement -> 3s total -> 30 slots
    schedule = ArrivalSchedule(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        warmup_duration_s=1.0,
        measurement_duration_s=2.0,
        start_time=100.0,
    )
    slots = schedule.slots()
    assert len(slots) == 30

    # First slot at t=0 relative, scheduled_at=100.0
    assert slots[0].index == 0
    assert slots[0].scheduled_at == 100.0
    assert slots[0].is_warmup is True
    assert math.isclose(slots[0].offset_s, 0.0)

    # 10th slot at index 9, offset 0.9s -> warmup
    assert slots[9].index == 9
    assert math.isclose(slots[9].offset_s, 0.9)
    assert slots[9].is_warmup is True

    # 11th slot at index 10, offset 1.0s -> active measurement window
    assert slots[10].index == 10
    assert math.isclose(slots[10].offset_s, 1.0)
    assert slots[10].is_warmup is False

    # Last slot at index 29, offset 2.9s
    assert slots[29].index == 29
    assert math.isclose(slots[29].offset_s, 2.9)
    assert slots[29].is_warmup is False

    # Interval consistency: delta_t = 0.1
    for i in range(1, len(slots)):
        diff = slots[i].scheduled_at - slots[i - 1].scheduled_at
        assert math.isclose(diff, 0.1, abs_tol=1e-6)


def test_constant_arrival_zero_warmup():
    schedule = ArrivalSchedule(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=5.0,
        warmup_duration_s=0.0,
        measurement_duration_s=2.0,
        start_time=0.0,
    )
    slots = schedule.slots()
    assert len(slots) == 10
    assert all(not slot.is_warmup for slot in slots)


def test_constant_arrival_zero_measurement():
    schedule = ArrivalSchedule(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=5.0,
        warmup_duration_s=2.0,
        measurement_duration_s=0.0,
        start_time=0.0,
    )
    slots = schedule.slots()
    assert len(slots) == 10
    assert all(slot.is_warmup for slot in slots)


def test_constant_arrival_zero_total_duration():
    schedule = ArrivalSchedule(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        warmup_duration_s=0.0,
        measurement_duration_s=0.0,
    )
    assert schedule.slots() == []


def test_poisson_arrival_seed_reproducibility():
    sched1 = ArrivalSchedule(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=20.0,
        warmup_duration_s=2.0,
        measurement_duration_s=5.0,
        seed=12345,
        start_time=50.0,
    )
    sched2 = ArrivalSchedule(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=20.0,
        warmup_duration_s=2.0,
        measurement_duration_s=5.0,
        seed=12345,
        start_time=50.0,
    )
    slots1 = sched1.slots()
    slots2 = sched2.slots()

    assert len(slots1) > 0
    assert len(slots1) == len(slots2)
    for s1, s2 in zip(slots1, slots2):
        assert s1.index == s2.index
        assert s1.is_warmup == s2.is_warmup
        assert math.isclose(s1.scheduled_at, s2.scheduled_at, abs_tol=1e-9)
        assert math.isclose(s1.offset_s, s2.offset_s, abs_tol=1e-9)


def test_poisson_arrival_different_seeds():
    sched1 = ArrivalSchedule(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=20.0,
        warmup_duration_s=1.0,
        measurement_duration_s=2.0,
        seed=42,
    )
    sched2 = ArrivalSchedule(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=20.0,
        warmup_duration_s=1.0,
        measurement_duration_s=2.0,
        seed=999,
    )
    slots1 = sched1.slots()
    slots2 = sched2.slots()

    # Different seeds should produce different arrival offsets
    offsets1 = [s.offset_s for s in slots1]
    offsets2 = [s.offset_s for s in slots2]
    assert offsets1 != offsets2


def test_poisson_arrival_rate_approximation():
    # Over a long duration (e.g. 50s at 100 req/s = ~5000 requests),
    # sample mean rate should be within 5% of target rate
    rate = 100.0
    duration = 50.0
    sched = ArrivalSchedule(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=rate,
        warmup_duration_s=10.0,
        measurement_duration_s=duration,
        seed=42,
    )
    slots = sched.slots()
    active_slots = [s for s in slots if not s.is_warmup]
    observed_rate = len(active_slots) / duration

    # 3 standard deviations for Poisson count with mean 5000 is ~3*sqrt(5000) ~= 212 (~4.2%)
    assert abs(observed_rate - rate) / rate < 0.05


def test_poisson_warmup_partition():
    sched = ArrivalSchedule(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=50.0,
        warmup_duration_s=2.0,
        measurement_duration_s=3.0,
        seed=42,
        start_time=10.0,
    )
    slots = sched.slots()
    for s in slots:
        if s.offset_s < 2.0:
            assert s.is_warmup is True
        else:
            assert s.is_warmup is False


def test_from_workload_spec():
    spec = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="test_workload",
        fixture_id="fix_123",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=15.0,
        concurrency_limit=32,
        warmup_duration_s=2,
        measurement_duration_s=4,
        max_input_tokens=128,
        max_output_tokens=64,
    )
    sched = ArrivalSchedule.from_workload_spec(spec, seed=42, start_time=200.0)
    assert sched.arrival_mode == ArrivalMode.CONSTANT
    assert sched.target_offered_rate == 15.0
    assert sched.warmup_duration_s == 2.0
    assert sched.measurement_duration_s == 4.0
    assert sched.start_time == 200.0
    slots = sched.slots()
    assert len(slots) == 15 * 6


def test_invalid_parameters_raise():
    with pytest.raises(ValueError, match="target_offered_rate must be positive"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=0.0)

    with pytest.raises(ValueError, match="target_offered_rate must be positive"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=-5.0)

    with pytest.raises(ValueError, match="warmup_duration_s must be non-negative"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=10.0, warmup_duration_s=-1.0)

    with pytest.raises(ValueError, match="measurement_duration_s must be non-negative"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=10.0, measurement_duration_s=-1.0)

    with pytest.raises(ValueError, match="Unsupported arrival mode"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CLOSED, target_offered_rate=10.0)

    with pytest.raises(ValueError, match="Unsupported arrival mode"):
        ArrivalSchedule(arrival_mode="unknown_mode", target_offered_rate=10.0)


def test_non_finite_parameters_raise():
    """Verifies that NaN and Inf parameters are rejected with ValueError rather than hanging in infinite loops."""
    with pytest.raises(ValueError, match="target_offered_rate must be positive and finite"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=float("inf"))

    with pytest.raises(ValueError, match="target_offered_rate must be positive and finite"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=float("nan"))

    with pytest.raises(ValueError, match="warmup_duration_s must be non-negative and finite"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=10.0, warmup_duration_s=float("nan"))

    with pytest.raises(ValueError, match="measurement_duration_s must be non-negative and finite"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=10.0, measurement_duration_s=float("inf"))

    with pytest.raises(ValueError, match="start_time must be finite"):
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=10.0, start_time=float("nan"))

    sched = ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=10.0, measurement_duration_s=1.0)
    with pytest.raises(ValueError, match="start_time must be finite"):
        list(sched.generate(start_time=float("inf")))
