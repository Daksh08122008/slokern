# SLOKern Engineering Ownership & Execution Model

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Reference / Single Authoritative Source of Ownership & Governance  
> **Execution Model:** Single-Owner Core Execution with Bounded Collaborators (Updated: October 19, 2026)  
> **Sole Technical Owner & Integration Authority:** Rajdeep  
> **Collaborators:** Adriraj (Benchmark Integrity, active Oct 21), Daksh (Independent Decision Verification, active Oct 24)  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

---

## 1. Operating Model & Execution Philosophy

SLOKern operates under a **single technical owner with bounded contributions from two collaborators** (a hybrid solo-core model).

The ownership model is:

- **Rajdeep:** Sole technical owner, architecture authority, critical-path implementer, integrator, and final submission owner.
- **Adriraj:** Benchmark integrity and measurement credibility, with active execution beginning **October 21, 2026**.
- **Daksh:** Independent correctness verification, with active execution beginning **October 24, 2026**.

### Core Invariants of the Operating Model

1. **Consolidated Accountability:** Rajdeep is the sole technical owner, architecture authority, and final release owner. He owns and implements all critical-path subsystems end-to-end.
2. **Autonomous Minimum Viable Product:** Rajdeep remains capable of executing the complete minimum viable product without waiting for either collaborator. No critical-path milestone is blocked by collaborator availability.
3. **Bounded Collaborator Start Dates:**
   - Adriraj is not available for substantive execution before **October 21, 2026**.
   - Daksh is not available for substantive execution before **October 24, 2026**.
   - Neither collaborator is assigned tasks before their respective start dates.
4. **No Assignment to Former Contributors:** Former team members (Aman, Rohan) are no longer participating. No work is assigned to former contributors. Their early design contributions remain acknowledged in historical project records and ADRs.
5. **Preserved Architecture & Scope Boundaries:** This transition is a restructuring of execution accountability and daily delivery. It is **not** a transfer of architecture authority, a rewrite of the engineering organization, or permission to expand product scope. The modular monolith architecture, Pydantic v2 contracts, deterministic evaluator, 6-run budget invariant, and dual-mode cost policy remain non-negotiable.

---

## 2. Authoritative Subsystem Ownership Matrix

Every subsystem has exactly one directly accountable owner mapped to actual repository modules:

