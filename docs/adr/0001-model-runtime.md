# ADR 0001-A: Target Model, Serving Runtime, and Nebius Infrastructure

> **Status:** Accepted  
> **Date:** 2026-10-14  
> **Owner:** Aman (Serving/GPU Infrastructure) & Rajdeep (Technical Lead)  
> **Scope:** Serving and Infrastructure Workstream  
> **Authority:** Aligned with [README.md](../../README.md) and [ROADMAP.md](../../ROADMAP.md)

---

## 1. Context and Problem Statement

To deliver an evidence-backed optimization system within the Nebius × NVIDIA Global AI Hackathon, SLOKern must select an accessible, high-performance open-source LLM, a compatible serving runtime, and an appropriate hosting configuration on Nebius Cloud GPU infrastructure.

Attempting to support arbitrary models or multiple runtimes concurrently during the MVP sprint would dilute engineering focus and prevent thorough verification of configuration effects.

---

## 2. Decision Drivers

1. **Hackathon Eligibility:** Must use an approved NVIDIA-supported open-source model and deploy on Nebius infrastructure.
2. **Observability of Timings:** The serving runtime must expose streaming tokens or granular timestamp APIs necessary to measure Time to First Token (TTFT) and Inter-Token Latency (ITL).
3. **Verifiable Mutability:** The runtime must support dynamic or containerized configuration knobs that can be read back and verified by the serving adapter.
4. **Execution Reliability:** The model must fit comfortably within the provisioned GPU memory (e.g., 80GB SXM on H100 or A100) without out-of-memory crashes during benchmark bursts.

---

## 3. Decision Outcome

We select the following baseline serving target:

1. **Target Model:** A single NVIDIA-optimized open-source instruction-tuned model:
   - Primary: `meta-llama/Meta-Llama-3-8B-Instruct` (or `mistralai/Mistral-7B-Instruct-v0.3`).
   - Justification: Widely supported, fits comfortably in GPU memory with ample room for KV-cache experimentation, and produces realistic multi-turn inference dynamics.
2. **Serving Engine:** `vLLM` (with secondary evaluation of `TensorRT-LLM` if runtime controls permit).
   - Justification: Native support for streaming responses (enabling accurate TTFT and per-token timings), mature OpenAI-compatible API, and transparent tuning knobs.
3. **Hosting Infrastructure:** Nebius Cloud GPU instance (1× NVIDIA H100 or A100 80GB).
4. **Searchable Parameter Allowlist:** The serving adapter will restrict candidate configurations to parameters actively supported and verified on the endpoint:
   - `max_model_len` (e.g., 2048, 4096)
   - `gpu_memory_utilization` (e.g., 0.80, 0.90, 0.95)
   - `max_num_seqs` / max batch concurrency (e.g., 16, 32, 64)
   - `kv_cache_dtype` (fp16 vs. fp8, subject to GPU architecture support)

---

## 4. Consequences and Mitigations

- **Bounded Portability:** Optimization results are specific to the tested model revision and hardware platform. The report generator must include the full environment fingerprint and disclose this limitation.
- **Secret Redaction:** Serving endpoint URLs, authorization tokens, and cloud project IDs must be redacted before persisting artifacts or publishing reports.

---

## 5. Related Documents

- [System Architecture](../architecture.md)
- [Serving Deployment Notes](../deployment.md)
- [ADR 0001: MVP Scope & Evidence Policy](0001-mvp-scope-and-evidence.md)
- [ADR 0002: Dual-Mode Cost Accounting](0002-cost-model.md)
