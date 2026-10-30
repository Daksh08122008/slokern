# SLOKern Daily Integration & Verification Checklist

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Operational Guide  
> **Sole Technical Owner & Integration Authority:** Rajdeep  
> **Execution Model:** Strict Solo Execution (Sole Owner: Rajdeep)  
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
Contributor: Rajdeep (Solo Execution)
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
[2. Valid Single-Run Measurements (Rajdeep) & Automated Integrity Audit]
         ↓
[3. Deterministic Evaluator (Rajdeep)]
         ↓
[4. Baseline Establishment (Rajdeep)]
         ↓
[5. Bounded Candidate Search (Rajdeep)]
         ↓
[6. Feasible Candidate Selection (Rajdeep)]
         ↓
[7. Independent Verification (Rajdeep) & Automated Decision Verification]
         ↓
[8. Dashboard & Report Integration (Rajdeep)]
         ↓
[9. Demo Hardening & Rehearsal (Rajdeep)]
```

### Stage Checkpoints

- [x] **Step 1: Serving Adapter & Preflight Infrastructure (Rajdeep):**
  - `FakeServingAdapter` implemented in `src/slokern/engine/serving/fake.py` generating deterministic synthetic runs labeled **`DEMO DATA`**.
  - `OllamaServingAdapter` implemented in `src/slokern/engine/serving/ollama.py` on loopback (`http://127.0.0.1:11434`) targeting model `qwen3:4b-instruct-2507-q4_K_M` over `/api/tags` and `/api/chat` with strict loopback security, redirect prohibition, URL userinfo rejection, and monotonic duration timing (DEC-0014).
  - `NebiusServingAdapter` implemented in `src/slokern/engine/serving/nebius.py` with OpenAI-compatible HTTP client and health probe; live endpoint verification pending credentials (`BLK-04`, `BLK-17`).
  - Adapter factory (`src/slokern/engine/serving/factory.py`) enforces strict three-tier precedence (`--adapter` > `SLOKERN_ADAPTER` > `"local"`) with zero silent fallback.
- [x] **Step 2: Single-Run Measurement & Load Generation (Rajdeep; automated integrity audit):**
  - Subprocess load generator `LoadGeneratorRunner` (`runner.py`) dispatches Poisson and constant arrivals.
  - `RawRequestMeasurement` records written to JSONL with client-side timestamps.
  - Metrics engine (`src/slokern/core/metrics/`) computes TTFT/ITL percentiles and throughput.
  - Automated benchmark trace schema validation and fixture conformance active in `tests/contract/test_fixtures_validate.py`.
- [x] **Step 3: Feasibility Evaluation & Hard SLOs (Rajdeep; automated decision verification):**
  - Evaluator enforces hard constraint thresholds, reason codes, and boundary conditions (NaN, negative latency guarded).
  - Automated verification of feasibility edge cases, inclusive boundaries, and missing metric handling in `tests/contract/test_verification_independence.py`.
- [x] **Step 4: Baseline Establishment (Rajdeep):**
  - Single-run executor (`SingleRunExecutor`) executes reference baseline run before candidate exploration.
  - Persists `RunRecord`, raw JSONL traces, and `FeasibilityResult` on disk.
- [x] **Step 5: Bounded Candidate Search & Budget Enforcement (Rajdeep):**
  - 2x2 grid search controller (`src/slokern/core/search/grid.py`) explores `max_num_batched_tokens` in {1024, 2048} × `max_num_seqs` in {16, 64}.
  - Capability preflight gating (`validate_search_capabilities()`): halts immediately on `local` and `nebius` citing `BLK-17` before allocating any benchmark runs. Offline campaign runs on `fake` labeled `DEMO DATA`.
  - Strict budget enforcement (`validate_budget` + `BudgetLimiter`) guarantees the 6-run campaign invariant (5 search + 1 verification).
- [x] **Step 6: Feasible Candidate Selection (Rajdeep):**
  - Strict ranker (`src/slokern/core/search/rank.py`) selects winning candidate by declared objective (Mode A cost or Mode B throughput/proxy).
  - Breaks ties deterministically by candidate ID; rejects missing objective values.
