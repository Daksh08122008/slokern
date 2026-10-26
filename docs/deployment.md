# SLOKern Serving Deployment & Runtime Notes

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Operational Guide  
> **Owner:** Rajdeep (Architecture, Serving & Infrastructure; Historical design: Aman)  
> **Authority:** Aligned with [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [docs/ownership.md](ownership.md)

> **Evidence boundary (2026-10-23):** No Nebius resource was provisioned and no provider API was called for this guide update. The accepted model-family candidate is `Nemotron-3-Nano-30B-A3B` (FP8), with exact checkpoint/API ID pending. The current proposal is a Nebius Serverless AI custom container using vLLM 0.12.0 and one H100 SXM GPU; account capacity, flag support, model compatibility, and live behavior are unresolved. See [DEC-0013](decision-log.md#dec-0013-reconcile-the-controlled-deployment-and-search-profile-open). Treat profile values below as planned until a pinned-image preflight confirms requested/effective equality.

---

## 1. Target Infrastructure & Serving Environment

For the Nebius × NVIDIA Global AI Hackathon, SLOKern's accepted model-family candidate is planned for Nebius infrastructure; no deployment is currently verified:

- **Proposed Compute Platform:** Nebius AI Cloud Serverless AI custom-container endpoint with an H100 SXM GPU. A GPU VM running Docker is the fallback if Serverless image arguments, lifecycle, or restart semantics cannot support the experiment. Nebius Token Factory is a managed comparison only; request fields do not expose or prove hidden vLLM scheduler settings.
- **Accelerator Tier:** 1× NVIDIA H100 80GB SXM5 (or A100 80GB PCIe).
- **Target Models & Roles (5-Concept Model Taxonomy):**
  - **1. Model-Agnostic Core:** The SLOKern engine, contracts, evaluator, and search controller are decoupled from specific model architectures.
  - **2. Hackathon Compliance Target (Accepted Candidate):** `Nemotron-3-Nano-30B-A3B` (FP8)
    *Specifications:* Official NVIDIA open-weights model family, combining Mamba-2 state-space hybrid layers and Mixture-of-Experts (MoE) architecture (~30B total parameters, ~3B active parameters per token in design), 262K context window, FP8 quantization.  
    *Status & Verification:* Serving throughput, latency percentiles, and memory headroom under SLOKern's benchmark are unmeasured and subject to empirical measurement during the smoke test and benchmark runs. Listed in Nebius catalog materials, but exact endpoint accessibility in the team's account is pending runtime verification.
    *Proposed fallback:* `Llama-3.1-Nemotron-Nano-8B-v1` if the primary model cannot be started reliably or a model-specific constraint blocks the experiment. Its exact model ID, revision, license/availability, and runtime compatibility have not been reverified for this account.
  - **3. Runtime-Verified Model & Endpoint:** *Pending Runtime Verification*  
    *Exact API String:* The exact model identifier in the Nebius API (e.g., `nvidia/Nemotron-3-Nano-30B-A3B` or endpoint slug) is **pending runtime verification via smoke test**. Access must be confirmed with a live single-request test before benchmark runs begin.
  - **4. Internal Pipeline Baseline (Comparative Only):** `meta-llama/Meta-Llama-3-8B-Instruct`  
    *Purpose:* Preserved from ADR 0001-A for pipeline validation, fake-adapter tests, and regression fixtures. Does *not* alone satisfy the hackathon's NVIDIA model mandate.
  - **5. Optional Secondary Comparison Model:** `nvidia/Llama-3.1-Nemotron-70B-Instruct`  
    *Status:* Unverified in the team's selected Nebius catalog; purely a hypothetical secondary model for comparison if access and quota are confirmed.
- **Proposed Serving Engine:** vLLM `0.12.0` in a custom container. This version, image, model, and launch arguments have not passed a compatibility smoke test. Use an immutable image digest at execution; do not use a floating `latest` tag. `--trust-remote-code` is a proposed option only if the selected checkpoint's reviewed serving instructions require it; pin the exact model commit and review its code because the flag permits repository code execution.
- **Deployment & Evidence Status:** `PENDING RUNTIME VERIFICATION` (blocked on live smoke test execution by Rajdeep on Nebius). Permitted terminology: `Selected candidate`, `Planned deployment target`, `Pending runtime verification`. Strictly avoid claims of `Successfully deployed`, `Verified model access`, or `Benchmark completed`.

---

## 2. Serving Adapter Architecture & Fake-Adapter-First Development

The serving adapter (`src/slokern/engine/serving/`) provides a clean abstraction between the SLOKern experiment worker and the physical inference runtime.

```mermaid
flowchart LR
    ExpWorker[Experiment Worker\nSearch Controller] -->|CandidateConfig\n(requested knobs)| Adapter[Serving Adapter\nbase.py / fake.py / nebius.py]
    Adapter -->|Launch / Configure| Runtime[Serving Runtime Container\nvLLM / Token Factory]
    Runtime -->|Read-back effective config| Adapter
    Adapter -->|Inspect GPU & environment| GPU[NVIDIA GPU / CUDA Driver]
    Adapter -->|Effective Settings &\nEnvironment Fingerprint| ExpWorker
```

This diagram shows the intended adapter contract. Current `NebiusServingAdapter.apply_config()` evaluates settings against local capability declarations but does not send launch flags to a process or read effective values back from the endpoint (`BLK-17`).

### 2.1 Three Canonical Execution Backends (DEC-0014)

To balance rapid offline developer velocity, deterministic unit testing, and authoritative live cloud GPU measurements, SLOKern implements three distinct execution backends sharing the identical core pipeline:

```mermaid
flowchart TD
    AdapterFactory["Serving Adapter Boundary
create_serving_adapter()"]
    AdapterFactory -->|--adapter local| Local["Local Ollama Backend (local)
• Loopback: http://127.0.0.1:11434
• Model: qwen3:4b-instruct-2507-q4_K_M
• Native /api/tags & /api/chat
• Monotonic client timing; zero cloud keys"]
    AdapterFactory -->|--adapter fake| Fake["Deterministic Fake Backend (fake)
• Standalone simulator for CI & unit tests
• Simulates latency scaling, OOM, timeouts
• Persistently labeled: DEMO DATA"]
    AdapterFactory -->|--adapter nebius| Nebius["Live Nebius Backend (nebius)
• Nebius Token Factory Dedicated Endpoint
• Model: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B (FP8)
• Live GPU measurements; explicit NEBIUS_API_KEY"]
```

#### A. Local Development Backend (`local` / `OllamaServingAdapter`)
- **Runtime Host:** Ollama instance running locally on loopback (`http://127.0.0.1:11434`).
- **Exact Model Target:** `qwen3:4b-instruct-2507-q4_K_M`. Pull command:
  ```bash
  ollama pull qwen3:4b-instruct-2507-q4_K_M
  ```
- **Native Ollama API:** Interacts directly with native Ollama endpoints:
  - `/api/tags`: Validates model presence and readiness prior to execution without silently triggering model downloads.
  - `/api/chat`: Issues streaming chat completion requests with JSON payload formatting.
- **Loopback Security Boundary:**
  - Enforces loopback IP addressing (`127.0.0.1` / `::1`) by default; remote connections require explicit opt-in (`allow_remote=True`).
  - Unconditionally blocks HTTP 3xx redirects (`StrictLoopbackRedirectHandler`) to prevent loopback pivoting (SSRF).
  - Strictly rejects embedded URL user credentials (`user:pass@host`).
  - Disables proxy-based routing for local loopback requests.
  - Requires zero Nebius API credentials or cloud compute allocation.
- **Client-Observed Timing Authority:**
  - Elapsed durations are measured strictly via monotonic clocks (`time.monotonic()`).
  - Client-observed request-start-to-first-content latency is recorded as TTFT.
  - Ollama server-reported metadata (`prompt_eval_duration`, `eval_duration`) is preserved in separate metadata fields, converted from nanoseconds to milliseconds, without conflation.
  - Chunk arrivals are recorded as chunk-gap intervals, not individual token-level ITL.
- **Scope & BLK-17 Limitation:** Local mode records real host system observations with explicit local environment metadata. It does not validate the 2x2 serving-engine optimization matrix because Ollama does not support dynamic process-startup flag read-back per request (`BLK-17`).

#### B. Deterministic Fake Backend (`fake` / `FakeServingAdapter`)
- **Role:** Offline deterministic unit testing, failure injection (timeouts, CUDA OOM, client saturation), and synthetic 6-run campaign testing.
- **Mandatory Guardrail:** All synthetic runs and artifacts are unmistakably labeled **`DEMO DATA`** and never presented as live GPU evidence.

#### C. Live Nebius Benchmark Backend (`nebius` / `NebiusServingAdapter`)
- **Provider & Target:** Nebius Token Factory dedicated endpoint serving `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (FP8).
- **Authentication & Gating:** Requires explicit operator selection (`--adapter nebius`), valid `NEBIUS_API_KEY`, and manual authorization. No automated provisioning, starting, stopping, or deletion of cloud instances.
- **BLK-17 Gating:** Optimization campaigns halt with `SearchConfigurationError` citing `BLK-17` until dynamic serving-engine flag application and read-back are provisioned.

### 2.2 Intended Benchmark Budget (Six Controller Runs vs. Operational Runs)

The intended controller allocation is six runs:
  1. Baseline measurement (default configuration anchor).
  2. Candidate 1.
  3. Candidate 2.
  4. Candidate 3.
  5. Candidate 4.
  6. Independent verification rerun of the selected winning candidate under a fresh `verification_run_id`.
- **Current enforcement limitation:** `BudgetLimiter` defaults to five search runs plus one verification run, but its constructor accepts values that can consume the verification reserve (`BLK-15`). The current controller executes the baseline and candidates; it does not perform independent verification.
- **Preflight Smoke Test Counted Separately:**
  The preflight is operational activity outside the six controller-counted runs. It still needs a run/artifact record and must be included in the provider cost/time cap. The current repository does not provide a dedicated preflight orchestrator.
- **Pilot and Replicate Runs:** The proposed load ladder and baseline replicate are not included in the controller's search/verification counters. They must be separately authorized, bounded, assigned run IDs, persisted, and included in the operational and billable-resource ledger. Excluding a run from the controller counter does not make it free. If the six-run total is intended to include these runs, reduce the candidate campaign and amend DEC-0010 before execution.
- **Duration Policy:** The newer proposal is a 120-second warm-up and a measurement duration of `max(600 seconds, 2000 / λ*)`, then drain to zero, with at least 2,000 measured requests. This replaces the older illustrative 60s/180s example for planning, but is not ratified or implemented. Record actual active-window start/end, warm-up classification, drain time, and all request outcomes. p95 is the proposed primary tail statistic at this sample size; p99 is informational unless the pre-registered sample size supports it.

### 2.3 Proposed Search Profile (Not the Current Code Grid)

The current request proposes this centre baseline plus four candidates:

| Point | `--max-num-seqs` | `--max-num-batched-tokens` |
|---|---:|---:|
| Centre baseline | 128 | 8192 |
| Candidate 1 | 64 | 2048 |
| Candidate 2 | 64 | 16384 |
| Candidate 3 | 256 | 2048 |
| Candidate 4 | 256 | 16384 |

These are vLLM process-start flags and require the serving process/endpoint to restart or be recreated. Their effect on TTFT, chunk-gap ITL, throughput, memory, queueing, and errors is a hypothesis to measure, not a supported-provider fact. Verify the exact vLLM 0.12.0 option names/ranges and Serverless argument forwarding before use. Keep context cap 8192, GPU memory utilization 0.90, explicit KV/SSM cache dtypes, async scheduling, and disabled prefix caching fixed only after the chosen image/model confirms each option. No current code applies or reads these launch flags.

This proposed profile differs from the current Python generator, which emits `{max_num_batched_tokens: 1024 or 2048} × {max_num_seqs: 16 or 64}`. Do not describe the proposed five-point profile as implemented until an owner decision and matching code/adapter validation exist. DEC-0013 tracks the decision.

### 2.4 Fixed 2×2 Search Space, Parameter Legality & Architectural Blocker

The candidate search space is constrained by explicit design and interface realities:

- **Fixed 2×2 Search Space Design Requirement:**
  Current source generates a 2×2 matrix (`max_num_batched_tokens ∈ {1024, 2048}`, `max_num_seqs ∈ {16, 64}`). Its remote legality and effect are **not confirmed**; the proposed five-point profile is a separate unresolved decision.
- **Distinguishing Client/Workload from Serving-Engine Controls:**
  - *Client/Workload Parameters (e.g., `concurrency_limit`, `max_tokens`):* Regulate client load generation and prompt payload constraints. **Altering workload parameters does not prove GPU-serving optimization.** Workload tuning merely alters the offered traffic pattern or generation bounds.
  - *Serving-Engine Parameters (e.g., `max_num_seqs`, `gpu_memory_utilization`, `max_model_len`, `kv_cache_dtype`):* Directly configure the internal runtime and GPU memory layout on the serving host.
  - Neither set of parameters is confirmed supported until verified by runtime read-back on the live Nebius endpoint.
- **Architectural Blocker Notice:**
  If the target deployment interface (such as a managed Token Factory endpoint) exposes only standard client request parameters and lacks observable or tunable serving-engine controls:
  - This constitutes an **architectural blocker** for engine optimization.
  - An **explicit architecture decision** (owned by Rajdeep) must be made — either deploying containerized `vLLM` on a dedicated Nebius Compute GPU instance to access engine-level knobs, or formally refining the optimization problem boundary via an accepted ADR.

### 2.4 Cost Policy & Metric Disambiguation

SLOKern enforces strict cost and metric calculation boundaries:
- **Cost Mode B Default:** Mode B remains the default cost accounting mode until authoritative, verified cloud pricing is provided.
- **Monetary Cost Fallback:** Monetary cost is reported as **`unavailable`** when hourly rates or pricing structures cannot be established reliably (never fabricate prices!).
- **GPU-Seconds per Request Fallback:** GPU-seconds per request is reported as **`unavailable`** if the deployment environment cannot provide verified GPU count and dedicated residency data (e.g. on managed serverless endpoints where physical GPU allocation is abstracted).
- **Metric Disambiguation:**
  - *Request Throughput (`request_throughput_rps`):* Rate of successfully completed valid requests over the measurement window (`req/s`).
  - *Achieved Load (`achieved_load_rps`):* Actual request delivery rate achieved by the client/server under the offered workload (`req/s`).
  - *GPU Utilization:* Hardware-level resource consumption metric (percentage of GPU compute/memory active during execution). Never confuse throughput or load with hardware utilization.

### 2.5 Environment Fingerprinting

Before executing any benchmark, the adapter captures an immutable `environment_fingerprint`:
- GPU device model, PCI device ID, total VRAM (if accessible).
- NVIDIA driver version and CUDA runtime version (if accessible).
- Container image hash, serving engine version, and git commit.
- Operating system kernel version.

This fingerprint is attached to every `RunRecord` and embedded in the final `ReportArtifact` to guarantee reproducibility.

---

## 3. Operational Lifecycle & Failure Handling

### 3.1 Preflight Endpoint Smoke Test & Calibration Protocol
Before committing GPU credits to any benchmark campaign, the adapter executes a mandatory preflight smoke test:
1. **Endpoint Reachability:** Checks that the HTTP `/health` or `/v1/models` endpoint returns 200 OK.
2. **Exact Model Identifier Read-Back:** Queries the endpoint to confirm the exact served model string matches the expected `Nemotron-3-Nano-30B-A3B` (FP8) deployment.
3. **Single Live Request Verification:** Dispatches a minimal 1-request prompt to verify streaming SSE response headers, token deltas, and that TTFT is recorded without client errors.
4. **Duration & Overhead Calibration:** Measures engine startup, model loading, warm-up, request execution, and shutdown overhead. The observed variance determines the practical measurement schedule (e.g., 15–30s warm-up and 45–60s measurement) rather than defaulting to the illustrative 60s/180s estimate.
5. **Smoke Test Evidence Artifact (planned):** Persist `smoke_test_result.json` with timestamp, confirmed model/revision, endpoint type, image digest, effective flags, health/stream behavior, and timings. The current repository does not implement this complete preflight artifact. Benchmark runs must remain blocked until the real provider/runtime control path is verified.

### 3.2 Proposed workload and validity gates

- Use an immutable JSONL prompt fixture with 70% small (256 input / 128 output tokens), 25% medium (1024 / 256), and 5% large (4096 / 256) classes. Record exact tokenizer revision, per-prompt token counts, fixture hash, output cap, and prompt IDs. These lengths are a proposal; current loadgen token counts use a whitespace-based estimate and are not exact tokenizer evidence.
- Precompute a seeded open-loop Poisson schedule. Open-loop arrivals keep offered traffic independent of completions so a slow service cannot reduce its own offered load and conceal queueing. The current arrival generator supports constant and seeded Poisson schedules; `CLOSED` exists in the contract enum but is rejected by the generator.
- Proposed gates: requested/effective configuration equality; health before and after; generator dispatch p99 lateness ≤20 ms and client CPU <70%; achieved/offered ≥0.98; no restart/OOM; preserve all failures, timeouts, partial streams, and schedule deviations. These numerical gates are proposals and not current evaluator rules. A failed evidence-validity gate means invalid/inconclusive evidence, not an SLO failure.
- Measure cache state and endpoint preemption/restarts if the platform exposes them. If these cannot be observed, state that they are uncontrolled; do not claim cache isolation or stable dedicated capacity.

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

1. **Zero Hardcoded Secrets:** Nebius API tokens, Hugging Face download tokens, and endpoint passwords come from environment variables or provider secret facilities. Local `.env` files are ignored and never committed; do not echo them into command output or artifacts.
2. **Artifact Redaction:** All persisted logs, manifests, and reports pass through `src/slokern/engine/store/redact.py`:
   - Authorization headers (`Bearer ***`) are masked.
   - Private IP addresses (`10.x.x.x`, `192.168.x.x`) are redacted.
   - Internal DNS names and cloud account IDs are sanitized.

The current adapter sanitizes handled HTTP/network error strings and omits credentials from its environment fingerprint. This source audit does not prove every process log, provider response, traceback, report, or remote log is redacted; audit those channels before live use. Scope secret-redaction claims to code paths and output actually inspected.

---

## 5. Related Documentation

- [System Architecture](architecture.md)
- [MVP Scope & Acceptance Checklist](mvp-checklist.md)
- [ADR 0001-A: Target Model & Runtime](adr/0001-model-runtime.md)
- [Daily Integration Checklist](integration-checklist.md)
