"""
Purpose: Subprocess-isolated load generator runner producing request-level microsecond timings.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/experiment-methodology.md Section 2-4 and AGENTS.md Section 1, 3, 4
"""

import asyncio
import multiprocessing as mp
from multiprocessing.connection import Connection
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.spec import WorkloadSpec
from slokern.engine.loadgen.arrival import ArrivalSchedule, ArrivalSlot
from slokern.engine.loadgen.recorder import JSONLRecorder
from slokern.engine.serving.base import BaseServingAdapter, ServingRequest, ServingResponse


class LoadGeneratorResult(BaseModel):
    """Execution summary and saturation diagnostics from a completed load generator run."""
    model_config = ConfigDict(extra="forbid")

    total_requests: int = Field(..., description="Total requests scheduled and recorded")
    warmup_requests: int = Field(..., description="Warm-up requests count")
    active_requests: int = Field(..., description="Active window requests count")
    completed_requests: int = Field(..., description="Successfully completed requests count")
    failed_requests: int = Field(..., description="Failed requests count")

    target_offered_rate: float = Field(..., description="Intended arrival rate (req/s)")
    offered_load_rps: float = Field(..., description="Actual rate at which client scheduled requests")
    achieved_load_rps: float = Field(..., description="Delivered valid throughput over measurement window")
    generator_saturated: bool = Field(..., description="Flag indicating if load generator experienced scheduler saturation")

    mean_dispatch_lag_ms: float = Field(..., description="Mean delay between scheduled time and socket write start")
    max_dispatch_lag_ms: float = Field(..., description="Maximum delay between scheduled time and socket write start")

    output_path: str = Field(..., description="Path to generated .jsonl trace file")
    error: Optional[str] = Field(None, description="Error detail if execution encountered an unhandled exception")

    @property
    def mean_dispatch_skew_ms(self) -> float:
        """Alias for mean_dispatch_lag_ms conforming to documentation nomenclature."""
        return self.mean_dispatch_lag_ms

    @property
    def max_dispatch_skew_ms(self) -> float:
        """Alias for max_dispatch_lag_ms conforming to documentation nomenclature."""
        return self.max_dispatch_lag_ms


