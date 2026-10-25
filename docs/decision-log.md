# SLOKern Architecture Decision Log

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Project Decision Register  
> **Owner:** Rajdeep (Technical Lead / Architecture)  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

---

## 1. Decision Log Protocol

This document serves as the historical record of architectural, scope, technical, and process decisions for SLOKern. Any substantive change affecting system boundaries, shared contracts, measurement semantics, cost policies, or external claims must be recorded here using the standardized template below.

### Decision Record Template

```text
Decision ID: DEC-XXXX
Date: YYYY-MM-DD
Question: [Concise statement of the architectural or engineering dilemma]
Options Considered:
  1. [Option A]
  2. [Option B]
Decision: [The chosen direction]
Reason: [Core rationale and engineering justification]
Owner: [Accountable owner]
Affected Contracts/Components: [List of impacted modules, contracts, or docs]
Evidence: [Tests, benchmarks, platform docs, or reference materials supporting the choice]
Trade-offs: [Accepted downsides or limitations]
Revisit Condition: [Trigger under which this decision should be re-evaluated]
```

---

## 2. Active Decision Register

### DEC-0001: Model and Serving Runtime Target for MVP
- **Date:** 2026-10-13
- **Question:** Which model and serving runtime should SLOKern target for the hackathon MVP?
- **Options Considered:**
  1. Multi-model, multi-cloud deployment (vLLM, TGI, Triton across AWS, GCP, and Nebius).
  2. A single NVIDIA-supported open-source model (e.g., Llama-3-8B-Instruct or Mistral-7B) hosted on Nebius Cloud GPU infrastructure using vLLM or TensorRT-LLM.
  3. Local mock-only model without real cloud GPU serving.
- **Decision:** Option 2. Focus on a single permitted NVIDIA open-source model running on Nebius GPU infrastructure with a dedicated serving engine (vLLM/TensorRT-LLM).
- **Reason:** Satisfies the core principle: "One model, one serving environment, a small configuration space, reproducible experiments." Multi-cloud or multi-model support introduces massive operational complexity without improving the defensibility of the core optimization thesis.
- **Owner:** Aman (Serving/GPU Infrastructure) & Rajdeep
- **Affected Contracts/Components:** `CandidateConfig`, `RunRecord`, `src/slokern/engine/serving/nebius.py`, `docs/deployment.md`
- **Evidence:** Nebius platform documentation and hackathon GPU quota guidelines.
- **Trade-offs:** Optimization results are specific to the tested model and hardware tier; no claim of cross-platform portability.
- **Revisit Condition:** If Nebius infrastructure is unavailable or fails the Phase 1 smoke test by Oct 15, fall back to a pre-approved alternative runtime.

---

### DEC-0002: Bounded Empirical Search with Mandatory Independent Verification
- **Date:** 2026-10-13
- **Question:** How should SLOKern discover optimal serving configurations and prevent false winners from noisy runs?
- **Options Considered:**
  1. Continuous black-box Bayesian optimization or genetic algorithms running unbounded iterations.
  2. A single benchmark run of multiple candidates, selecting the lowest-cost configuration with no verification.
  3. A bounded search (reference baseline + controlled grid/random candidates within a strict budget) paired with an independent verification run under a new run ID.
- **Decision:** Option 3. Bounded candidate search with mandatory independent verification.
- **Reason:** LLM inference measurements exhibit significant variance. Selecting a winner from a single lucky search run often produces false positives. Rerunning the winner independently under a fresh `run_id` provides empirical verification that the configuration genuinely satisfies the SLO.
- **Owner:** Rohan (Search) & Daksh (Verification)
- **Affected Contracts/Components:** `SearchResult`, `VerificationRecord`, `src/slokern/core/search/`, `src/slokern/core/verification/`
- **Evidence:** Benchmarking noise profiles documented in inference literature.
- **Trade-offs:** Verification consumes additional experiment budget (at least one full workload rerun).
- **Revisit Condition:** If experiment budgets are critically constrained, reduce candidate count rather than eliminating independent verification.

