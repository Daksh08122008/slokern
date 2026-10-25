# SLOKern Daily Integration & Verification Checklist

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Operational Guide  
> **Sole Technical Owner & Integration Authority:** Rajdeep  
> **Collaborator Workstreams:** Adriraj (Benchmark Integrity, active Oct 21), Daksh (Decision Verification, active Oct 24)  
> **Authority:** Aligned with [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [docs/ownership.md](ownership.md)

> **Guide status:** This is an acceptance checklist, not proof that its CLI commands or live controls currently exist. `slokern smoke-test/optimize/verify`, provider preflight artifacts, vLLM flag application/read-back, and independent verification must be treated as planned until implemented and executed. Current gaps are tracked in TASK-09–TASK-11 and BLK-04/08/15/16/17.

---

## 1. Single-Owner Daily Engineering Ritual

To maintain continuous system coherence and rigorous validation, Rajdeep adheres to a structured daily engineering and integration workflow:

### 1.1 Daily Objective & Dependency Check
At the start of each development block:
1. **Single High-Value Deliverable:** What concrete artifact, module, or test suite will advance the critical path today?
2. **Blockers & External Dependencies:** Are cloud instance availability, credentials, or API tokens verified?
3. **Contingency Plan:** What is the fallback if an external dependency or runtime access stalls?

### 1.2 Implementation & Verification Block
- Implement on clean, focused topic branches (`feat/<milestone-name>`).
- Enforce contract adherence against `src/slokern/contracts/`.
- Run contract validation tests (`pytest tests/contract` or test runners).
- Run targeted unit tests on changed components before merging to `main`.

### 1.3 End-of-Day Evidence & Progress Audit
Log progress, test output, and remaining risks in the project records:

#### Daily Progress Log Template
```text
Date: YYYY-MM-DD
Contributor: [ Rajdeep | Adriraj | Daksh ]
Phase: [ Phase A | Phase B | Phase C | Phase D | Phase E | Phase F ]
Status: [ TODO | IN PROGRESS | BLOCKED | DONE ]

Deliverable: [Exact file, PR, artifact, or test suite]
Evidence / Test Output: [Command executed and actual result]
Blocker / Dependency: [External system or environment blocker]
Contingency / Fallback Executed: [What was done if blocked]
Artifacts Produced: [Generated JSON/JSONL, reports, or test summaries]
Remaining Risks: [Critical path or demo risks]
Next Action: [Next milestone deliverable]
```

---

## 2. Contract Testing & Schema Verification Protocol

Every change that affects data models or API routes must pass the contract test suite before merging.

### Automated Contract Checks

1. **Schema Roundtrip Testing (`tests/contract/test_schema_roundtrip.py`):**
   - Validates that sample JSON payloads serialize and deserialize cleanly through Pydantic v2 models without data loss or coercion errors.
2. **Fixture Provenance & Conformance (`tests/contract/test_fixtures_validate.py`):**
   - Asserts that all workload fixtures (`fixtures/workloads/`) and golden metric fixtures (`fixtures/metrics_golden/`) conform to `WorkloadSpec` and `MetricSet` schemas and declare valid provenance metadata.
3. **Generated Type Synchronization (`tests/contract/test_generated_files_current.py`):**
   - Ensures exported JSON Schemas in `schemas/` and TypeScript type definitions in `frontend/src/generated/` are up to date with `src/slokern/contracts/`.
4. **Verification Independence Audit (`tests/contract/test_verification_independence.py`):**
   - Enforces that `VerificationRecord` always references a distinct `verification_run_id` that is mathematically and structurally distinct from `original_run_id`.

---

## 3. Critical Path Step-by-Step Verification

Work progresses in strict dependency order. Never proceed to downstream stages if upstream gates have not been verified.

```text
[1. Serving Smoke Test (Rajdeep)]
         ↓
[2. Valid Single-Run Measurements (Rajdeep) & Integrity Audit (Adriraj, Oct 21)]
         ↓
[3. Deterministic Evaluator (Rajdeep)]
         ↓
[4. Baseline Establishment (Rajdeep)]
         ↓
[5. Bounded Candidate Search (Rajdeep)]
         ↓
[6. Feasible Candidate Selection (Rajdeep)]
         ↓
[7. Independent Verification (Rajdeep) & Decision Audit (Daksh, Oct 24)]
         ↓
[8. Dashboard & Report Integration (Rajdeep)]
         ↓
[9. Demo Hardening & Rehearsal (Rajdeep)]
```

### Stage Checkpoints

- [x] **Step 1: Serving Adapter & Preflight Infrastructure (Rajdeep):**
  - `FakeServingAdapter` implemented in `src/slokern/engine/serving/fake.py` generating deterministic synthetic runs labeled **`DEMO DATA`**.
  - `NebiusServingAdapter` implemented in `src/slokern/engine/serving/nebius.py` with OpenAI-compatible HTTP client and health probe; live endpoint verification pending credentials (`BLK-04`, `BLK-17`).
- [x] **Step 2: Single-Run Measurement & Load Generation (Rajdeep; Adriraj audit from Oct 21):**
  - Subprocess load generator `LoadGeneratorRunner` (`runner.py`) dispatches Poisson and constant arrivals.
  - `RawRequestMeasurement` records written to JSONL with client-side timestamps.
  - Metrics engine (`src/slokern/core/metrics/`) computes TTFT/ITL percentiles, throughput, error rate, and offered vs achieved load.
  - Client dispatch skew and generator saturation detected (`generator_saturated = True`).
- [x] **Step 3: Deterministic Evaluator (Rajdeep):**
  - Implemented in `src/slokern/core/evaluator/evaluate.py`.
  - Inclusive boundary checks, NaN misclassification guard, and negative latency guards active.
  - Emits `FeasibilityResult` with structured reason codes.
- [x] **Step 4: Single-Run Executor & Baseline Pipeline (Rajdeep):**
  - Implemented in `src/slokern/engine/runner/run_executor.py` (`SingleRunExecutor`).
  - Wires together serving adapter, load generator, metrics engine, and feasibility evaluator.
  - Persists JSON metadata and unaggregated JSONL recordings.
- [x] **Step 5: Bounded 2×2 Search Controller (Rajdeep):**
  - Implemented in `src/slokern/core/search/grid.py` (`GridSearchController`), `space.py`, and `budget.py`.
  - Evaluates 2×2 discrete search grid under `BudgetLimiter` (default 5 search runs, 1 verification reserve; caveat `BLK-15`).
- [x] **Step 6: Deterministic Candidate Selection (Rajdeep):**
  - Implemented in `src/slokern/core/search/rank.py` (`CandidateRanker`).
  - Filters strictly on `FEASIBLE` candidates with deterministic candidate-ID tie-breaking.
- [ ] **Step 7: Independent Verification (Rajdeep) & Decision Verification Audit (Daksh, from Oct 24):**
  - Pydantic contract `VerificationRecord` locked and round-trip tested.
  - Verification runner in `src/slokern/core/verification/` ready for Phase C implementation (`TASK-11`).
  - Confirms unique `verification_run_id`, re-evaluates candidate, and computes metric drift ($\Delta M$).
  - Daksh audits decision correctness and verification independence.
- [ ] **Step 8: Dashboard & Report Integration (Rajdeep):**
  - Standalone React + Vite command center delivered in PR #2 (`frontend/src/App.tsx`, 2553 lines, `DESIGN.md`, labeled **`DEMO DATA`**).
  - Report artifact generator (`src/slokern/engine/reporting/report_builder.py`) pending implementation.
- [ ] **Step 9: Demo Hardening & Rehearsal (Rajdeep):**
  - Run clean environment setup test.
  - Validate demo script timing ($\le 3$ minutes).


---

## 4. Evidence Integrity & Pre-Submission Audit

Before preparing the final hackathon submission package, execute the following audit checklist:

### 4.1 Truth in Evidence Audit
- [ ] **No Fabricated Data:** Every number in the results table, report, or presentation slides corresponds to a real raw JSONL file in `artifacts/`.
- [ ] **Explicit Demo Labels:** All synthetic fixtures and offline frontend states are prominently labelled **DEMO DATA**; none are described as live benchmark results.
- [ ] **No Unsupported Claims:** No claim of "global optimality," "universal platform support," or "X% cost savings" without disclosed assumptions.
- [ ] **Cost Disclosure:** If monetary pricing was unverified, cost is explicitly marked **`unavailable`** and the non-monetary proxy (e.g., throughput under SLO or GPU-seconds/request) is clearly explained.

### 4.2 Security & Operational Safety Audit
- [ ] **Zero Secrets Committed:** Run `git grep -i -E "api_key|token|secret|password|bearer"` across repository to ensure no credentials or private tokens are stored.
- [ ] **Private IP Redaction:** Verify endpoint URLs and internal cluster hostnames are redacted in published reports and screenshots.
- [ ] **Resource Cleanup:** Verify all temporary serving instances and test workers are safely terminated.

### 4.3 Submission Package Readiness (Target: Oct 30)
- [ ] Hackathon eligibility, platform rules, and submission deadline reconfirmed.
- [ ] Architecture diagram and 3–5 minute demo video/script finalized.
- [ ] Submission archive created and verified from a fresh directory clone.
- [ ] Confirmation receipt archived.

---

## 5. Related Documentation

- [System Architecture](architecture.md)
- [MVP Scope & Acceptance Checklist](mvp-checklist.md)
- [Engineering Ownership & Execution Model](ownership.md)
- [Architecture Decision Log](decision-log.md)
- [Demo Script & Fallback Plan](demo-script.md)