async def _async_dispatch_loop(
    workload: WorkloadSpec,
    adapter: BaseServingAdapter,
    output_path: str,
    run_id: str,
    seed: Optional[int],
    stream: bool,
    prompts: Optional[List[str]],
    artificial_dispatch_delay_ms: float,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> LoadGeneratorResult:
    """Core asynchronous dispatch and measurement loop."""
    prompt_list = prompts if prompts else [
        f"Benchmark prompt for {workload.workload_name} request execution under SLOKern loadgen."
    ]

    concurrency_limit = max(1, workload.concurrency_limit)
    semaphore = asyncio.Semaphore(concurrency_limit)
    recorder = JSONLRecorder(file_path=output_path, flush_immediately=True)

    t_start = time.time()
    schedule = ArrivalSchedule.from_workload_spec(workload, seed=seed, start_time=t_start)
    slots = list(schedule)

    async def _dispatch_single_request(slot: ArrivalSlot) -> None:
        async with semaphore:
            # Client-side delay injection for saturation testing
            if artificial_dispatch_delay_ms > 0:
                await asyncio.sleep(artificial_dispatch_delay_ms / 1000.0)

            # Monotonicity protection: socket write timestamp must never precede scheduled time
            sent_at = max(time.time(), slot.scheduled_at)

            prompt = prompt_list[slot.index % len(prompt_list)]
            req_id = f"req-{run_id}-{slot.index:06d}"
            req = ServingRequest(
                prompt=prompt,
                max_tokens=workload.max_output_tokens,
                request_id=req_id,
                run_id=run_id,
                stream=stream,
            )

            input_tokens = max(1, int(len(prompt.split()) * 1.3))

            if stream:
                first_token_at: Optional[float] = None
                tokens_received = 0
                itl_observations: List[float] = []
                prev_token_time: Optional[float] = None
                status_code = 200
                err_type: Optional[str] = None
                err_msg: Optional[str] = None

                try:
                    async for chunk in adapter.astream_generate(req):
                        chunk_time = time.time()
                        if chunk.error:
                            err_msg = chunk.error
                            err_type = (
                                chunk.metadata.get("failure_injected")
                                or chunk.metadata.get("error_type")
                                or "streaming_error"
                            )
                            status_code = chunk.metadata.get("status_code", 500)
                            break

                        if first_token_at is None:
                            if chunk.latency_ms > 0 and (not getattr(adapter, "simulate_delay", True)):
                                first_token_at = sent_at + (chunk.latency_ms / 1000.0)
                            else:
                                first_token_at = max(chunk_time, sent_at)
                            prev_token_time = chunk_time
                        else:
                            delta_ms = max(0.0, (chunk_time - prev_token_time) * 1000.0)
                            # Preserve synthetic latencies when simulating delay is disabled in tests
                            if chunk.latency_ms > 0 and (not getattr(adapter, "simulate_delay", True)):
                                itl_observations.append(chunk.latency_ms)
                            else:
                                itl_observations.append(round(delta_ms, 3))
                            prev_token_time = chunk_time

                        tokens_received += 1
                except Exception as exc:
                    err_msg = str(exc)
                    err_type = type(exc).__name__
                    status_code = 500

                now_complete = time.time()
                if (not getattr(adapter, "simulate_delay", True)) and itl_observations and first_token_at is not None:
                    completed_at = first_token_at + (sum(itl_observations) / 1000.0)
                else:
                    completed_at = max(now_complete, first_token_at if first_token_at is not None else sent_at)
                is_valid = (status_code == 200 and err_type is None and err_msg is None)

                # Monotonicity verification invariant
                if slot.scheduled_at > sent_at:
                    raise AssertionError(f"Monotonicity violation: scheduled_at ({slot.scheduled_at}) > sent_at ({sent_at})")
                if first_token_at is not None:
                    if not (sent_at <= first_token_at <= completed_at):
                        raise AssertionError(
                            f"Monotonicity violation: sent_at ({sent_at}) <= first_token_at ({first_token_at}) <= completed_at ({completed_at})"
                        )
                else:
                    if sent_at > completed_at:
                        raise AssertionError(f"Monotonicity violation: sent_at ({sent_at}) > completed_at ({completed_at})")

                measurement = RawRequestMeasurement(
                    request_id=req_id,
                    run_id=run_id,
                    scheduled_at=slot.scheduled_at,
                    sent_at=sent_at,
                    first_token_at=first_token_at,
                    completed_at=completed_at,
                    http_status=status_code,
                    input_tokens=input_tokens,
                    output_tokens=tokens_received,
                    itl_observations_ms=itl_observations if itl_observations else None,
                    error_type=err_type,
                    is_warmup=slot.is_warmup,
                    is_valid=is_valid,
                )
            else:
                try:
                    response = await adapter.agenerate(req)
                except Exception as exc:
                    response = ServingResponse(
                        request_id=req_id,
                        run_id=run_id,
                        text="",
                        input_tokens=input_tokens,
                        output_tokens=0,
                        first_token_latency_ms=None,
                        itl_observations_ms=[],
                        total_latency_ms=1.0,
                        status_code=500,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )

                measurement = response.to_raw_measurement(
                    scheduled_at=slot.scheduled_at,
                    sent_at=sent_at,
                    is_warmup=slot.is_warmup,
                )

                # Ensure monotonicity on non-streaming path
                if measurement.first_token_at is not None:
                    if not (measurement.scheduled_at <= measurement.sent_at <= measurement.first_token_at <= measurement.completed_at):
                        raise AssertionError(
                            f"Monotonicity violation: scheduled_at ({measurement.scheduled_at}) <= sent_at ({measurement.sent_at}) <= first_token_at ({measurement.first_token_at}) <= completed_at ({measurement.completed_at})"
                        )
                else:
                    if not (measurement.scheduled_at <= measurement.sent_at <= measurement.completed_at):
                        raise AssertionError(
                            f"Monotonicity violation: scheduled_at ({measurement.scheduled_at}) <= sent_at ({measurement.sent_at}) <= completed_at ({measurement.completed_at})"
                        )

            recorder.record(measurement)

    # Open-loop dispatch schedule
    tasks: List[asyncio.Task] = []
    task_error: Optional[str] = None
    try:
        for slot in slots:
            if is_cancelled is not None and is_cancelled():
                break
            now = time.time()
            wait_time = slot.scheduled_at - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            if is_cancelled is not None and is_cancelled():
                break

            task = asyncio.create_task(_dispatch_single_request(slot))
            tasks.append(task)

        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in task_results:
                if isinstance(res, BaseException):
                    if task_error is None:
                        task_error = f"{type(res).__name__}: {res}"
    finally:
        if tasks:
            pending = [t for t in tasks if not t.done()]
            if pending:
                for t in pending:
                    t.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
        recorder.close()

    stats = recorder.get_stats()

    # Load metrics calculation over the active measurement window
    active_duration_s = float(workload.measurement_duration_s)
    if active_duration_s > 0:
        offered_load_rps = round(stats.active_count / active_duration_s, 4)
        achieved_load_rps = round(stats.active_valid_count / active_duration_s, 4)
        mean_dispatch_lag_ms = stats.active_mean_dispatch_lag_ms
        max_dispatch_lag_ms = stats.active_max_dispatch_lag_ms
    else:
        warmup_dur = float(workload.warmup_duration_s) if workload.warmup_duration_s > 0 else 1.0
        offered_load_rps = round(stats.total_count / warmup_dur, 4)
        achieved_load_rps = round(stats.valid_count / warmup_dur, 4)
        mean_dispatch_lag_ms = stats.mean_dispatch_lag_ms
        max_dispatch_lag_ms = stats.max_dispatch_lag_ms

    target_rate = float(workload.target_offered_rate)
    rate_deficit = (target_rate > 0) and (offered_load_rps < 0.90 * target_rate)
    skew_exceeded = mean_dispatch_lag_ms > 10.0
    generator_saturated = bool(skew_exceeded or rate_deficit)

    return LoadGeneratorResult(
        total_requests=stats.total_count,
        warmup_requests=stats.warmup_count,
        active_requests=stats.active_count,
        completed_requests=stats.valid_count,
        failed_requests=stats.error_count,
        target_offered_rate=target_rate,
        offered_load_rps=offered_load_rps,
        achieved_load_rps=achieved_load_rps,
        generator_saturated=generator_saturated,
        mean_dispatch_lag_ms=mean_dispatch_lag_ms,
        max_dispatch_lag_ms=max_dispatch_lag_ms,
        output_path=output_path,
        error=task_error,
    )



def _sync_dispatch_loop(
    workload: WorkloadSpec,
    adapter: BaseServingAdapter,
    output_path: str,
    run_id: str,
    seed: Optional[int],
    stream: bool,
    prompts: Optional[List[str]],
    artificial_dispatch_delay_ms: float,
    is_cancelled: Optional[Callable[[], bool]] = None,
    timeout: Optional[float] = None,
) -> LoadGeneratorResult:
    """Synchronous open-loop dispatch fallback for environments where loopback socketpair is restricted."""
    prompt_list = prompts if prompts else [
        f"Benchmark prompt for {workload.workload_name} request execution under SLOKern loadgen."
    ]

    recorder = JSONLRecorder(file_path=output_path, flush_immediately=True)
    t_start = time.time()
    schedule = ArrivalSchedule.from_workload_spec(workload, seed=seed, start_time=t_start)
    slots = list(schedule)
    task_error: Optional[str] = None

    try:
        for slot in slots:
            if is_cancelled is not None and is_cancelled():
                break
            now = time.time()
            if timeout is not None and (now - t_start) >= timeout:
                raise TimeoutError(f"In-process load generation timed out after {timeout:.3f}s")
            wait_time = slot.scheduled_at - now
            if wait_time > 0:
                if timeout is not None and (now - t_start + wait_time) >= timeout:
                    time.sleep(max(0.0, timeout - (now - t_start)))
                    raise TimeoutError(f"In-process load generation timed out after {timeout:.3f}s")
                time.sleep(wait_time)
            if is_cancelled is not None and is_cancelled():
                break

            if artificial_dispatch_delay_ms > 0:
                time.sleep(artificial_dispatch_delay_ms / 1000.0)

            sent_at = max(time.time(), slot.scheduled_at)
            prompt = prompt_list[slot.index % len(prompt_list)]
            req_id = f"req-{run_id}-{slot.index:06d}"
            req = ServingRequest(
                prompt=prompt,
                max_tokens=workload.max_output_tokens,
                request_id=req_id,
                run_id=run_id,
                stream=stream,
            )
            input_tokens = max(1, int(len(prompt.split()) * 1.3))

            if stream:
                first_token_at: Optional[float] = None
                tokens_received = 0
                itl_observations: List[float] = []
                prev_token_time: Optional[float] = None
                status_code = 200
                err_type: Optional[str] = None
                err_msg: Optional[str] = None

                try:
                    for chunk in adapter.stream_generate(req):
                        chunk_time = time.time()
                        if chunk.error:
                            err_msg = chunk.error
                            err_type = (
                                chunk.metadata.get("failure_injected")
                                or chunk.metadata.get("error_type")
                                or "streaming_error"
                            )
                            status_code = chunk.metadata.get("status_code", 500)
                            break
                        if first_token_at is None:
                            if chunk.latency_ms > 0 and (not getattr(adapter, "simulate_delay", True)):
                                first_token_at = sent_at + (chunk.latency_ms / 1000.0)
                            else:
                                first_token_at = max(chunk_time, sent_at)
                            prev_token_time = chunk_time
                        else:
                            delta_ms = max(0.0, (chunk_time - prev_token_time) * 1000.0)
                            if chunk.latency_ms > 0 and (not getattr(adapter, "simulate_delay", True)):
                                itl_observations.append(chunk.latency_ms)
                            else:
                                itl_observations.append(round(delta_ms, 3))
                            prev_token_time = chunk_time
                        tokens_received += 1
                except Exception as exc:
                    err_msg = str(exc)
                    err_type = type(exc).__name__
                    status_code = 500

                now_complete = time.time()
                if (not getattr(adapter, "simulate_delay", True)) and itl_observations and first_token_at is not None:
                    completed_at = first_token_at + (sum(itl_observations) / 1000.0)
                else:
                    completed_at = max(now_complete, first_token_at if first_token_at is not None else sent_at)
                is_valid = (status_code == 200 and err_type is None and err_msg is None)

                if slot.scheduled_at > sent_at:
                    raise AssertionError(f"Monotonicity violation: scheduled_at ({slot.scheduled_at}) > sent_at ({sent_at})")
                if first_token_at is not None:
                    if not (sent_at <= first_token_at <= completed_at):
                        raise AssertionError(
                            f"Monotonicity violation: sent_at ({sent_at}) <= first_token_at ({first_token_at}) <= completed_at ({completed_at})"
                        )
                else:
                    if sent_at > completed_at:
                        raise AssertionError(f"Monotonicity violation: sent_at ({sent_at}) > completed_at ({completed_at})")

                measurement = RawRequestMeasurement(
                    request_id=req_id,
                    run_id=run_id,
                    scheduled_at=slot.scheduled_at,
                    sent_at=sent_at,
                    first_token_at=first_token_at,
                    completed_at=completed_at,
                    http_status=status_code,
                    input_tokens=input_tokens,
                    output_tokens=tokens_received,
                    itl_observations_ms=itl_observations if itl_observations else None,
                    error_type=err_type,
                    is_warmup=slot.is_warmup,
                    is_valid=is_valid,
                )
            else:
                try:
                    response = adapter.generate(req)
                except Exception as exc:
                    response = ServingResponse(
                        request_id=req_id,
                        run_id=run_id,
                        text="",
                        input_tokens=input_tokens,
                        output_tokens=0,
                        first_token_latency_ms=None,
                        itl_observations_ms=[],
                        total_latency_ms=1.0,
                        status_code=500,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
                measurement = response.to_raw_measurement(
                    scheduled_at=slot.scheduled_at,
                    sent_at=sent_at,
                    is_warmup=slot.is_warmup,
                )
                if measurement.first_token_at is not None:
                    if not (measurement.scheduled_at <= measurement.sent_at <= measurement.first_token_at <= measurement.completed_at):
                        raise AssertionError("Monotonicity violation on non-streaming path")
                else:
                    if not (measurement.scheduled_at <= measurement.sent_at <= measurement.completed_at):
                        raise AssertionError("Monotonicity violation on non-streaming path")

            recorder.record(measurement)
    except TimeoutError:
        raise
    except Exception as exc:
        if task_error is None:
            task_error = f"{type(exc).__name__}: {exc}"
    finally:
        recorder.close()

    stats = recorder.get_stats()
    active_duration_s = float(workload.measurement_duration_s)
    if active_duration_s > 0:
        offered_load_rps = round(stats.active_count / active_duration_s, 4)
        achieved_load_rps = round(stats.active_valid_count / active_duration_s, 4)
        mean_dispatch_lag_ms = stats.active_mean_dispatch_lag_ms
        max_dispatch_lag_ms = stats.active_max_dispatch_lag_ms
    else:
        warmup_dur = float(workload.warmup_duration_s) if workload.warmup_duration_s > 0 else 1.0
        offered_load_rps = round(stats.total_count / warmup_dur, 4)
        achieved_load_rps = round(stats.valid_count / warmup_dur, 4)
        mean_dispatch_lag_ms = stats.mean_dispatch_lag_ms
        max_dispatch_lag_ms = stats.max_dispatch_lag_ms

    target_rate = float(workload.target_offered_rate)
    rate_deficit = (target_rate > 0) and (offered_load_rps < 0.90 * target_rate)
    skew_exceeded = mean_dispatch_lag_ms > 10.0
    generator_saturated = bool(skew_exceeded or rate_deficit)

    return LoadGeneratorResult(
        total_requests=stats.total_count,
        warmup_requests=stats.warmup_count,
        active_requests=stats.active_count,
        completed_requests=stats.valid_count,
        failed_requests=stats.error_count,
        target_offered_rate=target_rate,
        offered_load_rps=offered_load_rps,
        achieved_load_rps=achieved_load_rps,
        generator_saturated=generator_saturated,
        mean_dispatch_lag_ms=mean_dispatch_lag_ms,
        max_dispatch_lag_ms=max_dispatch_lag_ms,
        output_path=output_path,
        error=task_error,
    )


def _subprocess_entrypoint(
    conn: Connection,
    workload: WorkloadSpec,
    adapter: BaseServingAdapter,
    output_path: str,
    run_id: str,
    seed: Optional[int],
    stream: bool,
    prompts: Optional[List[str]],
    artificial_dispatch_delay_ms: float,
) -> None:
    """Entrypoint executing inside the isolated child process."""
    try:
        result = asyncio.run(
            _async_dispatch_loop(
                workload=workload,
                adapter=adapter,
                output_path=output_path,
                run_id=run_id,
                seed=seed,
                stream=stream,
                prompts=prompts,
                artificial_dispatch_delay_ms=artificial_dispatch_delay_ms,
            )
        )
        conn.send({"success": True, "result": result.model_dump()})
    except BaseException as exc:
        try:
            conn.send({"success": False, "error": str(exc), "error_type": type(exc).__name__})
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


class LoadGeneratorRunner:
    """
    Subprocess-isolated load generator runner.
    Spawns an isolated Python process to avoid GC/GIL interference with benchmark timings.
    """

    def __init__(
        self,
        isolate_process: bool = True,
        spawn_timeout_s: Optional[float] = None,
    ) -> None:
        self.isolate_process = isolate_process
        self.spawn_timeout_s = spawn_timeout_s
        self._current_proc: Optional[mp.Process] = None
        self._proc_lock = threading.Lock()
        self._cancel_requested = False

    def cancel(self) -> None:
        """Terminates active child process if currently running."""
        with self._proc_lock:
            self._cancel_requested = True
            proc = self._current_proc
            if proc is not None:
                try:
                    if proc.is_alive():
                        proc.kill()
                    proc.join(timeout=1.0)
                except Exception:
                    pass
                if proc.pid is not None:
                    try:
                        os.kill(proc.pid, 0)
                    except OSError:
                        if proc._popen is not None and proc._popen.returncode is None:
                            proc._popen.returncode = -9
                self._current_proc = None

    def run(
        self,
        workload: WorkloadSpec,
        adapter: BaseServingAdapter,
        output_path: Union[str, Path],
        run_id: str = "run-001",
        seed: Optional[int] = 42,
        stream: bool = True,
        prompts: Optional[Union[List[str], str]] = None,
        artificial_dispatch_delay_ms: float = 0.0,
    ) -> LoadGeneratorResult:
        """
        Executes the benchmark load generation run.
        If isolate_process=True, runs within a dedicated multiprocessing child process.
        """
        with self._proc_lock:
            self._cancel_requested = False

        prompt_list: Optional[List[str]] = None
        if isinstance(prompts, str):
            prompt_list = [prompts]
        elif prompts is not None:
            prompt_list = list(prompts)

        out_str = str(Path(output_path).resolve())

        total_workload_time = float(workload.warmup_duration_s + workload.measurement_duration_s)
        timeout = (
            self.spawn_timeout_s
            if self.spawn_timeout_s is not None
            else max(120.0, total_workload_time + 60.0)
        )

        if not self.isolate_process:
            import sys
            if sys.platform == "win32" and hasattr(adapter, "stream_generate") and hasattr(adapter, "generate"):
                res = _sync_dispatch_loop(
                    workload=workload,
                    adapter=adapter,
                    output_path=out_str,
                    run_id=run_id,
                    seed=seed,
                    stream=stream,
                    prompts=prompt_list,
                    artificial_dispatch_delay_ms=artificial_dispatch_delay_ms,
                    is_cancelled=lambda: self._cancel_requested,
                    timeout=self.spawn_timeout_s,
                )
                if self._cancel_requested:
                    raise asyncio.CancelledError("LoadGenerator run was cancelled")
                return res

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            coro = _async_dispatch_loop(
                workload=workload,
                adapter=adapter,
                output_path=out_str,
                run_id=run_id,
                seed=seed,
                stream=stream,
                prompts=prompt_list,
                artificial_dispatch_delay_ms=artificial_dispatch_delay_ms,
                is_cancelled=lambda: self._cancel_requested,
            )

            if loop is not None and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    res = executor.submit(
                        asyncio.run,
                        asyncio.wait_for(coro, timeout=timeout),
                    ).result(timeout=timeout)
            else:
                res = asyncio.run(
                    asyncio.wait_for(coro, timeout=timeout)
                )

            if self._cancel_requested:
                raise asyncio.CancelledError("LoadGenerator run was cancelled")
            return res

        ctx = mp.get_context("spawn")
        parent_conn, child_conn = ctx.Pipe(duplex=False)

        proc = ctx.Process(
            target=_subprocess_entrypoint,
            args=(
                child_conn,
                workload,
                adapter,
                out_str,
                run_id,
                seed,
                stream,
                prompt_list,
                artificial_dispatch_delay_ms,
            ),
        )

        with self._proc_lock:
            if self._cancel_requested:
                child_conn.close()
                parent_conn.close()
                raise asyncio.CancelledError("LoadGenerator run cancelled before process start")
            self._current_proc = proc
            try:
                proc.start()
            except Exception:
                child_conn.close()
                parent_conn.close()
                self._current_proc = None
                raise
            finally:
                child_conn.close()

        msg = None
        try:
            has_data = parent_conn.poll(timeout)
            if not has_data:
                with self._proc_lock:
                    if proc.is_alive():
                        proc.kill()
                    proc.join(timeout=5.0)
                raise TimeoutError(
                    f"LoadGenerator subprocess timed out after {timeout}s"
                )

            try:
                msg = parent_conn.recv()
            except EOFError:
                msg = None

            with self._proc_lock:
                proc.join(timeout=5.0)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=1.0)
                if proc.pid is not None:
                    try:
                        os.kill(proc.pid, 0)
                    except OSError:
                        if proc._popen is not None and proc._popen.returncode is None:
                            proc._popen.returncode = -9

            if self._cancel_requested:
                raise asyncio.CancelledError("LoadGenerator run was cancelled")

            if proc.exitcode != 0:
                err_detail = ""
                if msg and isinstance(msg, dict):
                    err_detail = f": {msg.get('error')} ({msg.get('error_type')})"
                raise RuntimeError(
                    f"LoadGenerator subprocess exited abnormally with code {proc.exitcode}{err_detail}"
                )

            if not msg or not msg.get("success"):
                err = msg.get("error") if msg else "No message received from subprocess (channel closed)"
                err_type = msg.get("error_type") if msg else "SubprocessError"
                raise RuntimeError(
                    f"LoadGenerator execution failed in subprocess: {err} ({err_type})"
                )

            return LoadGeneratorResult.model_validate(msg["result"])
        finally:
            with self._proc_lock:
                self._current_proc = None
            parent_conn.close()
            if proc.is_alive():
                try:
                    proc.kill()
                    proc.join(timeout=1.0)
                except Exception:
                    pass

    async def arun(
        self,
        workload: WorkloadSpec,
        adapter: BaseServingAdapter,
        output_path: Union[str, Path],
        run_id: str = "run-001",
        seed: Optional[int] = 42,
        stream: bool = True,
        prompts: Optional[Union[List[str], str]] = None,
        artificial_dispatch_delay_ms: float = 0.0,
    ) -> LoadGeneratorResult:
        """Asynchronous execution wrapper delegating process management to a background thread."""
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(
            None,
            self.run,
            workload,
            adapter,
            output_path,
            run_id,
            seed,
            stream,
            prompts,
            artificial_dispatch_delay_ms,
        )
        try:
            return await asyncio.wrap_future(future)
        except asyncio.CancelledError:
            self.cancel()
            try:
                await asyncio.shield(asyncio.wrap_future(future))
            except Exception:
                pass
            raise