- [x] **Step 7: Independent Verification Rerun (Rajdeep; automated decision verification):**
  - Independent verification engine (`src/slokern/core/verification/protocol.py` and `compare.py`, resolving `BLK-08`) re-executes winning candidate under distinct `verification_run_id` (Run 6).
  - Recomputes metrics from fresh verification trace evidence.
  - Evaluates metric drift against explicit thresholds (+15% latency, -15% throughput, +0.01 error rate).
  - Emits canonical `VerificationRecord` with definitive verdict (`VERIFIED`, `VERIFICATION_FAILED`, or `VERIFICATION_INCONCLUSIVE`).
  - Automated contract tests asserting verification independence and distinct run IDs in `tests/contract/test_verification_independence.py` (17 passed).
- [x] **Step 8: Artifacts, CLI & Reporting (Rajdeep):**
  - Report generator (`report_builder.py`, resolving `BLK-09`) compiles immutable `ReportArtifact` and Markdown summary linking recommendation directly to raw trace paths.
  - Minimal CLI runner (`src/slokern/cli/main.py`) provides `smoke-test`, `optimize`, `verify`, `report`, `validate`, and `serve` commands.
  - Automated secret scanner asserts zero secrets or private API tokens in generated report output.
  - Frontend command center reflects backend state with persistent **`DEMO DATA`** labeling.
- [x] **Step 8b: Control Plane API & Frontend Vertical Slice Integration (Rajdeep):**
  - Minimal stdlib HTTP control plane & SSE streaming engine implemented in `src/slokern/api/` (`slokern serve`).
  - Endpoints: `GET /api/health`, `POST /api/smoke-test`, `POST /api/runs/single`, `GET /api/runs`, `GET /api/runs/<id>`, `GET /api/runs/<id>/trace`, `POST /api/runs/verify`, `GET /api/reports/<id>`.
  - Canonical TypeScript contract definitions in `frontend/src/types/contracts.ts` and typed API client in `frontend/src/api/client.ts`.
  - Frontend features: live preflight smoke probe on Runtime Profile with actionable serving readiness diagnostics, live benchmark dispatch with SSE progress streaming on Live Monitor, measured candidate card with physical JSONL provenance and BLK-17 capability gating notice on Tuning Lab, independent verification rerun with fresh run ID and drift analysis on Verification Lab, on-demand Markdown report generation and dossier download on Evidence & Reports, and browser download of unaggregated JSONL traces (`/api/runs/:id/trace`) with duplicate action guards.
  - Automated test coverage: 15 API unit tests (`tests/unit/api/`) and full end-to-end lifecycle integration test (`tests/integration/test_frontend_api_integration.py` with 12 lifecycle verification stages) passing 100%. Full repository test suite: 484 passed, 13 skipped in 25.85s. Frontend compiles with 0 TypeScript/JSX errors (`npm run build`).
- [x] **Step 9: Demo Hardening & UI Integration (Rajdeep):**
  - Full dual-runtime launch verified: Python API (`http://127.0.0.1:8000`) and React frontend (`http://127.0.0.1:5173`).
  - Real project evidence hydrated from filesystem: Live Nebius smoke test (`artifacts/smoke_test_result.json`) and 5-candidate offline optimization campaign (`artifacts/audit-offline-validation/experiments/exp-audit-offline-campaign/`).
  - Honest provenance badges rendered: `LIVE SMOKE TEST` (813.8 ms TTFT), `LIVE BASELINE NOT YET RECORDED`, `DEMO DATA · OFFLINE OPTIMIZATION` (winner `15594344d2bf`, 160 tok/s), and `INDEPENDENT VERIFICATION PENDING`.
  - 7 high-resolution screenshots (1920×1080) verified and persisted in `artifacts/screenshots/` (`01-overview-live.png` through `07-reports.png`).
  - Automated tests passing: 181 backend unit/contract/integration tests (`pytest`) and 13 frontend tests (`npm test`); Vite production build succeeded cleanly (`npm run build`).
  - Run clean environment setup test and offline synthetic walkthrough.
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

