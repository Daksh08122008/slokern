"""
Independent Victory Auditor Verification Suite for SLOKern SUB-06 / TASK-06.
Executes independent checks against all requirements in ORIGINAL_REQUEST.md.
"""

import asyncio
import math
import os
import tempfile
import time
from pathlib import Path
from pydantic import ValidationError

from slokern.contracts.enums import ArrivalMode
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.spec import WorkloadSpec
from slokern.engine.loadgen.arrival import ArrivalSchedule, ArrivalSlot
from slokern.engine.loadgen.recorder import JSONLRecorder, RecorderStats
from slokern.engine.loadgen.runner import LoadGeneratorRunner, LoadGeneratorResult
from slokern.engine.serving.fake import FakeServingAdapter


def test_independent_arrival_schedules():
    print("[1/6] Auditing ArrivalSchedule (Constant, Poisson, Warmup, PRNG)...")
    # Constant
    rate = 25.0
    warmup = 1.0
    meas = 2.0
    sched = ArrivalSchedule(
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=rate,
        warmup_duration_s=warmup,
        measurement_duration_s=meas,
        start_time=1000.0,
    )
    slots = sched.slots()
    assert len(slots) == 75, f"Expected 75 slots, got {len(slots)}"
    assert slots[0].scheduled_at == 1000.0
    assert slots[0].is_warmup is True
    assert slots[24].is_warmup is True
    assert slots[25].is_warmup is False
    assert slots[-1].is_warmup is False
    # Check exact interval
    for i in range(1, len(slots)):
        dt = slots[i].scheduled_at - slots[i-1].scheduled_at
        assert math.isclose(dt, 1.0 / rate, abs_tol=1e-7), f"Slot {i} interval discrepancy: {dt}"

    # Poisson reproducibility
    p1 = ArrivalSchedule(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=50.0,
        warmup_duration_s=1.0,
        measurement_duration_s=3.0,
        seed=98765,
        start_time=500.0,
    )
    p2 = ArrivalSchedule(
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=50.0,
        warmup_duration_s=1.0,
        measurement_duration_s=3.0,
        seed=98765,
        start_time=500.0,
    )
    s1 = p1.slots()
    s2 = p2.slots()
    assert len(s1) == len(s2) > 0
    for a, b in zip(s1, s2):
        assert math.isclose(a.scheduled_at, b.scheduled_at, abs_tol=1e-9)
        assert a.is_warmup == b.is_warmup

    # Non-finite rejection
    try:
        ArrivalSchedule(arrival_mode=ArrivalMode.CONSTANT, target_offered_rate=float("nan"))
        assert False, "Should have raised ValueError on NaN rate"
    except ValueError:
        pass

    print(" -> PASS: ArrivalSchedule verified.")


def test_independent_recorder_integrity():
    print("[2/6] Auditing JSONLRecorder (Disk flush, Pydantic extra=forbid, Running stats)...")
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_file = Path(tmpdir) / "recorder_audit.jsonl"
        rec = JSONLRecorder(file_path=trace_file, flush_immediately=True)

        # 1. Warmup record
        w_event = RawRequestMeasurement(
            request_id="w-01",
            run_id="audit-run",
            scheduled_at=100.0,
            sent_at=100.002,
            first_token_at=100.010,
            completed_at=100.050,
            http_status=200,
            input_tokens=50,
            output_tokens=10,
            is_warmup=True,
            is_valid=True,
        )
        rec.record(w_event)

        # Verify immediate disk flush before closing
        content_on_disk = trace_file.read_text(encoding="utf-8").strip()
        assert len(content_on_disk) > 0, "File on disk is empty before close; flush_immediately failed"
        read_back = RawRequestMeasurement.model_validate_json(content_on_disk)
        assert read_back.request_id == "w-01"

        # 2. Active valid record
        a_event = RawRequestMeasurement(
            request_id="a-01",
            run_id="audit-run",
            scheduled_at=101.0,
            sent_at=101.004,
            first_token_at=101.015,
            completed_at=101.080,
            http_status=200,
            input_tokens=60,
            output_tokens=12,
            is_warmup=False,
            is_valid=True,
        )
        rec.record(a_event)

        # 3. Active error record
        e_event = RawRequestMeasurement(
            request_id="a-02",
            run_id="audit-run",
            scheduled_at=102.0,
            sent_at=102.006,
            first_token_at=None,
            completed_at=102.020,
            http_status=500,
            input_tokens=70,
            output_tokens=0,
            is_warmup=False,
            is_valid=False,
            error_type="simulated_failure",
        )
        rec.record(e_event)

        # Verify extra="forbid" rejection
        try:
            rec.record({
                "request_id": "bad-01",
                "run_id": "audit-run",
                "scheduled_at": 103.0,
                "sent_at": 103.001,
                "completed_at": 103.010,
                "input_tokens": 10,
                "output_tokens": 5,
                "is_warmup": False,
                "is_valid": True,
                "unauthorized_field": "illegal",
            })
            assert False, "Should have rejected extra='forbid' fields"
        except ValidationError:
            pass

        stats = rec.get_stats()
        assert stats.total_count == 3
        assert stats.warmup_count == 1
        assert stats.active_count == 2
        assert stats.valid_count == 2
        assert stats.active_valid_count == 1
        assert stats.error_count == 1
        assert stats.active_error_count == 1
        # Lags: w1: 2ms, a1: 4ms, a2: 6ms
        assert math.isclose(stats.mean_dispatch_lag_ms, 4.0, abs_tol=1e-3)
        assert math.isclose(stats.active_mean_dispatch_lag_ms, 5.0, abs_tol=1e-3)
        assert stats.max_dispatch_lag_ms == 6.0
        assert stats.min_dispatch_lag_ms == 2.0

        rec.close()

    print(" -> PASS: JSONLRecorder verified.")