| Subsystem / Area | Accountable Owner | Active From | Repository Modules & Contracts | Scope & Architectural Responsibilities |
|---|---|---|---|---|
| **Architecture & Contracts** | **Rajdeep** | Immediate (Oct 18) | `src/slokern/contracts/`, `docs/architecture.md` | Scope boundaries, modular monolith design, Pydantic v2 schemas (`WorkloadSpec`, `SLOSpec`, `CandidateConfig`, `RunRecord`, `MetricSet`, `FeasibilityResult`, `SearchResult`, `VerificationRecord`, `ReportArtifact`), enums, lifecycle state machine, and interface stability. |
| **Serving Integration & Infrastructure** | **Rajdeep** *(Hist: Aman)* | Immediate (Oct 18) | `src/slokern/engine/serving/`, `docs/deployment.md` | Base serving adapter interface, deterministic fake adapter (`fake.py`), Nebius cloud adapter (`nebius.py`), preflight smoke testing, environment fingerprinting (`environment_fingerprint`), and parameter read-back. |
| **Loadgen Subprocess & Workload** | **Rajdeep** *(Hist: Adriraj)* | Immediate (Oct 18) | `src/slokern/engine/loadgen/`, `src/slokern/engine/workload/` | Subprocess load generator execution, arrival schedules (Poisson/constant), client dispatch, unaggregated microsecond event capture to JSONL (`RawRequestMeasurement`), and generator saturation detection. |
| **Metrics Engine Core** | **Rajdeep** *(Hist: Adriraj)* | Immediate (Oct 18) | `src/slokern/core/metrics/`, `docs/metrics.md` | Deterministic percentiles (p50/p95/p99) calculation, throughput, error rates, sample count thresholds, and separation of offered load from achieved load. |
| **Feasibility Evaluator Core** | **Rajdeep** *(Hist: Daksh)* | Immediate (Oct 18) | `src/slokern/core/evaluator/`, `docs/decision-policy.md` | Deterministic hard constraint audit engine, machine-readable reason code taxonomy (`enums.py`), pass/fail/inconclusive evaluation, and audit notes. |
| **Optimizer & Search Controller** | **Rajdeep** *(Hist: Rohan)* | Immediate (Oct 18) | `src/slokern/core/search/`, `src/slokern/core/cost/` | Bounded 2×2 parameter matrix definition, stable candidate hashing, candidate ranking under declared objective (Mode A cost or Mode B proxy), 6-run budget enforcement, and stopping rationale. |
| **Verification Runner Core** | **Rajdeep** *(Hist: Daksh)* | Immediate (Oct 18) | `src/slokern/core/verification/` | Independent rerun orchestration under a fresh, distinct `verification_run_id`, metric drift computation ($\Delta M$), and final verdict determination. |
| **Control Plane API & CLI** | **Rajdeep** | Immediate (Oct 18) | `src/slokern/api/`, `src/slokern/cli/`, `src/slokern/engine/store/` | FastAPI routes, SSE streaming progress, CLI commands (`slokern verify / optimize / smoke-test`), artifact store layout, and token/secret redaction. |
| **Reporting & Presentation** | **Rajdeep** | Immediate (Oct 18) | `src/slokern/engine/reporting/`, `frontend/` | Immutable `ReportArtifact` generator, demo dashboard (offline fixtures strictly labeled **`DEMO DATA`**), demo video production, and Devpost submission. |
| **Benchmark Integrity & Credibility** | **Adriraj** | **October 21** | `src/slokern/engine/loadgen/`, `src/slokern/core/metrics/`, `fixtures/workloads/` | Measurement schema validation, metadata completeness verification, missing/inconsistent record detection, offered-vs-achieved load audits, reproducible comparison summaries, failed-run test fixtures, and measurement limitations documentation. |
| **Independent Decision Verification** | **Daksh** | **October 24** | `src/slokern/core/evaluator/`, `src/slokern/core/verification/`, `tests/unit/core/evaluator/` | Independent correctness verification test suite, hard SLO violation tests, feasibility boundary tests, missing/invalid measurement handling, failed/incomplete experiment tests, candidate selection verification under documented objective semantics, observed evidence vs reported recommendations consistency checks, and reproducible defect reports. |

### Historical Workstream Context

During the initial hackathon sprint (October 13–17, 2026), architectural concepts were explored across 5 roles:
- Rajdeep (Architecture, contracts, API), Aman (Serving runtime), Daksh (Evaluator and verification), Adriraj (Benchmarking and metrics), Rohan (Search and ranking).

Effective October 18, 2026, critical-path execution was consolidated under Rajdeep. Effective October 19, 2026, bounded collaborator workstreams are established for Adriraj (starting Oct 21) and Daksh (starting Oct 24), while Aman and Rohan are acknowledged as historical design contributors with no ongoing tasks.

---

## 3. Bounded Collaborator Workstreams

### 3.1 Adriraj: Benchmark Integrity and Measurement Credibility
**Execution Window:** October 21–30, 2026.

Adriraj owns a bounded workstream covering the benchmark-result pipeline and data integrity:

- **Specific Responsibilities:**
  1. Validate recorded benchmark measurements against existing Pydantic schemas (`RawRequestMeasurement`, `MetricSet`).
  2. Verify completeness of required metrics, units, timestamps, and hardware metadata in experiment artifacts.
  3. Detect and flag missing, corrupt, or inconsistent result records in JSONL traces.
  4. Verify that offered arrival rate is rigorously distinguished from achieved throughput, validating client saturation flags (`generator_saturated = True`).
  5. Produce reproducible candidate-comparison summaries and tables from preserved run evidence.
  6. Construct test fixtures and automated checks for failed runs, invalid measurements, and aborted requests.
  7. Document experimental measurement limitations, client overhead, and reproducibility requirements.
