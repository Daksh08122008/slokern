# SLOKern Implementation Status & MVP Scope Freeze

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Document Type:** October 19 Audit & Scope Freeze Deliverable (Reconciled Day 5 Audit & Offline Campaign Verification)
> **Audit Date:** 2026-10-26 13:15:00 UTC (Sprint Day 5 Implementation Audit & Repair)
> **Audit Baseline Git Commit:** `ba3199b` on branch `main`
> **Working Tree State:** `CLEAN / AUDITED & REPAIRED`
> **Integration Branch:** `main`
> **Authority & Sole Technical Owner:** Rajdeep  
> **Execution Model:** Strict Solo Execution (Sole Owner: Rajdeep)  
> **Hackathon Submission Deadline:** October 30, 2026, 10:00 AM PDT (10:30 PM IST / 17:00 UTC)  
> **Remaining Sprint Time:** 3 days, 21 hours, 45 minutes (~93.75 hours)


---

## 1. Audit Baseline & Verification Logs

### 1.1 Environment Snapshot
- **Host OS:** Windows 11 Enterprise (Version: `10.0.26300.0`, Win32NT)
- **Python Version:** `Python 3.11.9`
- **Package Manager:** `pip 24.0`
- **Pydantic Runtime Version:** `2.14.1` (Pydantic v2 core `2.50.1`)
- **Pytest Version:** `9.1.1`
- **Isolated Snapshot Directory:** `$TEMP/slokern-audit/src` (extracted via `git archive HEAD`)

### 1.2 Baseline Command Execution Log (`R-xx`)

| ID | Command Executed | Proves | Exit Code | Result Summary |
|---|---|---|---|---|
| **R-01** | `git status --short --branch --untracked-files=all` | Git repository and working tree hygiene | 0 | `## repository-audit-and-mvp-scope-freeze`, ` M README.md` (uncommitted badge modification). Working tree labeled **`NOT CLEAN-BASELINE`**. |
| **R-02** | `git archive HEAD -o archive.tar && tar -xf archive.tar -C $TEMP/slokern-audit/src` | Snapshot file extraction and source isolation | 0 | Codebase snapshot isolated from working directory into clean directory. |
| **R-03** | `python -m venv $TEMP/slokern-audit/venv` | Python 3.11 isolated runtime environment creation | 0 | Python 3.11.9 and pip 24.0 venv initialized. |
| **R-04** | `pip install -e ".[dev]"` (offline snapshot venv) | Packaging installation and dependency resolver | 1 | Failed due to setuptools PEP 517 build-isolation network requirement in offline environment. |
| **R-05** | `pip install --no-build-isolation --no-deps -e $TEMP/slokern-audit/src` | Setuptools packaging and editable metadata generation | 1 | `error: invalid command 'bdist_wheel'`. Proves build tooling gap: `wheel` not installed in baseline environment. |
| **R-06** | `Set-Content __editable__.slokern-0.1.0.pth $TEMP/slokern-audit/src/src && python -c "import slokern"` | Package importability from snapshot source | 0 | `slokern` successfully imported from snapshot directory `C:\Users\paulr\AppData\Local\Temp\slokern-audit\src\src\slokern\__init__.py`. |
| **R-07** | `pip check` | Dependency graph consistency | 0 | `No broken requirements found.` |
| **R-08** | `python -m compileall -q src tests` | Syntax and bytecode compilation | 0 | 0 syntax errors across all 90 source modules and 67 test files. |
| **R-09** | `python -c "import pkgutil, importlib, slokern; ..."` & AST import inspection | Undeclared dependency probe | 0 | All 90 modules imported without error. Top-level imports across `src/`: `dataclasses`, `enum`, `hashlib`, `json`, `pydantic`, `slokern`, `typing`. Zero undeclared third-party dependencies. |
| **R-10** | `pytest -v -m "not live"` (Run 1, provider credentials unset) | Unit test suite behavior and marker isolation | 0 | 24 passed, 1 deselected, 0 failed in 0.56s. |
| **R-11** | `pytest -v -m "not live"` (Run 2, provider credentials unset) | Test determinism and flakiness audit | 0 | 24 passed, 1 deselected, 0 failed in 0.51s. Zero flaky tests. |
| **R-12** | `pytest --collect-only -q -m live` | Live test marker enforcement | 0 | 1 test collected (`tests/live/test_smoke_live.py::test_smoke_live_endpoint`), 24 deselected. Marker correctly registered and enforced. |

---

### 1.3 Behavioral Probes Log (`P-xx`)

| ID | Probe Target | Input | Observed Output | Verdict / Finding |
|---|---|---|---|---|
| **P-01** | Evaluator boundary: exact threshold | `ttft_ms.p95 = 200.0`, threshold `200.0`, op `<=` | `overall_verdict=FEASIBLE`, `passed=True`, `reason=HARD_CONSTRAINTS_PASSED` | Inclusive threshold evaluation passes. |
| **P-02** | Evaluator boundary: above threshold | `ttft_ms.p95 = 200.0001`, threshold `200.0`, op `<=` | `overall_verdict=INFEASIBLE`, `passed=False`, `reason=TTFT_P95_EXCEEDED` | Epsilon threshold breach triggers infeasibility. |
| **P-03** | Evaluator boundary: below threshold | `ttft_ms.p95 = 199.9999`, threshold `200.0`, op `<=` | `overall_verdict=FEASIBLE`, `passed=True`, `reason=HARD_CONSTRAINTS_PASSED` | Sub-threshold measurement passes. |
| **P-04** | Evaluator: missing metric value | `ttft_ms.p95 = None` | `overall_verdict=INCONCLUSIVE`, `passed=None`, `reason=MISSING_REQUIRED_METRIC` | Invariant verified: missing metric yields INCONCLUSIVE, never FEASIBLE. |
| **P-05** | Evaluator: NaN metric value | `ttft_ms.p95 = float('nan')` | `overall_verdict=INFEASIBLE`, `passed=False`, `reason=TTFT_P95_EXCEEDED` | **DEFECT (BLK-05):** Python `nan <= 200.0` evaluates to `False`, causing NaN to be misclassified as a threshold failure (`INFEASIBLE`) instead of corrupted evidence (`INCONCLUSIVE`). |
| **P-06** | Evaluator: negative metric value | `ttft_ms.p95 = -10.0 <= 200.0` | `overall_verdict=FEASIBLE`, `passed=True`, `reason=HARD_CONSTRAINTS_PASSED` | **DEFECT (BLK-06):** Impossible negative latency passes without physical boundary validation. |
| **P-07** | Evaluator: generator saturated | `generator_saturated = True` | `overall_verdict=INCONCLUSIVE`, `validity_status=CONTAMINATED`, `reason=GENERATOR_SATURATED` | Saturated client load generator invalidates run. |
| **P-08** | Evaluator: insufficient samples | `sample_count = 10 < min_sample_count = 30` | `overall_verdict=INCONCLUSIVE`, `reason=INSUFFICIENT_SAMPLES` | Sample starvation yields INCONCLUSIVE. |
| **P-09** | Evaluator: all distributions missing | `ttft_ms = {}`, `itl_ms = {}`, `e2e_latency_ms = {}` | `overall_verdict=INCONCLUSIVE`, `reason=MISSING_REQUIRED_METRIC` | Complete absence of metrics handled safely. |
| **P-10** | Evaluator: missing metric vs failing metric | Constraint 1 `itl=None`, Constraint 2 `ttft=250` (fails) | `overall_verdict=INCONCLUSIVE`, reasons `[MISSING_REQUIRED_METRIC, TTFT_P95_EXCEEDED]` | `INCONCLUSIVE` takes precedence over `INFEASIBLE`. |
| **P-11** | Candidate ID: dictionary key order | `{"max_num_seqs": 16, "gpu_mem": 0.9}` vs reversed | Hash: `c2264f035deb` for both | `json.dumps(sort_keys=True)` guarantees key order invariance. |
| **P-12** | Candidate ID: float vs integer formatting | `{"tensor_parallel_size": 1}` vs `{"tensor_parallel_size": 1.0}` | Hashes differ: `4fe93deaf8d0` vs `cd0ce0cb5b73` | **EDGE CASE (BLK-11):** Candidate ID changes if numbers are coerced between int and float. |
| **P-13** | Ranking: non-feasible filtering | Pool with FEASIBLE, INFEASIBLE, INCONCLUSIVE | Output contains only candidates with `verdict == FEASIBLE` | Invariant verified: non-feasible candidates never enter eligible rankings. |
| **P-14** | Ranking: deterministic tie-breaking | Candidates tied at metric `0.02` | `cand-A` ranked before `cand-C` | Explicit deterministic tie-breaking by candidate ID verified. |
| **P-15** | Ranking: sort stability across shuffles | Input candidate pool shuffled 20 times | Exact identical ranking order across all 20 iterations | Sorting determinism verified. |
| **P-16** | Ranking: None metric handling | Candidates with throughput `100.0`, `50.0`, `None` | Output order: `100.0`, `50.0`, `None` | None metric sorted to tail (+inf key) under maximization. |
| **P-17** | Contracts: Pydantic v2 validation | All 11 models probed via `model_json_schema()` | All 11 subclass `pydantic.BaseModel`; zero v1 APIs found | Pydantic v2 architecture verified. |
| **P-18** | Contracts: round-trip serialization | `model_validate_json(m.model_dump_json()) == m` | All 11 models match exactly (`round-trip match=True`) | Lossless serialization verified. |
| **P-19** | Contracts: extra field policy | Model instantiation with unrecognized fields | Field accepted without validation error (`extra='ignore'`) | **GAP (BLK-12):** Models lack `ConfigDict(extra='forbid')`. |
| **P-20** | Frontend: buildability and mock data | Inspection of `frontend/package.json` and `src/` | Empty `package.json`, 2-line placeholder comments in all files | Frontend is **ABSENT**; no mock data exists. |