def test_independent_subprocess_dispatch_and_monotonicity():
    print("[3/6] Auditing Subprocess-Isolated Dispatch Runner & Monotonicity Invariants...")
    workload = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="audit_isolated_workload",
        fixture_id="audit_fix",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=20.0,
        concurrency_limit=8,
        warmup_duration_s=1,
        measurement_duration_s=2,
        max_input_tokens=64,
        max_output_tokens=8,
    )
    adapter = FakeServingAdapter(simulate_delay=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "subprocess_audit_trace.jsonl"
        runner = LoadGeneratorRunner(isolate_process=True)
        res = runner.run(
            workload=workload,
            adapter=adapter,
            output_path=trace_path,
            run_id="audit-sp-01",
            stream=True,
        )

        assert res.total_requests == 60  # 20 rps * 3s
        assert res.warmup_requests == 20
        assert res.active_requests == 40
        assert res.completed_requests == 60
        assert res.failed_requests == 0
        assert res.generator_saturated is False

        # Read back all records and verify strict monotonicity
        records = JSONLRecorder.read_records(trace_path)
        assert len(records) == 60
        for i, rec in enumerate(records):
            assert rec.run_id == "audit-sp-01"
            assert rec.http_status == 200
            assert rec.is_valid is True
            assert rec.first_token_at is not None
            # Monotonicity: scheduled_at <= sent_at <= first_token_at <= completed_at
            assert rec.scheduled_at <= rec.sent_at, f"Record {i}: scheduled_at ({rec.scheduled_at}) > sent_at ({rec.sent_at})"
            assert rec.sent_at <= rec.first_token_at, f"Record {i}: sent_at ({rec.sent_at}) > first_token_at ({rec.first_token_at})"
            assert rec.first_token_at <= rec.completed_at, f"Record {i}: first_token_at ({rec.first_token_at}) > completed_at ({rec.completed_at})"

    print(" -> PASS: Subprocess runner and timestamp monotonicity verified.")


def test_independent_saturation_detection():
    print("[4/6] Auditing Scheduler & Queue Saturation Detection Logic...")
    workload = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="audit_sat_workload",
        fixture_id="audit_sat",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        concurrency_limit=16,
        warmup_duration_s=0,
        measurement_duration_s=1,
        max_input_tokens=64,
        max_output_tokens=4,
    )
    adapter = FakeServingAdapter(simulate_delay=False)

    # Condition 1: artificial dispatch delay > 10ms -> generator_saturated = True
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "sat_skew_trace.jsonl"
        runner = LoadGeneratorRunner(isolate_process=False)
        res_skew = runner.run(
            workload=workload,
            adapter=adapter,
            output_path=trace_path,
            artificial_dispatch_delay_ms=16.0,
        )
        assert res_skew.mean_dispatch_lag_ms >= 12.0
        assert res_skew.generator_saturated is True, "Failed to flag generator_saturated on skew > 10ms"

    # Condition 2: rate deficit (offered_load_rps < 0.90 * target) -> generator_saturated = True
    # Zero duration workload yields offered_load_rps = 0 < 0.90 * 10
    workload_zero = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="audit_zero_workload",
        fixture_id="audit_zero",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        concurrency_limit=16,
        warmup_duration_s=0,
        measurement_duration_s=0,
        max_input_tokens=64,
        max_output_tokens=4,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "sat_deficit_trace.jsonl"
        runner = LoadGeneratorRunner(isolate_process=False)
        res_deficit = runner.run(
            workload=workload_zero,
            adapter=adapter,
            output_path=trace_path,
        )
        assert res_deficit.generator_saturated is True, "Failed to flag generator_saturated on rate deficit"

    # Healthy run -> generator_saturated = False
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "healthy_trace.jsonl"
        runner = LoadGeneratorRunner(isolate_process=False)
        res_healthy = runner.run(
            workload=workload,
            adapter=adapter,
            output_path=trace_path,
            artificial_dispatch_delay_ms=0.0,
        )
        assert res_healthy.mean_dispatch_lag_ms < 10.0
        assert res_healthy.generator_saturated is False, "Healthy run should not flag generator_saturated"

    print(" -> PASS: Saturation detection logic verified.")


