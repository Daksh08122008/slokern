# SLOKern Engineering Roadmap & Practical Execution Guide

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Document Type:** Canonical Engineering Delivery Roadmap & Practical Operating Guide  
> **Authority:** Aligned with [README.md](README.md), [docs/implementation-status.md](docs/implementation-status.md), [docs/ownership.md](docs/ownership.md), and [AGENTS.md](AGENTS.md)  
> **Sole Technical Owner & Integration Authority:** Rajdeep  
> **Collaborator Workstreams:** Adriraj (Benchmark Integrity, active Oct 21–30), Daksh (Decision Verification, active Oct 24–30)  
> **Submission Deadline:** October 30, 2026, 10:00 AM PDT (10:30 PM IST / 17:00:00 UTC)  
> **Last Verified:** 2026-10-21 12:20:00 UTC (Sprint Day 3 / Active Milestone: Phase B)  

---

## 1. Executive Execution Dashboard

### 1.1 Sprint Snapshot & Milestone Window
- **Current Milestone:** **Phase B: Establish Single-Run Execution** (Window: October 21–23, 2026).
- **Execution Model:** Single-owner core execution (Rajdeep) with bounded collaborators (Adriraj active Oct 21, Daksh active Oct 24).
- **Current Critical-Path Tasks:**
  - [`TASK-04`](#task-04--harden-evaluator-boundary-conditions-nan-and-negative-metric-safety): Harden Evaluator Boundary Conditions (NaN and negative metric safety).
  - [`TASK-05`](#task-05--implement-deterministic-fake-serving-adapter): Implement Deterministic Fake Serving Adapter (`FakeServingAdapter`).
  - [`TASK-03`](#task-03--export-committed-json-schemas-and-strict-contract-boundaries): Export Committed JSON Schemas and Strict Contract Boundaries (`ConfigDict(extra='forbid')`).

### 1.2 Immediate Next 1–3 Actions
1. **Action 1 (Rajdeep — TASK-04):** Patch `src/slokern/core/evaluator/evaluate.py` to assert non-negative latencies and evaluate `math.isnan(obs_val)` as `FeasibilityVerdict.INCONCLUSIVE` (closes [`BLK-05`](#61-active-blockers-register) & [`BLK-06`](#61-active-blockers-register)).
2. **Action 2 (Rajdeep — TASK-05):** Implement `FakeServingAdapter` in `src/slokern/engine/serving/fake.py` generating deterministic synthetic request responses labeled **`DEMO DATA`** (closes [`BLK-01`](#61-active-blockers-register)).
3. **Action 3 (Rajdeep — TASK-03):** Implement `scripts/gen_contracts.py` exporting canonical JSON schemas to `schemas/` and add `extra='forbid'` to all 11 contract classes in `src/slokern/contracts/` (closes [`BLK-10`](#61-active-blockers-register) & [`BLK-12`](#61-active-blockers-register)).

### 1.3 Active Blockers & Responsible Owners
| Blocker ID | Priority | Summary | Accountable Owner | Direct Remediation Action | Closing Validation |
|---|---|---|---|---|---|
| **BLK-01** | **P0** | Serving adapter files are empty stubs; cannot execute inference requests. | Rajdeep | Implement `FakeServingAdapter` generating synthetic responses. | `pytest tests/unit/engine/serving/test_fake.py` |
| **BLK-04** | **P0** | Nebius API model string for `Nemotron-3-Nano-30B-A3B` unverified; live test skips. | Rajdeep | Execute live single-request preflight probe against Nebius endpoint. | `pytest tests/live/test_smoke_live.py -v -m live` |
| **BLK-05** | **P1** | Evaluator routes `float('nan')` to `INFEASIBLE` with `TTFT_P95_EXCEEDED` instead of `INCONCLUSIVE`. | Rajdeep | Add `math.isnan(obs_val)` check in `evaluate.py`. | `pytest tests/unit/core/test_evaluator.py` |
| **BLK-06** | **P1** | Evaluator accepts negative latencies (e.g. `-10.0 ms`) as `FEASIBLE`. | Rajdeep | Add physical non-negative assertion (`obs_val >= 0`) in `evaluate.py`. | `pytest tests/unit/core/test_evaluator.py` |
| **BLK-10** | **P1** | `schemas/` contains only `.gitkeep`; JSON schemas not emitted. | Rajdeep | Complete `scripts/gen_contracts.py` and commit 11 `.json` schemas. | `pytest tests/contract/test_generated_files_current.py` |
| **BLK-12** | **P2** | Contracts accept unrecognized fields silently (`extra='ignore'`). | Rajdeep | Add `model_config = ConfigDict(extra='forbid')` to all 11 contracts. | `pytest tests/contract/test_schemas.py` |
| **BLK-11** | **P2** | Float vs integer formatting (`1` vs `1.0`) produces differing candidate IDs. | Rajdeep | Canonicalize numeric types prior to hashing in `candidate_id.py`. | `pytest tests/unit/core/test_ranker.py` |
| **BLK-08** | **P1** | `compare.py` is an empty docstring; cannot compute metric drift ($\Delta M$). | Rajdeep | Implement drift calculation comparing two `MetricSet` instances. | `pytest tests/unit/core/verification/test_compare.py` |
| **BLK-09** | **P1** | `report_builder.py` is an empty docstring; cannot serialize `ReportArtifact`. | Rajdeep | Implement Markdown serializer for immutable report artifacts. | `pytest tests/unit/engine/reporting/test_report_builder.py` |
| **BLK-13** | **P2** | CI workflow lacks linting, mypy type checks, and secret scanning. | Rajdeep | Add ruff, mypy, and secret checks to `.github/workflows/ci.yml`. | GitHub Actions CI run |

### 1.4 Most Recent Validation Evidence
- **Test Suite Status:** `.venv\Scripts\pytest -v -m "not live"` $\longrightarrow$ **24 passed, 1 deselected, 0 failed in 0.92s** (clean, non-flaky execution).
- **Dependency & Bytecode Hygiene:** `python -m pip check` $\longrightarrow$ **No broken requirements found.**; `python -m compileall -q src tests` $\longrightarrow$ **0 syntax errors across all 90 source modules and 67 test files**.
- **Working Tree Hygiene:** Core application code clean; documentation baseline actively maintained on branch `repository-audit-and-mvp-scope-freeze`.

### 1.5 Scope Classification: Submission-Critical vs. Deferred
- **Submission-Critical MVP Scope (IN):**
  - Contract validation and strict boundary enforcement (`src/slokern/contracts/`).
  - Deterministic Fake Serving Adapter for offline testing and CI (`src/slokern/engine/serving/fake.py`).
  - Nebius Cloud live serving adapter for NVIDIA H100 inference (`src/slokern/engine/serving/nebius.py`).
  - Subprocess load generator with microsecond JSONL event logging (`src/slokern/engine/loadgen/`).
  - Deterministic metrics engine computing TTFT/ITL percentiles and throughput (`src/slokern/core/metrics/`).
  - Deterministic feasibility evaluator with hard constraints and reason codes (`src/slokern/core/evaluator/`).
  - Fixed 2×2 bounded search controller (5 runs = 1 baseline + 4 candidates) (`src/slokern/core/search/`).
  - Deterministic candidate ranking under Mode B systems proxy (`src/slokern/core/search/rank.py`).
  - Independent verification rerun under a fresh `verification_run_id` (Run 6) (`src/slokern/core/verification/`).
  - Self-contained Markdown `ReportArtifact` linking metrics to raw JSONL traces (`src/slokern/engine/reporting/`).
  - Minimal terminal CLI runner (`slokern verify / optimize / smoke-test`) (`src/slokern/cli/`).
- **Formally Deferred Work (POST-HACKATHON / OUT OF CRITICAL PATH):**
  - FastAPI control plane REST API and Server-Sent Events (`src/slokern/api/` / [`TASK-17`](#task-17--control-plane-rest-api-and-sse-streaming)).
  - React + Vite web dashboard command center (`frontend/` / [`TASK-18`](#task-18--frontend-command-center-react-ui)).
  *(Rationale: Freeze non-essential UI/API to eliminate concentration risk [BLK-07] and protect delivery of the core verified inference pipeline).*

---

## 2. Status Vocabulary & Evidence Framework

To eliminate ambiguous or conflicting progress claims, this repository enforces a unified, evidence-based status taxonomy distinguishing **task progress**, **subsystem maturity**, and **validation levels**.

### 2.1 Task Status Vocabulary
| Status | Meaning | Entry Precondition | Evidence Required to Exit |
|---|---|---|---|
| **`NOT STARTED`** | Work has not begun; upstream dependencies are incomplete. | Dependent on preceding tasks. | None. |
| **`READY`** | All direct upstream dependencies are satisfied; work can be picked up immediately. | Preceding tasks marked `DONE`. | Implementation started. |
| **`IN PROGRESS`** | Actively under development or validation by the assigned owner. | Assigned owner actively modifying files. | PR or commit with passing narrow tests. |
| **`BLOCKED`** | Cannot proceed due to an explicit defect (`BLK-xx`), missing upstream output, or unresolved architectural decision (`DEC-xx`). | Documented blocker entry with root cause. | Blocker remediation merged and verified. |
| **`DONE`** | Fully implemented, adheres to contracts, passes automated validation, backed by physical artifacts. | All acceptance criteria satisfied. | Test command output, clean git diff, physical evidence artifact. |
| **`DEFERRED`** | Formally de-scoped from hackathon MVP critical path to eliminate delivery risk. | Explicit ratification in `docs/ownership.md`. | N/A (post-hackathon). |

### 2.2 Subsystem Maturity States (docs/implementation-status.md)
- **`ABSENT`:** Directory or module files contain only empty docstrings or skeletons; no executable logic.
- **`PARTIAL`:** Basic code exists, but key methods, error handling, or subcomponents remain unfinished.
- **`IMPLEMENTED`:** Complete, cohesive implementation matching architectural specifications.

### 2.3 Validation Levels (Orthogonal to Task Status)
- **`NONE`:** No automated tests or verification checks exist.
- **`STATIC`:** Verified via static analysis, compilation (`compileall`), linters (`ruff`), or schema validation.
- **`UNIT`:** Verified via offline unit tests in isolation (`pytest tests/unit`), mocks, or synthetic fixtures.
- **`INTEGRATION`:** Verified via multi-component offline integration tests (e.g., `FakeServingAdapter` pipeline).
- **`LIVE`:** Verified against live external cloud infrastructure (e.g., Nebius Cloud NVIDIA GPU endpoint).

---

## 3. Reconciliation of Planning Contradictions

The October 21 audit revealed four cross-document contradictions across earlier planning artifacts. This roadmap establishes their authoritative resolutions based on repository reality:

### 3.1 Task Status vs. Subsystem Status
- **Contradiction:** An earlier roadmap version marked `TASK-02` as `DONE`, while `docs/implementation-status.md` Table 2 listed `SUB-13` as `PARTIAL / UNIT` and `BLOCKED(by=BLK-13)`. Similarly, `SUB-02` and `SUB-03` were listed as `IMPLEMENTED / UNIT`, yet `TASK-03` and `TASK-04` were `READY`.
- **Resolution:** Subsystem status measures overall component maturity, whereas task status measures bounded units of engineering work:
  - `SUB-13` (CI/CD & Packaging) is `PARTIAL / UNIT` because full CI hardening (`BLK-13`: adding ruff, mypy, and secret scanning to GitHub Actions) remains open. In contrast, `TASK-02` (Restore Clean Working Tree Baseline) was a focused task to resolve test collection errors, verify unit tests (24 passed), and clean up working tree hygiene; its specific Definition of Done was satisfied.
  - `SUB-02` (Contracts) and `SUB-03` (Evaluator) are `IMPLEMENTED / UNIT` because their core classes exist and pass baseline tests. However, bounded hardening tasks (`TASK-03` for committed schemas/extra fields and `TASK-04` for NaN/negative latency safety) are `READY` to address specific edge cases (`BLK-05`, `BLK-06`, `BLK-10`, `BLK-12`).

### 3.2 Total 6-Run Experiment Budget vs. 5 Search Runs
- **Contradiction:** Some passages referenced a "6-run search budget", while search controller specifications stated that candidate search terminates after 5 runs.
- **Resolution:** The declared experiment budget is strictly **six benchmark runs total**, divided into two sequential phases:
  $$\text{Total Budget} = 1 \text{ Baseline Run} + 4 \text{ Candidate Search Runs} + 1 \text{ Independent Verification Rerun} = 6 \text{ Runs}$$
  1. **Phase 1 — Candidate Search (Runs 1–5):** Run 1 measures empirical baseline performance. Runs 2–5 evaluate the fixed 2×2 candidate parameter grid. The search controller strictly terminates after these 5 runs, evaluates hard constraints, and ranks feasible candidates.
  2. **Phase 2 — Independent Verification (Run 6):** The verification runner reruns the single winning candidate under a fresh, distinct `verification_run_id` to audit metric drift ($\Delta M$) and render the final verification verdict.
  - *Rule:* Search terminates after 5 runs so that the 6th run is preserved exclusively for independent verification. A preflight smoke test is a 1-request health probe, not a full benchmark run.

### 3.3 Critical Path Derivation vs. Dependency Edge List
- **Contradiction:** Section 3.1 dependency edges showed `TASK-08` branching to `TASK-09` and `TASK-10` independently, but Section 3.2 critical path chained `TASK-08 -> TASK-09 -> TASK-10`.
- **Resolution:** The repository operates on a **dual-track architecture**:
  1. *Offline Software Engine Track (CI & Synthetic Development):*
     $$\text{TASK-01} \longrightarrow \text{TASK-02} \longrightarrow \text{TASK-05} \longrightarrow \text{TASK-06} \longrightarrow \text{TASK-07} \longrightarrow \text{TASK-08} \longrightarrow \text{TASK-10} \longrightarrow \text{TASK-11} \longrightarrow \text{TASK-12} \longrightarrow \text{TASK-13}$$
     The offline search controller (`TASK-10`) can be implemented and validated using `FakeServingAdapter` without waiting for live Nebius credentials.
  2. *Live Physical Evidence Track (Hackathon Submission):*
     $$\text{TASK-08} \longrightarrow \text{TASK-09 (Nebius Live Preflight)} \longrightarrow \text{Live 2×2 Search Campaign} \longrightarrow \text{TASK-11 (Live Verification)} \longrightarrow \text{TASK-16}$$
     To generate authentic physical H100 benchmarks for submission, `TASK-09` is a direct prerequisite for live search execution. Both tracks converge at `TASK-11` and `TASK-16`.

### 3.4 Reconciled Status Ledger (Tasks 01–18)
| Task ID | Component / Area | Status | Validation Level | Primary Dependency / Blocker | Accountable Owner |
|---|---|---|---|---|---|
| **TASK-01** | Baseline Audit & Scope Freeze | `DONE` | `STATIC` | None | Rajdeep |
| **TASK-02** | Clean Baseline & Hardened Build | `DONE` | `UNIT` | None | Rajdeep |
| **TASK-03** | Schema Export & Contract Boundaries | `READY` | `UNIT` | TASK-02, BLK-10, BLK-12 | Rajdeep |
| **TASK-04** | Evaluator NaN & Negative Latency Safety | `READY` | `UNIT` | TASK-02, BLK-05, BLK-06 | Rajdeep |
| **TASK-05** | Deterministic Fake Serving Adapter | `READY` | `INTEGRATION` | TASK-02, BLK-01 | Rajdeep |
| **TASK-06** | Subprocess Load Generator | `BLOCKED` | `NONE` | TASK-05, BLK-02 | Rajdeep (Adriraj audit Oct 21) |
| **TASK-07** | Deterministic Metrics Engine Core | `BLOCKED` | `NONE` | TASK-06, BLK-03 | Rajdeep (Adriraj audit Oct 21) |
| **TASK-08** | Single-Run Pipeline Orchestrator | `BLOCKED` | `NONE` | TASK-04, TASK-05, TASK-06, TASK-07 | Rajdeep |
| **TASK-09** | Nebius Live Serving Adapter & Smoke Probe | `BLOCKED` | `NONE` | TASK-08, DEC-01, DEC-02, BLK-04 | Rajdeep |
| **TASK-10** | 2×2 Bounded Search Controller | `BLOCKED` | `NONE` | TASK-08, BLK-11 | Rajdeep |
| **TASK-11** | Independent Verification Engine | `BLOCKED` | `NONE` | TASK-10, BLK-08 | Rajdeep (Daksh audit Oct 24) |
| **TASK-12** | Report Artifact Generator & Publisher | `BLOCKED` | `NONE` | TASK-11, BLK-09 | Rajdeep |
| **TASK-13** | Minimal CLI Runner (`slokern verify`) | `BLOCKED` | `NONE` | TASK-12 | Rajdeep |
| **TASK-14** | Benchmark Data Integrity & Trace Audit Suite | `BLOCKED` | `NONE` | TASK-07 (Adriraj active Oct 21) | Adriraj |
| **TASK-15** | Decision Correctness Verification Suite | `BLOCKED` | `NONE` | TASK-11 (Daksh active Oct 24) | Daksh |
| **TASK-16** | End-to-End Smoke Test & Submission Package | `BLOCKED` | `NONE` | TASK-13, TASK-14, TASK-15, Live Runs | Rajdeep |
| **TASK-17** | Control Plane REST API & SSE Streaming | `DEFERRED` | `NONE` | Post-Hackathon | Rajdeep |
| **TASK-18** | Frontend Command Center React UI | `DEFERRED` | `NONE` | Post-Hackathon | Rajdeep |

---

## 4. Milestone Sequence & Architecture

```mermaid
flowchart TD
    PhaseA[Phase A: Audit & Scope Freeze\nOct 19 Audit\nDONE] --> PhaseB[Phase B: Single-Run Execution\nOct 21-23\nIN PROGRESS]
    PhaseB --> PhaseC[Phase C: Search & Feasibility\nOct 24-25\nPLANNED]
    PhaseC --> PhaseD[Phase D: Independent Verification\nOct 26-27\nPLANNED]
    PhaseD --> PhaseE[Phase E: Hardening & Submission Packaging\nOct 28-29\nPLANNED]
    PhaseE --> PhaseF[Phase F: Final Submission\nOct 30, 10:00 AM PDT\nPLANNED]

    classDef done fill:#1f3a2d,stroke:#4ade80,color:#fff;
    classDef inprog fill:#1e3a5f,stroke:#38bdf8,color:#fff;
    classDef planned fill:#2d2d3a,stroke:#94a3b8,color:#fff;
    class PhaseA done;
    class PhaseB inprog;
    class PhaseC,PhaseD,PhaseE,PhaseF planned;
```

| Phase | Calendar Window | Milestone Target | Status | Milestone Deliverable & Reality |
|---|---|---|---|---|
| **Phase A** | Oct 19 | Audit & Scope Freeze | `DONE` | Baseline audit completed; scope frozen in `docs/implementation-status.md`. Contradicted claims removed. |
| **Phase B** | Oct 21–23 | Establish Single-Run Execution | `IN PROGRESS` | Implement `FakeServingAdapter`, subprocess loadgen, metrics engine, and Nebius live smoke preflight. |
| **Phase C** | Oct 24–25 | Bounded Search & Feasibility | `PLANNED` | Execute 2×2 grid search (4 candidates + 1 baseline), evaluate hard SLO constraints, rank candidates. |
| **Phase D** | Oct 26–27 | Independent Verification | `PLANNED` | Execute independent rerun under fresh `verification_run_id`, compute drift ($\Delta M$), publish Markdown report. |
| **Phase E** | Oct 28–29 | Hardening & Defect Closure | `PLANNED` | Feature freeze; close critical defects; clean clone install check; rehearse demo video ($\le 3$ min). |
| **Phase F** | Oct 30 | Final Submission | `PLANNED` | Devpost submission delivered before 10:00 AM PDT (10:30 PM IST) with 4-hour safety buffer. |

---

## 5. Dependency Graph & Critical Path Analysis

### 5.1 Authoritative Dependency Edges
- `TASK-01` $\to$ `TASK-02`
- `TASK-02` $\to$ `TASK-03`, `TASK-04`, `TASK-05`
- `TASK-05` $\to$ `TASK-06`
- `TASK-06` $\to$ `TASK-07`
- `TASK-04`, `TASK-05`, `TASK-06`, `TASK-07` $\to$ `TASK-08`
- `TASK-08` $\to$ `TASK-09` *(Live Adapter & Smoke Preflight)*
- `TASK-08` $\to$ `TASK-10` *(2×2 Search Controller)*
- `TASK-07` $\to$ `TASK-14` *(Benchmark Integrity Suite — Adriraj)*
- `TASK-09`, `TASK-10` $\to$ `TASK-11` *(Independent Verification Engine)*
- `TASK-11` $\to$ `TASK-12` *(Report Artifact Generator)*
- `TASK-11` $\to$ `TASK-15` *(Decision Correctness Suite — Daksh)*
- `TASK-12` $\to$ `TASK-13` *(Minimal CLI Runner)*
- `TASK-13`, `TASK-14`, `TASK-15` $\to$ `TASK-16` *(End-to-End Smoke Test & Submission)*
- `TASK-16` $\to$ `TASK-17` *(Deferred: Control Plane API)*
- `TASK-17` $\to$ `TASK-18` *(Deferred: Frontend UI)*

### 5.2 Critical Path Derivation
The submission-critical path consists of 12 sequential engineering tasks:
$$\text{TASK-01} \longrightarrow \text{TASK-02} \longrightarrow \text{TASK-05} \longrightarrow \text{TASK-06} \longrightarrow \text{TASK-07} \longrightarrow \text{TASK-08} \longrightarrow \text{TASK-09} \longrightarrow \text{TASK-10} \longrightarrow \text{TASK-11} \longrightarrow \text{TASK-12} \longrightarrow \text{TASK-13} \longrightarrow \text{TASK-16}$$

- **Critical Path Length:** 12 sequential tasks.
- **Collaborator Integration Points:**
  - `TASK-14` (Adriraj): Branches from `TASK-07` on Oct 21; converges at `TASK-16`.
  - `TASK-15` (Daksh): Branches from `TASK-11` on Oct 24; converges at `TASK-16`.

---

## 6. Actionable Blockers & Decisions Register

### 6.1 Active Blockers Register
Every blocker is bound to an accountable owner, an explicit impact, an unblocking action, and a fallback:

| Blocker ID | Priority | Blocking Condition | Impact | Unblock Action | Owner | Fallback / Escalation Point |
|---|---|---|---|---|---|---|
| **BLK-01** | **P0** | `fake.py` and `nebius.py` are empty docstrings. | Cannot execute any inference requests locally or live. | Implement `FakeServingAdapter` generating deterministic synthetic responses. | Rajdeep | Fall back to synthetic mock fixtures with **`DEMO DATA`** watermark. |
| **BLK-02** | **P0** | `src/slokern/engine/loadgen/runner.py` is an empty docstring. | Cannot dispatch requests or record raw `RawRequestMeasurement` event traces. | Implement minimal dispatch loop writing unaggregated JSONL recordings. | Rajdeep | Use single-threaded loop with microsecond timestamps; flag client saturation. |
| **BLK-03** | **P0** | `src/slokern/core/metrics/percentiles.py` is an empty docstring. | Cannot calculate `MetricSet` from raw event traces. | Implement standard library percentile and throughput calculators. | Rajdeep | Use Python `math` module linear interpolation percentiles. |
| **BLK-04** | **P0** | `test_smoke_live.py` skips; exact Nebius API model string unverified. | Cannot run live compliance benchmark on Nebius Cloud. | Execute live preflight probe using `curl` or single-request script with valid API key. | Rajdeep | Fall back to `FakeServingAdapter` for offline demo, documenting live credentials limitation. |
| **BLK-05** | **P1** | `float('nan') <= 200.0` yields `INFEASIBLE` with `TTFT_P95_EXCEEDED`. | Corrupted or uncalculable floating-point evidence is misclassified as an SLO failure. | Add `math.isnan(obs_val)` check in `evaluate.py` to route NaN to `INCONCLUSIVE`. | Rajdeep | Mark invalid metric runs as `INCONCLUSIVE` (`MISSING_REQUIRED_METRIC`). |
| **BLK-06** | **P1** | `-10.0 <= 200.0` yields `FEASIBLE` with `HARD_CONSTRAINTS_PASSED`. | Physically impossible negative latency passes feasibility checks without rejection. | Add physical non-negative constraint assertion (`obs_val >= 0`) in `evaluate.py`. | Rajdeep | Reject negative values with `ReasonCode.INVALID_MEASUREMENT`. |
| **BLK-07** | **P1** | Rajdeep accountable for 9 of 13 subsystems (69% concentration). | Delivery bottleneck on critical path; risk of exhaustion before deadline. | Formally freeze API (`SUB-11`) and Frontend (`SUB-12`) as `DEFERRED`. | Rajdeep | Focus sprint exclusively on CLI + static Markdown report artifact. |
| **BLK-08** | **P1** | `src/slokern/core/verification/compare.py` is an empty docstring. | Cannot independently verify selected winning candidates or compute drift ($\Delta M$). | Implement deterministic drift calculation and pass/fail evaluation comparing two `MetricSet`s. | Rajdeep | Escalate to Daksh for boundary test review on Oct 24. |
| **BLK-09** | **P1** | `src/slokern/engine/reporting/report_builder.py` is an empty docstring. | Cannot publish immutable `ReportArtifact` for hackathon submission evidence. | Implement Markdown builder serializing `ReportArtifact` into an inspectable document. | Rajdeep | Generate plain GitHub-flavored Markdown document with embedded tables. |
| **BLK-10** | **P1** | `schemas/` contains only `.gitkeep`; `scripts/gen_contracts.py` is a stub. | No emitted JSON Schemas exist in source control; cannot validate external tools. | Implement script exporting `model_json_schema()` for all 11 models into `schemas/`. | Rajdeep | Commit exported schemas to git; add drift check to CI. |
| **BLK-11** | **P2** | Numeric types (`1` vs `1.0`) produce differing candidate hashes. | Inadvertent type coercion between float and integer changes candidate hash identity. | Enforce canonical integer/float normalization before hashing in `candidate_id.py`. | Rajdeep | Cast integral floats (`x.is_integer()`) to `int` prior to hashing. |
| **BLK-12** | **P2** | All 11 models accept unrecognized fields silently (`extra='ignore'`). | Contracts do not strictly reject invalid or misspelled fields at system boundaries. | Add `model_config = ConfigDict(extra='forbid')` to all 11 contract classes. | Rajdeep | Enforce strict pydantic validation across all boundaries. |
| **BLK-13** | **P2** | `ci.yml` lacks linting, type checks, schema drift, and secret scanning steps. | Code regressions, typing errors, or secret leaks can bypass CI unnoticed. | Add `ruff check`, `mypy --strict src/slokern`, and secret scanning checks to `ci.yml`. | Rajdeep | Run narrow local checks before push; update CI workflow. |
| **BLK-14** | **P2** | Git preflight R-01: Working tree baseline had uncommitted edits. | Working tree baseline not clean, preventing clean clone verification. | Commit all pending modifications on integration branch. | Rajdeep | Verify `git status --porcelain` returns 0 changes outside documentation. |

### 6.2 Architectural Decisions Register (DEC-xx)
| Decision ID | Question / Problem | Recommended Option | Accountable Owner | Impact if Unresolved |
|---|---|---|---|---|
| **DEC-01** | Nebius serving endpoint interface & parameter controls. | **Option A:** Test live endpoint reachability; if engine knobs inaccessible, bound search to client request parameters (`max_tokens`, `concurrency`). | Rajdeep | Blocks `SUB-05` and live Nebius benchmark execution. |
| **DEC-02** | Target model deployment confirmation string. | **Option A:** Run single-request live preflight probe to confirm active model ID (e.g. `nvidia/Nemotron-3-Nano-30B-A3B`). | Rajdeep | Blocks hackathon NVIDIA model compliance verification. |
| **DEC-03** | Default cost accounting basis lock (Mode A vs Mode B). | **Option A:** Default to Mode B (non-monetary systems proxy: GPU-sec/req or throughput under SLO); report monetary cost as `unavailable`. | Rajdeep | Prevents fabricated or estimated pricing claims. |
| **DEC-04** | Integration branch & baseline hygiene. | **Option A:** Commit baseline documentation updates to integration branch; maintain clean working tree. | Rajdeep | Blocks clean-clone reproducible installation check. |
| **DEC-05** | Frontend and API scope deferral. | **Option A:** Formally freeze FastAPI and React UI as `DEFERRED`; submit CLI + Markdown `ReportArtifact`. | Rajdeep | Eliminates concentration risk (BLK-07). |

---

## 7. Day-by-Day Execution Plan (Oct 21–30, 2026)

This day-by-day plan governs all development leading up to the submission deadline on **October 30, 2026, at 10:00 AM PDT (10:30 PM IST / 17:00:00 UTC)**.

### Day 1: Wednesday, October 21, 2026 — Phase B: Serving Foundation & Contract Boundaries
- **Intended Outcome:** Eliminate contract ambiguities, harden evaluator against NaN/negative values, implement `FakeServingAdapter`, and initiate Adriraj's benchmark integrity onboarding.
- **Ordered Actions:**
  - [ ] **Action 1.1 (Rajdeep):** Execute `TASK-04`: Patch `src/slokern/core/evaluator/evaluate.py` to route `math.isnan(obs_val)` to `INCONCLUSIVE` and assert non-negative latencies. Run `pytest tests/unit/core/test_evaluator.py`.
  - [ ] **Action 1.2 (Rajdeep):** Execute `TASK-03`: Update `src/slokern/contracts/` with `extra='forbid'`, implement `scripts/gen_contracts.py`, and commit 11 `.json` schemas to `schemas/`. Run `pytest tests/contract/test_generated_files_current.py`.
  - [ ] **Action 1.3 (Rajdeep):** Execute `TASK-05`: Implement `FakeServingAdapter` in `src/slokern/engine/serving/fake.py` returning synthetic token streams labeled **`DEMO DATA`**.
  - [ ] **Action 1.4 (Adriraj — Active Window Starts):** Inspect `src/slokern/contracts/evidence.py` (`RawRequestMeasurement`) and construct benchmark validation fixtures for invalid/saturated traces (`tests/contract/test_fixtures_validate.py`).
- **Accountable Owner:** Rajdeep (Implementation); Adriraj (Benchmark Schema Review).
- **Dependencies & Fallback:** If contract updates break existing tests, revert `extra='forbid'` on non-boundary internal models first.
- **Completion Evidence:** `pytest tests/unit/core/test_evaluator.py tests/contract/test_schemas.py` passing 100%; `schemas/` populated with 11 JSON files.

### Day 2: Thursday, October 22, 2026 — Phase B: Subprocess Load Generator & Metrics Engine
- **Intended Outcome:** Operational load generator capable of dispatching Poisson/constant traffic to the fake adapter and writing valid `.jsonl` traces; metrics engine computing percentiles.
- **Ordered Actions:**
  - [ ] **Action 2.1 (Rajdeep):** Execute `TASK-06`: Implement subprocess-isolated load generator in `src/slokern/engine/loadgen/runner.py` writing unaggregated microsecond events to `.jsonl`.
  - [ ] **Action 2.2 (Adriraj):** Audit load generator output traces against `RawRequestMeasurement` schema; verify timestamp monotonicity (`scheduled_at <= sent_at <= first_token_at <= completed_at`).
  - [ ] **Action 2.3 (Rajdeep):** Execute `TASK-07`: Implement `src/slokern/core/metrics/percentiles.py` and `aggregate.py` calculating TTFT/ITL percentiles and throughput from raw traces.
  - [ ] **Action 2.4 (Adriraj):** Populate golden metric fixtures (`fixtures/metrics_golden/percentiles_basic.json`) with hand-calculated percentiles for unit testing.
- **Accountable Owner:** Rajdeep (Implementation); Adriraj (Trace Auditing & Fixtures).
- **Dependencies & Fallback:** If subprocess IPC encounters platform issues on Windows, fall back to synchronous dispatch loop with explicit lag detection.
- **Completion Evidence:** `pytest tests/unit/engine/loadgen/ tests/unit/core/metrics/` passes cleanly; sample `.jsonl` trace produced and validated.

### Day 3: Friday, October 23, 2026 — Phase B: Single-Run Orchestrator & Live Nebius Preflight Smoke Test
- **Intended Outcome:** Complete single-run execution path verified offline; live Nebius endpoint probed with valid API key to confirm NVIDIA model identifier string.
- **Ordered Actions:**
  - [ ] **Action 3.1 (Rajdeep):** Execute `TASK-08`: Implement `SingleRunExecutor` in `src/slokern/engine/runner/run_executor.py` wiring adapter, loadgen, metrics, and evaluator into an end-to-end run.
  - [ ] **Action 3.2 (Rajdeep):** Verify single-run execution offline using `FakeServingAdapter`, saving `RunRecord`, raw JSONL, and `FeasibilityResult`.
  - [ ] **Action 3.3 (Rajdeep):** Execute `TASK-09`: Implement `NebiusServingAdapter` in `src/slokern/engine/serving/nebius.py` and run live preflight smoke probe (`test_smoke_live.py`) with `NEBIUS_API_KEY`. Confirm model string (`DEC-02`).
  - [ ] **Action 3.4 (Adriraj):** Audit single-run JSONL output for client saturation flags (`generator_saturated = True`) when queue lag exceeds 10 ms.
- **Accountable Owner:** Rajdeep (Implementation & Cloud Probe); Adriraj (Output Validation).
- **Dependencies & Fallback:** If Nebius live credentials or quota are unavailable, mark `BLK-04` as offline limitation and proceed using `FakeServingAdapter` with persistent **`DEMO DATA`** labeling.
- **Completion Evidence:** `SingleRunExecutor` produces valid `RunRecord` on disk; live smoke probe logs verified `environment_fingerprint` or documented offline fallback.

### Day 4: Saturday, October 24, 2026 — Phase C: 2×2 Bounded Search Controller & Hard SLO Feasibility
- **Intended Outcome:** Search controller executes 5 runs (1 baseline + 4 candidates in 2×2 space), enforces 6-run total budget, and filters infeasible candidates; Daksh initiates correctness auditing.
- **Ordered Actions:**
  - [ ] **Action 4.1 (Rajdeep):** Execute `TASK-10`: Implement bounded grid search controller (`src/slokern/core/search/grid.py`) exploring 2×2 parameter matrix (`max_num_batched_tokens` ∈ {1024, 2048} × `max_num_seqs` ∈ {16, 64}).
  - [ ] **Action 4.2 (Rajdeep):** Fix candidate hashing in `candidate_id.py` to ensure numeric type invariance (`1` vs `1.0` yield identical hashes, closing `BLK-11`).
  - [ ] **Action 4.3 (Daksh — Active Window Starts):** Inspect `src/slokern/core/evaluator/evaluate.py` and construct boundary tests in `tests/contract/test_verification_independence.py` auditing operator thresholds (`<`, `<=`, `>`, `>=`).
  - [ ] **Action 4.4 (Daksh):** Test candidate rejection behavior: verify that candidates with `verdict != FEASIBLE` are strictly excluded from ranking pools.
- **Accountable Owner:** Rajdeep (Search Controller); Daksh (Evaluator Boundary Auditing).
- **Dependencies & Fallback:** If search controller overshoots budget, hard-terminate search loop at exactly 5 runs using `budget_limiter`.
- **Completion Evidence:** `pytest tests/unit/core/search/` passes; search controller executes 5 runs offline and outputs structured candidate pool.

### Day 5: Sunday, October 25, 2026 — Phase C: Deterministic Candidate Ranking & 5-Run Search Campaign
- **Intended Outcome:** Deterministic ranking of feasible candidates under Mode B systems proxy (or Mode A monetary cost if verified); complete 5-run search campaign executed.
- **Ordered Actions:**
  - [ ] **Action 5.1 (Rajdeep):** Wire ranking logic into search controller; verify tie-breaking deterministically selects winning candidate by candidate ID.
  - [ ] **Action 5.2 (Rajdeep):** Execute 5-run search campaign (1 baseline + 4 candidates) against live Nebius endpoint (or `FakeServingAdapter` if offline), generating raw JSONL traces for each run.
  - [ ] **Action 5.3 (Adriraj):** Audit all 5 JSONL traces for data completeness, request count consistency, and offered-vs-achieved load integrity.
  - [ ] **Action 5.4 (Daksh):** Independently audit ranking results to ensure selected winning candidate satisfies every hard constraint and achieves lowest cost/proxy.
- **Accountable Owner:** Rajdeep (Search Execution); Adriraj & Daksh (Data & Decision Audits).
- **Dependencies & Fallback:** If zero candidates evaluate to `FEASIBLE`, verify search controller halts safely with `INCONCLUSIVE_NO_FEASIBLE_CANDIDATE`.
- **Completion Evidence:** Search history saved on disk containing exactly 5 `RunRecord`s, 1 baseline, 4 candidates, and 1 designated winner.

### Day 6: Monday, October 26, 2026 — Phase D: Independent Verification Engine (Run 6) & Metric Drift Auditing
- **Intended Outcome:** Verification runner reruns winning candidate under a fresh `verification_run_id` (Run 6), computes metric drift ($\Delta M$), and assigns definitive verification verdict.
- **Ordered Actions:**
  - [ ] **Action 6.1 (Rajdeep):** Execute `TASK-11`: Implement verification engine in `src/slokern/core/verification/protocol.py` and drift comparison in `compare.py` (closing `BLK-08`).
  - [ ] **Action 6.2 (Rajdeep):** Execute the 6th benchmark run: independent verification rerun of the winning candidate under fresh `verification_run_id`.
  - [ ] **Action 6.3 (Daksh):** Audit verification independence: verify that verification run does NOT reuse search metrics or copy run IDs, and recomputes all metrics from fresh evidence.
  - [ ] **Action 6.4 (Daksh):** Test drift threshold evaluation: assert verification fails if metric drift exceeds declared tolerance ($\Delta \text{TTFT} > \epsilon$).
- **Accountable Owner:** Rajdeep (Verification Implementation); Daksh (Verification Auditing).
- **Dependencies & Fallback:** If live verification fails due to network jitter, record `VERIFICATION_FAILED` honestly; do not fudge numbers or suppress the run.
- **Completion Evidence:** `VerificationRecord` emitted with status `VERIFIED` or `VERIFICATION_FAILED`; fresh verification `.jsonl` trace saved to disk.

### Day 7: Tuesday, October 27, 2026 — Phase D: Immutable Report Generator & Minimal CLI Runner
- **Intended Outcome:** Self-contained Markdown report generator published; terminal CLI runner operational (`slokern verify`, `slokern optimize`, `slokern smoke-test`).
- **Ordered Actions:**
  - [ ] **Action 7.1 (Rajdeep):** Execute `TASK-12`: Implement `report_builder.py` in `src/slokern/engine/reporting/` compiling specs, candidate comparisons, verification records, and limitations into Markdown.
  - [ ] **Action 7.2 (Rajdeep):** Add secret redaction filter asserting zero API keys, tokens, or private endpoint URLs in generated reports.
  - [ ] **Action 7.3 (Rajdeep):** Execute `TASK-13`: Implement minimal CLI in `src/slokern/cli/main.py` using standard library `argparse`.
  - [ ] **Action 7.4 (Adriraj):** Review generated report artifact for honest disclosure of measurement limitations, client overhead, and cost accounting mode.
- **Accountable Owner:** Rajdeep (Implementation); Adriraj (Report Disclosures Review).
- **Dependencies & Fallback:** If CLI command parsing has edge cases, keep subcommands minimal: `smoke-test`, `optimize`, `verify`, `report`.
- **Completion Evidence:** `slokern --help` exits code 0; `ReportArtifact` JSON and `report.md` generated cleanly and pass schema validation.

### Day 8: Wednesday, October 28, 2026 — Phase E: Collaborator Audit Signoffs, Regression Hardening & Feature Freeze
- **Intended Outcome:** Full test suite execution across all modules; collaborator audit test suites merged; code freeze declared; zero unhandled regressions.
- **Ordered Actions:**
  - [ ] **Action 8.1 (Adriraj):** Deliver and merge `TASK-14` (`tests/contract/test_fixtures_validate.py`) with full trace integrity assertions. Sign off on data credibility.
  - [ ] **Action 8.2 (Daksh):** Deliver and merge `TASK-15` (`tests/contract/test_verification_independence.py`) with decision correctness assertions. Sign off on evaluator verdicts.
  - [ ] **Action 8.3 (Rajdeep):** Execute full test suite: `pytest -v` across all contract, unit, and integration tests.
  - [ ] **Action 8.4 (Rajdeep):** Implement `ci.yml` hardening (`BLK-13`): add `ruff check`, `mypy --strict src/slokern`, and secret scanning.
  - [ ] **Action 8.5 (Rajdeep):** Declare formal **FEATURE FREEZE**; no new features or interface changes allowed.
- **Accountable Owner:** Rajdeep (Integrator & CI); Adriraj & Daksh (Audit Signoffs).
- **Dependencies & Fallback:** If collaborator PRs have merge conflicts, Rajdeep reconciles conflicts while preserving test assertions.
- **Completion Evidence:** 100% green test run across all tests; GitHub Actions CI passing on `main`; signed audit checklists.

### Day 9: Thursday, October 29, 2026 — Phase E: Clean Clone Rehearsal, Demo Video Recording & Documentation
- **Intended Outcome:** Reproducibility verified on clean clone; demo script rehearsed and recorded ($\le 3$ minutes); final documentation polished.
- **Ordered Actions:**
  - [ ] **Action 9.1 (Rajdeep):** Test clean clone installation on isolated machine/directory: `git clone`, `python -m venv`, `pip install -e .`, run full test suite.
  - [ ] **Action 9.2 (Rajdeep):** Finalize `README.md` and `docs/demo-script.md` ensuring all CLI examples and outputs match actual code behavior.
  - [ ] **Action 9.3 (Rajdeep):** Record demonstration video ($\le 3$ minutes) walking through workload specification, bounded search execution, independent verification verdict, and inspectable Markdown report.
  - [ ] **Action 9.4 (Rajdeep):** Populate tool feedback register (`docs/hackathon-feedback.md`) with authentic feedback on Nebius Cloud and NVIDIA tools.
- **Accountable Owner:** Rajdeep (Rehearsal, Video, & Docs).
- **Dependencies & Fallback:** If screen recording requires editing, keep it simple and unedited: clear terminal demonstration with narration.
- **Completion Evidence:** Clean clone installs and passes tests cleanly; demo video recorded, uploaded, and URL verified.

### Day 10: Friday, October 30, 2026 — Phase F: Final Audit, Submission Packaging & Devpost Delivery
- **Intended Outcome:** Official hackathon submission package completed and delivered 4 hours before deadline.
- **Ordered Actions:**
  - [ ] **Action 10.1 (Rajdeep):** Complete final pre-submission audit: verify zero committed secrets, zero broken links, and zero unverified claims.
  - [ ] **Action 10.2 (Rajdeep):** Tag release commit in git: `git tag -a v1.0.0-hackathon -m "SLOKern Hackathon Submission Release"`.
  - [ ] **Action 10.3 (Rajdeep):** Finalize Devpost submission text, attaching GitHub repository link, demo video link, and report artifact.
  - [ ] **Action 10.4 (Rajdeep):** Submit Devpost package before **6:00 AM PDT / 6:30 PM IST** (4-hour safety buffer ahead of 10:00 AM PDT deadline).
- **Accountable Owner:** Rajdeep (Sole Submission Authority).
- **Dependencies & Fallback:** If Devpost experiences high traffic, submission buffer guarantees ample time for retries.
- **Completion Evidence:** Devpost submission confirmation received; git release tag pushed to remote repository.

---

## 8. Complete Task Catalog (TASK-01 through TASK-18)

### TASK-01 — Complete Baseline Repository Audit and MVP Scope Freeze
- **Owner:** Rajdeep (CONFIRMED) · **Subsystem:** `SUB-01` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `DONE` · **Validation Level:** `STATIC`
- **Objective:** Replace completion assumptions with verified repository evidence and freeze MVP scope.
- **Needs:** None.
- **Boundary & Isolation:** Confined to documentation (`docs/implementation-status.md`, `docs/ownership.md`, `ROADMAP.md`). Forbidden to touch runtime code, contracts, CI, or frontend.
- **Deliverables:** Authoritative audit report, updated ownership matrix, and ratified scope freeze in `docs/implementation-status.md`.
- **Definition of Done:**
  1. Baseline commands R-01 through R-12 and behavioral probes P-01 through P-20 fully documented with exact outputs and citations.
  2. Scope freeze ratified: 1 model, 1 serving runtime, bounded 2×2 parameter matrix, 6-run total budget lock.
  3. Contradicted claims identified and cataloged in Claims Ledger.
- **Verify:** `docs/implementation-status.md` committed and verified consistent.
- **Completion Evidence:** Commit `356c489` and active branch audit report.

---

### TASK-02 — Restore Clean Working Tree Baseline and Hardened Build Tooling
- **Owner:** Rajdeep (CONFIRMED) · **Subsystem:** `SUB-13` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `DONE` · **Validation Level:** `UNIT`
- **Objective:** Clean working tree modifications, resolve test collection errors, and ensure reproducible installs.
- **Needs:** `TASK-01`, `BLK-13`, `BLK-14`, `DEC-04`.
- **Boundary & Isolation:** Confined to build metadata (`pyproject.toml`) and baseline working tree hygiene. Forbidden to modify contracts.
- **Deliverables:** Clean working tree on `main`; verified test execution across all 24 unit tests without collection errors.
- **Definition of Done:**
  1. `pytest -v -m "not live"` runs cleanly with 0 collection errors across the entire repository.
  2. All 24 unit tests pass cleanly (100% green).
  3. `python -m pip check` and `python -m compileall src tests` exit with code 0.
  4. Working tree verified clean outside allowed documentation paths.
- **Verify:** `.venv\Scripts\pytest -v -m "not live"` exits code 0 (24 passed, 1 deselected, 0 failed in 0.92s).
- **Completion Evidence:** Verified test execution log; commit `b895b3e` (README badge update).

---

### TASK-03 — Export Committed JSON Schemas and Strict Contract Boundaries
- **Owner:** Rajdeep (CONFIRMED) · **Subsystem:** `SUB-02` · **Priority:** P1 (DEMO-CRITICAL) · **Status:** `READY` · **Validation Level:** `UNIT`
- **Objective:** Generate committed JSON Schemas for all 11 models and configure `model_config = ConfigDict(extra='forbid')`.
- **Needs:** `TASK-02`, `BLK-10`, `BLK-12`.
- **Boundary & Isolation:** Confined to `scripts/gen_contracts.py`, `schemas/*.json`, and `src/slokern/contracts/`. Contract fields and units cannot be altered without Rajdeep's explicit approval.
- **Deliverables:** Functional `scripts/gen_contracts.py`; 11 canonical JSON schemas committed in `schemas/`; `extra='forbid'` configured across all contract models.
- **Definition of Done:**
  1. Running `python scripts/gen_contracts.py` writes 11 schema files into `schemas/` matching all 11 models.
  2. All 11 schema files committed to git (resolving `BLK-10`).
  3. Contract models reject unrecognized attributes (`extra='forbid'`), preventing silent field dropping (resolving `BLK-12`).
  4. `test_generated_files_current.py` passes cleanly on a fresh clone without manual regeneration.
- **Verify:** `pytest tests/contract/test_generated_files_current.py tests/contract/test_schemas.py` exits code 0.
- **Completion Evidence:** 11 `.json` files in `schemas/` and passing contract tests.

---

### TASK-04 — Harden Evaluator Boundary Conditions (NaN and Negative Metric Safety)
- **Owner:** Rajdeep (CONFIRMED) · **Subsystem:** `SUB-03` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `READY` · **Validation Level:** `UNIT`
- **Objective:** Ensure floating-point NaN values evaluate to `INCONCLUSIVE` and negative latencies are rejected.
- **Needs:** `TASK-02`, `BLK-05`, `BLK-06`.
- **Boundary & Isolation:** Confined strictly to `src/slokern/core/evaluator/evaluate.py` and `tests/unit/core/test_evaluator.py`. Does NOT modify contracts or search controller.
- **Deliverables:** Hardened `evaluate_slo()` function asserting non-negative latencies and treating `math.isnan(obs_val)` as `INCONCLUSIVE`.
- **Definition of Done:**
  1. `math.isnan(obs_val)` check added to `evaluate_slo()`; emits `FeasibilityVerdict.INCONCLUSIVE` with reason code `MISSING_REQUIRED_METRIC` (resolving `BLK-05`).
  2. Non-negative assertion added for latency distributions (TTFT, ITL, e2e latency); negative values emit `FeasibilityVerdict.INCONCLUSIVE` (resolving `BLK-06`).
  3. All existing 7 evaluator tests pass; new unit tests for NaN and negative latencies pass.
- **Verify:** `pytest tests/unit/core/test_evaluator.py` passes with 100% assertions green.
- **Completion Evidence:** Unit tests asserting NaN yields `INCONCLUSIVE` and negative latency yields `INCONCLUSIVE`.

---

### TASK-05 — Implement Deterministic Fake Serving Adapter
- **Owner:** Rajdeep (INTERIM) · **Subsystem:** `SUB-05` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `READY` · **Validation Level:** `INTEGRATION`
- **Objective:** Implement an offline serving adapter generating reproducible synthetic request completions labeled **`DEMO DATA`**.
- **Needs:** `TASK-02`, `BLK-01`.
- **Boundary & Isolation:** Confined to `src/slokern/engine/serving/fake.py`, `base.py`, `capabilities.py`, and `tests/unit/engine/serving/`. Must NOT perform network I/O or call external APIs.
- **Deliverables:** Complete `FakeServingAdapter` implementing `ServingAdapter` interface, returning deterministic token streams, timings, and environment fingerprints.
- **Definition of Done:**
  1. `FakeServingAdapter` implements `apply_config()`, `health_check()`, `get_capabilities()`, and `get_environment_fingerprint()`.
  2. Emitted responses contain simulated token streams with explicit `note: "DEMO DATA"` and `simulated: True`.
  3. Unit tests in `tests/unit/engine/serving/test_fake.py` pass cleanly offline.
- **Verify:** `pytest tests/unit/engine/serving/test_fake.py` passes.
- **Completion Evidence:** `FakeServingAdapter` handles simulated requests offline without cloud access.

---

### TASK-06 — Implement Subprocess Load Generator
- **Owner:** Rajdeep (CONFIRMED) · **Subsystem:** `SUB-06` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-05) · **Validation Level:** `UNIT`
- **Objective:** Implement subprocess-isolated load generator generating Poisson/constant arrival and writing unaggregated JSONL events.
- **Needs:** `TASK-05`, `BLK-02`.
- **Boundary & Isolation:** Confined to `src/slokern/engine/loadgen/` (`runner.py`, `arrival.py`, `recorder.py`) and `tests/unit/engine/loadgen/`. Must output valid `RawRequestMeasurement` records.
- **Deliverables:** Subprocess load generator writing microsecond request events to `.jsonl` files and detecting client saturation (`generator_saturated = True`).
- **Definition of Done:**
  1. Request dispatch loop executes in a separate process to avoid Python GIL timing contamination.
  2. Poisson and constant arrival intervals generated with microsecond timestamps (`scheduled_at`, `sent_at`, `first_token_at`, `completed_at`).
  3. Output JSONL records validate 100% against `RawRequestMeasurement` schema.
- **Verify:** `pytest tests/unit/engine/loadgen/test_runner.py` passes.
- **Completion Evidence:** Subprocess dispatches 100 simulated requests and outputs valid unaggregated `.jsonl` file.

---

### TASK-07 — Implement Deterministic Metrics Engine
- **Owner:** Rajdeep (CONFIRMED) · **Subsystem:** `SUB-07` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-06) · **Validation Level:** `UNIT`
- **Objective:** Compute percentiles, throughput, error rate, and saturation flags from unaggregated JSONL request traces.
- **Needs:** `TASK-06`, `BLK-03`.
- **Boundary & Isolation:** Confined to `src/slokern/core/metrics/` and `fixtures/metrics_golden/`. Pure mathematical calculations; forbidden to make feasibility verdicts or rank candidates.
- **Deliverables:** Validated `percentiles.py`, `throughput.py`, `latency.py`, `validity.py`, and `aggregate.py`; golden metrics test fixtures with real numerical values.
- **Definition of Done:**
  1. Derives `MetricSet` containing exact percentiles (p50, p90, p95, p99), offered load, achieved load, and `generator_saturated` flag.
  2. Golden fixtures `percentiles_basic.json` populated with hand-calculated inputs and expected outputs.
  3. Linear interpolation percentiles match hand-calculated golden fixtures to 3 decimal places.
- **Verify:** `pytest tests/unit/core/metrics/` passes.
- **Completion Evidence:** Derived `MetricSet` from raw test JSONL trace matches golden fixtures.

---

### TASK-08 — Implement Single-Run Pipeline Orchestrator
- **Owner:** Rajdeep (INTERIM) · **Subsystem:** `SUB-08` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-04..07) · **Validation Level:** `INTEGRATION`
- **Objective:** Wire serving adapter, load generator, metrics engine, and evaluator into a single end-to-end execution path.
- **Needs:** `TASK-04`, `TASK-05`, `TASK-06`, `TASK-07`.
- **Boundary & Isolation:** Confined to `src/slokern/engine/runner/` and `tests/unit/engine/runner/`. Orchestrates components via established interfaces.
- **Deliverables:** `SingleRunExecutor` in `src/slokern/engine/runner/run_executor.py`, lifecycle management, and artifact persistence.
- **Definition of Done:**
  1. `SingleRunExecutor.execute()` wires: apply config -> health check -> warmup -> active measurement -> metrics derivation -> feasibility evaluation.
  2. Emits and saves immutable `RunRecord`, raw request `.jsonl`, `MetricSet`, and `FeasibilityResult` into structured disk directory.
  3. Clean cancellation handling via `CancellationToken` without leaving zombie subprocesses.
  4. Unit tests in `tests/unit/engine/runner/test_run_executor.py` pass offline using `FakeServingAdapter`.
- **Verify:** `pytest tests/unit/engine/runner/test_run_executor.py` passes with 0 errors.
- **Completion Evidence:** Single run executes end-to-end locally and persists all required artifacts.

---

### TASK-09 — Implement Nebius Serving Adapter and Execute Live Smoke Test
- **Owner:** Rajdeep (INTERIM) · **Subsystem:** `SUB-05` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-08, DEC-01, DEC-02, BLK-04) · **Validation Level:** `LIVE`
- **Objective:** Connect to Nebius Cloud endpoint, verify model identifier, and execute live preflight probe.
- **Needs:** `TASK-08`, `DEC-01`, `DEC-02`, `BLK-04`.
- **Boundary & Isolation:** Confined to `src/slokern/engine/serving/nebius.py` and `tests/live/test_smoke_live.py`. Provider keys read exclusively from environment variables (`NEBIUS_API_KEY`); zero secrets in code.
- **Deliverables:** `NebiusServingAdapter` communicating with OpenAI-compatible vLLM endpoint; live smoke test script.
- **Definition of Done:**
  1. Adapter connects to Nebius instance, reads back applied settings, and captures `environment_fingerprint` (GPU model, CUDA version, vLLM version).
  2. Live smoke test sends 1 streaming prompt request, records TTFT and streaming tokens, and receives valid completion.
  3. Preflight test verifies serving parameters (`max_num_batched_tokens`, `max_num_seqs`) are actively respected.
- **Verify:** `pytest tests/live/test_smoke_live.py -v -m live` passes against live Nebius endpoint.
- **Completion Evidence:** Preflight smoke test succeeds on live hardware and outputs verified environment fingerprint.

---

### TASK-10 — Implement 2×2 Bounded Search Controller and History Store
- **Owner:** Rajdeep (INTERIM) · **Subsystem:** `SUB-04` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-08, BLK-11) · **Validation Level:** `UNIT`
- **Objective:** Enforce 6-run total budget (1 baseline + 4 candidates + 1 verification), canonical candidate hashing, and ranking.
- **Needs:** `TASK-08`, `BLK-11`.
- **Boundary & Isolation:** Confined to `src/slokern/core/search/` and `tests/unit/core/search/`. Enforces budget limits; ranking must strictly exclude non-feasible candidates.
- **Deliverables:** Bounded grid search controller (`src/slokern/core/search/grid.py`), candidate ID canonical hashing fix (`candidate_id.py`), and budget limiter (`budget.py`).
- **Definition of Done:**
  1. Candidate ID hash instability resolved: `candidate_id.py` normalizes numeric types so `1` and `1.0` yield identical hashes (resolving `BLK-11`).
  2. Bounded search space generates exactly 4 legal candidates across declared 2×2 grid: `max_num_batched_tokens` in {1024, 2048} × `max_num_seqs` in {16, 64}.
  3. Controller executes 1 baseline run + 4 candidate search runs; strictly terminates when 5 runs complete.
  4. Ranks feasible candidates deterministically by declared objective; breaks ties alphabetically by candidate ID.
- **Verify:** `pytest tests/unit/core/search/ tests/unit/core/test_ranker.py` passes with 100% green assertions.
- **Completion Evidence:** Search controller executes 4 candidate runs within budget and identifies lowest-cost feasible candidate.

---

### TASK-11 — Implement Independent Verification Engine
- **Owner:** Rajdeep (CONFIRMED) · **Subsystem:** `SUB-09` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-10, BLK-08) · **Validation Level:** `UNIT`
- **Objective:** Orchestrate fresh verification rerun under new run ID, compute metric drift ($\Delta M$), and render `VERIFIED` verdict.
- **Needs:** `TASK-10`, `BLK-08`.
- **Boundary & Isolation:** Confined to `src/slokern/core/verification/` and `tests/unit/core/verification/`. Verification run must use a fresh run ID; cannot copy or alias search evidence.
- **Deliverables:** `src/slokern/core/verification/protocol.py`, `compare.py`, and automated drift comparison logic.
- **Definition of Done:**
  1. Re-executes the winning candidate configuration under a fresh, distinct `verification_run_id` (Run 6).
  2. Recomputes derived metrics from scratch using raw verification trace evidence.
  3. Evaluates metric drift ($\Delta \text{TTFT}$, $\Delta \text{Throughput}$) between search and verification runs against threshold tolerance.
  4. Emits canonical `VerificationRecord` with definitive enum: `VERIFIED`, `VERIFICATION_FAILED`, or `VERIFICATION_INCONCLUSIVE`.
- **Verify:** `pytest tests/unit/core/verification/` passes.
- **Completion Evidence:** Independent verification workflow completes and produces an auditable `VerificationRecord`.

---

### TASK-12 — Implement Report Artifact Generator and Markdown Publisher
- **Owner:** Rajdeep (INTERIM) · **Subsystem:** `SUB-10` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-11, BLK-09) · **Validation Level:** `UNIT`
- **Objective:** Serialize complete optimization history, fingerprints, drift, and verdict into an immutable Markdown and JSON report.
- **Needs:** `TASK-11`, `BLK-09`.
- **Boundary & Isolation:** Confined to `src/slokern/engine/reporting/` and `tests/unit/engine/reporting/`. Output report must redact all secrets, API tokens, and private URLs.
- **Deliverables:** `src/slokern/engine/reporting/report_builder.py`, Jinja/Markdown report template, and secret redaction filter.
- **Definition of Done:**
  1. Compiles full experiment spec, environment fingerprint, baseline summary, candidate comparison table, and verification record.
  2. Emits valid `ReportArtifact` JSON and self-contained human-readable `report.md`.
  3. Discloses all declared limitations, measurement bounds, and cost accounting mode (Mode A vs Mode B).
  4. Automated secret scanner asserts zero API keys, tokens, or private endpoint URLs in generated output.
- **Verify:** `pytest tests/unit/engine/reporting/` passes; generated report validates against `ReportArtifact` schema.
- **Completion Evidence:** Self-contained report artifact is published and passes schema validation and secret audit.

---

### TASK-13 — Implement Minimal CLI Runner (`slokern verify / optimize / smoke-test`)
- **Owner:** Rajdeep (INTERIM) · **Subsystem:** `SUB-11` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-12) · **Validation Level:** `UNIT`
- **Objective:** Build command-line interface allowing users to run preflight smoke tests, 2×2 optimization, and verification.
- **Needs:** `TASK-12`.
- **Boundary & Isolation:** Confined to `src/slokern/cli/` and entry points in `pyproject.toml`. Standard library `argparse` only; no large external CLI frameworks.
- **Deliverables:** `src/slokern/cli/main.py` implementing `smoke-test`, `optimize`, `verify`, and `report` subcommands.
- **Definition of Done:**
  1. `slokern --help` displays clean, documented commands and exits with code 0.
  2. `slokern smoke-test` runs preflight check and prints environment fingerprint.
  3. `slokern optimize --spec <path>` executes baseline + 4-candidate search, selects winner, and runs verification.
  4. Machine-readable JSON output supported via `--json` flag; human-readable summaries formatted in terminal tables.
- **Verify:** `pytest tests/unit/cli/` passes.
- **Completion Evidence:** An end-to-end experiment can be launched and audited purely from the terminal.

---

### TASK-14 — Benchmark Data Integrity and Trace Audit Suite
- **Owner:** Adriraj (CONFIRMED) · **Subsystem:** `SUB-06` / `SUB-07` · **Priority:** P1 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-07; active Oct 21–30) · **Validation Level:** `UNIT`
- **Objective:** Build comprehensive test suite verifying JSONL trace integrity, metadata completeness, and client saturation detection.
- **Needs:** `TASK-07`.
- **Boundary & Isolation:** Confined to `tests/contract/test_fixtures_validate.py` and benchmark audit utilities. Owned and executed by Adriraj.
- **Deliverables:** Automated trace integrity audit test suite; test fixtures for invalid, contaminated, and saturated runs.
- **Definition of Done:**
  1. Audits recorded request traces for monotonic microsecond timestamp progression (`scheduled_at <= sent_at <= first_token_at <= completed_at`).
  2. Audits offered rate vs achieved rate; verifies `generator_saturated` is accurately flagged when client queue builds up.
  3. Detects and rejects missing fields, corrupt records, or synthetic anomalies in benchmark data.
  4. Signs off on experimental measurement credibility and documents measurement limitations.
- **Verify:** `pytest tests/contract/test_fixtures_validate.py` passes with 0 errors.
- **Completion Evidence:** Adriraj completes benchmark integrity audit and validates physical trace authenticity.

---

### TASK-15 — Independent Decision Correctness Verification Suite
- **Owner:** Daksh (CONFIRMED) · **Subsystem:** `SUB-03` / `SUB-09` · **Priority:** P1 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-11; active Oct 24–30) · **Validation Level:** `UNIT`
- **Objective:** Build independent test suite auditing hard SLO evaluations, reason codes, tie-breaking, and verification verdicts.
- **Needs:** `TASK-11`.
- **Boundary & Isolation:** Confined to `tests/contract/test_verification_independence.py` and decision audit test suites. Owned and executed by Daksh.
- **Deliverables:** Independent decision verification test suite covering boundary cases, edge cases, and ranking policies.
- **Definition of Done:**
  1. Tests all comparison operators (`<`, `<=`, `>`, `>=`) across edge values ($\epsilon$ above/below threshold).
  2. Verifies that non-feasible and inconclusive candidates are strictly excluded from ranking across all objectives.
  3. Audits independent verification run: verifies that verification fails if threshold drift exceeds declared margin.
  4. Validates that candidate selection deterministically follows declared objective semantics and tie-breaking rules.
- **Verify:** `pytest tests/contract/test_verification_independence.py` passes with 0 errors.
- **Completion Evidence:** Daksh completes decision correctness audit and verifies deterministic evaluator behavior.

---

### TASK-16 — End-to-End System Smoke Test and Submission Packaging
- **Owner:** Rajdeep (CONFIRMED) · **Subsystem:** `SUB-01` · **Priority:** P0 (DEMO-CRITICAL) · **Status:** `BLOCKED` (by TASK-13..15, Live Runs) · **Validation Level:** `LIVE`
- **Objective:** Validate full pipeline from clean clone install to verified report artifact; compile Devpost submission text and demo runbook.
- **Needs:** `TASK-13`, `TASK-14`, `TASK-15`, Live Runs.
- **Boundary & Isolation:** Repository-wide integration smoke test. Must execute cleanly in an isolated clean environment without pre-existing state.
- **Deliverables:** Devpost submission package, finalized README, verified demo runbook (`docs/demo-script.md`), tool feedback register (`docs/hackathon-feedback.md`), demo video recording ($\le 3$ minutes).
- **Definition of Done:**
  1. Complete pipeline executes end-to-end on clean machine clone: install -> smoke test -> 2×2 search -> verification -> report.
  2. Verified physical evidence artifact (`ReportArtifact`) committed with unaggregated JSONL traces and environment fingerprint.
  3. Demo script rehearsed and verified against live system; video recorded showing real verification verdict.
  4. Devpost text, video link, and repository tagged and submitted 4 hours before October 30, 10:00 AM PDT deadline.
- **Verify:** Clean clone automated smoke test script passes with exit code 0.
- **Completion Evidence:** Official submission package submitted to hackathon organizers.

---

### TASK-17 — Control Plane REST API and SSE Streaming
- **Owner:** Rajdeep (INTERIM) · **Subsystem:** `SUB-11` · **Priority:** P2 (POST-HACKATHON) · **Status:** `DEFERRED` · **Validation Level:** `NONE`
- **Objective:** Implement FastAPI HTTP endpoints and SSE streams for web consumers.
- **Needs:** `TASK-16`.
- **Boundary & Isolation:** Confined to `src/slokern/api/` and `tests/unit/api/`. Formally deferred to post-hackathon execution to protect core inference verification critical path.
- **Deliverables:** FastAPI application exposing `/experiments`, `/runs`, `/verification`, and `/reports` endpoints.
- **Definition of Done:**
  1. HTTP endpoints serve valid Pydantic contract payloads.
  2. Server-Sent Events (SSE) stream live progress telemetry during active experiments.
  3. API test suite in `tests/unit/api/` passes.
- **Verify:** `pytest tests/unit/api/` passes.
- **Completion Evidence:** Post-hackathon release tag.

---

### TASK-18 — Frontend Command Center React UI
- **Owner:** Rajdeep (INTERIM) · **Subsystem:** `SUB-12` · **Priority:** P2 (POST-HACKATHON) · **Status:** `DEFERRED` · **Validation Level:** `NONE`
- **Objective:** Implement React + Vite dashboard displaying experiment telemetry, comparison charts, and verification badges.
- **Needs:** `TASK-17`.
- **Boundary & Isolation:** Confined to `frontend/`. Formally deferred to post-hackathon execution to eliminate concentration risk (`BLK-07`).
- **Deliverables:** React components in `frontend/src/` displaying metrics, Pareto charts, and verification proof badges.
- **Definition of Done:**
  1. Frontend compiles without TypeScript errors (`tsc --noEmit`).
  2. Dashboard renders telemetry, comparison graphs, and verification badges.
  3. Offline fixtures and simulated runs unambiguously labeled **`DEMO DATA`**.
- **Verify:** `npm run build && npm test` in `frontend/`.
- **Completion Evidence:** Post-hackathon release tag.

---

## 9. Agent Operating Checklist & Safe Execution Protocol

All coding agents operating in this repository must strictly follow this operating protocol:

### 9.1 Pre-Implementation Checklist
- [ ] **Step 1: Read Applicable Instructions:** Read repository-level `AGENTS.md`, `README.md`, `ROADMAP.md`, and subsystem notes before touching any files.
- [ ] **Step 2: Inspect Git Status & Diffs:** Run `git status` and `git diff` first. Preserve all existing uncommitted user changes; never reset, overwrite, or discard them.
- [ ] **Step 3: Verify Subsystem Ownership:** Confirm that the task belongs to the authorized owner and falls strictly within allowable file paths (`docs/ownership.md`).
- [ ] **Step 4: Contract Immutability Discipline:** Never alter Pydantic models in `src/slokern/contracts/` or enum values without explicit authorization from Rajdeep.

### 9.2 Implementation & Modification Rules
- [ ] **Step 5: Bounded & Minimal Changes:** Implement the narrowest, most cohesive change that satisfies the task acceptance criteria. Avoid sprawling refactors.
- [ ] **Step 6: No Synthetic Claims:** Never present mocks, fixtures, or simulated runs as live GPU measurements. Always label synthetic data **`DEMO DATA`**.
- [ ] **Step 7: Preserved Documentation Comments:** Maintain documentation integrity. Preserve all existing docstrings, rationale comments, and ADR references.

### 9.3 Validation & Reporting Rules
- [ ] **Step 8: Run Repository-Supported Tests:** Execute the narrowest relevant checks first, then broader checks (e.g. `.venv\Scripts\pytest.exe -v -m "not live"`).
- [ ] **Step 9: Report Exact Test Outcomes Honestly:** Never claim tests passed if they were not run or failed. Distinguish `passed`, `failed`, `skipped`, and `not run`.
- [ ] **Step 10: Task Status Transition Rule:** Update a task's status to `DONE` only when its defined physical evidence threshold is met.
- [ ] **Step 11: Document Diffs & Artifacts:** Provide a clear summary of exact files modified, test commands executed, evidence produced, limitations, and follow-up actions.

---

## 10. Human Daily Review Checklist & Update Template

### 10.1 Human Daily Review Checklist (Rajdeep & Collaborators)
Every evening during active sprint execution (Oct 21–30):
- [ ] **1. Test Suite Green Check:** Verify `.venv\Scripts\pytest -v -m "not live"` passes 100% on active integration branch.
- [ ] **2. Dependency & Bytecode Check:** Verify `python -m pip check` and `python -m compileall src tests` exit with code 0.
- [ ] **3. Working Tree Hygiene:** Verify `git status --porcelain` shows zero untracked debris, stray test artifacts, or temporary logs.
- [ ] **4. Blocker Register Review:** Review active blockers in Section 1.3 and Section 6.1; verify each blocker has an active unblocking action.
- [ ] **5. Collaborator Handoff Check:** Review incoming trace audits from Adriraj (Oct 21–30) and decision verification reports from Daksh (Oct 24–30).
- [ ] **6. Next Day Priorities Alignment:** Confirm next day's 1–3 priorities match the day-by-day checklist in Section 7.

### 10.2 Concise Daily Update Template
```markdown
### Daily Engineering Update — YYYY-MM-DD
- **Active Milestone:** Phase [B/C/D/E/F] (Day X of 10)
- **Completed Work & Deliverables:**
  - [Task ID]: Summary of deliverable and physical artifact location.
- **Validation Evidence:**
  - Test command: `[exact command]` -> [X passed, Y failed, Z seconds]
  - Bytecode / Pip check: [Exit code 0 / clean]
- **Active Blockers & Decisions Needed:**
  - [BLK-xx]: Current status, accountable owner, direct next step.
  - [DEC-xx]: Option recommended and rationale.
- **Modified Files Summary:**
  - `path/to/file.py`: Reason for modification.
- **Next Day Priorities (Top 1–3):**
  1. Priority 1 (Owner: [Name])
  2. Priority 2 (Owner: [Name])
  3. Priority 3 (Owner: [Name])
```

---

## 11. Core Product Principles & Evidence Invariants

All implementation and documentation across this repository must adhere to the six non-negotiable delivery invariants:

1. **Do Not Guess the Optimal Configuration:** Find it experimentally, then independently verify it under controlled, reproducible conditions.
2. **Deterministic Governance:** Deterministic Python code strictly owns metric calculation, constraint evaluation, experiment-budget enforcement, candidate ranking, and verification verdicts. No LLM or heuristic may override hard SLO constraints.
3. **Strict 6-Run Total Experiment Budget:**
   $$\text{Total Runs} = 1 \text{ Baseline} + 4 \text{ Search Candidates} + 1 \text{ Independent Verification Rerun} = 6 \text{ Runs}$$
   Search strictly terminates after 5 runs to preserve the 6th run for independent verification.
4. **Mandatory Independent Verification:** A candidate configuration marked `FEASIBLE` during search is never awarded the verified badge until a secondary run under a distinct `verification_run_id` independently satisfies all constraints. Search metrics are never recycled as verification proof.
5. **Traceable Microsecond Evidence:** Every aggregate metric must be directly traceable to microsecond-accurate raw client request traces (`RawRequestMeasurement` in JSONL). Warm-up requests (`is_warmup = True`) are strictly excluded from percentile calculations.
6. **Honest Dual-Mode Cost Accounting:** If authoritative cloud provider rates cannot be verified in writing, monetary cost is reported as **`unavailable`**, and candidate selection falls back to Mode B (non-monetary systems proxy: GPU-seconds per request or throughput under SLO). Never fabricate or guess prices. Never claim global optimality beyond the tested search space.

---

## 9. Agent Operating Checklist & Safe Execution Protocol

All coding agents operating in this repository must strictly follow this operating protocol:

### 9.1 Pre-Implementation Checklist
- [ ] **Step 1: Read Applicable Instructions:** Read repository-level `AGENTS.md`, `README.md`, `ROADMAP.md`, and subsystem notes before touching any files.
- [ ] **Step 2: Inspect Git Status & Diffs:** Run `git status` and `git diff` first. Preserve all existing uncommitted user changes; never reset, overwrite, or discard them.
- [ ] **Step 3: Verify Subsystem Ownership:** Confirm that the task belongs to the authorized owner and falls strictly within allowable file paths (`docs/ownership.md`).
- [ ] **Step 4: Contract Immutability Discipline:** Never alter Pydantic models in `src/slokern/contracts/` or enum values without explicit authorization from Rajdeep.

### 9.2 Implementation & Modification Rules
- [ ] **Step 5: Bounded & Minimal Changes:** Implement the narrowest, most cohesive change that satisfies the task acceptance criteria. Avoid sprawling refactors.
- [ ] **Step 6: No Synthetic Claims:** Never present mocks, fixtures, or simulated runs as live GPU measurements. Always label synthetic data **`DEMO DATA`**.
- [ ] **Step 7: Preserved Documentation Comments:** Maintain documentation integrity. Preserve all existing docstrings, rationale comments, and ADR references.

### 9.3 Validation & Reporting Rules
- [ ] **Step 8: Run Repository-Supported Tests:** Execute the narrowest relevant checks first, then broader checks (e.g. `.venv\Scripts\pytest.exe -v -m "not live"`).
- [ ] **Step 9: Report Exact Test Outcomes Honestly:** Never claim tests passed if they were not run or failed. Distinguish `passed`, `failed`, `skipped`, and `not run`.
- [ ] **Step 10: Task Status Transition Rule:** Update a task's status to `DONE` only when its defined physical evidence threshold is met.
- [ ] **Step 11: Document Diffs & Artifacts:** Provide a clear summary of exact files modified, test commands executed, evidence produced, limitations, and follow-up actions.

---

## 10. Human Daily Review Checklist & Update Template

### 10.1 Human Daily Review Checklist (Rajdeep & Collaborators)
Every evening during active sprint execution (Oct 21–30):
- [ ] **1. Test Suite Green Check:** Verify `.venv\Scripts\pytest -v -m "not live"` passes 100% on active integration branch.
- [ ] **2. Dependency & Bytecode Check:** Verify `python -m pip check` and `python -m compileall src tests` exit with code 0.
- [ ] **3. Working Tree Hygiene:** Verify `git status --porcelain` shows zero untracked debris, stray test artifacts, or temporary logs.
- [ ] **4. Blocker Register Review:** Review active blockers in Section 1.3 and Section 6.1; verify each blocker has an active unblocking action.
- [ ] **5. Collaborator Handoff Check:** Review incoming trace audits from Adriraj (Oct 21–30) and decision verification reports from Daksh (Oct 24–30).
- [ ] **6. Next Day Priorities Alignment:** Confirm next day's 1–3 priorities match the day-by-day checklist in Section 7.

### 10.2 Concise Daily Update Template
```markdown
### Daily Engineering Update — YYYY-MM-DD
- **Active Milestone:** Phase [B/C/D/E/F] (Day X of 10)
- **Completed Work & Deliverables:**
  - [Task ID]: Summary of deliverable and physical artifact location.
- **Validation Evidence:**
  - Test command: `[exact command]` -> [X passed, Y failed, Z seconds]
  - Bytecode / Pip check: [Exit code 0 / clean]
- **Active Blockers & Decisions Needed:**
  - [BLK-xx]: Current status, accountable owner, direct next step.
  - [DEC-xx]: Option recommended and rationale.
- **Modified Files Summary:**
  - `path/to/file.py`: Reason for modification.
- **Next Day Priorities (Top 1–3):**
  1. Priority 1 (Owner: [Name])
  2. Priority 2 (Owner: [Name])
  3. Priority 3 (Owner: [Name])
```

---

## 11. Core Product Principles & Evidence Invariants

All implementation and documentation across this repository must adhere to the six non-negotiable delivery invariants:

1. **Do Not Guess the Optimal Configuration:** Find it experimentally, then independently verify it under controlled, reproducible conditions.
2. **Deterministic Governance:** Deterministic Python code strictly owns metric calculation, constraint evaluation, experiment-budget enforcement, candidate ranking, and verification verdicts. No LLM or heuristic may override hard SLO constraints.
3. **Strict 6-Run Total Experiment Budget:**
   $$\text{Total Runs} = 1 \text{ Baseline} + 4 \text{ Search Candidates} + 1 \text{ Independent Verification Rerun} = 6 \text{ Runs}$$
   Search strictly terminates after 5 runs to preserve the 6th run for independent verification.
4. **Mandatory Independent Verification:** A candidate configuration marked `FEASIBLE` during search is never awarded the verified badge until a secondary run under a distinct `verification_run_id` independently satisfies all constraints. Search metrics are never recycled as verification proof.
5. **Traceable Microsecond Evidence:** Every aggregate metric must be directly traceable to microsecond-accurate raw client request traces (`RawRequestMeasurement` in JSONL). Warm-up requests (`is_warmup = True`) are strictly excluded from percentile calculations.
6. **Honest Dual-Mode Cost Accounting:** If authoritative cloud provider rates cannot be verified in writing, monetary cost is reported as **`unavailable`**, and candidate selection falls back to Mode B (non-monetary systems proxy: GPU-seconds per request or throughput under SLO). Never fabricate or guess prices. Never claim global optimality beyond the tested search space.