---

## 2. Subsystem Summary Table

> **Reconciled Status (2026-10-26 audit):** Current audit collected 469 tests. The full repository test suite achieved **456 passed, 13 skipped in 21.78s** (0 failures). Breakdown: contract test suite passed **141/141 tests** 100% (`tests/contract/`), core evaluator, search, metrics, and verification engines passed **137/137 tests** (`tests/unit/core/`), serving, loadgen, runner, and reporting engines passed **136 passed, 12 skipped in 13.02s** (`tests/unit/engine/`), CLI passed **27/27 tests** (`tests/unit/cli/`), and integration tests passed **15/15 tests** (`tests/integration/`). 12 tests skip due to Windows Codex sandbox loopback socket constraints (`[WinError 10013]`), and 1 live test skips because `NEBIUS_API_KEY` is unset (`BLK-04` offline limitation; offline simulation uses `FakeServingAdapter` labeled **`DEMO DATA`**). SUB-09 (Verification Engine / `compare.py`) and SUB-10 (Report Generator / `report_builder.py`) are fully implemented, verified via end-to-end offline campaign execution (`exp-audit-offline-campaign`) across 5 search runs + 1 independent verification run, and integrated into `GridSearchController` campaign orchestration (`auto_verify` / `run_full_campaign` / `slokern optimize --verify`).

| ID | Subsystem | Implementation | Verification | Flags | Owner | Blocked-by |
|---|---|---|---|---|---|---|
| **SUB-01** | Architecture & Scope Governance | `IMPLEMENTED` | `STATIC` | `NONE` | Rajdeep (CONFIRMED) | None |
| **SUB-02** | Shared Contracts & Schema Registry | `IMPLEMENTED` | `UNIT` | `NONE` | Rajdeep (CONFIRMED) | None |
| **SUB-03** | Feasibility Evaluator Core | `IMPLEMENTED` | `UNIT` | `NONE` | Rajdeep (CONFIRMED) | None |
| **SUB-04** | Candidate Identity, Search Space & Ranking | `IMPLEMENTED (GridSearchController + 2×2 Space + BudgetLimiter + Ranker)` | `UNIT` | `NONE` | Rajdeep (CONFIRMED) | None |
| **SUB-05** | Serving Adapter & Runtime Infrastructure | `IMPLEMENTED (Fake + Nebius urllib transport + SSE)` | `UNIT; LIVE NOT RUN` | `OFFLINE FALLBACK` | Rajdeep (CONFIRMED) | BLK-04, BLK-17 |
| **SUB-06** | Subprocess Load Generator & Workload Fixtures | `IMPLEMENTED (Loadgen Runner & JSONL Tracing)` | `UNIT` | `SANDBOX IPC CONSTRAINT` | Rajdeep (CONFIRMED) | None |
| **SUB-07** | Metrics Engine Core | `IMPLEMENTED (Metrics Engine Core)` | `UNIT` | `NONE` | Rajdeep (CONFIRMED) | None |
| **SUB-08** | Experiment Orchestration & Run Lifecycle | `IMPLEMENTED (SingleRunExecutor & 2×2 Grid Search)` | `UNIT` | `SYNTHETIC VERIFIED (DEMO DATA)` | Rajdeep (CONFIRMED) | None |
| **SUB-09** | Independent Verification Engine | `IMPLEMENTED & VERIFIED (Verification Protocol + DriftPolicy + Campaign Rerun)` | `UNIT, CONTRACT & CAMPAIGN (22 verification + 17 contract tests pass)` | `VERIFIED OFFLINE` | Rajdeep (CONFIRMED) | None |
| **SUB-10** | Report Artifact Generator | `IMPLEMENTED (ReportBuilder & Markdown Exporter)` | `UNIT & CAMPAIGN VERIFIED` | `NONE` | Rajdeep (CONFIRMED) | None |
| **SUB-11** | Control Plane API & CLI | `MINIMAL CLI / DEFERRED API` | `UNIT` | `DEFERRED API` | Rajdeep (INTERIM) | None |
| **SUB-12** | Frontend Command Center & Presentation | `IMPLEMENTED (Frontend Command Center) / API DEFERRED` | `MANUAL / DEV BUILD (DEMO DATA)` | `NONE` | Rajdeep (INTERIM) | None |
| **SUB-13** | CI/CD, Packaging & Test Automation | `PARTIAL` | `UNIT` | `BLOCKED(by=BLK-13)` | Rajdeep (CONFIRMED) | BLK-13 |


---

## 3. Subsystem Detail Blocks

### SUB-01: Architecture & Scope Governance
- **Intended Behavior:** Single-owner technical authority governing modular monolith architecture, strict 6-run budget, deterministic decision policies, and hackathon compliance rules.
- **Actual Behavior:** Modular monolith design documented in `docs/architecture.md:L1-430@356c489` and `docs/decision-policy.md:L1-141@356c489`. Governance is active, but documentation contained completion claims that contradicted repository reality.
- **Evidence:** `docs/architecture.md:L1-430@356c489`, `docs/decision-policy.md:L1-141@356c489`, `docs/ownership.md:L1-188@356c489`.
- **Dependencies:** None.
- **Risks:** High concentration of ownership under Rajdeep (P1 concentration risk BLK-07).
- **Next Testable Step:** Ratify the MVP Scope Freeze and resolve DEC-01 through DEC-05. Acceptance: `docs/implementation-status.md` accepted as sole status source of truth.

### SUB-02: Shared Contracts & Schema Registry
- **Intended Behavior:** 11 canonical Pydantic v2 models representing the entire optimization lifecycle, exporting committed JSON schemas and enforcing strict boundary validation.
- **Actual Behavior:** All 11 models are defined and exported in `src/slokern/contracts/`. All round-trip serialize perfectly (P-18). However, only 4 contracts are consumed outside contracts (`SLOSpec`, `CandidateConfig`, `MetricSet`, `FeasibilityResult`). Schemas directory contains only `.gitkeep`; `scripts/gen_contracts.py` is a stub (BLK-10); models lack `extra='forbid'` (BLK-12).
- **Evidence:** `src/slokern/contracts/__init__.py:L1-36@356c489`, `tests/contract/test_schemas.py:L1-114@356c489` (observed in R-10, R-11), `probe_b_contracts_roundtrip.py` (P-18).
- **Dependencies:** None.
- **Risks:** Drift between contracts and external tooling due to missing emitted JSON schemas.
- **Next Testable Step:** Update `scripts/gen_contracts.py` to write JSON schemas into a temporary directory and verify with `pytest tests/contract/test_generated_files_current.py`.

### SUB-03: Feasibility Evaluator Core
- **Intended Behavior:** Pure deterministic Python evaluation of a `MetricSet` against `SLOSpec`, producing an auditable `FeasibilityResult` with machine-readable `ReasonCode`.
- **Actual Behavior:** Implemented in `src/slokern/core/evaluator/evaluate.py:evaluate_slo@356c489`. Evaluates hard constraints, generator saturation, and sample size. Tested across 7 unit tests. However, NaN floating-point values are misclassified as `INFEASIBLE` with `TTFT_P95_EXCEEDED` (P-05 / BLK-05), and negative latencies are accepted as `FEASIBLE` (P-06 / BLK-06).
- **Evidence:** `src/slokern/core/evaluator/evaluate.py:L66-130@356c489`, `tests/unit/core/test_evaluator.py:L1-133@356c489` (R-10, R-11), probes P-01 through P-10.
- **Dependencies:** `SUB-02` (Contracts).
- **Risks:** Invalid or corrupted measurements generating incorrect feasibility verdicts.
- **Next Testable Step:** Add `math.isnan(obs_val)` check and non-negative boundary assertions in `evaluate.py`. Acceptance: Probe P-05 returns `INCONCLUSIVE` and unit test passes.