def test_independent_error_and_cancellation_resilience():
    print("[5/6] Auditing Subprocess Error Resilience and Task Cancellation...")
    workload = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="audit_error_workload",
        fixture_id="audit_err",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        concurrency_limit=4,
        warmup_duration_s=0,
        measurement_duration_s=1,
        max_input_tokens=64,
        max_output_tokens=4,
    )
    adapter = FakeServingAdapter(simulate_delay=False)
    adapter.inject_oom(True)

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "oom_trace.jsonl"
        runner = LoadGeneratorRunner(isolate_process=True)
        res = runner.run(
            workload=workload,
            adapter=adapter,
            output_path=trace_path,
            run_id="audit-oom",
        )
        assert res.failed_requests == 10
        assert res.completed_requests == 0
        records = JSONLRecorder.read_records(trace_path)
        assert len(records) == 10
        for r in records:
            assert r.is_valid is False
            assert r.error_type == "cuda_out_of_memory"
            assert r.http_status == 500
            assert r.scheduled_at <= r.sent_at <= r.completed_at

    # Cancellation test
    async def _test_cancel():
        runner = LoadGeneratorRunner(isolate_process=True)
        slow_workload = WorkloadSpec(
            schema_version="1.0.0",
            workload_name="audit_cancel_workload",
            fixture_id="audit_cancel",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=2.0,
            concurrency_limit=4,
            warmup_duration_s=0,
            measurement_duration_s=4,
            max_input_tokens=64,
            max_output_tokens=4,
        )
        slow_adapter = FakeServingAdapter(simulate_delay=True, base_ttft_ms=500.0)
        with tempfile.TemporaryDirectory() as c_tmp:
            c_trace = Path(c_tmp) / "cancel.jsonl"
            task = asyncio.create_task(
                runner.arun(
                    workload=slow_workload,
                    adapter=slow_adapter,
                    output_path=c_trace,
                )
            )
            await asyncio.sleep(0.08)
            task.cancel()
            try:
                await task
                assert False, "Should have raised CancelledError"
            except asyncio.CancelledError:
                pass
            assert runner._current_proc is None or not runner._current_proc.is_alive()

    asyncio.run(_test_cancel())
    print(" -> PASS: Error resilience and cancellation verified.")


def test_independent_metrics_engine_integration():
    print("[6/6] Auditing Downstream Integration with MetricEngine...")
    from slokern.core.metrics.aggregate import calculate_metrics

    workload = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="audit_e2e_workload",
        fixture_id="audit_e2e",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=20.0,
        concurrency_limit=16,
        warmup_duration_s=1,
        measurement_duration_s=2,
        max_input_tokens=64,
        max_output_tokens=10,
    )
    adapter = FakeServingAdapter(simulate_delay=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "e2e_trace.jsonl"
        runner = LoadGeneratorRunner(isolate_process=True)
        runner.run(
            workload=workload,
            adapter=adapter,
            output_path=trace_path,
            run_id="audit-e2e",
            stream=True,
        )

        metrics = calculate_metrics(
            records=trace_path,
            run_id="audit-e2e",
            target_offered_rate=20.0,
            measurement_duration_s=2.0,
        )

        assert metrics.run_id == "audit-e2e"
        assert metrics.sample_count == 40
        assert metrics.failed_request_count == 0
        assert metrics.generator_saturated is False
        assert metrics.error_rate == 0.0
        assert math.isclose(metrics.request_throughput_rps, 20.0, rel_tol=0.02)
        assert math.isclose(metrics.achieved_load_rps, 20.0, rel_tol=0.02)
        assert math.isclose(metrics.offered_load_rps, 20.0, rel_tol=0.02)
        assert metrics.ttft_ms.mean is not None and metrics.ttft_ms.mean >= 0.0
        assert metrics.itl_ms.mean is not None and metrics.itl_ms.mean >= 0.0

    print(" -> PASS: MetricEngine integration verified.")


if __name__ == "__main__":
    test_independent_arrival_schedules()
    test_independent_recorder_integrity()
    test_independent_subprocess_dispatch_and_monotonicity()
    test_independent_saturation_detection()
    test_independent_error_and_cancellation_resilience()
    test_independent_metrics_engine_integration()
    print("\nALL 6 INDEPENDENT AUDITOR VERIFICATION CHECKS PASSED PERFECTLY!")
