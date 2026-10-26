with open("src/slokern/engine/loadgen/runner.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)

content = "".join(new_lines)

# Block in async loop
target_async = """                        if first_token_at is None:
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
                completed_at = max(now_complete, first_token_at if first_token_at is not None else sent_at)"""

repl_async = """                        if first_token_at is None:
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
                    completed_at = max(now_complete, first_token_at if first_token_at is not None else sent_at)"""

# Block in sync loop
target_sync = """                        if first_token_at is None:
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
                completed_at = max(now_complete, first_token_at if first_token_at is not None else sent_at)"""

repl_sync = """                        if first_token_at is None:
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
                    completed_at = max(now_complete, first_token_at if first_token_at is not None else sent_at)"""

content_crlf = content.replace("\r\n", "\n")
if target_async in content_crlf:
    print("Found target_async")
    content_crlf = content_crlf.replace(target_async, repl_async)
else:
    print("Did NOT find target_async")

if target_sync in content_crlf:
    print("Found target_sync")
    content_crlf = content_crlf.replace(target_sync, repl_sync)
else:
    print("Did NOT find target_sync")

with open("src/slokern/engine/loadgen/runner.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(content_crlf)
print("Done")