### SUB-04: Candidate Identity & Deterministic Ranking
- **Intended Behavior:** Stable deterministic candidate ID generation from canonical configurations; deterministic ranking of feasible candidates under declared objective with candidate-ID tie-breaking; 2×2 bounded search space generation.
- **Actual Behavior:** **IMPLEMENTED & AUDITED.** The 2×2 space, canonical candidate hashing (`candidate_id.py`), and default 5-search-run budget are operational. Day 5 audit remediation resolved `BLK-15` (preflight `validate_budget` in `src/slokern/core/search/grid.py` strictly enforcing `max_total_runs <= 6`, `max_search_runs == 5`, `reserved_verification_runs == 1`) and `BLK-16` (strict `rank.py` finite check rejecting unmeasured/missing metrics and deterministic candidate-ID tie-breaking). Tested with 15 unit tests in `tests/unit/core/search/` and 11 unit tests in `tests/unit/core/test_ranker*.py` (26 tests total).
- **Evidence:** `tests/unit/core/search/` (15 passed), `tests/unit/core/test_ranker.py` and `test_ranker_validation.py` (11 passed). See `BLK-15` and `BLK-16` (both RESOLVED).
- **Dependencies:** `SUB-02` (Contracts), `SUB-03` (Evaluator).
- **Risks:** Closed. Preflight budget validation and strict ranking validation prevent budget relaxation or unmeasured winners.
- **Next Testable Step:** Feed ranked winner into Independent Verification Engine (`TASK-11`). Acceptance: `VerificationRunner` reruns winning candidate under a fresh run ID.

### SUB-05: Serving Adapter & Runtime Infrastructure
- **Intended Behavior:** Interface for serving runtimes (capabilities, apply, environment fingerprint, health); fake adapter for offline testing; Nebius Cloud adapter for live serving.
- **Actual Behavior:** `FakeServingAdapter` supports offline synthetic runs labeled **`DEMO DATA`**. `NebiusServingAdapter` uses stdlib urllib for OpenAI-compatible completions and sanitizes handled API-key/Bearer-token errors. Its local `apply_config()` does not transmit or read back `max_num_seqs` or `max_num_batched_tokens`; the live smoke test skipped because credentials were absent. Secret handling was checked in mocked unit paths; live behavior is unverified.
- **Evidence:** Current requested deterministic subset: 322 passed; `tests/live/test_smoke_live.py`: 1 skipped. See `BLK-04` and `BLK-17`.
- **Dependencies:** DEC-01, BLK-04.
- **Risks:** Endpoint reachability, engine-control application/read-back, model identity, and live inference remain unverified; standard API requests alone do not establish GPU serving optimization.
- **Next Testable Step:** Resolve the endpoint control interface/architecture decision, then run a credentialed preflight and verify effective engine settings.

### SUB-06: Subprocess Load Generator & Workload Fixtures
- **Intended Behavior:** Subprocess-isolated load generator generating Poisson/constant request schedules, recording unaggregated request-level timing observations to JSONL (`RawRequestMeasurement`), and detecting client saturation (`generator_saturated = True`).
- **Actual Behavior:** **IMPLEMENTED, with measurement limitations.** Modules in `src/slokern/engine/loadgen/` (`arrival.py`, `recorder.py`, `runner.py`) dispatch requests in an isolated subprocess when configured, generate constant and Poisson arrivals, write JSONL records, and flag saturation when mean dispatch lag >10 ms or offered load <90% of target. Timestamps use floating-point epoch seconds from `time.time()`; this does not prove microsecond clock accuracy. Prompt token count is estimated from whitespace, not measured with a pinned tokenizer. Note: under the Windows Codex sandbox environment (`BLK-18`), inter-process loopback sockets/queues stall, so unit tests (`test_arrival.py`, `test_recorder.py`) pass 100% (38 passing unit tests) while multi-process integration tests require unconstrained/Linux environments.
- **Evidence:** `src/slokern/engine/loadgen/`: 38 unit tests passing (`.venv/bin/pytest tests/unit/engine/loadgen/ -v`); 100-request subprocess acceptance case verified; independent victory audit passed cleanly.
- **Dependencies:** `SUB-02` (Contracts), `SUB-05` (Serving Adapter).
- **Risks:** Windows multiprocessing spawn overhead requires proper guard protection; verified under isolated runner tests.
- **Next Testable Step:** Wire load generator runner into `SingleRunExecutor` (`TASK-08`). Acceptance: `SingleRunExecutor` executes a full run using the load generator.

### SUB-07: Metrics Engine Core
- **Intended Behavior:** Pure, deterministic derivation of `MetricSet` from raw `.jsonl` request recordings, computing TTFT/ITL percentiles (p50, p95, p99), throughput, error rate, and offered vs achieved load.
- **Actual Behavior:** **IMPLEMENTED.** Fully functional modules in `src/slokern/core/metrics/` (`percentiles.py`, `latency.py`, `throughput.py`, `validity.py`, `aggregate.py`). Computes linear-interpolated percentiles, steady-state latency filtering (warmup exclusion), request/token throughputs, offered/achieved loads, and client saturation detection (`generator_saturated = True` on lag > 10ms or load < 90% target). Verified against hand-calculated golden fixtures (`fixtures/metrics_golden/`).
- **Evidence:** `src/slokern/core/metrics/`: 42 unit tests passing in `tests/unit/core/metrics/` (`.venv/bin/pytest tests/unit/core/metrics/ -v`); bytecode compilation passes cleanly (`python3 -m py_compile src/slokern/core/metrics/*.py`).
- **Dependencies:** `SUB-02` (Contracts), `SUB-06` (Raw Request Measurements).
- **Risks:** Unit tests prove mathematical correctness on synthetic/golden traces; physical evidence on live Nebius GPU serving (`SUB-05`) remains pending integration in `TASK-08` / `TASK-09`.
- **Next Testable Step:** Integrate `calculate_metrics` into `SingleRunExecutor` (`TASK-08`) to process end-to-end runs. Acceptance: `tests/unit/engine/runner/test_run_executor.py` passes.

### SUB-08: Experiment Orchestration & Run Lifecycle
- **Intended Behavior:** Modular monolith experiment controller managing the 6-run search budget (1 baseline + 4 grid candidates + 1 verification run), lifecycle states (`ExecutionStatus`), cancellation, and artifact persistence.
- **Actual Behavior:** **IMPLEMENTED (SingleRunExecutor & GridSearchController).** `SingleRunExecutor` (`src/slokern/engine/runner/run_executor.py`), `RunLifecycle`, and `CancellationToken` provide the single-run execution path, wiring together serving adapter, load generator, metrics engine, and feasibility evaluator, and writing JSON and JSONL artifacts to disk. The 2×2 grid search controller (`src/slokern/core/search/grid.py`) coordinates search iterations under `validate_budget` + `BudgetLimiter`, strictly enforcing the 5 search runs + 1 verification run invariant (`BLK-15` resolved).
- **Evidence:** `src/slokern/engine/runner/run_executor.py`, `src/slokern/core/search/grid.py`, `tests/unit/engine/runner/test_cancel.py`, `tests/unit/engine/runner/test_lifecycle.py`, `tests/unit/core/search/test_grid.py`. Current audit: 322 deterministic tests passed.
- **Dependencies:** `SUB-04` (Search), `SUB-05` (Serving), `SUB-06` (Loadgen), `SUB-07` (Metrics).
- **Risks:** Offline simulation uses `FakeServingAdapter` and must be clearly labeled **`DEMO DATA`**; live Nebius execution remains credential-blocked (`BLK-04`, `BLK-17`).
- **Next Testable Step:** Connect winning search candidate to `VerificationRunner` (`TASK-11`).

