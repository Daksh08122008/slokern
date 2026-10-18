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

## 3. Pending Decisions to Finalize

The following decisions remain open and are assigned for resolution during Phases 1 and 2:

1. **Exact Nebius GPU Instance & Runtime Revision (Aman / Oct 15):** Finalize exact GPU model (e.g., 1× H100 80GB SXM) and serving container version (vLLM version).
2. **Confirmed Search Space Dimensions (Aman & Rohan / Oct 18):** Confirm whether `kv_cache_dtype` (fp8 vs. fp16) and `gpu_memory_utilization` are reliably tunable on the deployed instance.
3. **Official Deadline & Submission Verification (Rajdeep / Oct 18):** Reconfirm target deadline of October 30, 2026, 10:00 AM PDT / 10:30 PM IST with hackathon organizers.

---

## 4. Related Documentation

- [System Architecture](architecture.md)
- [MVP Checklist & Scope Boundaries](mvp-checklist.md)
- [Ownership & Team Matrix](ownership.md)
- [ADR 0001: MVP Scope & Evidence Policy](adr/0001-mvp-scope-and-evidence.md)
- [ADR 0002: Dual-Mode Cost Accounting](adr/0002-cost-model.md)