- **Contract Boundary:** Adriraj operates on existing schemas and interfaces. If a required measurement or metadata field is absent, he documents the gap and proposes an update to Rajdeep rather than modifying contracts unilaterally.
- **Non-Duplication:** Adriraj's work does not duplicate Daksh's decision-correctness test suite or modify search/optimizer logic.

### 3.2 Daksh: Independent Decision Verification
**Execution Window:** October 24–30, 2026.

Daksh owns a bounded workstream covering independent correctness verification and evaluator auditing:

- **Specific Responsibilities:**
  1. Construct deterministic verification test suites auditing hard SLO constraint evaluation across boundary thresholds (`<`, `<=`, `>`, `>=`).
  2. Test candidate feasibility and rejection behavior to ensure infeasible or inconclusive candidates can never win candidate selection.
  3. Verify system handling of edge cases: missing metrics, invalid measurements, divide-by-zero, empty traces, and client saturation.
  4. Validate system behavior on failed or incomplete experiments, ensuring `FAILED` execution state is never conflated with `INFEASIBLE` SLO verdict.
  5. Validate that candidate selection deterministically follows declared objective semantics (Mode A cost ranking or Mode B systems proxy ranking) and tie-breaking rules.
  6. Audit consistency between observed physical evidence (JSONL traces) and reported recommendations.
  7. Produce deterministic test suites and reproducible defect reports.
- **Contract Boundary:** Daksh must not independently redefine SLO semantics, alter optimizer logic, or change shared interfaces. If documented behavior is ambiguous, he records the ambiguity for Rajdeep to resolve.

### 3.3 Shared Ownership Rules

- Every subsystem has exactly one directly accountable owner.
- Rajdeep is the sole final integration, architecture, and submission authority.
- Adriraj owns measurement credibility; Daksh owns decision correctness.
- Neither collaborator owns system architecture or the final release package.
- Shared contracts (`src/slokern/contracts/`) are altered only with Rajdeep's explicit approval.
- Contributors submit small, reviewable changes backed by automated tests and evidence.
- Critical-path functionality must remain executable without pending collaborator contributions.

---

## 4. Dependency and Integration Policy

The conceptual dependency sequence reflects the real system data flow:

$$\text{Workload \& Configuration} \longrightarrow \text{Candidate Generation} \longrightarrow \text{Serving Execution} \longrightarrow \text{Measurement Capture} \longrightarrow \text{Result Validation} \longrightarrow \text{Feasibility \& Optimization} \longrightarrow \text{Recommendation \& Report}$$

### Integration Rules
1. **Interface Pre-Confirmation:** Rajdeep defines and confirms the schemas and interfaces collaborators consume before their respective tasks begin.
2. **Early Work Without Live Infrastructure:**
   - Adriraj begins work on October 21 using existing schemas (`src/slokern/contracts/metrics.py`) and supplied sample records / fake-adapter JSONL traces before live GPU inference is available.
   - Daksh begins work on October 24 constructing deterministic verification test cases from documented contracts and controlled test data fixtures (`fixtures/metrics_golden/`).
3. **No Unilateral Interface Changes:** Neither collaborator needs to modify core implementations or shared contracts simply to start or execute their work.
4. **Collision Avoidance:** Work on isolated branches or focused pull requests. Do not edit shared contracts or critical engine files concurrently.

---

## 5. Daily Reporting & Acceptance Protocol

To minimize overhead while maintaining absolute clarity across the hybrid team, active contributors report daily using a standardized 6-point update:

### Contributor Daily Report Format
```text
Date: YYYY-MM-DD
Contributor: [ Rajdeep | Adriraj | Daksh ]
1. What was completed today:
2. Which files changed:
3. Which tests or validation commands were executed:
4. Actual outcomes (passed / failed / skipped):
5. Outstanding blockers or ambiguities:
6. Next concrete deliverable:
```