### SUB-09: Independent Verification Engine
- **Intended Behavior:** Takes the winning feasible candidate, triggers a fresh independent rerun under a new `verification_run_id`, computes metric drift ($\Delta M$), and renders a deterministic verification verdict (`VERIFIED` or `VERIFICATION_FAILED`).
- **Actual Behavior:** **IMPLEMENTED & VERIFIED.** Pydantic contract models `VerificationRecord` and `DriftAnalysis` extended with structured `MetricDriftComparison` and machine-readable `ReasonCode` taxonomy. `DriftPolicy` enforces strict boundary conditions (+15% latency, -15% throughput, +0.01 error rate). `verify_search_campaign()` validates search winners, executes Run 6 under a distinct `verification_run_id`, writes unaggregated raw JSONL traces, recalculates metrics, and persists `verification_record.json`. 22 unit tests in `tests/unit/core/verification/` and 17 contract tests in `tests/contract/test_verification_independence.py` pass 100%. End-to-end campaign rerun demonstrated on `exp-audit-offline-campaign`.
- **Evidence:** `src/slokern/contracts/verification.py`, `src/slokern/core/verification/compare.py`, `src/slokern/core/verification/protocol.py`, `tests/unit/core/verification/test_drift_boundary.py`, `tests/unit/core/verification/test_verification_campaign.py`, `artifacts/experiments/exp-audit-offline-campaign/verification_record.json`.
- **Dependencies:** `SUB-08` (Experiment Orchestration), `SUB-03` (Evaluator).
- **Risks:** None remaining for offline verification. Live Nebius cloud verification gated by BLK-04/BLK-17.
- **Status:** **RESOLVED (BLK-08 CLOSED).** Verified by automated unit, boundary, contract, and campaign rerun execution.

### SUB-10: Report Artifact Generator
- **Intended Behavior:** Generates a self-contained, immutable Markdown and JSON `ReportArtifact` linking headline numbers directly to raw measurement traces, environment fingerprints, cost disclosure, and verification records.
- **Actual Behavior:** **IMPLEMENTED & VERIFIED (BLK-09 CLOSED).** `src/slokern/engine/reporting/report_builder.py` compiles canonical `ReportArtifact` contracts adhering to `schemas/ReportArtifact.json` and renders human-readable Markdown reports (`report.md`) disclosing specifications, baseline metrics, candidate comparison tables, drift comparisons, and verification verdicts with automated secret redaction.
- **Evidence:** `src/slokern/engine/reporting/report_builder.py`, `tests/unit/engine/reporting/test_report_builder.py` passes cleanly; verified on `exp-audit-offline-campaign`.
- **Dependencies:** `SUB-02` (Contracts), `SUB-08` (Run artifacts), `SUB-09` (Verification).
- **Risks:** None for offline reporting. Secret sanitization asserted.
- **Status:** **RESOLVED (BLK-09 CLOSED).** Fully integrated into CLI `slokern report`.

### SUB-11: Control Plane API & CLI
- **Intended Behavior:** Minimal CLI runner (`slokern verify`, `slokern optimize`, `slokern smoke-test`, `slokern report`, `slokern validate`); FastAPI REST/SSE application deferred post-hackathon.
- **Actual Behavior:** **IMPLEMENTED (CLI RUNNER) / API DEFERRED.** `src/slokern/cli/main.py` implements all 5 subcommands with standard library `argparse`:
  - `slokern smoke-test`: preflight probe across `local`, `fake`, and `nebius`.
  - `slokern optimize`: enforces capability gating (halts with `SearchConfigurationError` citing `BLK-17` on `local` and `nebius`; runs 6-run campaign on `fake` labeled `DEMO DATA`).
  - `slokern verify`: independent single-run verification under compatible backend and invariant matching.
  - `slokern report`: serializes immutable Markdown and JSON report artifacts.
  - `slokern validate`: validates `ExperimentSpec` JSON against canonical Pydantic v2 schemas.
  FastAPI application (`src/slokern/api/app.py`) is formally deferred post-hackathon per DEC-0015 to protect critical path delivery.
- **Evidence:** `src/slokern/cli/main.py`, `src/slokern/cli/commands/`, `tests/unit/cli/` (27/27 unit tests pass).
- **Dependencies:** `SUB-08` (Runner), `SUB-09` (Verification), `SUB-10` (Reporting).
- **Risks:** None for CLI runner.
- **Status:** **RESOLVED (TASK-13 COMPLETE).** CLI functional and fully verified.

### SUB-12: Frontend Command Center & Presentation
- **Intended Behavior:** React + Vite cyber-technical command center visualizing specifications, live run progress, comparisons, and report badges.
- **Actual Behavior:** **IMPLEMENTED (DEMO DATA UI) / API INTEGRATION DEFERRED.** Delivered in PR #2 (`a450175`). Full React + Vite dashboard (`frontend/src/App.tsx`, 2553 lines, `DESIGN.md`, `frontend/package.json`) with 9 workflow pages (Overview, Experiments, Specify, Tuning Lab, Measure, Verify, Reports, Runtime Profile, Settings), 2D Pareto frontier visualizer, and strict `DEMO DATA` labeling. Built-in offline demo fixtures allow standalone presentation decoupled from backend execution. Live API integration (`TASK-17`) remains deferred post-hackathon.
- **Evidence:** `frontend/src/App.tsx` (2553 lines), `frontend/package.json`, `DESIGN.md`, PR #2 (`a450175`).
- **Dependencies:** SUB-11 (API, deferred).
- **Risks:** Decoupled presentation runs on fixtures; must maintain clear `DEMO DATA` labeling until live API integration is delivered.
- **Next Testable Step:** Maintain offline fixtures with strict `DEMO DATA` watermarks; complete backend verification engine (`TASK-11`) before reconsidering live API wiring.


### SUB-13: CI/CD, Packaging & Test Automation
- **Intended Behavior:** Production-quality GitHub Actions workflow enforcing linting, static typing, dependency checks, test execution, and contract drift checks; clean reproducible packaging.
- **Actual Behavior:** `ci.yml` runs `pip install -e ".[dev]"`, `pip check`, `compileall`, and `pytest -v -m "not live"`. However, CI does NOT run linting, static type checking (mypy), contract schema generation, or secret scanning. Build tooling lacks `wheel` in venv. Working tree has uncommitted `README.md` modification (BLK-14).
- **Evidence:** `.github/workflows/ci.yml:L1-58@356c489`, command runs R-01, R-04, R-05, R-10, R-11.
- **Dependencies:** None.
- **Risks:** Regressions escaping into `main` due to incomplete CI test matrix.
- **Next Testable Step:** Revert or commit `README.md` to restore a clean working tree; add `wheel` to `build-system.requires` or local setup instructions. Acceptance: Clean `git status --porcelain` and reproducible editable install.

---

## 4. Contract Matrix & Pipeline Stages

### 4.1 Contract Audit Matrix (`A`)

