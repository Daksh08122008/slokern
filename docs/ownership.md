# SLOKern Engineering Ownership & Execution Model

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Canonical Single Source of Truth for Subsystem Ownership & Governance  
> **Execution Model:** Strict Solo Execution  
> **Sole Technical & Implementation Owner:** Rajdeep  
> **Authority:** Aligned with [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [docs/implementation-status.md](implementation-status.md)  
> **Last Updated:** 2026-10-26 (Sprint Day 7 / Strict Solo Execution Migration)

---

## 1. Operating Model & Accountability Governance

SLOKern operates under a **Strict Solo-Development and Solo-Execution Model**: a single accountable technical owner (**Rajdeep**) responsible for all architecture, critical-path implementation, benchmarking, evaluator logic, verification, documentation, and final hackathon integration.

### Core Invariants:
1. **Sole Accountable Owner:** Rajdeep is the sole active technical owner, implementation owner, testing/verification owner, benchmarking owner, architecture authority, integration authority, and hackathon submission owner across all 13 subsystems (`SUB-01` through `SUB-13`). There are no active collaborator assignments, delegated responsibilities, shared ownership, or external reviewer gates in the execution plan.
2. **Autonomous Critical Path:** Complete MVP functionality is executed, tested, and verified independently by Rajdeep. No critical-path milestone or task depends on another person's availability, sign-off, or approval.
3. **Automated Verification Standards:** Former collaborator audit workstreams (Benchmark Data Integrity and Decision Correctness) are incorporated directly into Rajdeep-owned automated regression test suites (`tests/contract/test_fixtures_validate.py` and `tests/contract/test_verification_independence.py`). Measurement credibility and decision correctness are enforced through deterministic code and reproducible physical evidence, not manual human reviews.
4. **Historical Contributors:** Early architectural and design contributions from former team members are acknowledged in Section 4. They have no active tasks or ongoing project responsibilities.
5. **Concentration Risk Policy (BLK-07):** Because Rajdeep is the sole owner across all 13 subsystems (100% concentration), non-essential subsystems (FastAPI control plane, React frontend live integration) are strictly deferred to post-hackathon execution to protect delivery of the core inference verification pipeline (CLI + report generator).

---

## 2. Authoritative Subsystem Ownership Matrix

| SUB-ID | Subsystem | Accountable Owner (+Status) | Responsibility | Current Status | Dependencies | Next Deliverable | Acceptance Criterion | Proposed Delegate (Optional) |
|---|---|---|---|---|---|---|---|---|
| **SUB-01** | Architecture & Scope Governance | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Architectural integrity, scope freeze enforcement, decision policies, and hackathon compliance. | IMPLEMENTED / STATIC | None | Ratified MVP Scope Freeze & DEC resolutions | Acceptance of `docs/implementation-status.md` as canonical scope. | None |
| **SUB-02** | Shared Contracts & Schema Registry | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Pydantic v2 schemas (`src/slokern/contracts/`), strict model validation (`extra='forbid'`), and committed JSON schema emission. | IMPLEMENTED / UNIT | None | Maintain contract immutability | 11 JSON schemas match committed contracts; 135 contract tests pass. | None |
| **SUB-03** | Feasibility Evaluator Core | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Deterministic evaluation of `MetricSet` against hard `SLOSpec`, reason code assignment, and boundary safety. | IMPLEMENTED / UNIT | SUB-02 | Implement hard SLO boundary regression suite | Deterministic verdict emitted; NaN/negative latencies safely guarded. | None |
| **SUB-04** | Candidate Identity & Deterministic Ranking | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Deterministic candidate ID generation, 2×2 parameter matrix definition, and ranking by declared objective. | IMPLEMENTED / UNIT | SUB-02, SUB-03 | Resolve budget and ranking caveats (`BLK-15`, `BLK-16`) | Enforce 6-run budget invariant and require valid objective evidence for ranking. | None |
| **SUB-05** | Serving Adapter & Runtime Infrastructure | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Serving runtime adapter interface, deterministic `FakeServingAdapter`, and Nebius Cloud adapter (`nebius.py`). | IMPLEMENTED (Fake + Nebius Transport) / UNIT; LIVE NOT RUN | DEC-01, BLK-04 | Execute live preflight smoke test on Nebius Cloud | Live endpoint responds with valid HTTP 200 token stream under `NEBIUS_API_KEY`. | None |
| **SUB-06** | Subprocess Load Generator & Workload Fixtures | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Subprocess request dispatch, Poisson/constant scheduling, saturation detection, and raw JSONL logging. | IMPLEMENTED (Loadgen Runner & JSONL Tracing) / UNIT & SYNTHETIC VERIFICATION (DEMO DATA) | SUB-02, SUB-05 | Implement trace integrity automated verification | Output JSONL passes validation against `RawRequestMeasurement`; unit tests pass. | None |
| **SUB-07** | Metrics Engine Core | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Deterministic derivation of `MetricSet` from raw request traces, percentiles, throughput, and error rates. | IMPLEMENTED (Metrics Engine Core) / UNIT & SYNTHETIC VERIFICATION | SUB-02, SUB-06 | Implement golden metric validation suite | Percentiles, throughput, and offered/achieved loads computed against golden fixtures. | None |
| **SUB-08** | Experiment Orchestration & Run Lifecycle | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Single-run executor (`run_executor.py`), multi-candidate search controller (`grid.py`), 6-run budget enforcement, and run persistence. | IMPLEMENTED (SingleRunExecutor & 2×2 Grid Search) / UNIT & SYNTHETIC VERIFICATION (DEMO DATA) | SUB-04, SUB-05, SUB-06, SUB-07 | Wire winning candidate into Independent Verification Runner (`TASK-11`) | Complete 5-run search executes end-to-end and saves `search_result.json` under DEMO DATA. | None |
| **SUB-09** | Independent Verification Engine | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Independent rerun orchestration under fresh run ID, metric drift computation ($\Delta M$), and verification verdict. | READY / STUB | SUB-03, SUB-08 | Implement drift comparison and verification protocol (`TASK-11`) | Verification runner emits `VERIFIED` or `VERIFICATION_FAILED` under fresh `verification_run_id`. | None |
| **SUB-10** | Report Artifact Generator | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Compilation of self-contained Markdown and JSON `ReportArtifact` linking headline metrics to physical traces. | ABSENT / CRITICAL PATH | SUB-02, SUB-08, SUB-09 | Markdown report serializer script (`TASK-12`) | Markdown report generated with physical trace paths and fingerprints. | None |
| **SUB-11** | Control Plane API & CLI | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Minimal CLI runner (`slokern verify`, `slokern optimize`, `slokern smoke-test`); FastAPI REST app (deferred). | MINIMAL CLI / DEFERRED API | SUB-08, SUB-09, SUB-10 | CLI entry point implementing `slokern verify` (`TASK-13`) | `slokern --help` executes and returns exit code 0. | None |
| **SUB-12** | Frontend Command Center & Presentation | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | Full React + Vite dashboard in `frontend/src/App.tsx` (2553 lines, `DESIGN.md`) with 9 pages, Pareto visualizer, and reporting views operating with persistent `DEMO DATA` labeling. | IMPLEMENTED (Frontend Command Center & Reporting Presentation) / DEMO DATA (API DEFERRED) | SUB-11 | Maintain demo fixtures; defer live API integration | UI displays 9 pages with persistent DEMO DATA labeling. | None |
| **SUB-13** | CI/CD, Packaging & Test Automation | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | GitHub Actions CI workflow, packaging metadata (`pyproject.toml`), test harness, and baseline hygiene. | PARTIAL / UNIT | None | CI hardening: add ruff, mypy, and secret checks (`BLK-13`) | Clean `git status --porcelain` and hardened GitHub Actions CI workflow. | None |

---

## 3. Solo Verification & Quality Assurance Model

Under strict solo execution, quality and credibility are guaranteed by deterministic code and physical evidence rather than multi-person review gates:

1. **Automated Benchmark Integrity:** Trace validity, monotonicity of timestamps, schema conformance (`RawRequestMeasurement`), and saturation detection (`generator_saturated = True`) are verified programmatically via `tests/contract/test_fixtures_validate.py` and metrics unit tests.
2. **Automated Decision Verification:** Hard SLO boundary tests (`<`, `<=`, `>`, `>=`), missing/invalid metric handling (NaN, negative values), and fresh verification run ID invariants (`verification_run_id != original_run_id`) are verified via `tests/contract/test_verification_independence.py` (16 passed contract tests).
3. **Independent Verification Execution:** In SLOKern, "independent verification" is an automated experiment pipeline invariant: re-running the selected candidate configuration under a fresh run ID with a clean load generator invocation and recomputing metrics from scratch. It is an algorithmic protocol, not a human collaborator review.

---

## 4. Historical Contributors

The following individuals contributed early architectural explorations or prototype designs:
- **Aman:** Historical serving runtime designs (Phase 1, Oct 13–17, 2026).
- **Rohan:** Historical search and ranking designs (Phase 1, Oct 13–17, 2026).
- **Adriraj:** Historical benchmark schema exploration and golden fixtures (Phase 1–2).
- **Daksh:** Historical boundary test suite structure and audit concepts (Phase 1–2).

All active project workstreams are consolidated under Rajdeep. Former contributors are not participating in current execution, and no ongoing tasks, gates, or deliverables are assigned to them.

---

## 5. Governance Protocols

### 5.1 Recording Ownership Changes
To update subsystem scope, status, or deliverables:
1. Update the accountable owner entry in the Authoritative Subsystem Ownership Matrix table in Section 2.
2. Append a dated entry to the Ownership Changelog (Section 6) citing the reason, decision reference, and Rajdeep's approval.
3. Commit the change to the active integration branch.

### 5.2 Reporting Blocked Work
When work on a subsystem is impeded:
1. File a structured blocker entry in `docs/implementation-status.md` using the format:
   `BLK-xx | Priority (P0/P1/P2) | Evidence | Actual Consequence | Affected Subsystems | Owner | Smallest Remediation | Closing Test`
2. Update the `Blocked-by` column in the Subsystem Summary Table of `docs/implementation-status.md`.
3. If the blocker requires an architectural or scope decision, escalate to Rajdeep with a numbered decision (`DEC-xx`) containing concrete options and recommendations.

---

## 6. Ownership Changelog

| Date | Subsystem ID | Previous Owner | New Owner | Status | Authority / Rationale |
|---|---|---|---|---|---|
| **2026-10-18** | SUB-01 to SUB-13 | Distributed team (Aman, Rohan, Daksh, Adriraj) | Rajdeep | CONSOLIDATED | Consolidation of critical-path execution under sole technical owner. |
| **2026-10-19** | SUB-06, SUB-07 | Rajdeep | Rajdeep (Adriraj audit) | BOUNDED COLLABORATOR | Established bounded collaborator workstream for Adriraj (Benchmark Integrity, active Oct 21). |
| **2026-10-19** | SUB-03, SUB-09 | Rajdeep | Rajdeep (Daksh audit) | BOUNDED COLLABORATOR | Established bounded collaborator workstream for Daksh (Decision Verification, active Oct 24). |
| **2026-10-21** | SUB-11, SUB-12 | Rajdeep | Rajdeep | DEFERRED | Formally deferred FastAPI control plane and React UI to post-MVP to mitigate concentration risk (BLK-07). |
| **2026-10-22** | SUB-03, SUB-09 | Rajdeep (Daksh audit) | Rajdeep (confirmed sole implementer; Daksh restricted to decision audit allowlist) | RESTRICTED | Repository repair and strict collaborator scope isolation: Daksh restricted to test allowlist `tests/contract/test_verification_independence.py`. |
| **2026-10-24** | SUB-06, SUB-07, SUB-08, SUB-12 | Rajdeep | Rajdeep (Adriraj/Daksh active audits) | RECONCILED / DAY 5 | Reconciled Day 5 status: confirmed SUB-06, SUB-07, SUB-08, SUB-12 implemented with DEMO DATA / synthetic verification. Hybrid solo-core model confirmed. |
| **2026-10-26** | SUB-01 to SUB-13 | Rajdeep (Hybrid solo-core with Adriraj & Daksh audits) | Owner: Rajdeep \| Status: ACTIVE \| Execution: SOLO | STRICT SOLO EXECUTION | Migration from hybrid solo-core to strict solo-development and solo-execution model (DEC-0015). All active collaborator workstreams removed. Benchmark integrity and decision verification absorbed into Rajdeep-owned automated regression suites. |
