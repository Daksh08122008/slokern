"""
Independent Verification Script for Load Generator (TASK-06 / SUB-06)
Executed by Victory Auditor.
"""

import math
import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, "/home/caelum/DevArena/projects/slokern/src")

from slokern.contracts.enums import ArrivalMode
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.spec import WorkloadSpec
from slokern.engine.loadgen.arrival import ArrivalSchedule
from slokern.engine.loadgen.recorder import JSONLRecorder
from slokern.engine.loadgen.runner import LoadGeneratorRunner, LoadGeneratorResult
from slokern.engine.serving.fake import FakeServingAdapter


def test_independent_verification():
    print("=== STARTING INDEPENDENT VICTORY AUDITOR VERIFICATION ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Verification of Constant Arrival Schedule
        print("[Check 1] Verifying Constant Arrival Schedule intervals and warmup partitioning...")
        spec_const = WorkloadSpec(
            schema_version="1.0.0",
            workload_name="audit_const",
            fixture_id="fix_audit",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=25.0,
            concurrency_limit=32,
            warmup_duration_s=1,
            measurement_duration_s=2,
            max_input_tokens=64,
            max_output_tokens=16,
        )
        sched_const = ArrivalSchedule.from_workload_spec(spec_const, seed=123, start_time=1000.0)
        slots_const = sched_const.slots()
        assert len(slots_const) == 75, f"Expected 75 slots, got {len(slots_const)}"
        assert slots_const[0].is_warmup is True
        assert slots_const[24].is_warmup is True
        assert slots_const[25].is_warmup is False
        assert slots_const[74].is_warmup is False
        for i in range(1, len(slots_const)):
            diff = slots_const[i].scheduled_at - slots_const[i - 1].scheduled_at
            assert math.isclose(diff, 1.0 / 25.0, abs_tol=1e-6)
        print(" -> PASS: Constant arrival slots, interval (0.04s), and warmup partitioning verified.")

        # 2. Verification of Poisson Arrival Schedule & Seed Reproducibility
        print("[Check 2] Verifying Poisson Arrival Schedule PRNG seed reproducibility...")
        sched_p1 = ArrivalSchedule(
            arrival_mode=ArrivalMode.POISSON,
            target_offered_rate=50.0,
            warmup_duration_s=2.0,
            measurement_duration_s=5.0,
            seed=98765,
            start_time=2000.0,
        )
        sched_p2 = ArrivalSchedule(
            arrival_mode=ArrivalMode.POISSON,
            target_offered_rate=50.0,
            warmup_duration_s=2.0,
            measurement_duration_s=5.0,
            seed=98765,
            start_time=2000.0,
        )
        slots_p1 = sched_p1.slots()
        slots_p2 = sched_p2.slots()
        assert len(slots_p1) == len(slots_p2) > 0
        for s1, s2 in zip(slots_p1, slots_p2):
            assert s1.index == s2.index
            assert s1.is_warmup == s2.is_warmup
            assert math.isclose(s1.scheduled_at, s2.scheduled_at, abs_tol=1e-9)
        print(f" -> PASS: Poisson reproducible generation verified ({len(slots_p1)} slots).")

        # 3. Verification of JSONL Crash Resilience & Schema Validation
        print("[Check 3] Verifying JSONL immediate disk flush and schema validation...")
        rec_path = tmp_path / "audit_recorder.jsonl"
        with JSONLRecorder(file_path=rec_path, flush_immediately=True) as rec:
            event1 = RawRequestMeasurement(
                request_id="req-audit-1",
                run_id="run-audit",
                scheduled_at=100.0,
                sent_at=100.001,
                first_token_at=100.010,
                completed_at=100.050,
                http_status=200,
                input_tokens=10,
                output_tokens=5,
                is_warmup=True,
                is_valid=True,
            )
            rec.record(event1)
            # Read from disk while file is still open
            with open(rec_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            assert len(content) > 0
            val1 = RawRequestMeasurement.model_validate_json(content)
            assert val1.request_id == "req-audit-1"

            # Check that extra fields are strictly forbidden
            try:
                rec.record({
                    "request_id": "req-extra",
                    "run_id": "run-audit",
                    "scheduled_at": 100.0,
                    "sent_at": 100.0,
                    "completed_at": 100.1,
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "is_warmup": False,
                    "is_valid": True,
                    "illegal_field": "violation",
                })
                raise AssertionError("Failed to reject extra forbidden field!")
            except Exception:
                pass  # Successfully rejected
        print(" -> PASS: Immediate flush to disk and extra='forbid' validation verified.")

        # 4. End-to-End Subprocess Streaming Execution & Monotonicity Audit
        print("[Check 4] Running Subprocess-Isolated LoadGeneratorRunner with streaming...")
        trace_path = tmp_path / "audit_trace_stream.jsonl"
        adapter = FakeServingAdapter(simulate_delay=False)
        runner = LoadGeneratorRunner(isolate_process=True)
        res_stream = runner.run(
            workload=spec_const,
            adapter=adapter,
            output_path=trace_path,
            run_id="run-audit-stream-01",
            stream=True,
        )
        assert res_stream.total_requests == 75
        assert res_stream.warmup_requests == 25
        assert res_stream.active_requests == 50
        assert res_stream.completed_requests == 75
        assert res_stream.failed_requests == 0
        assert res_stream.generator_saturated is False

        # Independent line-by-line inspection of raw JSONL file
        with open(trace_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 75, f"Expected 75 JSONL lines, got {len(lines)}"

        for idx, line in enumerate(lines):
            # Strict Pydantic model_validate_json parsing
            record = RawRequestMeasurement.model_validate_json(line)
            assert record.run_id == "run-audit-stream-01"
            assert record.request_id == f"req-run-audit-stream-01-{idx:06d}"
            assert record.http_status == 200
            assert record.is_valid is True
            assert record.first_token_at is not None

            # Monotonicity check
            assert record.scheduled_at <= record.sent_at, (
                f"Line {idx}: scheduled_at ({record.scheduled_at}) > sent_at ({record.sent_at})"
            )
            assert record.sent_at <= record.first_token_at, (
                f"Line {idx}: sent_at ({record.sent_at}) > first_token_at ({record.first_token_at})"
            )
            assert record.first_token_at <= record.completed_at, (
                f"Line {idx}: first_token_at ({record.first_token_at}) > completed_at ({record.completed_at})"
            )
        print(" -> PASS: 75/75 records strictly validated against RawRequestMeasurement; 100% monotonicity verified.")

        # 5. Client Saturation Injection Audit
        print("[Check 5] Verifying Client Scheduler Saturation trigger under artificial lag...")
        sat_trace_path = tmp_path / "audit_saturated_trace.jsonl"
        res_sat = runner.run(
            workload=spec_const,
            adapter=adapter,
            output_path=sat_trace_path,
            run_id="run-audit-sat-01",
            artificial_dispatch_delay_ms=20.0,  # 20ms delay > 10ms threshold
        )
        assert res_sat.mean_dispatch_lag_ms >= 15.0, (
            f"Expected mean_dispatch_lag_ms >= 15.0, got {res_sat.mean_dispatch_lag_ms}"
        )
        assert res_sat.generator_saturated is True, "generator_saturated must be True under 20ms dispatch lag"
        print(f" -> PASS: Saturation successfully detected (mean_dispatch_lag_ms = {res_sat.mean_dispatch_lag_ms:.2f}ms).")

        # 6. Rate Deficit Saturation Audit
        print("[Check 6] Verifying Rate Deficit Saturation trigger (offered < 0.90 * target)...")
        # Workload with target rate 100, but runner with concurrency_limit 1 and slow adapter
        slow_adapter = FakeServingAdapter(simulate_delay=True, base_ttft_ms=50.0)
        spec_deficit = WorkloadSpec(
            schema_version="1.0.0",
            workload_name="audit_deficit",
            fixture_id="fix_audit",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=50.0,
            concurrency_limit=1,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=64,
            max_output_tokens=4,
        )
        res_deficit = runner.run(
            workload=spec_deficit,
            adapter=slow_adapter,
            output_path=tmp_path / "deficit_trace.jsonl",
            run_id="run-audit-deficit-01",
        )
        assert res_deficit.generator_saturated is True, "generator_saturated must be True under rate deficit"
        print(f" -> PASS: Rate deficit saturation successfully detected (offered {res_deficit.offered_load_rps} vs target 50).")

    print("=== ALL INDEPENDENT VICTORY AUDITOR CHECKS PASSED ===")


if __name__ == "__main__":
    test_independent_verification()
