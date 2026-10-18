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

## 5. Addendum 0001-B: Official NVIDIA Model Compliance & Hardware Feasibility

> **Status:** Accepted (Reconciliation)  
> **Date:** 2026-10-18  
> **Owners:** Rajdeep (Technical Lead) & Aman (Serving Infrastructure)  
> **Authority:** Reconciles ADR 0001-A with official Nebius × NVIDIA Hackathon Rules

### 5.1 Problem Statement
The official Nebius × NVIDIA Global AI Hackathon rules mandate:
> *"Projects must utilize at least one NVIDIA open-source model (such as models from the Nemotron, GR00T, Cosmos, Sonic, or Alpamayo families)."*

ADR 0001-A originally selected `meta-llama/Meta-Llama-3-8B-Instruct` under the heading of an "NVIDIA-optimized open-source instruction-tuned model." While Meta-Llama is supported on NVIDIA runtimes (TensorRT-LLM/NIM), Meta is the model author. Relying solely on `meta-llama/Meta-Llama-3-8B-Instruct` creates a compliance disqualification risk.

### 5.2 Resolution & 5-Tier Model Taxonomy
We establish the following explicit taxonomy to separate architectural abstractions from physical benchmark evidence:

1. **Model-Agnostic System Architecture:**
   - The SLOKern core engine, shared contracts, deterministic feasibility evaluator, search controller, load generator, and report generator are fundamentally model-agnostic.
   - Any LLM runtime exposing standard completions/chat streaming APIs can be evaluated under the same contract without code changes.

2. **Accepted Internal Pipeline Baseline (Comparative Only):** `meta-llama/Meta-Llama-3-8B-Instruct`
   - *Status:* Preserved from ADR 0001-A as an internal development baseline for validating load generation, deterministic fake-adapter fixtures, and metric calculation pipelines.
   - *Compliance Boundary:* Does **not** satisfy the hackathon's NVIDIA model mandate on its own. It is retained strictly as an internal development and comparative baseline.

3. **Selected NVIDIA Model Candidate (Hackathon Compliance Target):** `Nemotron-3-Nano-30B-A3B` (FP8)
   - *Model Family:* Official NVIDIA Nemotron open-source model family.
   - *Catalog Specifications:* Hybrid Mamba-2 Mixture-of-Experts (MoE) architecture (~30B total parameters, ~3B active parameters per token in design), 262K context window, FP8 quantization, NVIDIA provider.
   - *Nebius Catalog Availability:* Listed in Nebius catalog materials; actual endpoint access in the team's account is pending runtime verification.
   - *Serving Reality:* Serving throughput, memory pressure, and latency percentiles under SLOKern's benchmark are unmeasured and subject to empirical measurement during the smoke test and benchmark runs.

4. **Runtime-Verified Model & Endpoint:** *Pending Runtime Verification*
   - *Exact Nebius API Identifier:* The exact API string in Nebius Token Factory or container runtime (e.g., `nvidia/Nemotron-3-Nano-30B-A3B` or endpoint-specific identifier) is **pending runtime verification via smoke test**.
   - *Verification Protocol:* Prior to executing any benchmark run, Aman will execute a single-request live smoke test to confirm endpoint reachability, exact model ID read-back, streaming headers, and initial TTFT. This smoke test is a separate preliminary health check and is **not counted among the six benchmark runs**.
   - *Status:* Permitted status is `Selected candidate`, `Planned deployment target`, or `Pending runtime verification`. Claims of `Successfully deployed`, `Verified model access`, or `Benchmark completed` are strictly forbidden until physical execution artifacts exist.

5. **Optional Secondary Comparison Target:** `nvidia/Llama-3.1-Nemotron-70B-Instruct`
   - *Status:* Unverified in the team's selected Nebius catalog; retained only as a hypothetical secondary comparison model if access and quota are confirmed.

### 5.3 Benchmark Budget & Duration Policy
- **Six Benchmark Runs Budget:** The experiment campaign is locked to strictly six benchmark runs: one baseline run, four candidate runs (in a fixed 2×2 configuration space), and one independent verification rerun under a fresh `verification_run_id`.
- **Preflight Smoke Test Separated:** The preflight smoke test is a separate preliminary single-request verification and is not counted among the six benchmark runs.
- **Duration Policy:** The original schedule of 60 seconds warm-up and 180 seconds measurement per benchmark run remains **labelled illustrative**. Proposed shorter durations remain **strictly unvalidated** until actual timing and measurement-quality evidence is collected during live runs.

### 5.4 Fixed 2×2 Search Space, Parameter Legality & Architectural Blocker
- **Fixed 2×2 Design Requirement:** The candidate space is restricted to a fixed 2×2 matrix (4 candidates total). Its two specific dimensions and candidate values are **pending confirmation from the actual serving interface**.
- **Distinguishing Client/Workload vs. Serving-Engine Knobs:**
  - *Client/Workload Parameters (e.g., concurrency limit, max output tokens):* Control client traffic generation and request payload limits. **Changing workload parameters does not prove GPU-serving optimization.**
  - *Serving-Engine Parameters (e.g., batch concurrency, GPU memory utilization, max model length, KV-cache precision):* Directly configure the serving runtime and GPU execution on the host.
  - Neither parameter set is confirmed supported until verified by runtime read-back on the live Nebius endpoint.
- **Architectural Blocker Notice:** If the endpoint interface exposes only client request parameters and lacks serving-engine controls, this constitutes an architectural blocker. Resolving this blocker requires an explicit architecture decision by Rajdeep and Aman (such as deploying containerized vLLM on a dedicated Nebius Compute GPU instance).

### 5.5 Implementation & Verification Status
- The `Nemotron-3-Nano-30B-A3B` (FP8) deployment is marked `PENDING RUNTIME VERIFICATION` (blocked on live smoke test execution on Nebius).
- All mock and synthetic runs are labeled `DEMO DATA`. No benchmark numbers will be asserted as real until physical run artifacts are captured in `artifacts/`.

---

## 6. Related Documents

- [Hackathon Compliance Matrix](../hackathon-compliance.md)
- [System Architecture](../architecture.md)
- [Serving Deployment Notes](../deployment.md)
- [ADR 0001: MVP Scope & Evidence Policy](0001-mvp-scope-and-evidence.md)
- [ADR 0002: Dual-Mode Cost Accounting](0002-cost-model.md)

