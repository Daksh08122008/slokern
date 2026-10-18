# SLOKern Serving Deployment & Runtime Notes

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Operational Guide  
> **Owner:** Rajdeep (Architecture, Serving & Infrastructure; Historical design: Aman)  
> **Authority:** Aligned with [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [docs/ownership.md](ownership.md)

---

## 1. Target Infrastructure & Serving Environment

For the Nebius × NVIDIA Global AI Hackathon, SLOKern deploys its target model on Nebius Cloud GPU infrastructure:

- **Compute Platform:** Nebius Compute Cloud GPU instance and/or Nebius Token Factory managed endpoints.
- **Accelerator Tier:** 1× NVIDIA H100 80GB SXM5 (or A100 80GB PCIe).
- **Target Models & Roles (5-Concept Model Taxonomy):**
  - **1. Model-Agnostic Core:** The SLOKern engine, contracts, evaluator, and search controller are decoupled from specific model architectures.
  - **2. Hackathon Compliance Target (Selected Candidate):** `Nemotron-3-Nano-30B-A3B` (FP8)  
    *Specifications:* Official NVIDIA open-weights model family, combining Mamba-2 state-space hybrid layers and Mixture-of-Experts (MoE) architecture (~30B total parameters, ~3B active parameters per token in design), 262K context window, FP8 quantization.  
    *Status & Verification:* Serving throughput, latency percentiles, and memory headroom under SLOKern's benchmark are unmeasured and subject to empirical measurement during the smoke test and benchmark runs. Listed in Nebius catalog materials, but exact endpoint accessibility in the team's account is pending runtime verification.
  - **3. Runtime-Verified Model & Endpoint:** *Pending Runtime Verification*  
    *Exact API String:* The exact model identifier in the Nebius API (e.g., `nvidia/Nemotron-3-Nano-30B-A3B` or endpoint slug) is **pending runtime verification via smoke test**. Access must be confirmed with a live single-request test before benchmark runs begin.
  - **4. Internal Pipeline Baseline (Comparative Only):** `meta-llama/Meta-Llama-3-8B-Instruct`  
    *Purpose:* Preserved from ADR 0001-A for pipeline validation, fake-adapter tests, and regression fixtures. Does *not* alone satisfy the hackathon's NVIDIA model mandate.
  - **5. Optional Secondary Comparison Model:** `nvidia/Llama-3.1-Nemotron-70B-Instruct`  
    *Status:* Unverified in the team's selected Nebius catalog; purely a hypothetical secondary model for comparison if access and quota are confirmed.
- **Serving Engine:** Containerized runtime (e.g., `vLLM`) or managed inference endpoint (OpenAI-compatible HTTP/SSE API).
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

### 2.1 Fake-Adapter-First Development Workflow

To protect hackathon GPU credit budgets and accelerate development:
1. **Deterministic Fake Adapter (`fake.py`):** The feasibility evaluator, metrics calculation pipeline, search controller, report generator, and dashboard are implemented and thoroughly verified against the deterministic fake adapter.
   - Generates schema-valid, deterministic synthetic measurements.
   - Simulates edge-case failure modes (CUDA OOM, request timeouts, client generator saturation, threshold-adjacent breaches).
   - **Persistent Labeling:** All synthetic outputs and simulated runs are strictly labeled **`DEMO DATA`**. Never presented as live GPU measurements.
2. **Real Adapter (`nebius.py`):** Targets the live Nebius endpoint and records actual inference timings.
   - Shares the identical adapter interface (`BaseServingAdapter`) as the fake adapter.
   - Consumes GPU credits **only** for:
     1. Preflight integration smoke test (1 request).
     2. Empirical baseline measurement.
     3. Bounded 4-candidate search.
     4. Independent verification rerun of the selected candidate.

### 2.2 Bounded Benchmark Budget (Six Benchmark Runs vs. Preflight Smoke Test)

To enforce experiment-budget safety, the campaign is strictly bounded:
- **Six Benchmark Runs Budget:**
  The benchmark budget is defined as exactly **six benchmark runs**:
  1. Baseline measurement (default configuration anchor).
  2. Candidate 1.
  3. Candidate 2.
  4. Candidate 3.
  5. Candidate 4.
  6. Independent verification rerun of the selected winning candidate under a fresh `verification_run_id`.
- **Preflight Smoke Test Counted Separately:**
  The preflight smoke test is a **separate preliminary health request** (single prompt to check endpoint reachability, read back the exact model string, and confirm streaming response headers). It is **not counted among the six benchmark runs**.
- **Duration Policy & Unvalidated Calibration:**
  - The original schedule of **60 seconds warm-up and 180 seconds measurement** per benchmark run remains **labelled illustrative** ($6 \times 240\text{ s} = 24\text{ minutes}$ pure load).
  - Any proposed shorter durations (e.g., 15–30s warm-up and 45–60s measurement) remain **strictly unvalidated** until actual timing, overhead, and measurement-quality evidence is gathered during the live smoke test.
  - The actual duration and applied settings of every run must be recorded immutably.

### 2.3 Fixed 2×2 Search Space, Parameter Legality & Architectural Blocker

The candidate search space is constrained by explicit design and interface realities:

- **Fixed 2×2 Search Space Design Requirement:**
  The optimization search is restricted to a fixed 2×2 parameter matrix (4 candidates total). However, its **two specific dimensions and values are pending confirmation from the actual serving interface** during Rajdeep's preflight inspection.
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
5. **Smoke Test Evidence Artifact:** Persists a `smoke_test_result.json` artifact containing timestamp, confirmed model ID, endpoint type, and initial latency timings. Benchmark runs are blocked until this preflight check passes.

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
