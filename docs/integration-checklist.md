# SLOKern Daily Integration & Verification Checklist

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Operational Guide  
> **Owner:** Rajdeep (Single Technical Owner & Integration Authority)  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

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
Owner: Rajdeep
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
[1. Serving Smoke Test]
         ↓
[2. Valid Single-Run Measurements]
         ↓
[3. Deterministic Evaluator]
         ↓
[4. Baseline Establishment]
         ↓
[5. Bounded Candidate Search]
         ↓
[6. Feasible Candidate Selection]
         ↓
[7. Independent Verification]
         ↓
[8. Dashboard & Report Integration]
         ↓
[9. Demo Hardening & Rehearsal]
```

### Stage Checkpoints

- [ ] **Step 1: Serving Smoke Test (Rajdeep):**
  - Run `slokern smoke-test` against live endpoint.
  - Verify model name, runtime version, and GPU fingerprint are returned.
  - Assert HTTP 200 response and valid non-empty token stream.
- [ ] **Step 2: Single-Run Measurement (Rajdeep):**
  - Dispatch small workload (e.g., 20 requests at 2 req/s).
  - Verify `RawRequestMeasurement` records are written to JSONL with non-zero timestamps.
  - Verify `MetricSet` calculates TTFT, ITL, throughput, and error rate.
- [ ] **Step 3: Deterministic Evaluator (Rajdeep):**
  - Feed single-run `MetricSet` into `FeasibilityEvaluator`.
  - Assert that an exact threshold violation produces `INFEASIBLE` with the correct reason code.
  - Assert that insufficient samples produce `INCONCLUSIVE`.
- [ ] **Step 4: Baseline Establishment (Rajdeep):**
  - Execute the default/reference serving configuration.
  - Archive baseline raw measurements, metric summary, and verdict.
- [ ] **Step 5: Bounded Search (Rajdeep):**
  - Execute `slokern optimize` across 3–5 legal candidates within budget (fixed 2×2 matrix).
  - Verify each candidate settings change is applied and verified by the adapter.
  - Verify search stops when budget is exhausted.
- [ ] **Step 6: Candidate Selection (Rajdeep):**
  - Verify that only `FEASIBLE` candidates are ranked.
  - Verify candidate with best declared objective is selected with documented rationale.
- [ ] **Step 7: Independent Verification (Rajdeep):**
  - Automatically dispatch `slokern verify` for the winning candidate.
  - Confirm a NEW unique `run_id` is assigned.
  - Verify raw measurements are collected afresh.
  - Confirm final verdict is emitted (`VERIFIED` or `VERIFICATION_FAILED`).
- [ ] **Step 8: Dashboard & Report Integration (Rajdeep):**
  - Verify web UI renders the experiment run state, candidate comparison, and verification verdict.
  - Confirm exportable Markdown/JSON report compiles and saves to disk.
- [ ] **Step 9: Demo Hardening (Rajdeep):**
  - Run clean environment setup test.
  - Validate demo script timing (3–5 minutes).

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

