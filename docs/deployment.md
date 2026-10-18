# SLOKern Serving Deployment & Runtime Notes

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Operational Guide  
> **Owner:** Aman (Serving / GPU Infrastructure)  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

---

## 1. Target Infrastructure & Serving Environment

For the Nebius × NVIDIA Global AI Hackathon, SLOKern deploys its target model on Nebius Cloud GPU infrastructure:

- **Compute Platform:** Nebius Compute Cloud GPU instance.
- **Accelerator Tier:** 1× NVIDIA H100 80GB SXM5 (or A100 80GB PCIe).
- **Target Model:** `meta-llama/Meta-Llama-3-8B-Instruct` (or approved NVIDIA open-source equivalent).
- **Serving Engine:** `vLLM` containerized runtime (OpenAI-compatible HTTP/SSE API).

---

## 2. Serving Adapter Architecture

The serving adapter (`src/slokern/engine/serving/`) provides a clean abstraction between the SLOKern experiment worker and the physical inference runtime.

```mermaid
flowchart LR
    ExpWorker[Experiment Worker\nSearch Controller] -->|CandidateConfig\n(requested knobs)| Adapter[Serving Adapter\nnebius.py / base.py]
    Adapter -->|Launch / Configure| Runtime[Serving Runtime Container\nvLLM on GPU]
    Runtime -->|Read-back effective config| Adapter
    Adapter -->|Inspect GPU & environment| GPU[NVIDIA GPU / CUDA Driver]
    Adapter -->|Effective Settings &\nEnvironment Fingerprint| ExpWorker
```

### 2.1 Supported vs. Speculative Knobs

The serving adapter strictly filters proposed candidate parameters against a confirmed allowlist. A knob is never accepted into the search space unless it can be applied and confirmed.

| Parameter | Type | Tested Range | Read-Back Method |
|---|---|---|---|
| `max_model_len` | Integer | `[2048, 4096]` | Runtime API `/version` or container startup argument |
| `gpu_memory_utilization` | Float | `[0.75, 0.95]` | Server startup configuration read-back |
| `max_num_seqs` | Integer | `[16, 64]` | Engine batch parameters query |
| `kv_cache_dtype` | String | `"auto"`, `"fp8"` | Engine model config inspection |

### 2.2 Environment Fingerprinting

Before executing any benchmark, the adapter captures an immutable `environment_fingerprint`:
- GPU device model, PCI device ID, total VRAM.
- NVIDIA driver version and CUDA runtime version.
- Container image hash, serving engine version, and git commit.
- Operating system kernel version.

This fingerprint is attached to every `RunRecord` and embedded in the final `ReportArtifact` to guarantee reproducibility.

---

## 3. Operational Lifecycle & Failure Handling

### 3.1 Preflight Health Check
Before launching an experiment, the adapter runs `smoke_test`:
1. Checks that the HTTP `/health` endpoint returns 200 OK.
2. Dispatches a minimal 1-token test prompt (`"ping"`).
3. Verifies that streaming response headers and token deltas are returned within 500 ms.

### 3.2 CUDA Out-of-Memory (OOM) Protection
If a candidate configuration allocates excessive KV-cache or concurrency causing a CUDA OOM:
1. The adapter captures the stderr log indicating OOM.
2. Sets `execution_status = FAILED` with error classification `CUDA_OOM`.
3. Triggers container restart and VRAM purge before the next candidate is evaluated.
4. Prevents the failure from contaminating the search space or crashing the controller.

### 3.3 Safe Teardown & Resource Cleanup
- Upon experiment completion or cancellation (`slokern` cancellation signal), the adapter gracefully releases open client connections, flushes remaining log buffers, and stops background worker processes.
- No dangling processes are left running on the host or GPU instance.

---

## 4. Security & Secret Redaction

1. **Zero Hardcoded Secrets:** Nebius API tokens, Hugging Face download tokens, and endpoint passwords are read exclusively from environment variables (`.env`).
2. **Artifact Redaction:** All persisted logs, manifests, and reports pass through `src/slokern/engine/store/redact.py`:
   - Authorization headers (`Bearer ***`) are masked.
   - Private IP addresses (`10.x.x.x`, `192.168.x.x`) are redacted.
   - Internal DNS names and cloud account IDs are sanitized.

---

## 5. Related Documentation

- [System Architecture](architecture.md)
- [MVP Scope & Acceptance Checklist](mvp-checklist.md)
- [ADR 0001-A: Target Model & Runtime](adr/0001-model-runtime.md)
- [Daily Integration Checklist](integration-checklist.md)
