# SLOKern
### Optimize inference. Verify performance.

> **SLOKern is an SLO-aware LLM inference optimization system that measures a bounded set of serving configurations, identifies the lowest-cost configuration that satisfies a declared workload and service-level objective (SLO), and independently verifies the recommendation.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Hackathon: Nebius × NVIDIA 2026](https://img.shields.io/badge/Hackathon-Nebius_%C3%97_NVIDIA_2026-76B900.svg)](https://nebiusglobalaihackathon.devpost.com/)
[![Track: Best Agents and Apps Tracks](https://img.shields.io/badge/Track-Best_Agents_and_Apps_Tracks-purple.svg)](https://nebiusglobalaihackathon.devpost.com/)
[![Status: Single--Owner Execution](https://img.shields.io/badge/Status-Single--Owner_Execution-cyan.svg)](docs/ownership.md)

**Product Principle:** *Do not guess the optimal configuration. Find it experimentally, then verify it.*

---

## Contents

- [1. Why SLOKern?](#1-why-slokern)
- [2. Problem Statement & Core Value](#2-problem-statement--core-value)
- [3. System Architecture & Component Design](#3-system-architecture--component-design)
- [4. The 7-Step Execution Pipeline](#4-the-7-step-execution-pipeline)
- [5. Four-Domain Lifecycle & State Separation](#5-four-domain-lifecycle--state-separation)
- [6. Supported Models, Serving Path & Search Space](#6-supported-models-serving-path--search-space)
- [7. Fake-Adapter-First vs. Live Infrastructure](#7-fake-adapter-first-vs-live-infrastructure)
- [8. Cost Accounting Policy & Systems Proxy](#8-cost-accounting-policy--systems-proxy)
- [9. Current Implementation Status](#9-current-implementation-status)
- [10. Quick Start & Execution Instructions](#10-quick-start--execution-instructions)
- [11. Testing, Validation & Reproducibility](#11-testing-validation--reproducibility)
- [12. Known Limitations & Risk Management](#12-known-limitations--risk-management)
- [13. Single-Owner Roadmap (Phases A–F)](#13-single-owner-roadmap-phases-af)
- [14. Consolidated Engineering Ownership](#14-consolidated-engineering-ownership)
- [15. Related Documentation & In-Depth Guides](#15-related-documentation--in-depth-guides)

---

## 1. Why SLOKern?

In modern LLM inference serving, high throughput metrics are frequently deceptive. A serving engine configuration may deliver impressive aggregate token generation rates, yet violate critical tail-latency constraints—causing the 95th percentile Time to First Token ($\text{TTFT}_{p95}$) to spike into seconds and destroying interactive user experience. Conversely, over-provisioning GPU instances to guarantee safety margins wastes thousands of dollars in cloud spend.

Manual trial-and-error tuning is slow, noisy, and prone to false positives: a single lucky benchmark run can fool engineering teams into deploying an unstable configuration.

**SLOKern replaces guesswork with automated, deterministic systems engineering.** It accepts declared traffic profiles and non-negotiable service-level objectives, executes a bounded campaign of controlled benchmarks, deterministically eliminates infeasible candidates, selects the most cost-efficient candidate, and **independently verifies the winning configuration** under a fresh run ID before publishing recommendations.

---

## 2. Problem Statement & Core Value

SLOKern answers the fundamental systems engineering question:

> **What is the lowest-cost, verified serving configuration that reliably satisfies declared tail-latency and error-rate SLOs under a specific offered workload?**

### Core Invariants

1. **Deterministic Evaluation:** Feasibility verdicts are calculated strictly by deterministic Python code. No LLM or heuristic scorer may override hard SLO constraints or pass/fail thresholds.
2. **Missing $\ne$ Passing:** A missing or uncalculable metric returns `INCONCLUSIVE`. It can never be treated as a pass.
3. **Strict Benchmark Budget:** Total exploration is strictly locked to **six benchmark runs**:
   - 1 Baseline run (default configuration).
   - 4 Candidate runs (fixed 2×2 parameter matrix).
   - 1 Independent verification rerun.
   *(Preflight smoke test is a preliminary health check counted separately).*
4. **Mandatory Independent Verification:** A candidate configuration marked `FEASIBLE` during search is never awarded the verified badge until a secondary run under a distinct `verification_run_id` independently satisfies all constraints.
5. **Traceable Raw Evidence:** Aggregates are never stored alone. Every metric is traceable to microsecond-accurate raw client request traces (`RawRequestMeasurement` in JSONL).
6. **No Fabricated Pricing:** If authoritative cloud provider rates cannot be verified, monetary cost is reported as **`unavailable`**, and optimization falls back to Mode B (non-monetary systems proxy: GPU-seconds per request or throughput under SLO).

---

## 3. System Architecture & Component Design

SLOKern is architected as a **modular monolith with an isolated experiment worker**. The control plane is decoupled from the request-generation path so that API streaming, logging overhead, and UI interactions never contaminate benchmark measurements.

```mermaid
flowchart TD
    subgraph UI_API["Control Plane & Presentation"]
        Dashboard[Frontend Command Center\nReact + Vite + Tailwind]
        FastAPIApp[Control Plane API\nFastAPI + SSE Streaming]
    end

    subgraph CoreEngine["Deterministic Core Engine"]
        SpecValidator[Contract & Budget Validator\nPydantic v2 Models]
        SearchController[Search Controller\nFixed 2x2 Candidate Space]
        MetricsEngine[Metrics Engine\nTTFT, ITL, Load, Percentiles]
        FeasibilityEval[Feasibility Evaluator\nReason Codes Taxonomy]
        VerifRunner[Independent Verification Runner\nFresh verification_run_id]
        ReportBuilder[Report Artifact Generator\nImmutable Publishable Bundle]
    end

    subgraph IsolatedWorker["Isolated Experiment Worker"]
        LoadGen[Subprocess Load Generator\nArrival Process & Raw JSONL]
        ServingAdapter[Serving Adapter\nbase.py / fake.py / nebius.py]
    end

    subgraph Infrastructure["Inference Runtime (Nebius Cloud)"]
        TargetRuntime[vLLM / Token Factory\nNVIDIA H100 GPU Instance]
    end

    Dashboard <-->|SSE Stream & REST| FastAPIApp
    FastAPIApp --> SpecValidator
    SpecValidator --> SearchController
    SearchController --> ServingAdapter
    ServingAdapter -->|Configure & Read-back| TargetRuntime
    SearchController --> LoadGen
    LoadGen -->|Dispatch Traffic| TargetRuntime
    LoadGen -->|Raw Measurements JSONL| MetricsEngine
    MetricsEngine --> FeasibilityEval
    FeasibilityEval --> SearchController
    SearchController --> VerifRunner
    VerifRunner --> ReportBuilder
    ReportBuilder --> Dashboard
```

### Component Responsibilities

| Subsystem | Component | Implementation Path | Architectural Responsibility |
|---|---|---|---|
| **Contracts** | `Pydantic Data Models` | `src/slokern/contracts/` | Canonical schemas for specs, configurations, metrics, and verdicts (`enums.py`, `metrics.py`). |
| **Control Plane** | `FastAPI & SSE API` | `src/slokern/api/` | Accepts specifications, enforces experiment budgets, manages cancellation, streams progress. |
| **Serving** | `Serving Adapter` | `src/slokern/engine/serving/` | Manages runtime lifecycle; captures `environment_fingerprint`; reads back effective settings. |
| **Benchmarking** | `Subprocess Loadgen` | `src/slokern/engine/loadgen/` | Dispatches Poisson/constant arrival traffic; writes raw microsecond event timestamps to JSONL. |
| **Metrics** | `Metrics Engine` | `src/slokern/core/metrics/` | Computes percentiles (p50/p95/p99), throughput, error rates; separates offered from achieved load. |
| **Evaluator** | `Feasibility Evaluator` | `src/slokern/core/evaluator/` | Audits hard constraints; emits `FEASIBLE`, `INFEASIBLE`, or `INCONCLUSIVE` with reason codes. |
| **Search** | `Search Controller` | `src/slokern/core/search/` | Explores bounded 2×2 parameter matrix within budget; ranks feasible candidates by declared objective. |
| **Verification**| `Verification Runner` | `src/slokern/core/verification/`| Executes fresh independent rerun under new run ID; calculates drift deltas ($\Delta M$) and final verdict. |
| **Reporting** | `Report Builder` | `src/slokern/engine/reporting/` | Compiles immutable, publishable `ReportArtifact` linking all evidence, fingerprints, and limitations. |
| **Dashboard** | `Command Center` | `frontend/` | Cyberpunk-inspired technical UI displaying live monitor, candidate comparison, and audit reports. |

---

## 4. The 7-Step Execution Pipeline

SLOKern executes every experiment through a deterministic 7-step pipeline:

```text
1. Workload & SLO Specification
   Declare traffic arrival (Poisson/constant, rate, token limits) and hard constraints (TTFT p95 <= 250ms).
                ↓
2. Contract & Budget Validation
   Validate schemas and enforce candidate budget (<= 6 benchmark runs) before allocating GPU resources.
                ↓
3. Empirical Baseline Measurement
   Run default serving configuration to establish starting performance anchor and record raw JSONL traces.
                ↓
4. Bounded Candidate Search (4 runs)
   Sequentially benchmark fixed 2x2 candidate space; verify effective parameters via runtime read-back.
                ↓
5. Deterministic Feasibility Evaluation
   Calculate metrics from active measurement window; evaluate hard constraints; emit machine-readable reason codes.
                ↓
6. Objective Candidate Selection
   Filter out infeasible/inconclusive candidates; rank feasible candidates by declared efficiency objective.
                ↓
7. Independent Verification & Reporting
   Rerun winning candidate under fresh verification_run_id; compute drift; publish immutable ReportArtifact.
```

---

## 5. Four-Domain Lifecycle & State Separation

Naive benchmark harnesses collapse execution state, data quality, and SLO feasibility into a single status string. SLOKern maintains **four distinct state domains**:

```text
1. Execution Status:   PENDING → RUNNING → [ COMPLETED | FAILED | CANCELLED ]
2. Evidence Validity:  VALID | INVALID | CONTAMINATED
3. SLO Feasibility:    FEASIBLE | INFEASIBLE | INCONCLUSIVE
4. Verification State: NOT_RUN → VERIFYING → [ VERIFIED | VERIFICATION_FAILED | VERIFICATION_INCONCLUSIVE ]
```

### State Rules & Semantics

- **Execution Failed $\ne$ SLO Infeasible:** If a CUDA out-of-memory error, network abort, or bad credential causes an experiment run to crash, the run is marked `FAILED` in execution status. It is **never** recorded as an SLO breach (`INFEASIBLE`), because no valid inference distribution was observed.
- **Client Saturation $\to$ Contaminated:** If client load generator dispatch delay exceeds 10 ms or offered rate deviates by > 10%, the run is marked `generator_saturated = True`, evidence validity becomes `CONTAMINATED`, and feasibility is marked `INCONCLUSIVE` (`GENERATOR_SATURATED` / `CONTAMINATED_LOAD`). A contaminated run can never win selection.
- **Verification Independence:** Search evidence is never reused as verification. The winning candidate must independently reproduce feasibility under a new run ID.

---

## 6. Supported Models, Serving Path & Search Space

### 5-Concept Model Taxonomy

| Model Role | Model Identifier | Architecture & Specifications | Current Status |
|---|---|---|---|
| **1. Model-Agnostic Core** | Decoupled Engine | Contracts, evaluator, load generator, and search controllers are model-agnostic. | `VERIFIED` |
| **2. Hackathon Compliance Target** | `Nemotron-3-Nano-30B-A3B` (FP8) | Official NVIDIA open-weights family: Mamba-2 hybrid layers + MoE (~30B total, ~3B active per token in design), 262K context, FP8 quantization. Listed in Nebius catalog. | `PENDING RUNTIME VERIFICATION` (Blocked on live smoke test) |
| **3. Runtime-Verified Endpoint** | *Pending Smoke Test* | Exact API model string on Nebius (e.g. `nvidia/Nemotron-3-Nano-30B-A3B`). | `PENDING RUNTIME VERIFICATION` |
| **4. Internal Pipeline Baseline** | `meta-llama/Meta-Llama-3-8B-Instruct` | Preserved from ADR 0001-A for pipeline validation, fake-adapter tests, and regression fixtures. | `COMPARATIVE ONLY` (Does not satisfy NVIDIA model mandate alone) |
| **5. Secondary Comparison Model** | `nvidia/Llama-3.1-Nemotron-70B-Instruct` | Hypothetical secondary comparison model if quota and access permit. | `UNVERIFIED` |

### Serving Infrastructure
- **Platform:** Nebius AI Cloud GPU Compute (1× NVIDIA H100 80GB SXM5 or A100 80GB PCIe) / Nebius Token Factory inference runtime.
- **Serving Engine:** Containerized `vLLM` or OpenAI-compatible managed streaming endpoint.

### Bounded Configuration Space & Architectural Notice
- **Fixed 2×2 Search Space:** The candidate search is bounded to a 2×2 parameter matrix (4 candidates total). Its two specific dimensions and values are pending confirmation from the serving interface during live inspection.
- **Workload Controls vs. Serving-Engine Controls:**
  - *Workload Parameters (`concurrency_limit`, `max_tokens`):* Regulate client load generation. Changing workload knobs does **not** prove GPU-serving optimization.
  - *Serving-Engine Parameters (`max_num_seqs`, `gpu_memory_utilization`, `kv_cache_dtype`):* Reconfigure internal serving runtime and GPU memory layout.
- **Architectural Blocker Notice:** If the live endpoint exposes only client request parameters and lacks observable/tunable serving-engine controls, this constitutes an architectural blocker. An explicit architecture decision (deploying containerized vLLM on dedicated Compute instance or refining search boundaries via ADR) will be logged.

---

## 7. Fake-Adapter-First vs. Live Infrastructure

To protect GPU credit budgets and allow rapid offline iteration, SLOKern implements two implementations of `BaseServingAdapter`:

```mermaid
flowchart LR
    ExpController[Experiment Runner] --> BaseAdapter[BaseServingAdapter]
    BaseAdapter -->|Offline Dev & CI| FakeAdapter[FakeServingAdapter\nsrc/slokern/engine/serving/fake.py]
    BaseAdapter -->|Live Benchmarks| NebiusAdapter[NebiusServingAdapter\nsrc/slokern/engine/serving/nebius.py]
    
    FakeAdapter -->|Deterministic Synthetic Data| DemoData[Labeled: DEMO DATA]
    NebiusAdapter -->|Real NVIDIA H100 Timings| LiveData[Live Evidence Artifacts]
```

1. **Deterministic Fake Adapter (`fake.py`):**
   - Implements realistic synthetic latency distributions, simulated CUDA OOM failures, timeouts, and client saturation.
   - Powers automated unit tests, contract validation, and offline dashboard development.
   - **Mandatory Guardrail:** All synthetic runs and fixture outputs are persistently labeled **`DEMO DATA`**. Never presented as live GPU measurements.
2. **Real Nebius Adapter (`nebius.py`):**
   - Connects to the live Nebius endpoint; captures `environment_fingerprint` (CUDA version, driver, hardware ID) and verifies effective parameter settings.
   - Consumes GPU credits strictly for:
     1. Preflight integration smoke test (1 request).
     2. Empirical baseline measurement.
     3. Bounded 4-candidate search.
     4. Independent verification rerun.

---

## 8. Cost Accounting Policy & Systems Proxy

SLOKern enforces strict cost accounting boundaries to prevent fabricated claims:

### Mode A: Trustworthy Monetary Costing
- **Precondition:** Verifiable hourly GPU instance pricing or token billing rates are officially provided (e.g., Nebius cloud rate card) and stored with explicit currency, billing increment, and time basis.
- **Formula:**
  $$\text{Cost per 1k requests} = \frac{\text{Hourly GPU Rate}}{\text{Achieved Requests per Hour}} \times 1000$$

### Mode B: Non-Monetary Systems Proxy (Active Default)
- **Precondition:** Cloud provider pricing is missing, variable, or unverified.
- **Policy:** Monetary cost is explicitly declared **`unavailable`** (never guess or fabricate prices!).
- **Objective Ranking Proxy:**
  1. *Resource-Time:* GPU seconds consumed per successful request ($\Delta t \times N_{\text{GPUs}} / N_{\text{completed}}$). *(Note: If GPU instance count and dedicated residency cannot be verified, such as on managed serverless endpoints where physical GPU allocation is hidden, GPU-seconds per request is also reported as `unavailable`, and ranking falls back to Throughput Under SLO).*
  2. *Throughput Under SLO:* Maximum achieved output tokens/second while satisfying all hard latency constraints.
- **Rule:** A non-monetary proxy must **never** be described as monetary savings or dollar amounts. Disambiguate request throughput (completed requests/s) and achieved load from hardware GPU utilization (compute/memory occupancy %).

---

## 9. Current Implementation Status

| Subsystem / Deliverable | Status | Verified Evidence & Repository Reality |
|---|---|---|
| **Data Contracts** | `IMPLEMENTED` | Pydantic v2 schemas in `src/slokern/contracts/` (`enums.py`, `metrics.py`). |
| **Subsystem Modules** | `IMPLEMENTED (STUBS)` | `api/`, `cli/`, `core/`, `engine/` scaffolded with clear typed signatures. |
| **Fake Serving Adapter** | `IMPLEMENTED` | `src/slokern/engine/serving/fake.py` generates deterministic synthetic runs. |
| **Nebius Serving Adapter** | `IN PROGRESS` | `src/slokern/engine/serving/nebius.py` scaffolded; live HTTP streaming client in development. |
| **Preflight Smoke Test** | `PENDING EXECUTION` | Preflight check defined in `docs/deployment.md`; blocked on live Nebius instance access. |
| **Target Model Deployment** | `PENDING VERIFICATION` | `Nemotron-3-Nano-30B-A3B` (FP8) selected from catalog; endpoint reachability unverified. |
| **Live Benchmark Evidence** | `NOT RUN` | No live GPU benchmarks have been executed; zero fabricated claims. |
| **Demo Dashboard UI** | `IMPLEMENTED` | React + Vite command center in `frontend/`; offline fixtures labeled **`DEMO DATA`**. |
| **Daily Delivery Roadmap** | `DOCUMENTED` | Daily execution plan (Oct 19–30, 2026) established in `ROADMAP.md`. |

---

## 10. Quick Start & Execution Instructions

### Prerequisites
- Python 3.11+ (virtual environment recommended).
- Node.js 18+ (for frontend dashboard).
- Nebius Cloud API token (for live serving benchmarks; optional for fake-adapter testing).

### 10.1 Environment Setup

```bash
# Clone the repository
git clone https://github.com/slokern/slokern.git
cd slokern

# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install package in editable mode
pip install -e .

# Configure environment variables (copy example and add credentials)
cp .env.example .env
```

### 10.2 Run Offline Pipeline Validation (Fake Adapter)

```bash
# Run contract and unit tests
pytest tests/contracts tests/unit

# Validate an experiment specification
slokern validate experiments/configs/default.yaml

# Execute an offline demonstration experiment (uses deterministic fake adapter)
slokern optimize --config experiments/configs/default.yaml --adapter fake

# Independently verify a candidate run
slokern verify --run run-mock-001 --adapter fake
```

### 10.3 Launch Frontend Command Center

```bash
# Navigate to frontend directory and install dependencies
cd frontend
npm install

# Start local Vite development server
npm run dev
# Dashboard opens at http://localhost:5173 (labeled DEMO DATA in offline mode)
```

### 10.4 Live Serving Execution (Once Preflight Smoke Test Passes)

```bash
# 1. Execute live endpoint preflight smoke test (1 request, health check, model string)
slokern smoke-test --adapter nebius

# 2. Run bounded 6-run optimization campaign
slokern optimize --config experiments/configs/nebius_nemotron.yaml --adapter nebius

# 3. Independently verify the winning candidate
slokern verify --run <winning-run-id> --adapter nebius

# 4. Generate self-contained report artifact
slokern report --run <winning-run-id> --output artifacts/reports/
```

---

## 11. Testing, Validation & Reproducibility

SLOKern enforces scientific reproducibility through strict experimental controls:

1. **Hardware & Environment Lock:** Device model, driver version, CUDA runtime, and container commit are hashed into an immutable `environment_fingerprint`.
2. **Warm-Up Isolation:** Requests initiated during the warm-up window (`warmup_duration_s`) are tagged `is_warmup = true` and strictly excluded from percentile calculations.
3. **Offered vs. Achieved Separation:** Intended arrival rate is verified against delivered completions; client thread starvation triggers `generator_saturated = True`.
4. **Deterministic Percentiles:** Computed using linear interpolation (`percentile(..., method='linear')`); minimum sample thresholds enforced ($N \ge 10$ for p50, $N \ge 30$ for p95, $N \ge 100$ for p99).
5. **Fresh Verification ID:** Rerunning the winning configuration generates a fresh `verification_run_id`; search evidence is never copied.

---

## 12. Known Limitations & Risk Management

SLOKern explicitly discloses its boundaries:

- **Bounded Search Space:** Explores a focused 2×2 configuration space. Does not claim global optimality across all possible parameters.
- **Single Serving Environment:** Optimized for single-node containerized serving on Nebius Cloud; multi-node distributed serving is out of MVP scope.
- **Non-Monetary Default:** If official cloud pricing is unavailable, monetary cost is declared `unavailable` and systems efficiency is evaluated via resource-time or throughput proxies.
- **Contingency Runbook:** If live cloud endpoints encounter connectivity interruptions during demonstrations, the dashboard falls back to pre-recorded evidence bundles (`fixtures/demo/demo_experiment.json`) with persistent **`DEMO DATA`** labeling.

---

## 13. Daily Delivery Roadmap (Phases A–F)

Execution is structured into 6 sequential phases spanning **October 19 to October 30, 2026**, targeting the hard submission deadline on **October 30, 2026, at 10:00 AM PDT (10:30 PM IST)**:

```mermaid
flowchart LR
    PhaseA[Phase A: Audit & Freeze\nOct 19\nDONE] --> PhaseB[Phase B: Real Execution\nOct 20-22\nREADY]
    PhaseB --> PhaseC[Phase C: Validate Optimization\nOct 23-25\nPLANNED]
    PhaseC --> PhaseD[Phase D: Review & Reproducibility\nOct 26-27\nPLANNED]
    PhaseD --> PhaseE[Phase E: Defect Closure & Freeze\nOct 28-29\nPLANNED]
    PhaseE --> PhaseF[Phase F: Final Submission\nOct 30, 10:00 AM PDT\nPLANNED]
```

- **Phase A (Oct 19) — Audit and Scope Freeze:** Repository audit completed; working baseline established; core interfaces locked.
- **Phase B (Oct 20–22) — Establish Real Execution:** Finalize Nebius adapter; execute preflight smoke test; confirm NVIDIA model identifier; record baseline benchmark; Adriraj begins benchmark integrity audit on Oct 21.
- **Phase C (Oct 23–25) — Validate Optimization:** Execute bounded 2×2 candidate search (4 runs); evaluate hard SLO feasibility; select winning candidate; Daksh begins independent decision verification on Oct 24.
- **Phase D (Oct 26–27) — Independent Review & Reproducibility:** Execute independent verification rerun under fresh run ID; audit metric drift; complete test suites; compile report artifact.
- **Phase E (Oct 28–29) — Defect Closure & Freeze:** Feature freeze; close critical defects; automated test suite validation; clean clone installation check; record demo video ($\le 3$ minutes).
- **Phase F (Oct 30) — Submit:** Final repository audit; Devpost submission completed before 10:00 AM PDT (10:30 PM IST) with 4-hour buffer.

See **[ROADMAP.md](ROADMAP.md)** for complete daily task descriptions, deliverables, and acceptance gates.

---

## 14. Subsystem Ownership & Execution Model

SLOKern operates under a **single technical owner with bounded contributions from two collaborators** (a hybrid solo-core model):

- **Rajdeep:** Sole technical owner, architecture authority, critical-path implementer, integrator, and final submission owner.
- **Adriraj:** Benchmark integrity and measurement credibility (active execution begins **October 21, 2026**).
- **Daksh:** Independent correctness verification (active execution begins **October 24, 2026**).

Former team members (Aman on serving, Rohan on search) contributed early design work in Phase 1 (Oct 13–17, 2026). They are not participating in current execution, and no ongoing tasks are assigned to them.

| Area / Subsystem | Accountable Owner | Active Window | Historical Attribution |
|---|---|---|---|
| **Architecture & Technical Direction** | **Rajdeep** | Full sprint | Rajdeep |
| **Serving & Infrastructure** | **Rajdeep** | Full sprint | Aman |
| **Loadgen Subprocess & Workload** | **Rajdeep** | Full sprint | Adriraj |
| **Evaluator Core & Verification Runner** | **Rajdeep** | Full sprint | Daksh |
| **Optimizer & Search Controller** | **Rajdeep** | Full sprint | Rohan |
| **CI, API & End-to-End Integration** | **Rajdeep** | Full sprint | Cross-team |
| **Documentation, Demo & Submission** | **Rajdeep** | Full sprint | Rajdeep |
| **Benchmark Integrity & Credibility** | **Adriraj** | **Oct 21–30** | Adriraj |
| **Independent Decision Verification** | **Daksh** | **Oct 24–30** | Daksh |

For the complete responsibility matrix, collaborator workstream boundaries, and daily rituals, see **[docs/ownership.md](docs/ownership.md)**.

---

## 15. Related Documentation & In-Depth Guides

- [Architecture & Contract Specification](docs/architecture.md)
- [Single-Owner Execution & Responsibility Matrix](docs/ownership.md)
- [Architecture Decision Log](docs/decision-log.md)
- [MVP Scope & Acceptance Checklist](docs/mvp-checklist.md)
- [Daily Integration Checklist & Protocol](docs/integration-checklist.md)
- [Decision Policy & Feasibility Semantics](docs/decision-policy.md)
- [Metrics Definitions & Aggregation Rules](docs/metrics.md)
- [Experiment & Measurement Methodology](docs/experiment-methodology.md)
- [Serving Deployment & Operational Guide](docs/deployment.md)
- [Demo Presentation Script & Runbook](docs/demo-script.md)
- [Official Hackathon Compliance & Requirements Matrix](docs/hackathon-compliance.md)
- [Project Flow & Mental Model Guide](docs/project-flow-and-mental-model.md)
- [Nebius & NVIDIA Tool Feedback Register](docs/hackathon-feedback.md)

---

## Final Operating Principle

Build the smallest complete system that can **measure, decide, verify, and explain**.

SLOKern does not claim universal optimality. It proves that its recommendation follows from controlled measurements, deterministic rules, a declared objective, and an independent verification run.

**Optimize inference. Verify performance.**