---

### DEC-0003: Contract-First Architecture with Pydantic v2
- **Date:** 2026-10-14
- **Question:** How should shared schemas be authored and synchronized across the Python backend, CLI, and TypeScript frontend?
- **Options Considered:**
  1. Hand-coded schema dictionaries in Python and manually duplicated TypeScript interfaces.
  2. JSON Schema specifications as the primary source of truth, generating code for all languages.
  3. Pydantic v2 models in Python as the canonical source of truth in `src/slokern/contracts/`, with automated generation of JSON Schema and TypeScript type definitions.
- **Decision:** Option 3. Pydantic v2 as canonical source of truth.
- **Reason:** Pydantic v2 provides high-performance validation, native FastAPI integration, rich validation error reporting, and straightforward export to JSON Schema and TypeScript.
- **Owner:** Rajdeep (Technical Lead / Architecture)
- **Affected Contracts/Components:** `src/slokern/contracts/`, `frontend/src/generated/`, `schemas/`
- **Evidence:** Fast prototyping and contract integrity across API routes and test fixtures.
- **Trade-offs:** Requires running code generation scripts (`scripts/generate_schemas.py`) when backend contracts change.
- **Revisit Condition:** None; locked for MVP.

---

### DEC-0004: Dual-Mode Cost Accounting Policy
- **Date:** 2026-10-14
- **Question:** How should candidate cost and cost savings be calculated when cloud pricing may not be officially published or accessible via API?
- **Options Considered:**
  1. Assume standard public hyperscaler pricing (e.g., \$2.50/hr for an A100/H100) and present estimated dollar savings.
  2. Exclude cost entirely from the product and focus purely on throughput.
  3. Establish a dual-mode policy: if authoritative provider pricing is verified, calculate monetary cost per request/token; if unverified or missing, report monetary cost as `unavailable` and optimize for a declared non-monetary proxy (resource-time or throughput under SLO).
- **Decision:** Option 3. Dual-mode cost policy with mandatory price source disclosure or `unavailable` declaration.
- **Reason:** Fabricating cloud prices destroys credibility. Never present estimated or heuristic prices as measured facts. Non-monetary efficiency metrics (GPU seconds per request or throughput under SLO) provide a valid, defensible optimization objective when dollar costs cannot be proven.
- **Owner:** Rajdeep (Architecture) & Aman (Infrastructure)
- **Affected Contracts/Components:** `src/slokern/core/cost/`, `ReportArtifact`, `SearchResult`, `docs/metrics.md`
- **Evidence:** AGENTS.md Section 1 ("Never fabricate prices") and README.md Section 4.
- **Trade-offs:** In the absence of confirmed pricing, the UI cannot show a dollar figure; it displays systems efficiency metrics instead.
- **Revisit Condition:** When official Nebius hackathon pricing documentation is signed off by Aman.

---

