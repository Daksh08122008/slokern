# SLOKern Engineering Ownership & Execution Model

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Canonical Single Source of Truth for Subsystem Ownership & Governance  
> **Execution Model:** Single-Owner Core Execution with Bounded Collaborators  
> **Sole Technical Owner & Integration Authority:** Rajdeep  
> **Collaborator Workstreams:** Adriraj (Benchmark Integrity, active Oct 21), Daksh (Decision Verification, active Oct 24)  
> **Authority:** Aligned with [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [docs/implementation-status.md](implementation-status.md)

---

## 1. Operating Model & Accountability Governance

SLOKern operates under a **hybrid solo-core model**: a single technical owner (Rajdeep) accountable for architecture and critical-path implementation, augmented by bounded collaborator workstreams for data integrity (Adriraj) and independent decision verification (Daksh).

### Core Invariants:
1. **Single Accountable Owner:** Every subsystem has exactly one directly accountable owner. No shared, diffuse, or team-level ownership.
2. **Autonomous Critical Path:** Rajdeep remains capable of delivering the complete minimum viable product without waiting for either collaborator. No critical-path milestone is blocked by collaborator availability.
3. **Bounded Collaborator Start Dates:**
   - **Adriraj:** Active execution window: **October 21–30, 2026**. Focus: measurement credibility, benchmark schema validation, load-generation integrity audits.
   - **Daksh:** Active execution window: **October 24–30, 2026**. Focus: decision correctness verification, hard SLO boundary auditing, optimizer validation.
4. **Historical Contributors:** Former team members (Aman on serving, Rohan on search) contributed early design work in Phase 1 (Oct 13–17, 2026). They are not participating in current execution, and no ongoing tasks are assigned to them.
5. **Concentration Risk Policy (BLK-07):** Because Rajdeep is currently accountable for more than half of all subsystems (69%), non-essential subsystems (FastAPI control plane, React frontend) are formally deferred to post-hackathon execution to protect delivery of the core inference verification pipeline.

---

## 2. Authoritative Subsystem Ownership Matrix

| SUB-ID | Subsystem | Accountable owner (+status) | Responsibility | Current status | Dependencies | Next deliverable | Acceptance criterion | Proposed delegate (optional) |
|---|---|---|---|---|---|---|---|---|
| **SUB-01** | Architecture & Scope Governance | Rajdeep (CONFIRMED) | Architectural integrity, scope freeze enforcement, decision policies, and hackathon compliance. | IMPLEMENTED / STATIC | None | Ratified MVP Scope Freeze & DEC resolutions | Acceptance of `docs/implementation-status.md` as canonical scope. | None |
| **SUB-02** | Shared Contracts & Schema Registry | Rajdeep (CONFIRMED) | Pydantic v2 schemas (`src/slokern/contracts/`), strict model validation, and committed JSON schema emission. | IMPLEMENTED / UNIT | None | JSON schema export script (`scripts/gen_contracts.py`) | Schemas exported to `schemas/` matching all 11 models. | None |
| **SUB-03** | Feasibility Evaluator Core | Rajdeep (CONFIRMED) | Deterministic evaluation of `MetricSet` against hard `SLOSpec`, reason code assignment, and boundary safety. | IMPLEMENTED / UNIT | SUB-02 | Evaluator boundary patch for NaN and negative values | NaN evaluates to INCONCLUSIVE; tests pass. | Daksh (Audit active Oct 24) |
| **SUB-04** | Candidate Identity & Deterministic Ranking | Rajdeep (INTERIM) | Deterministic candidate ID generation, 2×2 parameter matrix definition, and ranking by declared objective. | IMPLEMENTED / UNIT | SUB-02, SUB-03 | Float/integer canonicalization in candidate hashing | `generate_candidate_id` produces identical hash for int and float. | None |
| **SUB-05** | Serving Adapter & Runtime Infrastructure | Rajdeep (INTERIM) | Serving runtime adapter interface, deterministic `FakeServingAdapter`, and Nebius Cloud adapter. | ABSENT / NONE | DEC-01 | Working `FakeServingAdapter` generating synthetic responses | `tests/integration/test_pipeline_fake_adapter.py` passes offline. | None |
| **SUB-06** | Subprocess Load Generator & Workload Fixtures | Rajdeep (CONFIRMED) | Subprocess request dispatch, Poisson/constant scheduling, saturation detection, and raw JSONL logging. | ABSENT / NONE | SUB-02, SUB-05 | Minimal request dispatcher writing `.jsonl` recordings | Output JSONL passes validation against `RawRequestMeasurement`. | Adriraj (Audit active Oct 21) |
| **SUB-07** | Metrics Engine Core | Rajdeep (CONFIRMED) | Deterministic derivation of `MetricSet` from raw request traces, percentiles, throughput, and error rates. | ABSENT / NONE | SUB-02, SUB-06 | Percentile and throughput aggregation functions | `tests/unit/core/metrics/test_percentiles.py` passes on JSONL fixture. | Adriraj (Audit active Oct 21) |
| **SUB-08** | Experiment Orchestration & Run Lifecycle | Rajdeep (INTERIM) | Single-run executor, multi-candidate search controller, 6-run budget enforcement, and run persistence. | ABSENT / NONE | SUB-04, SUB-05, SUB-06, SUB-07 | Single-run execution pipeline script | Complete single run executes end-to-end and saves `RunRecord`. | None |
| **SUB-09** | Independent Verification Engine | Rajdeep (CONFIRMED) | Independent rerun orchestration under fresh run ID, metric drift computation ($\Delta M$), and verification verdict. | ABSENT / NONE | SUB-03, SUB-08 | Drift comparison and verification verdict evaluator | Drift calculation emits VERIFIED or VERIFICATION_FAILED. | Daksh (Audit active Oct 24) |
| **SUB-10** | Report Artifact Generator | Rajdeep (INTERIM) | Compilation of self-contained Markdown and JSON `ReportArtifact` linking headline metrics to physical traces. | ABSENT / NONE | SUB-02, SUB-08, SUB-09 | Markdown report serializer script | Markdown report generated with physical trace paths and fingerprints. | None |
| **SUB-11** | Control Plane API & CLI | Rajdeep (INTERIM) | Minimal CLI runner (`slokern verify`, `slokern optimize`, `slokern smoke-test`); FastAPI REST app (deferred). | ABSENT / NONE | SUB-08, SUB-09, SUB-10 | CLI entry point implementing `slokern verify` | `slokern --help` executes and returns exit code 0. | None |
| **SUB-12** | Frontend Command Center & Presentation | Rajdeep (INTERIM) | React + Vite UI dashboard (deferred to post-MVP). | ABSENT / NONE | SUB-11 | Scope deferral notice | Formal freeze documenting UI as out of MVP critical path. | None |
| **SUB-13** | CI/CD, Packaging & Test Automation | Rajdeep (CONFIRMED) | GitHub Actions CI workflow, packaging metadata (`pyproject.toml`), test harness, and baseline hygiene. | PARTIAL / UNIT | None | Working tree baseline cleanup & build tool hardening | Clean `git status --porcelain` and reproducible editable install. | None |

---

## 3. Supporting Collaborator Workstreams

### 3.1 Adriraj: Benchmark Integrity & Measurement Credibility
- **Status:** CONFIRMED
- **Active Window:** October 21–30, 2026.
- **Accountable Area:** Data integrity auditing for `SUB-06` (Loadgen) and `SUB-07` (Metrics).
- **Core Responsibilities:**
  1. Validate recorded benchmark measurements against existing Pydantic schemas (`RawRequestMeasurement`, `MetricSet`).
  2. Verify completeness of required metrics, units, timestamps, and hardware metadata in experiment artifacts.
  3. Detect and flag missing, corrupt, or inconsistent record entries in JSONL traces.
  4. Audit offered arrival rates against achieved throughput to validate client saturation flags (`generator_saturated = True`).
  5. Construct automated test fixtures for failed runs, invalid measurements, and aborted requests.
  6. Document experimental measurement limitations, client overhead, and reproducibility requirements.
- **Boundary Rule:** Adriraj does not modify shared contracts or optimizer logic. Gaps are reported to Rajdeep via documented defect reports.

### 3.2 Daksh: Independent Decision Verification & Verdict Audit
- **Role:** Independent Decision Correctness and Verdict Audit Engineer (adversarial audit, not production implementation)
- **Status:** CONFIRMED
- **Active Window:** October 24–30, 2026.
- **Accountable Area:** Decision correctness and verification audit for `SUB-03` (Evaluator) and `SUB-09` (Verification).
- **Sole Responsibilities:**
  1. **Decision Correctness:** Construct deterministic contract test suites auditing hard SLO constraint evaluation across boundary thresholds (`<`, `<=`, `>`, `>=`), reason codes, and missing/invalid metric handling.
  2. **Verification Independence:** Audit that verification reruns use distinct run identities (`verification_run_id != original_run_id`), recompute metrics from fresh physical evidence, and never conflate execution crashes with SLO infeasibility.
  3. **Verdict Audit:** Audit consistency between observed physical evidence (JSONL traces) and reported candidate recommendations, publishing reproducible verdict-audit reports.
- **Exclusive Permitted Routine Edit Allowlist:**
  - `tests/contract/test_verification_independence.py` (primary routine implementation edit surface)
  - Dedicated verdict-audit reports under `artifacts/audits/` or `docs/audits/` when explicitly authorized.
- **Strictly Forbidden Implementation Surfaces:**
  Daksh has zero implementation authority and must NOT directly modify:
  - `src/slokern/contracts/**`
  - `src/slokern/engine/**` (serving, loadgen, runner, reporting)
  - `src/slokern/core/evaluator/**` (production evaluator is owned by Rajdeep)
  - `src/slokern/core/verification/**` (production verification engine is owned by Rajdeep)
  - `src/slokern/core/search/**` (optimizer)
  - `src/slokern/core/metrics/**`
  - `scripts/gen_contracts.py` or contract-generation tooling
  - `pyproject.toml`, `.github/workflows/**`, `frontend/**`
  - `AGENTS.md`, `docs/architecture.md`, `docs/decision-policy.md`, `docs/ownership.md`, or general roadmap definitions
- **Defect Escalation Procedure:**
  Daksh operates as an adversarial auditor. Production defects must be reported to Rajdeep via documented issue or pull request proposing a minimal fix, accompanied by reproducible test cases in `tests/contract/test_verification_independence.py`. Daksh must never push fixes directly to production modules or introduce parallel architectures.

---

## 4. Historical Contributors
The following individuals contributed early architectural explorations during Phase 1 (October 13–17, 2026):
- **Aman:** Historical serving runtime designs.
- **Rohan:** Historical search and ranking designs.

Both contributors are no longer participating in execution. No tasks or ongoing responsibilities are assigned to them.

---

## 5. Governance Protocols

### 5.1 Recording Ownership Changes
To reassign a subsystem or update an owner's status:
1. Update the accountable owner in the Authoritative Subsystem Ownership Matrix table in Section 2.
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
