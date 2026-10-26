with open("src/slokern/engine/loadgen/runner.py", "r", encoding="utf-8") as f:
    text = f.read()

old_sync_sig = """def _sync_dispatch_loop(
    workload: WorkloadSpec,
    adapter: BaseServingAdapter,
    output_path: str,
    run_id: str,
    seed: Optional[int],
    stream: bool,
    prompts: Optional[List[str]],
    artificial_dispatch_delay_ms: float,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> LoadGeneratorResult:"""

new_sync_sig = """def _sync_dispatch_loop(
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
) -> LoadGeneratorResult:"""

text = text.replace(old_sync_sig, new_sync_sig)

old_loop_top = """        for slot in slots:
            if is_cancelled is not None and is_cancelled():
                break
            now = time.time()
            wait_time = slot.scheduled_at - now
            if wait_time > 0:
                time.sleep(wait_time)
            if is_cancelled is not None and is_cancelled():
                break"""

new_loop_top = """        for slot in slots:
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
                break"""

text = text.replace(old_loop_top, new_loop_top)

old_call = """                res = _sync_dispatch_loop(
                    workload=workload,
                    adapter=adapter,
                    output_path=out_str,
                    run_id=run_id,
                    seed=seed,
                    stream=stream,
                    prompts=prompt_list,
                    artificial_dispatch_delay_ms=artificial_dispatch_delay_ms,
                    is_cancelled=lambda: self._cancel_requested,
                )"""

new_call = """                res = _sync_dispatch_loop(
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
                )"""

text = text.replace(old_call, new_call)

with open("src/slokern/engine/loadgen/runner.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(text)

# Now decorate test_runner_arun_cancellation_in_process in test_runner.py
with open("tests/unit/engine/loadgen/test_runner.py", "r", encoding="utf-8") as f:
    t_text = f.read()

target_t = "def test_runner_arun_cancellation_in_process(tmp_path: Path):"
replacement_t = "@requires_subprocess_socket\ndef test_runner_arun_cancellation_in_process(tmp_path: Path):"

if replacement_t not in t_text:
    t_text = t_text.replace(target_t, replacement_t)
    with open("tests/unit/engine/loadgen/test_runner.py", "w", encoding="utf-8", newline="\n") as f:
        f.write(t_text)

print("Updated runner.py and test_runner.py")

