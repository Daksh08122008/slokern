# SLOKern Daily Integration & Verification Checklist

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Operational Guide  
> **Owner:** Rajdeep (Technical Lead / Architecture)  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

---

## 1. Daily Integration Ritual

To prevent "merge hell" and guarantee continuous system coherence, the 5-person team adheres to a structured daily integration ritual.

### 1.1 Morning Synchronization (10–15 minutes)
Every owner posts or speaks to three questions:
1. **Today's Single Deliverable:** What concrete artifact, PR, or test will move the critical path today?
2. **Blockers & Dependencies:** What external service, hardware access, or upstream contract could block it?
3. **Midday Fallback:** What is the contingency plan if that dependency is not unblocked by 1:00 PM?

### 1.2 Individual Build Block
Owners implement on isolated feature branches (`<owner>/<feature-name>`). Direct commits to `main` are prohibited.

### 1.3 Afternoon Integration Window (15–25 minutes)
- Review open PRs across workstreams.
- Run contract validation tests (`pytest tests/contract`).
- Merge verified small PRs into `main`.
- Run an end-to-end smoke test against the latest `main` branch.

### 1.4 End-of-Day Status Handoff (5–10 minutes)
Each owner posts the completed stand-up record into the team channel.

#### Stand-Up Record Template
```text
Date: YYYY-MM-DD
Owner: [Name]
Status: [ TODO | IN PROGRESS | BLOCKED | DONE ]

Today's Single Deliverable: [Exact file, PR, artifact, or test]
Evidence / Test Output: [Command run and passing result]
Blocker / Dependency: [Person, system, or decision blocking progress]
Fallback Plan Executed: [What was done if blocked]
Handoff To: [Named receiver and expected schema/format]
Risk to Critical Path: [None | Low | High - describe threat]
Tomorrow's Next Action: [Next milestone task]
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

- [ ] **Step 1: Serving Smoke Test (Aman):**
  - Run `slokern smoke-test` against live endpoint.
  - Verify model name, runtime version, and GPU fingerprint are returned.
  - Assert HTTP 200 response and valid non-empty token stream.
- [ ] **Step 2: Single-Run Measurement (Adriraj):**
  - Dispatch small workload (e.g., 20 requests at 2 req/s).
  - Verify `RawRequestMeasurement` records are written to JSONL with non-zero timestamps.
  - Verify `MetricSet` calculates TTFT, ITL, throughput, and error rate.
- [ ] **Step 3: Deterministic Evaluator (Daksh):**
  - Feed single-run `MetricSet` into `FeasibilityEvaluator`.
  - Assert that an exact threshold violation produces `INFEASIBLE` with the correct reason code.
  - Assert that insufficient samples produce `INCONCLUSIVE`.
- [ ] **Step 4: Baseline Establishment (Aman & Adriraj):**
  - Execute the default/reference serving configuration.
  - Archive baseline raw measurements, metric summary, and verdict.
- [ ] **Step 5: Bounded Search (Rohan):**
  - Execute `slokern optimize` across 3–5 legal candidates within budget.
  - Verify each candidate settings change is applied and verified by the adapter.
  - Verify search stops when budget is exhausted.
- [ ] **Step 6: Candidate Selection (Rohan & Daksh):**
  - Verify that only `FEASIBLE` candidates are ranked.
  - Verify candidate with best declared objective is selected with documented rationale.
- [ ] **Step 7: Independent Verification (Daksh & Aman):**
  - Automatically dispatch `slokern verify` for the winning candidate.
  - Confirm a NEW unique `run_id` is assigned.
  - Verify raw measurements are collected afresh.
  - Confirm final verdict is emitted (`VERIFIED` or `VERIFICATION_FAILED`).
- [ ] **Step 8: Dashboard & Report Integration (Rajdeep):**
  - Verify web UI renders the experiment run state, candidate comparison, and verification verdict.
  - Confirm exportable Markdown/JSON report compiles and saves to disk.
- [ ] **Step 9: Demo Hardening (Team):**
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
- [Team Ownership & Collaboration Model](ownership.md)
- [Architecture Decision Log](decision-log.md)
- [Demo Script & Fallback Plan](demo-script.md)