### DEC-0005: Decoupled Four-Domain Lifecycle State Model
- **Date:** 2026-10-15
- **Question:** How should execution health, measurement quality, SLO feasibility, and verification status be modeled?
- **Options Considered:**
  1. A single unified status string (e.g., `STATUS: PASSED`, `STATUS: FAILED`, `STATUS: RUNNING`).
  2. Two statuses: Execution Status and Feasibility Status.
  3. Four independent status domains:
     - `ExecutionStatus`: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`
     - `EvidenceValidity`: `VALID`, `INVALID`, `CONTAMINATED`
     - `FeasibilityVerdict`: `FEASIBLE`, `INFEASIBLE`, `INCONCLUSIVE`
     - `VerificationState`: `NOT_RUN`, `VERIFYING`, `VERIFIED`, `VERIFICATION_FAILED`, `VERIFICATION_INCONCLUSIVE`
- **Decision:** Option 3. Four independent state domains.
- **Reason:** Conflating execution failures (e.g., GPU crash or timeout) with SLO failures (e.g., TTFT p95 exceeded) destroys diagnostic clarity. Similarly, noisy or contaminated runs must result in `INCONCLUSIVE`, not a false `FEASIBLE` or `INFEASIBLE`.
- **Owner:** Daksh (Evaluation) & Rajdeep (Architecture)
- **Affected Contracts/Components:** `RunRecord`, `FeasibilityResult`, `VerificationRecord`, `src/slokern/core/evaluator/`, `src/slokern/api/routes/`
- **Evidence:** Test cases in `tests/unit/core/evaluator/test_evaluate.py`.
- **Trade-offs:** Slightly more complex status rendering in dashboard badges.
- **Revisit Condition:** None; fundamental to auditability.

---

### DEC-0006: Subprocess Isolation for Load Generation
- **Date:** 2026-10-15
- **Question:** How should the load generator be executed to ensure high timing fidelity without interference from the web API or dashboard?
- **Options Considered:**
  1. In-process `asyncio` tasks within the FastAPI application event loop.
  2. Distributed task queue (Celery + Redis + remote load generator nodes).
  3. Dedicated Python subprocess spawned by the experiment worker, logging events to disk.
- **Decision:** Option 3. Subprocess load generation.
- **Reason:** In-process load generation suffers from event loop latency jitter caused by API requests, SSE broadcasting, and garbage collection. A dedicated subprocess provides clean isolation and reliable microsecond-level request dispatch without the operational overhead of Celery or Redis.
- **Owner:** Adriraj (Benchmarking)
- **Affected Contracts/Components:** `src/slokern/engine/loadgen/runner.py`, `src/slokern/engine/runner/experiment_controller.py`
- **Evidence:** Benchmarking experiments showing event loop skew under concurrent API load.
- **Trade-offs:** Subprocess lifecycle and cancellation require process signaling and PID management.
- **Revisit Condition:** If single-node load generator cannot generate sufficient traffic to saturate the serving endpoint.

---

### DEC-0007: Benchmarking Owner Alignment (Adriraj)
- **Date:** 2026-10-17
- **Question:** Confirming the owner of the benchmarking and load generation workstream across documentation and codebases.
- **Decision:** Adriraj is the designated and sole owner of the Benchmarking workstream (`src/slokern/engine/loadgen/`, `src/slokern/core/metrics/`, `docs/experiment-methodology.md`, `docs/metrics.md`).
- **Reason:** Full alignment across `AGENTS.md`, `README.md`, `ROADMAP.md`, code docstrings, and documentation.
- **Owner:** Rajdeep
- **Affected Contracts/Components:** All documentation files, tests, and core metric modules.
- **Evidence:** Completed repository-wide owner reconciliation.
- **Trade-offs:** None.

---

### DEC-0008: Repository Structure Consolidation (`src/slokern/`)
- **Date:** 2026-10-18
- **Question:** Reconciling the package layout between the proposed README layout (`slokern/`) and the existing codebase layout (`src/slokern/`).
- **Options Considered:**
  1. Move existing files from `src/slokern/` to root `slokern/`.
  2. Keep `src/slokern/` as the standard modern Python layout and clarify documentation.
- **Decision:** Option 2. Retain `src/slokern/` and document it as the canonical package root.
- **Reason:** The `src/` layout prevents accidental imports of uninstalled in-development packages, enforces clean package installation via `uv`, and matches the existing codebase scaffolding.
- **Owner:** Rajdeep
- **Affected Contracts/Components:** `docs/architecture.md`, `README.md`, `pyproject.toml`
- **Evidence:** Standard Python packaging best practices (PyPA recommendation).
- **Trade-offs:** Slight divergence from initial README diagram, clarified in documentation.
- **Revisit Condition:** None.

---

### DEC-0009: Official NVIDIA Model Compliance Target & 5-Tier Architecture Reconciliation
- **Date:** 2026-10-18
- **Question:** How should SLOKern reconcile its accepted serving target (`meta-llama/Meta-Llama-3-8B-Instruct`) with the official hackathon rule mandating an NVIDIA open-source model?
- **Options Considered:**
  1. Continue relying solely on `meta-llama/Meta-Llama-3-8B-Instruct` and argue that it is NVIDIA-optimized. (Rejected: High risk of disqualification).
  2. Switch to `nvidia/Llama-3.1-Nemotron-70B-Instruct` as the only target. (Rejected: 70B parameter model is unverified in the team's catalog and cannot fit on a single 80GB GPU instance without multi-GPU tensor parallelism or heavy quantization).
  3. Select `Nemotron-3-Nano-30B-A3B` (FP8) as the primary **Hackathon Compliance Target Model Candidate** on Nebius Cloud, while retaining `meta-llama/Meta-Llama-3-8B-Instruct` as an internal pipeline development and comparison baseline.
- **Decision:** Option 3. Select `Nemotron-3-Nano-30B-A3B` (FP8) from the Nebius catalog as the primary compliance target candidate.
- **Reason:** `Nemotron-3-Nano-30B-A3B` satisfies the official NVIDIA open-source model mandate. Design specifications cite a hybrid Mamba-2 MoE architecture (~30B total, ~3B active parameters per token in design) with FP8 quantization. Serving throughput, memory pressure, and latency percentiles are unmeasured and subject to empirical measurement during live runs.
- **Owner:** Rajdeep (Architecture) & Aman (Serving Infrastructure)
- **Affected Contracts/Components:** `docs/adr/0001-model-runtime.md` (Addendum 0001-B), `docs/deployment.md`, `docs/hackathon-compliance.md`
- **Evidence:** Official Devpost Rules (§ Technical Requirements) and Nebius Token Factory catalog specifications.
- **Trade-offs:** The exact Nebius API identifier string and catalog access in the team's account are pending runtime verification via preflight smoke test before live benchmarks are claimed.
- **Revisit Condition:** When Aman completes preflight smoke test on Nebius.

---

### DEC-0010: Experiment Budget Lock (Strict 6 Benchmark Runs, Fixed 2×2 Search Space) & Parameter Legality
- **Date:** 2026-10-18
- **Question:** How do we constrain the benchmark execution budget to protect hackathon GPU credits while ensuring statistically sound and reproducible optimization?
- **Decision:**
  1. **Strict Six-Run Benchmark Budget:** The benchmark budget is defined as exactly six benchmark runs: 1 Baseline + 4 Candidates + 1 Independent Verification Rerun under a fresh `verification_run_id`.
  2. **Preflight Smoke Test Separated:** The preflight smoke test is a separate preliminary single-request verification (checking connectivity, model ID, and streaming headers) and is **not counted among the six benchmark runs**.
  3. **Fixed 2×2 Search Space:** Candidate exploration is restricted to four candidates. Current code defines `max_num_batched_tokens ∈ {1024, 2048}` and `max_num_seqs ∈ {16, 64}`; whether the selected runtime accepts and applies these values remains pending preflight read-back.
  4. **Distinguishing Client/Workload vs. Serving-Engine Knobs:**
     - Client/workload knobs (e.g. client concurrency limit, request output token limits) govern client request dispatch. **Changing workload parameters does not prove GPU-serving optimization.**
     - Serving-engine knobs (e.g. batch concurrency, GPU memory utilization, max model length) govern the internal serving runtime on the GPU.
     - Neither set of parameters is confirmed supported until verified by runtime read-back on the live Nebius endpoint.
  5. **Architectural Blocker Notice:** If the chosen endpoint interface (such as a managed Token Factory endpoint) exposes only client request parameters and lacks serving-engine controls, this constitutes an architectural blocker. Resolving this blocker requires an explicit architecture decision by Rajdeep and Aman (such as deploying containerized vLLM on a dedicated Nebius Compute GPU instance).
  6. **Duration Policy & Calibration:** The original 60s warm-up + 180s measurement schedule remains **labelled illustrative**. Proposed shorter durations remain **strictly unvalidated** until actual timing, overhead, and measurement-quality evidence is gathered during live runs.
  7. **Fake-Adapter-First Workflow:** Implement and validate the feasibility evaluator, metrics pipeline, search controller, report generator, and dashboard primarily against the deterministic fake adapter (`DEMO DATA` labeled) before consuming real GPU credits.
- **Implementation status (2026-10-23):** `generate_2x2_candidates()` now generates `{1024, 2048} × {16, 64}`, but this does not prove those controls are applied remotely. `BudgetLimiter` remains configurable and can spend the verification reserve (`BLK-15`); the current Nebius adapter does not read back remote flags (`BLK-17`). The proposed five-point profile is tracked separately in DEC-0013.
- **Owners:** Rajdeep (Architecture), Aman (Serving), Rohan (Search), Daksh (Evaluator), Adriraj (Benchmarking)
- **Affected Contracts/Components:** `docs/deployment.md`, `docs/architecture.md`, `README.md`, `ROADMAP.md`

---

### DEC-0011: Transition to Single-Owner Technical Execution Led by Rajdeep
- **Date:** 2026-10-18
- **Question:** How should engineering ownership, integration authority, and delivery accountability be structured for the remaining hackathon period (October 18–30, 2026)?
- **Options Considered:**
  1. Maintain the distributed 5-person team plan with separate daily standups and workstream handoffs.
  2. Consolidate all technical ownership, integration authority, and delivery responsibilities under Rajdeep as sole technical owner.
- **Decision:** Option 2. Transition to single-owner technical execution led by Rajdeep.
- **Reason:** The post-October 18 execution window requires rapid, decisive end-to-end integration and rigorous evidence collection. Consolidating all engineering responsibilities under Rajdeep eliminates inter-member coordination overhead and synchronization delays while preserving the modular subsystem boundaries, typed contracts, and deterministic invariants already established.
- **Owner:** Rajdeep (Sole Technical Owner & Integration Authority)
- **Affected Contracts/Components:** `AGENTS.md`, `README.md`, `ROADMAP.md`, `docs/ownership.md`, `docs/architecture.md`, `docs/mvp-checklist.md`, `docs/integration-checklist.md`
- **Evidence:** Repository audit confirming modular contracts (`src/slokern/contracts/`) allow unified execution without code rewrites.
- **Trade-offs:** Increases individual workload on Rajdeep; requires strict prioritization of core MVP capabilities over secondary extras.
- **Revisit Condition:** None; locked for hackathon execution.

---

### DEC-0012: Hybrid Solo-Core Execution Restructure & Daily Delivery Roadmap
- **Date:** 2026-10-19
- **Question:** How should subsystem ownership, collaborator contributions, and the daily execution schedule from October 19 through October 30 be structured to guarantee a defensible, evidence-backed delivery by October 30, 2026?
- **Options Considered:**
  1. Continue purely solo execution by Rajdeep without external audits or collaboration.
  2. Establish a hybrid solo-core execution model: Rajdeep owns the critical path and final integration; Adriraj executes a bounded benchmark-integrity audit starting October 21; Daksh executes an independent decision-verification audit starting October 24. Former members Aman and Rohan are acknowledged historically with no ongoing tasks.
- **Decision:** Option 2. Adopt the hybrid solo-core execution model with an explicit daily roadmap (Oct 19–30).
- **Reason:** Enhances measurement credibility and decision correctness through independent audits while keeping critical-path momentum unimpeded. Rajdeep remains capable of delivering the complete MVP independently without waiting for either collaborator. Explicit start dates (Oct 21 for Adriraj, Oct 24 for Daksh) align with collaborator availability without creating false dependencies.
- **Owner:** Rajdeep (Sole Technical Owner & Integration Authority)
- **Affected Contracts/Components:** `ROADMAP.md`, `README.md`, `AGENTS.md`, `docs/ownership.md`, `docs/mvp-checklist.md`, `docs/integration-checklist.md`, `docs/architecture.md`
- **Evidence:** Documented daily deliverables and acceptance criteria in `ROADMAP.md` covering every date from October 19 through October 30.
- **Trade-offs:** Requires Rajdeep to package sample schemas and records for Adriraj by Oct 21, and stable contracts/fixtures for Daksh by Oct 23.
- **Revisit Condition:** None; locked through final submission on October 30, 2026.

### DEC-0013: Reconcile the Controlled Deployment and Search Profile (OPEN)
- **Date:** 2026-10-23
- **Question:** What exact Nemotron checkpoint, Nebius hosting mode, vLLM release, launch-time search matrix, and benchmark protocol should the live campaign use?
- **Options Considered:**
  1. Continue with accepted ADR 0001-B's `Nemotron-3-Nano-30B-A3B` (FP8) family, verify the exact model revision, and use a Nebius Serverless AI custom container with H100 subject to account and runtime checks.
  2. Use the prior `deployment-decision-2026-10-23.md` alternative: Nemotron Nano 9B v2 on an H100 VM.
  3. Defer selection until the 30B deployment profile and vLLM 0.12.0 are smoke-tested and account constraints are known.
- **Decision:** **OPEN; no new deployment or search-profile decision is ratified by this documentation task.** ADR 0001-B remains the accepted model-family decision. The 30B exact checkpoint string, Serverless endpoint, vLLM 0.12.0, and the proposed five-point values remain planned pending compatibility and account validation. The 9B VM memo is an alternative study, not an amendment to the accepted ADR.
- **Reason:** Avoid replacing an accepted model decision with an unverified research alternative or documenting proposed flags as applied. Actual source still generates `{1024, 2048} × {16, 64}` candidates; it does not generate the new proposed `{2048, 16384} × {64, 256}` matrix or the `(128, 8192)` centre baseline.
- **Owner:** Rajdeep (Sole Technical Owner & Integration Authority)
- **Affected Contracts/Components:** `docs/deployment.md`, `docs/experiment-methodology.md`, `docs/metrics.md`, `docs/decision-policy.md`, `docs/deployment-decision-2026-10-23.md`, `src/slokern/core/search/`, `src/slokern/engine/serving/nebius.py`
- **Evidence:** Accepted `docs/adr/0001-model-runtime.md` Addendum 0001-B; current source reads in `src/slokern/core/search/{space.py,budget.py,grid.py,rank.py}` and `src/slokern/engine/serving/nebius.py`. No provider API or live deployment was checked in this documentation task.
- **Trade-offs:** The deployment and experiment schedule remain blocked until the owner resolves model revision, account capacity, container support, configuration application/read-back, and run-count policy. Provider startup, pilot, replicate, and teardown time still incur operational cost even if excluded from the controller's counted runs.
- **Revisit Condition:** After the owner accepts an ADR addendum/profile and a bounded preflight confirms effective runtime settings and model readiness.

---

## 3. Pending Decisions to Finalize

The following technical decisions remain open and are assigned to Rajdeep for resolution during Phases A and B (October 19–22):

1. **Deployment Profile (Rajdeep / DEC-0013):** Confirm the exact 30B model and tokenizer revisions, Serverless AI custom-container support, H100 quota/capacity, and vLLM 0.12.0 compatibility. No live access was checked in this documentation task.
2. **Search Profile and Budget (Rajdeep / DEC-0013, BLK-15–BLK-17):** Resolve the proposed `(128, 8192)` baseline and `{64, 256} × {2048, 16384}` candidate matrix against the current `{16, 64} × {1024, 2048}` generator, enforce a verification reserve, and verify every searched flag through runtime read-back.
3. **Official Deadline & Submission Verification (Rajdeep / Confirmed: Oct 19):** Target deadline confirmed: **October 30, 2026, 10:00 AM PDT / 10:30 PM IST**.

---

## 4. Related Documentation

- [Hackathon Compliance Matrix](hackathon-compliance.md)
- [System Architecture](architecture.md)
- [MVP Checklist & Scope Boundaries](mvp-checklist.md)
- [Engineering Ownership & Execution Model](ownership.md)
- [ADR 0001: MVP Scope & Evidence Policy](adr/0001-mvp-scope-and-evidence.md)
- [ADR 0002: Dual-Mode Cost Accounting](adr/0002-cost-model.md)