| Contract Model | Defined in Code | Exported in `__init__` | Consumed Outside Tests | Tests Present in Repo | Round-Trip Match (P-18) | Schema Valid (P-17) | Extra Fields Policy (P-19) | Units Explicit |
|---|---|---|---|---|---|---|---|---|
| `WorkloadSpec` | `spec.py:L12` | Yes | Yes (`arrival.py`, `runner.py`, `run_executor.py`, `grid.py`) | Valid + Invalid (`test_schemas.py`, `test_schema_roundtrip.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (`requests/s`, `s`, `tokens`) |
| `SLOSpec` | `spec.py:L34` | Yes | Yes (`evaluate.py`, `run_executor.py`, `grid.py`) | Valid (`test_schemas.py`, `test_verification_independence.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (via `SLOConstraint.unit`) |
| `CandidateConfig` | `config.py:L11` | Yes | Yes (`space.py`, `fake.py`, `nebius.py`, `grid.py`, `rank.py`, `run_executor.py`) | Valid (`test_schemas.py`, `test_grid.py`, `test_space.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (settings dictionary) |
| `ExperimentSpec` | `spec.py:L52` | Yes | Yes (`grid.py`) | Valid (`test_schemas.py`, `test_grid.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (`seconds`, `multiplier`) |
| `RunRecord` | `run.py:L11` | Yes | Yes (`run_executor.py`, `grid.py`) | Valid (`test_schemas.py`, `test_run_executor.py`, `test_verification_independence.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (ISO timestamps; resolution not guaranteed by clock source) |
| `RawRequestMeasurement`| `evidence.py:L11` | Yes | Yes (`aggregate.py`, `latency.py`, `throughput.py`, `validity.py`, `base.py`, `recorder.py`, `runner.py`, `run_executor.py`) | Valid (`test_schemas.py`, `test_recorder.py`, `test_latency.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (epoch seconds; input tokens currently estimated)|
| `MetricSet` | `metrics.py:L22` | Yes | Yes (`evaluate.py`, `rank.py`, `aggregate.py`, `run_executor.py`, `grid.py`) | Serialization (`test_schemas.py`, `test_verification_independence.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (`ms`, `rps`, `tps`, fraction) |
| `FeasibilityResult` | `verdict.py:L24` | Yes | Yes (`evaluate.py`, `run_executor.py`, `grid.py`) | Valid (`test_schemas.py`, `test_evaluate.py`, `test_verification_independence.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (preserves constraint units) |
| `SearchResult` | `search.py:L18` | Yes | Yes (`grid.py`, `budget.py`) | Valid (`test_schemas.py`, `test_grid.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (objective enum, metrics) |
| `VerificationRecord` | `verification.py:L19`| Yes | Ready for Phase C (`TASK-11`) | Valid (`test_schemas.py`, `test_verification_independence.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (drift percent, IDs) |
| `ReportArtifact` | `report.py:L27` | Yes | Ready for Phase C (`TASK-12`) | Serialization (`test_schemas.py`, `test_schema_roundtrip.py`) | True | True | `forbid` (BLK-12 resolved) | Yes (embedded specs & metrics) |

---

### 4.2 Pipeline Stage Execution Reality

```mermaid
flowchart LR
    S0[Stage 0: Spec & Contracts\nIMPLEMENTED] --> S1[Stage 1: Serving Preflight\nIMPLEMENTED (Fake+Nebius)]
    S1 --> S2[Stage 2: Loadgen & Event Capture\nIMPLEMENTED]
    S2 --> S3[Stage 3: Metrics Derivation\nIMPLEMENTED]
    S3 --> S4[Stage 4: Feasibility Evaluator\nIMPLEMENTED]
    S4 --> S5[Stage 5: Search & Ranking\nIMPLEMENTED]
    S5 --> S6[Stage 6: Independent Verification\nREADY / STUB]
    S6 --> S7[Stage 7: Report Publishing\nABSENT / STUB]

    classDef done fill:#1f3a2d,stroke:#4ade80,color:#fff;
    classDef ready fill:#3a351d,stroke:#facc15,color:#fff;
    classDef absent fill:#3b1d1d,stroke:#f87171,color:#fff;
    class S0,S1,S2,S3,S4,S5 done;
    class S6 ready;
    class S7 absent;
```

| Stage | Pipeline Function | Implemented Module | Current Reality | Verification Status | Real Pipeline Blockage |
|---|---|---|---|---|---|
| **0. Spec** | Workload & SLO contract specification | `src/slokern/contracts/` | Implemented; Pydantic v2 schemas valid, `extra='forbid'` enforced. | `UNIT` (pass, 119 tests) | Operational. |
| **1. Serving** | Runtime configuration & preflight check | `src/slokern/engine/serving/` | Fake adapter and Nebius HTTP transport exist; searched engine knobs are not transmitted or read back. Live probe skipped without credentials. | `UNIT` (targeted subset passed; live NOT RUN) | Cannot evidence remote application of engine parameters; blocked by BLK-04 and BLK-17. |
| **2. Loadgen** | Traffic generation & raw JSONL capture | `src/slokern/engine/loadgen/` | Subprocess load generator with Poisson/constant arrival implemented. | `UNIT` (pass, 38 tests) | Operational. Dispatches requests and records valid JSONL traces. |
| **3. Metrics** | Raw events to `MetricSet` aggregation | `src/slokern/core/metrics/` | Pure deterministic metrics engine implemented. | `UNIT` (pass, 42 tests) | Operational. Computes percentiles, throughput, and validity. |
| **4. Evaluator**| Feasibility verdict vs hard SLO constraints | `src/slokern/core/evaluator/` | Implemented; NaN & negative latency guards active. | `UNIT` (pass, 29 tests) | Operational. Emits deterministic FeasibilityResult. |
| **5. Search & Ranking** | 2×2 grid search & candidate ranking | `src/slokern/core/search/` | `GridSearchController`, `SearchSpace`, `BudgetLimiter`, and `CandidateRanker` implemented with 33 unit tests. Audit notes caveat BLK-15/16. | `UNIT` (pass, 33 tests in search) | Operational in unit paths; caveat BLK-15 (budget limiter enforcement) and BLK-16. |
| **6. Verification**| Independent rerun under fresh run ID | `src/slokern/core/verification/` | `IMPLEMENTED & VERIFIED.` Full protocol, drift policy, and campaign verification runner operational; 22 unit + 17 contract tests verified. | `NONE` | BLK-08 resolved. |
| **7. Report** | Publish self-contained evidence artifact | `src/slokern/engine/reporting/` | **ABSENT.** Skeletons only; no Markdown builder. | `NONE` | Blocked by Stage 6 & BLK-09. No report output. |


---

## 5. Claims Ledger

> **Ledger Status (Updated 2026-10-23, Sprint Day 5):** The Oct 21 audit identified 8 contradicted claims. Through Sprint Days 3–5 (PRs #1, #2, #4, #6, and 2×2 search controller commits), all 8 contradictions have been resolved in physical code.

| Claim ID | Completion Claim Text | Source Document | Oct 21 Audit Finding | Day 5 (Oct 23) Reconciled Reality |
|---|---|---|---|---|
| **CLM-01** | *"Fake Serving Adapter: IMPLEMENTED (src/slokern/engine/serving/fake.py generates deterministic synthetic runs)."* | `README.md:253` | **CONTRADICTED** | **RESOLVED (Oct 21).** `FakeServingAdapter` implemented in `fake.py` generating deterministic synthetic runs labeled `DEMO DATA`; passes 43 unit tests. |
| **CLM-02** | *"Demo Dashboard UI: IMPLEMENTED (React + Vite command center in frontend/; offline fixtures labeled DEMO DATA)."* | `README.md:258` | **CONTRADICTED** | **RESOLVED (Oct 22).** Delivered in PR #2 (`a450175`). Full React + Vite dashboard in `frontend/src/App.tsx` (2553 lines, `DESIGN.md`, `styles.css`) with 9 pages, Pareto visualizer, and strict `DEMO DATA` labeling. |
| **CLM-03** | *"1. Model-Agnostic Core: VERIFIED (Contracts, evaluator, load generator, and search controllers are model-agnostic)."* | `README.md:181` | **CONTRADICTED** | **RESOLVED (Oct 23).** Contracts, evaluator, load generator, metrics engine, and 2×2 search controller are model-agnostic and fully implemented. |
| **CLM-04** | *"Subsystem Modules: IMPLEMENTED (STUBS) (api/, cli/, core/, engine/ scaffolded with clear typed signatures)."* | `README.md:252` | **CONTRADICTED** | **RESOLVED (Oct 23).** Core (`metrics/`, `evaluator/`, `search/`) and engine (`serving/`, `loadgen/`, `runner/`) fully implemented with typed signatures and 242 passing tests. |
| **CLM-05** | *"Phase A (Oct 19) - Audit and Scope Freeze: DONE (Repository audit completed; working baseline established; core interfaces locked)."* | `README.md:370` | **CONTRADICTED** | **RESOLVED (Oct 21).** Audit executed on Oct 21 and ratified; working baseline established and locked. |
| **CLM-06** | *"Phase A | Oct 19 | Audit and scope freeze | DONE / VERIFIED"* | `ROADMAP.md:236` | **CONTRADICTED** | **RESOLVED (Oct 21).** Phase A completed and ratified with audit artifacts. |
| **CLM-07** | *"Gate A: Scope & Baseline Oct 19 DONE"* | `ROADMAP.md:441` | **CONTRADICTED** | **RESOLVED (Oct 21).** Gate A verified with physical evidence on Oct 21. |
| **CLM-08** | *"- [x] Deterministic fake adapter verified for offline development."* | `ROADMAP.md:451` | **CONTRADICTED** | **RESOLVED (Oct 21).** `FakeServingAdapter` implemented and verified offline in `tests/unit/engine/serving/test_fake.py`. |
| **CLM-09** | *"Serving Adapter ... IN PROGRESS (Rajdeep)"* | `ROADMAP.md:507` | **CONTRADICTED** | **RESOLVED (Oct 23).** `FakeServingAdapter` and `NebiusServingAdapter` implemented; live smoke pending credentials (`BLK-04`, `BLK-17`). |
| **CLM-10** | *"Loadgen Subprocess ... IN PROGRESS (Rajdeep)"* | `ROADMAP.md:508` | **CONTRADICTED** | **RESOLVED (Oct 22).** Subprocess load generator delivered in PR #4 (`bfc2c21`, 38 unit tests pass). |
| **CLM-11** | *"Search & Ranker ... IN PROGRESS (Rajdeep)"* | `ROADMAP.md:511` | **CONFIRMED** | **RESOLVED (Oct 23).** 2×2 bounded `GridSearchController`, `SearchSpace`, `BudgetLimiter`, and `CandidateRanker` implemented with 33 unit tests pass. |
| **CLM-12** | *"Data Contracts: IMPLEMENTED (Pydantic v2 schemas in src/slokern/contracts/)."* | `README.md:251` | **CONFIRMED** | **CONFIRMED (Oct 21).** All 11 models defined, exported, compile, pass schema generation and round-trip tests (P-17, P-18). |
| **CLM-13** | *"Adriraj active execution begins October 21, 2026."* | `docs/ownership.md` | **OBSOLETE** | **RECONCILED (Oct 26).** Superseded by Strict Solo Execution model under DEC-0015; active collaborator workstreams removed. |
| **CLM-14** | *"Daksh active execution begins October 24, 2026."* | `docs/ownership.md` | **OBSOLETE** | **RECONCILED (Oct 26).** Superseded by Strict Solo Execution model under DEC-0015; active collaborator workstreams removed. |


---

## 6. Blockers Register

| Blocker ID | Priority | Evidence | Actual Consequence | Affected Subsystems | Accountable Owner | Smallest Remediation | Closing Test |
|---|---|---|---|---|---|---|---|
| **BLK-01** | **P0** | `src/slokern/engine/serving/fake.py:L1-4@356c489` & `nebius.py:L1-4` were empty docstrings. | System could not execute any serving requests locally or live. | SUB-05, SUB-08 | Rajdeep | Implemented `FakeServingAdapter` generating deterministic synthetic responses. | **RESOLVED** (`afac3a6`, 43 serving tests pass in `tests/unit/engine/serving/`) |
| **BLK-02** | **P0** | `src/slokern/engine/loadgen/runner.py:L1-4@356c489` was an empty docstring. | Cannot dispatch requests or record raw `RawRequestMeasurement` event traces. | SUB-06, SUB-08 | Rajdeep | Implement minimal dispatch loop writing unaggregated JSONL recordings. | **RESOLVED** (38 unit tests pass in `tests/unit/engine/loadgen/`) |
| **BLK-03** | **P0** | `src/slokern/core/metrics/percentiles.py:L1-4@356c489` was an empty docstring. | Cannot calculate `MetricSet` from raw event traces. | SUB-07, SUB-08 | Rajdeep | Implement standard library percentile and throughput calculators. | **RESOLVED** (`tests/unit/core/metrics/` passing 42/42 tests) |
| **BLK-04** | **P0** | `tests/live/test_smoke_live.py:L12@356c489` skips; exact Nebius API model string unverified. | Cannot run live compliance benchmark on Nebius Cloud. Blocks Stage 1 on live infra. | SUB-05 | Rajdeep | Execute live preflight probe using `curl` or single-request script with valid API key. | `tests/live/test_smoke_live.py` (live run) |
| **BLK-05** | **P1** | Probe P-05: `float('nan') <= 200.0` returns `False`, yielding `INFEASIBLE` with `TTFT_P95_EXCEEDED`. | Corrupted or uncalculable floating-point evidence is misclassified as an SLO threshold breach instead of inconclusive evidence. | SUB-03 | Rajdeep | Added `math.isnan(obs_val)` check in `evaluate.py` to route NaN to `INCONCLUSIVE`. | **RESOLVED** (`2453f75`, 29 evaluator tests pass in `tests/unit/core/test_evaluator.py`) |
| **BLK-06** | **P1** | Probe P-06: `-10.0 <= 200.0` returns `True`, yielding `FEASIBLE` with `HARD_CONSTRAINTS_PASSED`. | Physically impossible negative latency passes feasibility checks without rejection. | SUB-03 | Rajdeep | Added physical non-negative constraint assertion (`obs_val >= 0`) in `evaluate.py`. | **RESOLVED** (`2453f75`, 29 evaluator tests pass in `tests/unit/core/test_evaluator.py`) |
| **BLK-07** | **P1** | `docs/ownership.md` lists Rajdeep as sole accountable owner for all 13 subsystems (100% concentration). | Potential delivery bottleneck on solo engineer. | SUB-01 through SUB-13 | Rajdeep | Freeze scope strictly to CLI + static Markdown report; defer API and Frontend; automate audit verification via contract suites. | Ratified `ROADMAP.md` with strict solo scope and DEC-0015. |
| **BLK-08** | **P1** | `src/slokern/core/verification/compare.py` & `protocol.py` lacked end-to-end drift calculation and campaign verification rerun. | Cannot independently verify selected winning candidates or compute metric drift ($\Delta M$). Blocks Stage 6. | SUB-09 | Rajdeep | Implemented `compare_metrics`, `DriftPolicy` (+15% latency, -15% throughput, +0.01 error rate), and `verify_search_campaign`. | **RESOLVED** (`tests/unit/core/verification/` 22/22 passed; campaign rerun `run-verify-838c1aef` verified) |
| **BLK-09** | **P1** | `src/slokern/engine/reporting/report_builder.py:L1-4@356c489` was an empty docstring. | Cannot publish immutable `ReportArtifact` for hackathon submission evidence. Blocks Stage 7. | SUB-10 | Rajdeep | Implement Markdown builder serializing `ReportArtifact` into an inspectable document. | **RESOLVED** (`tests/unit/engine/reporting/test_report_builder.py` passed; report serializer verified) |
| **BLK-10** | **P1** | `schemas/` contained only `.gitkeep`; `scripts/gen_contracts.py:L17@356c489` was a gap notice. | No emitted JSON Schemas exist in source control; cannot validate external tooling against contracts. | SUB-02 | Rajdeep | Implemented script exporting `model_json_schema()` for all 11 models into `schemas/`. | **RESOLVED** (16 schema tests pass in `tests/contract/`) |
| **BLK-11** | **P2** | Probe P-12: `{"tensor_parallel_size": 1}` vs `1.0` produces different candidate IDs (`4fe93deaf8d0` vs `cd0ce0cb5b73`). | Inadvertent type coercion between float and integer changes candidate hash identity. | SUB-04 | Rajdeep | Enforced canonical integer/float normalization before hashing in `candidate_id.py`. | **RESOLVED** (`afac3a6`, 13 tests pass in `tests/unit/core/`) |
| **BLK-12** | **P2** | Probe P-19: All 11 models accepted unrecognized fields silently (`extra='ignore'`). | Contracts did not strictly reject invalid or misspelled fields at system boundaries. | SUB-02 | Rajdeep | Added `model_config = ConfigDict(extra='forbid')` to all 11 contract classes. | **RESOLVED** (103 roundtrip tests pass in `tests/contract/`) |
| **BLK-13** | **P2** | `.github/workflows/ci.yml:L1-58@356c489` lacks linting, type checks, schema drift, and secret scanning steps. | Code regressions, typing errors, or secret leaks can bypass CI unnoticed. | SUB-13 | Rajdeep | Add `ruff check`, `mypy --strict src/slokern`, and secret scanning checks to `ci.yml`. | `.github/workflows/ci.yml` execution in GitHub Actions |
| **BLK-14** | **P2** | Git preflight R-01: `README.md` was modified in the working tree. | Working tree baseline was not clean. | SUB-13 | Rajdeep | Committed baseline modifications on integration branch. | **RESOLVED** (Clean tree verified on branch) |
| **BLK-15** | **P0** | `BudgetLimiter` constructor allowed configurable limits that could permit six search executions and zero verification runs. | A caller could violate the required 1 baseline + 4 candidate + 1 verification allocation. | SUB-04 | Rajdeep | Enforced strict campaign invariant via preflight `validate_budget` in `src/slokern/core/search/grid.py` (`max_total_runs <= 6`, `max_search_runs == 5`, `reserved_verification_runs == 1`). | **RESOLVED (Oct 24)** (15 tests pass in `tests/unit/core/search/`) |
| **BLK-16** | **P1** | Ranking accepted FEASIBLE results with missing objective metrics; Mode A could substitute reciprocal throughput when monetary cost metadata was absent. | A candidate without declared objective evidence could win, or a non-monetary proxy could be represented as monetary cost. | SUB-04 | Rajdeep | Enforced strict finite check in `rank.py` and alphanumeric candidate-ID tie-breaking; unmeasured metrics rejected. | **RESOLVED (Oct 24)** (11 tests pass in `tests/unit/core/test_ranker*.py`) |
| **BLK-17** | **P0** | Serving engine parameter application and read-back unavailable for optimization search space (`{max_num_batched_tokens: [1024, 2048]} × {max_num_seqs: [16, 64]}`). | Search results cannot evidence that declared configurations were applied on Ollama or Nebius Token Factory endpoints. | SUB-05 | Rajdeep | Halt `slokern optimize` immediately with `SearchConfigurationError (BLK-17)` on `local` and `nebius` before allocating benchmark runs. Offline campaign runs on `fake` labeled `DEMO DATA`. | **ACTIVE** (DEC-0014 capability preflight gating enforced in `validate_search_capabilities()` and CLI `optimize_command`) |
| **BLK-18** | **P2** | Windows Codex sandbox environment loopback socket / multiprocessing restrictions stall runner subprocess integration tests. | Cannot execute multi-process loadgen integration tests synchronously inside the Windows Codex sandbox. | SUB-06, SUB-08 | Rajdeep | Run standalone unit test suites (`test_arrival.py`, `test_recorder.py`) which pass 100% deterministically; gate multi-process runner integration tests to unconstrained/Linux environments. | `tests/unit/engine/loadgen/` unit tests passing 38/38 |

---

## 7. Scope Freeze (The MVP Boundary)

### 7.1 Scope Matrix Per Pipeline Stage

| Stage | Capability Description | Subsystem | Status | Depends On | Acceptance Criterion | Scope Verdict |
|---|---|---|---|---|---|---|
| **0. Specification** | Declarative WorkloadSpec and hard SLOSpec via Pydantic v2 | SUB-02 | `IMPLEMENTED` | None | Schemas compile, roundtrip validate, and reject invalid enums. | **IN** |
| **1. Serving Preflight** | Deterministic FakeServingAdapter for offline synthetic testing | SUB-05 | `IMPLEMENTED` | DEC-01 | Single request returns synthetic completion and simulated timestamps labeled DEMO DATA. | **IN (CRITICAL)** |
| **1. Serving Runtime** | Nebius Cloud serving adapter for live benchmark execution | SUB-05 | `ABSENT` | DEC-01, BLK-04 | Authenticates via `NEBIUS_API_KEY`, issues request to `Nemotron-3-Nano-30B-A3B`, returns response. | **IN (CRITICAL)** |
| **2. Load Generation** | Subprocess load generator with Poisson and constant arrival | SUB-06 | `IMPLEMENTED` | BLK-02 | Dispatches requests according to target offered rate and records raw events to JSONL. | **IN (CRITICAL)** |
| **2. Client Saturation** | Client thread starvation and saturation detection | SUB-06 | `IMPLEMENTED` | BLK-02 | Flags `generator_saturated = True` when client loop lag exceeds 10% of dispatch interval. | **IN (CRITICAL)** |
| **3. Metrics Derivation** | Derive TTFT/ITL percentiles (p50, p95, p99), throughput, error rate | SUB-07 | `IMPLEMENTED` | None | Produces valid `MetricSet` from unaggregated JSONL recordings. | **IN (CRITICAL)** |
| **4. Feasibility Audit** | Deterministic hard SLO constraint evaluation with reason codes | SUB-03 | `IMPLEMENTED` | BLK-05 | Emits `FeasibilityResult` with FEASIBLE, INFEASIBLE, or INCONCLUSIVE verdict. | **IN** |
| **5. Candidate Search** | Bounded 2×2 grid search (4 candidates + 1 baseline = 5 runs) | SUB-04, SUB-08 | `PARTIAL` | SUB-05 | Evaluates exactly 5 runs without exceeding declared 6-run experiment budget. | **IN (CRITICAL)** |
| **5. Ranking** | Deterministic candidate ranking by Mode B proxy or Mode A cost | SUB-04 | `IMPLEMENTED` | SUB-03 | Lowest cost/proxy feasible candidate selected with candidate-ID tie-breaking. | **IN** |
| **6. Verification** | Independent rerun of winning candidate under fresh run ID | SUB-09 | `IMPLEMENTED` | None | Re-evaluates candidate under distinct `verification_run_id`, computes drift $\Delta M$, outputs `VerificationRecord`. | **IN (CRITICAL)** |
| **7. Reporting** | Publish self-contained Markdown ReportArtifact with raw trace links | SUB-10 | `ABSENT` | BLK-09 | Emits complete Markdown file documenting spec, evidence, drift, and verdict. | **IN (CRITICAL)** |
| **Interface** | Minimal CLI tool (`slokern verify`, `slokern optimize`) | SUB-11 | `ABSENT` | SUB-08 | Command-line execution with exit code 0 on verified pass, exit code 1 on failure. | **IN** |
| **Interface** | FastAPI control plane REST API and SSE streaming endpoints | SUB-11 | `ABSENT` | SUB-08 | HTTP API serving experiment lifecycle and server-sent events. | **DEFERRED (POST-MVP)** |
| **Interface** | React + Vite frontend dashboard command center | SUB-12 | `ABSENT` | SUB-11 | Web UI displaying visual graphs and badges. | **DEFERRED (POST-MVP)** |
| **Search Space** | Continuous adaptive Bayesian optimization or multi-GPU search | SUB-04 | `ABSENT` | N/A | Heuristic search algorithms or multi-GPU topologies. | **OUT OF SCOPE** |
| **Serving** | Production Kubernetes auto-scaling or live cluster reconfiguration | SUB-05 | `ABSENT` | N/A | Production infrastructure modification. | **OUT OF SCOPE** |

---

### 7.2 Objectives & Supported Workflow
SLOKern solves one problem: **Given a declared workload and hard tail-latency/error-rate SLOs, it measures a bounded set of serving configurations, selects the lowest-cost evidenced configuration that satisfies all constraints, and independently verifies the recommendation.**

**Supported End-to-End Workflow:**
1. User provides `WorkloadSpec` and `SLOSpec`.
2. SLOKern verifies preflight connectivity to the serving endpoint (or selects `FakeServingAdapter` if offline).
3. Search controller evaluates a bounded 2×2 parameter matrix (4 candidates + 1 baseline).
4. Subprocess load generator executes each run, capturing unaggregated request-level timestamp observations to JSONL traces; exact clock resolution is not established.
5. Metrics engine derives `MetricSet` and flags load generator saturation.
6. Evaluator deterministically computes feasibility verdicts against hard SLOs.
7. Ranker selects the lowest-cost feasible candidate under Mode B systems proxy (or Mode A monetary cost if rates are verified).
8. Verification runner reruns the winning candidate under a fresh `verification_run_id` and computes metric drift ($\Delta M$).
9. Report generator outputs an immutable Markdown `ReportArtifact` linking all claims to physical JSONL evidence.

---

### 7.3 Out of Scope & Non-Negotiable Exclusions
1. **No Production Mutation:** SLOKern will not automatically reconfigure production Kubernetes clusters, auto-scaling groups, or live serving endpoints.
2. **No Multi-Cloud / Multi-Provider Orchestration:** The MVP targets exactly one provider (Nebius Cloud) and one local synthetic provider (`FakeServingAdapter`). No AWS, GCP, or Azure orchestration.
3. **No Unbounded or Adaptive Search:** Search space is strictly frozen to a bounded 2×2 discrete parameter grid (maximum 4 candidates + 1 baseline). No continuous Bayesian optimization, genetic algorithms, or random search.
4. **No LLM in Decision Path:** An LLM may be used for advisory spec drafting or post-hoc result explanations, but deterministic Python code strictly owns feasibility evaluation, ranking, budget enforcement, and verification verdicts.
5. **No Synthetic Data Presented as Live:** Any offline or simulated benchmark results must be unambiguously watermarked **`DEMO DATA`**.
6. **No Fabricated Pricing:** If authoritative Nebius GPU hourly rates cannot be verified in writing, monetary cost is reported as **`unavailable`**, and the system falls back to Mode B (GPU-seconds per request or throughput under SLO).

---

### 7.4 Accepted Architectural Decisions (ADR Citations)
- **ADR 0001 (MVP Scope & Evidence Standards):** Establishes modular monolith architecture, physical JSONL artifact preservation, and mandatory independent verification rerun under a fresh run ID.
- **ADR 0001-B (Model & Runtime Compliance Target):** Selects `Nemotron-3-Nano-30B-A3B` (FP8) as the primary NVIDIA open-source model candidate on Nebius Cloud to satisfy hackathon mandates, while preserving `meta-llama/Meta-Llama-3-8B-Instruct` as internal pipeline baseline.
- **ADR 0002 (Dual-Mode Cost Accounting Policy):** Mandates Mode A (monetary accounting) only when provider billing rates are verified, and enforces Mode B (non-monetary systems proxy: GPU-seconds per request or throughput under SLO) when pricing is variable or unconfirmed.

---

### 7.5 Unresolved Decisions for Rajdeep

#### DEC-01: Nebius Serving Endpoint Interface & Parameter Controls
- **Question:** Does the chosen Nebius endpoint expose serving-engine parameters (`max_num_seqs`, `gpu_memory_utilization`), or only client request parameters (`max_tokens`, `concurrency`)?
- **Options:**
  - *Option A (Recommended):* If Nebius managed endpoint is an OpenAI-compatible API without engine knobs, refine the search space to legal client request parameters (e.g. concurrency limits, max output tokens), or deploy containerized vLLM on a dedicated Nebius GPU instance if engine knobs are strictly required.
  - *Option B:* Require containerized vLLM deployment on Nebius Compute GPU instance to access engine-level flags.
- **Default Recommendation:** Option A (test endpoint reachability first; if engine knobs are inaccessible, bound search space to client concurrency and batch parameters).
- **What stays blocked if unresolved:** SUB-05 (Serving adapter) and live benchmark execution.

#### DEC-02: Target Model Deployment Confirmation
- **Question:** What is the verified Nebius API model identifier string for `Nemotron-3-Nano-30B-A3B` (FP8)?
- **Options:**
  - *Option A (Recommended):* Run an immediate single-request smoke test against Nebius to read back the active model catalog string (e.g., `nvidia/Nemotron-3-Nano-30B-A3B`).
  - *Option B:* Fall back to `meta-llama/Meta-Llama-3-8B-Instruct` for pipeline testing, acknowledging high disqualification risk under the NVIDIA model rule if submitted without an NVIDIA model.
- **Default Recommendation:** Option A (run smoke test to confirm model string).
- **What stays blocked if unresolved:** Live compliance test `tests/live/test_smoke_live.py`.

#### DEC-03: Cost Accounting Basis Lock (Mode A vs Mode B)
- **Question:** Which ranking objective is default for candidate selection during the hackathon benchmark?
- **Options:**
  - *Option A (Recommended):* Mode B (`RankingObjective.GPU_SECONDS_PER_REQUEST` or `MAX_THROUGHPUT_UNDER_SLO`), reporting monetary cost as `unavailable` unless official Nebius billing rates are verified.
  - *Option B:* Mode A (`RankingObjective.MONETARY_COST_PER_1K_REQUESTS`) using estimated public cloud rates.
- **Default Recommendation:** Option A (strictly enforces core non-negotiable principle: no fabricated pricing).
- **What stays blocked if unresolved:** Ranking objective configuration in experiment specifications.

#### DEC-04: Integration Branch and Baseline Hygiene
- **Question:** Should `origin/main` remain the sole integration branch, and should the uncommitted `README.md` badge edit be reverted or committed immediately?
- **Options:**
  - *Option A (Recommended):* Commit or revert the `README.md` badge change to restore a clean baseline (`CLEAN-BASELINE`), and merge all subsequent work to `main`.
  - *Option B:* Continue working on branch `repository-audit-and-mvp-scope-freeze`.
- **Default Recommendation:** Option A (a clean working tree is prerequisite for verifiable reproducible benchmarks).
- **What stays blocked if unresolved:** Verification that a clean clone reproduces the baseline.

#### DEC-05: Frontend Scope Deferral
- **Question:** Should the React + Vite frontend dashboard (`frontend/`) be formally frozen as `DEFERRED / OUT OF MVP CRITICAL PATH`?
- **Options:**
  - *Option A (Recommended):* Formally defer the frontend. Deliver all hackathon deliverables via the CLI runner and self-contained Markdown/JSON `ReportArtifact`s.
  - *Option B:* Attempt to implement the React UI in parallel.
- **Default Recommendation:** Option A (protects critical path; prevents failure to deliver a verified backend inference pipeline).
- **What stays blocked if unresolved:** Bandwidth allocation for sprint tasks.

---

### 7.6 Reopen Criteria
Scope freeze can only be reopened if:
1. Rajdeep explicitly ratifies an ADR amending the search space or execution model.
2. Nebius Cloud infrastructure proves incompatible with the selected model, requiring an emergency model substitution.
3. The submission deadline is extended by hackathon organizers.

### 7.7 Deployment Decision Research (2026-10-23)
- Read-only platform/model research is recorded in [`deployment-decision-2026-10-23.md`](deployment-decision-2026-10-23.md).
- **Research status:** The memo's Nemotron Nano 9B v2 / H100 VM conclusion is an alternative study, not an accepted change to ADR 0001-B's Nemotron-3-Nano-30B-A3B FP8 model-family target. DEC-0013 records the conflict and keeps the new 30B Serverless/vLLM 0.12.0 profile open pending Rajdeep's decision.
- **Implementation reality unchanged:** `SUB-04`/`TASK-10` remains blocked by `BLK-15`/`BLK-16`; `SUB-05`/`TASK-09` remains partial/blocked by `BLK-04`/`BLK-17`. No deployment, live inference, or account access was performed for the research.

### 7.8 Documentation and Profile Reality Audit (2026-10-23)
- The accepted product flow remains `SPECIFY → VALIDATE → MEASURE → EVALUATE → OPTIMIZE → VERIFY → EXPLAIN`; execution status, evidence validity, SLO feasibility, objective rankability, and verification status remain separate concepts.
- **Current source profile:** `generate_2x2_candidates()` creates four candidates from `max_num_batched_tokens ∈ {1024, 2048}` and `max_num_seqs ∈ {16, 64}`. `GridSearchController` counts a baseline plus up to four candidate runs under the default five-search/one-verification `BudgetLimiter`. The limiter accepts custom values that can consume the verification reserve (`BLK-15`).
- **New profile status:** The proposed centre baseline `(max_num_seqs=128, max_num_batched_tokens=8192)` and four candidates from `{64, 256} × {2048, 16384}` are a proposal only; no code or contract change was made. `NebiusServingAdapter.apply_config()` checks declared capabilities and updates local config state; it does not send or read back vLLM process flags (`BLK-17`).
- **Decision integrity:** `rank_candidates()` filters on `FEASIBLE` but leaves candidates with absent ranking values in the list. `extract_ranking_metric()` can substitute reciprocal throughput for missing monetary metrics. A missing objective value can therefore reach winner selection (`BLK-16`).
- **Measurement reality:** the load generator estimates input tokens as `int(len(prompt.split()) * 1.3)`; the contract describes `input_tokens` as measured. Current metrics derive an average of recorded chunk-gap observations per request (or an elapsed-time fallback), not a guaranteed per-token TPOT. There is no TPOT field, bootstrap interval, p99 lateness/CPU gate, cache/preemption metric, or accepted ±15% verification tolerance.
- **Verification reality:** `src/slokern/core/verification/protocol.py` and `compare.py` remain stubs. `SLOSpec.min_sample_count` is the implemented general sample gate; the percentile helper computes percentiles for any non-empty sample count and does not implement per-percentile 10/30/100 thresholds.
- **Operational and billable accounting:** preflight, pilot ladder, baseline replicate, retries, failed deployments, server startup/download/idle time, and teardown delay must be logged and capped separately from controller-counted search/verification runs. Exclusion from the controller counter does not make a run or resource time free.
- No task status, validation level, or hackathon compliance state is promoted by these documentation corrections.

### 7.9 Progress & Milestones Reconciliation (Sprint Day 5 / 2026-10-24)
- **Milestone Progress:**
  - **Phase A (Audit & Scope Freeze):** `DONE`. Baseline locked, Pydantic v2 contracts enforced (`extra='forbid'`), golden test fixtures established.
  - **Phase B (Single-Run Execution):** `DONE`. Full single-run pipeline operational via `SingleRunExecutor` (`run_executor.py`) integrating `FakeServingAdapter` (`fake.py`), `NebiusServingAdapter` (`nebius.py`), subprocess `LoadGeneratorRunner` (`runner.py`), `calculate_metrics` (`aggregate.py`), and `evaluate_slo` (`evaluate.py`). Standalone React+Vite frontend command center delivered in PR #2 (`frontend/src/App.tsx`, 2553 lines, `DEMO DATA` labeling).
  - **Phase C (Search & Feasibility Optimization):** `IN PROGRESS / CRITICAL PATH`. Bounded 2×2 `GridSearchController` (`grid.py`), `SearchSpace` (`space.py`), `BudgetLimiter` (`budget.py`), and `CandidateRanker` (`rank.py`) delivered (`TASK-10`, 26 search/ranker unit tests passing). Preflight `validate_budget` (`BLK-15`) and strict finite ranking (`BLK-16`) resolved. Next critical-path milestone is `TASK-11` (Independent Verification Engine in `src/slokern/core/verification/`), supported by 16 passing contract tests in `tests/contract/test_verification_independence.py` and verified by the automated contract test suite.
- **Verification Evidence:**
  - `python scripts/gen_contracts.py --check`: 11 schemas clean and up to date.
  - `python -m compileall -q src tests`: Exit code 0 across all files.
  - `python -m pip check`: No broken requirements found.
  - `pytest tests/contract tests/unit/core tests/unit/engine/serving tests/unit/engine/runner/test_cancel.py tests/unit/engine/runner/test_lifecycle.py tests/unit/engine/loadgen/test_arrival.py tests/unit/engine/loadgen/test_recorder.py`: 322 passed in 3.16s.
  - `pytest tests/contract/test_verification_independence.py`: 16 passed in 0.38s.
  - Live Nebius smoke test: Skipped (no credentials configured; `BLK-04`, `BLK-17`).