### Review & Acceptance Rules
- Rajdeep reviews progress daily and makes explicit decisions to continue, reassign, reduce, or cut work.
- An unfinished task is **never** marked complete merely because its scheduled calendar date has passed.
- If a collaborator misses an acceptance criterion:
  1. Assess whether the task was adequately specified and whether an external blocker exists.
  2. Narrow, reassign, or complete the critical-path portion directly to protect the delivery timeline.

---

## 6. Prioritization and Contingency

When engineering tradeoffs arise, prioritize tasks in this strict order:

1. **Submission Eligibility & Required Artifacts:** Public repository, Apache 2.0 license, clean clone setup, 3-minute demo video, Devpost filing with tool feedback.
2. **Real Serving Integration & Trustworthy Measurements:** Live Nebius preflight smoke test, parameter read-back, unaggregated JSONL traces.
3. **Correct SLO Enforcement & Candidate Feasibility:** Deterministic evaluator, unambiguous reason codes, hard constraint enforcement.
4. **Reproducible Experiment Records & Recommendations:** Bounded 6-run budget, traceable fingerprints, deterministic ranking.
5. **Verification, Regression Protection & End-to-End Reliability:** Independent rerun under fresh `verification_run_id`, drift audit, automated test matrix.
6. **Documentation & Demonstration Readiness:** Rehearsed demo script, verified fallback runbook, truthful evidence presentation.
7. **Optional Polish & Nonessential Features:** Dashboard visual styling, extra chart animations, advisory AI explainers.

### Contingency Runbook
- **Infrastructure Delay:** If live GPU access is unavailable, develop and validate against the deterministic fake adapter (`fake.py`). Persistently label all fixture output **`DEMO DATA`**. Never simulate live benchmark success.
- **Missing Serving Knobs:** If a managed endpoint exposes only client request parameters, record an architectural blocker and deploy containerized vLLM on a dedicated GPU instance or refine search boundaries via ADR.
- **Client Saturation:** If dispatch skew exceeds 10 ms or offered rate drops > 10%, mark run `CONTAMINATED` (`INCONCLUSIVE`), tune worker concurrency, and rerun.
- **Verification Failure:** If the independent rerun breaches an SLO, render `VERIFICATION_FAILED` honestly. Never award the verified status.
- **Time Constraints:** Reduce feature breadth before compromising evidence integrity or correctness.

---

## 7. Subsystem Boundaries & Invariant Guardrails

1. **Serving Reality vs. Optimizer Intent:** The serving adapter reports only what the runtime can apply and read back. The optimizer never invents hypothetical knobs.
2. **Benchmarking Fidelity vs. Feasibility Evaluation:** Loadgen records raw microsecond timestamps and flags saturation. It does not render verdicts. Evaluator applies mathematical rules to derived metrics; it does not alter raw traces.
3. **Feasibility Certification vs. Candidate Ranking:** Only candidates certified `FEASIBLE` are ranked. Infeasible or contaminated candidates can never win.
4. **Presentation Layer vs. Backend Core:** UI and CLI consume canonical schemas from `contracts/`. They never duplicate evaluator logic.
5. **Demo Data Labeling:** All offline mock data and synthetic fixtures must be persistently and unmistakably labeled **`DEMO DATA`**.

---

## 8. Related Documentation

- [System Architecture](architecture.md)
- [Execution Roadmap (October 19–30, 2026)](../ROADMAP.md)
- [MVP Scope & Acceptance Checklist](mvp-checklist.md)
- [Daily Integration & Verification Checklist](integration-checklist.md)
- [Architecture Decision Log](decision-log.md)
- [Decision Policy & Verdict Semantics](decision-policy.md)
- [Metrics Definitions & Aggregation Rules](metrics.md)
- [Demo Presentation Script & Runbook](demo-script.md)
