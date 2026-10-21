# SLOKern Implementation Status & MVP Scope Freeze

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Document Type:** October 19 Audit & Scope Freeze Deliverable  
> **Audit Date:** 2026-10-21T03:19:22Z (Nominal Audit Target: October 19, 2026)  
> **Audit Baseline Git Commit:** `52a088954e3bbf8f0bb83ef217ac7d2cdb37fab2` (`52a0889`)  
> **Working Tree State:** `NOT CLEAN-BASELINE` (`README.md` modified: uncommitted badge text edit)  
> **Integration Branch:** `origin/main` (active audit branch: `repository-audit-and-mvp-scope-freeze`)  
> **Authority & Sole Technical Owner:** Rajdeep  
> **Collaborator Workstreams:** Adriraj (Benchmark Integrity, active Oct 21), Daksh (Decision Verification, active Oct 24)  
> **Hackathon Submission Deadline:** October 30, 2026, 10:00 AM PDT (10:30 PM IST / 17:00 UTC)  
> **Remaining Sprint Time:** 9 days, 13 hours, 40 minutes (~229.7 hours)

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

| ID | Subsystem | Implementation | Verification | Flags | Owner | Blocked-by |
|---|---|---|---|---|---|---|
| **SUB-01** | Architecture & Scope Governance | `IMPLEMENTED` | `STATIC` | `NONE` | Rajdeep (CONFIRMED) | None |
| **SUB-02** | Shared Contracts & Schema Registry | `IMPLEMENTED` | `UNIT` | `BLOCKED(by=BLK-10)` | Rajdeep (CONFIRMED) | BLK-10, BLK-12 |
| **SUB-03** | Feasibility Evaluator Core | `IMPLEMENTED` | `UNIT` | `BLOCKED(by=BLK-05)` | Rajdeep (CONFIRMED) | BLK-05, BLK-06 |
| **SUB-04** | Candidate Identity & Deterministic Ranking | `IMPLEMENTED` | `UNIT` | `BLOCKED(by=BLK-11)` | Rajdeep (INTERIM) | BLK-11 |
| **SUB-05** | Serving Adapter & Runtime Infrastructure | `ABSENT` | `NONE` | `BLOCKED(by=BLK-01)` · `PENDING RUNTIME VERIFICATION` | Rajdeep (INTERIM) | BLK-01, BLK-04 |
| **SUB-06** | Subprocess Load Generator & Workload Fixtures | `ABSENT` | `NONE` | `BLOCKED(by=BLK-02)` | Rajdeep (CONFIRMED) | BLK-02 |
| **SUB-07** | Metrics Engine Core | `ABSENT` | `NONE` | `BLOCKED(by=BLK-03)` | Rajdeep (CONFIRMED) | BLK-03 |
| **SUB-08** | Experiment Orchestration & Run Lifecycle | `ABSENT` | `NONE` | `BLOCKED(by=BLK-01)` | Rajdeep (INTERIM) | BLK-01, BLK-02, BLK-03 |
| **SUB-09** | Independent Verification Engine | `ABSENT` | `NONE` | `BLOCKED(by=BLK-08)` | Rajdeep (CONFIRMED) | BLK-08 |
| **SUB-10** | Report Artifact Generator | `ABSENT` | `NONE` | `BLOCKED(by=BLK-09)` | Rajdeep (INTERIM) | BLK-09 |
| **SUB-11** | Control Plane API & CLI | `ABSENT` | `NONE` | `DEFERRED` | Rajdeep (INTERIM) | BLK-01, BLK-08 |
| **SUB-12** | Frontend Command Center & Presentation | `ABSENT` | `NONE` | `DEFERRED` | Rajdeep (INTERIM) | None |
| **SUB-13** | CI/CD, Packaging & Test Automation | `PARTIAL` | `UNIT` | `BLOCKED(by=BLK-13)` | Rajdeep (CONFIRMED) | BLK-13, BLK-14 |

---

## 3. Subsystem Detail Blocks

### SUB-01: Architecture & Scope Governance
- **Intended Behavior:** Single-owner technical authority governing modular monolith architecture, strict 6-run budget, deterministic decision policies, and hackathon compliance rules.
- **Actual Behavior:** Modular monolith design documented in `docs/architecture.md:L1-430@52a0889` and `docs/decision-policy.md:L1-141@52a0889`. Governance is active, but documentation contained completion claims that contradicted repository reality.
- **Evidence:** `docs/architecture.md:L1-430@52a0889`, `docs/decision-policy.md:L1-141@52a0889`, `docs/ownership.md:L1-188@52a0889`.
- **Dependencies:** None.
- **Risks:** High concentration of ownership under Rajdeep (P1 concentration risk BLK-07).
- **Next Testable Step:** Ratify the MVP Scope Freeze and resolve DEC-01 through DEC-05. Acceptance: `docs/implementation-status.md` accepted as sole status source of truth.

### SUB-02: Shared Contracts & Schema Registry
- **Intended Behavior:** 11 canonical Pydantic v2 models representing the entire optimization lifecycle, exporting committed JSON schemas and enforcing strict boundary validation.
- **Actual Behavior:** All 11 models are defined and exported in `src/slokern/contracts/`. All round-trip serialize perfectly (P-18). However, only 4 contracts are consumed outside contracts (`SLOSpec`, `CandidateConfig`, `MetricSet`, `FeasibilityResult`). Schemas directory contains only `.gitkeep`; `scripts/gen_contracts.py` is a stub (BLK-10); models lack `extra='forbid'` (BLK-12).
- **Evidence:** `src/slokern/contracts/__init__.py:L1-36@52a0889`, `tests/contract/test_schemas.py:L1-114@52a0889` (observed in R-10, R-11), `probe_b_contracts_roundtrip.py` (P-18).
- **Dependencies:** None.
- **Risks:** Drift between contracts and external tooling due to missing emitted JSON schemas.
- **Next Testable Step:** Update `scripts/gen_contracts.py` to write JSON schemas into a temporary directory and verify with `pytest tests/contract/test_generated_files_current.py`.

### SUB-03: Feasibility Evaluator Core
- **Intended Behavior:** Pure deterministic Python evaluation of a `MetricSet` against `SLOSpec`, producing an auditable `FeasibilityResult` with machine-readable `ReasonCode`.
- **Actual Behavior:** Implemented in `src/slokern/core/evaluator/evaluate.py:evaluate_slo@52a0889`. Evaluates hard constraints, generator saturation, and sample size. Tested across 7 unit tests. However, NaN floating-point values are misclassified as `INFEASIBLE` with `TTFT_P95_EXCEEDED` (P-05 / BLK-05), and negative latencies are accepted as `FEASIBLE` (P-06 / BLK-06).
- **Evidence:** `src/slokern/core/evaluator/evaluate.py:L66-130@52a0889`, `tests/unit/core/test_evaluator.py:L1-133@52a0889` (R-10, R-11), probes P-01 through P-10.
- **Dependencies:** `SUB-02` (Contracts).
- **Risks:** Invalid or corrupted measurements generating incorrect feasibility verdicts.
- **Next Testable Step:** Add `math.isnan(obs_val)` check and non-negative boundary assertions in `evaluate.py`. Acceptance: Probe P-05 returns `INCONCLUSIVE` and unit test passes.

### SUB-04: Candidate Identity & Deterministic Ranking
- **Intended Behavior:** Stable deterministic candidate ID generation from canonical configurations; deterministic ranking of feasible candidates under declared objective with candidate-ID tie-breaking.
- **Actual Behavior:** Implemented in `src/slokern/core/search/candidate_id.py:generate_candidate_id@52a0889` and `src/slokern/core/search/rank.py:rank_candidates@52a0889`. Infeasible/inconclusive candidates are excluded (P-13); ranking is deterministic across 20 shuffles (P-15); ties are broken by candidate ID (P-14). However, formatting numbers as float vs int produces different hashes (P-12 / BLK-11).
- **Evidence:** `src/slokern/core/search/candidate_id.py:L10-17@52a0889`, `src/slokern/core/search/rank.py:L21-56@52a0889`, probes P-11 through P-16.
- **Dependencies:** `SUB-02` (Contracts), `SUB-03` (Evaluator).
- **Risks:** Inconsistent hashing if numeric settings are not coerced to canonical types.
- **Next Testable Step:** Canonicalize numeric types before JSON serialization in `candidate_id.py`. Acceptance: `generate_candidate_id("m", "r", {"tp": 1}) == generate_candidate_id("m", "r", {"tp": 1.0})`.

### SUB-05: Serving Adapter & Runtime Infrastructure
- **Intended Behavior:** Interface for serving runtimes (capabilities, apply, environment fingerprint, health); fake adapter for offline testing; Nebius Cloud adapter for live serving.
- **Actual Behavior:** **ABSENT.** `src/slokern/engine/serving/fake.py`, `nebius.py`, `base.py`, and `capabilities.py` are 4-line docstrings with zero executable code. Live smoke test `test_smoke_live.py` executes `pytest.skip(...)`. Exact Nebius endpoint model string is unverified (BLK-04).
- **Evidence:** `src/slokern/engine/serving/fake.py:L1-4@52a0889`, `src/slokern/engine/serving/nebius.py:L1-4@52a0889`, `tests/live/test_smoke_live.py:L1-13@52a0889` (R-12).
- **Dependencies:** DEC-01 (Serving endpoint interface decision).
- **Risks:** System cannot execute a single inference request either locally or on cloud infrastructure (P0 Blocker BLK-01).
- **Next Testable Step:** Implement `FakeServingAdapter` that returns deterministic synthetic responses with simulated latencies tagged `DEMO DATA`. Acceptance: `tests/integration/test_pipeline_fake_adapter.py` passes.

### SUB-06: Subprocess Load Generator & Workload Fixtures
- **Intended Behavior:** Subprocess-isolated load generator generating Poisson/constant request schedules, recording unaggregated request-level microsecond timings to JSONL (`RawRequestMeasurement`), and detecting client saturation (`generator_saturated = True`).
- **Actual Behavior:** **ABSENT.** `src/slokern/engine/loadgen/arrival.py`, `recorder.py`, `runner.py`, and `src/slokern/engine/workload/fixtures.py` are empty docstrings. No workload fixtures exist.
- **Evidence:** `src/slokern/engine/loadgen/runner.py:L1-4@52a0889`, `src/slokern/engine/workload/fixtures.py:L1-4@52a0889`.
- **Dependencies:** `SUB-02` (Contracts), `SUB-05` (Serving Adapter).
- **Risks:** Cannot generate offered load or record raw request events (P0 Blocker BLK-02).
- **Next Testable Step:** Implement a minimal loadgen runner that dispatches synthetic requests, records timestamps into a `.jsonl` file, and validates each line against `RawRequestMeasurement`. Acceptance: `tests/unit/engine/loadgen/test_runner.py` passes.

### SUB-07: Metrics Engine Core
- **Intended Behavior:** Pure, deterministic derivation of `MetricSet` from raw `.jsonl` request recordings, computing TTFT/ITL percentiles (p50, p95, p99), throughput, error rate, and offered vs achieved load.
- **Actual Behavior:** **ABSENT.** `src/slokern/core/metrics/aggregate.py`, `latency.py`, `percentiles.py`, `throughput.py`, and `validity.py` are empty docstrings.
- **Evidence:** `src/slokern/core/metrics/percentiles.py:L1-4@52a0889`, `src/slokern/core/metrics/throughput.py:L1-4@52a0889`.
- **Dependencies:** `SUB-02` (Contracts), `SUB-06` (Raw Request Measurements).
- **Risks:** Missing pipeline link between raw execution traces and feasibility evaluation (P0 Blocker BLK-03).
- **Next Testable Step:** Implement percentile calculation using standard Python (`math`) and derive `MetricSet` from a fixture JSONL file. Acceptance: `tests/unit/core/metrics/test_percentiles.py` passes.

### SUB-08: Experiment Orchestration & Run Lifecycle
- **Intended Behavior:** Modular monolith experiment controller managing the 6-run search budget (1 baseline + 4 grid candidates + 1 verification run), lifecycle states (`ExecutionStatus`), cancellation, and artifact persistence.
- **Actual Behavior:** **ABSENT.** `src/slokern/engine/runner/experiment_controller.py`, `run_executor.py`, `lifecycle.py`, and `src/slokern/engine/store/writer.py` are empty docstrings.
- **Evidence:** `src/slokern/engine/runner/experiment_controller.py:L1-4@52a0889`, `src/slokern/engine/store/writer.py:L1-4@52a0889`.
- **Dependencies:** `SUB-04` (Search), `SUB-05` (Serving), `SUB-06` (Loadgen), `SUB-07` (Metrics).
- **Risks:** No automation exists to execute multi-candidate experiments or manage budgets.
- **Next Testable Step:** Implement a single-run executor that runs one configuration through serving, loadgen, metrics, and evaluator. Acceptance: A single run executes and persists a `RunRecord`.

### SUB-09: Independent Verification Engine
- **Intended Behavior:** Takes the winning feasible candidate, triggers a fresh independent rerun under a new `verification_run_id`, computes metric drift ($\Delta M$), and renders a deterministic verification verdict (`VERIFIED` or `VERIFICATION_FAILED`).
- **Actual Behavior:** **ABSENT.** `src/slokern/core/verification/protocol.py` and `compare.py` are empty docstrings.
- **Evidence:** `src/slokern/core/verification/protocol.py:L1-4@52a0889`, `src/slokern/core/verification/compare.py:L1-4@52a0889`.
- **Dependencies:** `SUB-08` (Experiment Orchestration), `SUB-03` (Evaluator).
- **Risks:** Verification cannot be performed independently; violates core product principle (P1 Blocker BLK-08).
- **Next Testable Step:** Implement drift calculation function comparing two `MetricSet` instances. Acceptance: `tests/unit/core/verification/test_compare.py` passes with positive and negative drift test cases.

### SUB-10: Report Artifact Generator
- **Intended Behavior:** Generates a self-contained, immutable Markdown and JSON `ReportArtifact` linking headline numbers directly to raw measurement traces, environment fingerprints, cost disclosure, and verification records.
- **Actual Behavior:** **ABSENT.** `src/slokern/engine/reporting/report_builder.py` and `templates/report.md.jinja` are empty docstrings.
- **Evidence:** `src/slokern/engine/reporting/report_builder.py:L1-4@52a0889`.
- **Dependencies:** `SUB-02` (Contracts), `SUB-08` (Run artifacts), `SUB-09` (Verification).
- **Risks:** Inability to publish inspectable proof for hackathon submission (P1 Blocker BLK-09).
- **Next Testable Step:** Implement a builder that formats a valid `ReportArtifact` instance into a human-readable Markdown summary. Acceptance: `tests/unit/engine/reporting/test_report_builder.py` passes.

### SUB-11: Control Plane API & CLI
- **Intended Behavior:** FastAPI application with SSE streaming endpoints; CLI tool (`slokern verify`, `slokern optimize`, `slokern smoke-test`).
- **Actual Behavior:** **ABSENT.** `src/slokern/api/app.py`, `src/slokern/cli/main.py`, and all command files are empty docstrings. No CLI scripts are registered in `pyproject.toml`.
- **Evidence:** `src/slokern/api/app.py:L1-4@52a0889`, `src/slokern/cli/main.py:L1-4@52a0889`, `pyproject.toml:L1-40@52a0889`.
- **Dependencies:** `SUB-08` (Runner), `SUB-09` (Verification), `SUB-10` (Reporting).
- **Risks:** Lack of user execution entry points.
- **Next Testable Step:** Freeze FastAPI as DEFERRED; implement minimal CLI entry point for `slokern verify` using Python standard library (`argparse`). Acceptance: `slokern --help` executes and exits code 0.

### SUB-12: Frontend Command Center & Presentation
- **Intended Behavior:** React + Vite cyber-technical command center visualizing specifications, live run progress, comparisons, and report badges.
- **Actual Behavior:** **ABSENT / SKELETON-ONLY.** All 22 files in `frontend/src/` are 88–141 byte placeholder comments. `package.json` contains no dependencies, no devDependencies, and no build scripts. No lockfile exists. No mock data exists.
- **Evidence:** `frontend/package.json:L1-8@52a0889`, `frontend/src/main.tsx:L1-3@52a0889`, probe P-20.
- **Dependencies:** SUB-11 (API).
- **Risks:** Building a full React frontend in remaining 9 days will consume all sprint bandwidth.
- **Next Testable Step:** **FREEZE AS OUT OF MVP SCOPE / DEFERRED.** All verification evidence and demo deliverables will be presented via static Markdown reports and CLI output.

### SUB-13: CI/CD, Packaging & Test Automation
- **Intended Behavior:** Production-quality GitHub Actions workflow enforcing linting, static typing, dependency checks, test execution, and contract drift checks; clean reproducible packaging.
- **Actual Behavior:** `ci.yml` runs `pip install -e ".[dev]"`, `pip check`, `compileall`, and `pytest -v -m "not live"`. However, CI does NOT run linting, static type checking (mypy), contract schema generation, or secret scanning. Build tooling lacks `wheel` in venv. Working tree has uncommitted `README.md` modification (BLK-14).
- **Evidence:** `.github/workflows/ci.yml:L1-58@52a0889`, command runs R-01, R-04, R-05, R-10, R-11.
- **Dependencies:** None.
- **Risks:** Regressions escaping into `main` due to incomplete CI test matrix.
- **Next Testable Step:** Revert or commit `README.md` to restore a clean working tree; add `wheel` to `build-system.requires` or local setup instructions. Acceptance: Clean `git status --porcelain` and reproducible editable install.

---

## 4. Contract Matrix & Pipeline Stages

### 4.1 Contract Audit Matrix (`A`)

| Contract Model | Defined in Code | Exported in `__init__` | Consumed Outside Tests | Tests Present in Repo | Round-Trip Match (P-18) | Schema Valid (P-17) | Extra Fields Policy (P-19) | Units Explicit |
|---|---|---|---|---|---|---|---|---|
| `WorkloadSpec` | `spec.py:L12` | Yes | No (0 files) | Valid + Invalid (`test_schemas.py`) | True | True | `ignore` (BLK-12) | Yes (`requests/s`, `s`, `tokens`) |
| `SLOSpec` | `spec.py:L34` | Yes | Yes (`evaluate.py`) | Valid (`test_schemas.py`) | True | True | `ignore` (BLK-12) | Yes (via `SLOConstraint.unit`) |
| `CandidateConfig` | `config.py:L11` | Yes | Yes (`space.py`) | None | True | True | `ignore` (BLK-12) | Yes (settings dictionary) |
| `ExperimentSpec` | `spec.py:L52` | Yes | No (0 files) | None | True | True | `ignore` (BLK-12) | Yes (`seconds`, `multiplier`) |
| `RunRecord` | `run.py:L11` | Yes | No (0 files) | None | True | True | `ignore` (BLK-12) | Yes (ISO microsecond timestamps) |
| `RawRequestMeasurement`| `evidence.py:L11` | Yes | No (0 files) | Valid (`test_schemas.py`) | True | True | `ignore` (BLK-12) | Yes (epoch seconds, token counts)|
| `MetricSet` | `metrics.py:L22` | Yes | Yes (`evaluate.py`, `rank.py`) | Serialization (`test_schemas.py`) | True | True | `ignore` (BLK-12) | Yes (`ms`, `rps`, `tps`, fraction) |
| `FeasibilityResult` | `verdict.py:L24` | Yes | Yes (`evaluate.py`) | Valid (`test_schemas.py`) | True | True | `ignore` (BLK-12) | Yes (preserves constraint units) |
| `SearchResult` | `search.py:L18` | Yes | No (0 files) | None | True | True | `ignore` (BLK-12) | Yes (objective enum, metrics) |
| `VerificationRecord` | `verification.py:L19`| Yes | No (0 files) | None | True | True | `ignore` (BLK-12) | Yes (drift percent, IDs) |
| `ReportArtifact` | `report.py:L27` | Yes | No (0 files) | None | True | True | `ignore` (BLK-12) | Yes (embedded specs & metrics) |

---

### 4.2 Pipeline Stage Execution Reality

```mermaid
flowchart LR
    S0[Stage 0: Spec & Contracts\nIMPLEMENTED] --> S1[Stage 1: Serving Preflight\nABSENT / STUB]
    S1 --> S2[Stage 2: Loadgen & Event Capture\nABSENT / STUB]
    S2 --> S3[Stage 3: Metrics Derivation\nABSENT / STUB]
    S3 --> S4[Stage 4: Feasibility Evaluator\nIMPLEMENTED]
    S4 --> S5[Stage 5: Candidate Ranking\nIMPLEMENTED]
    S5 --> S6[Stage 6: Independent Verification\nABSENT / STUB]
    S6 --> S7[Stage 7: Report Publishing\nABSENT / STUB]

    classDef done fill:#1f3a2d,stroke:#4ade80,color:#fff;
    classDef absent fill:#3b1d1d,stroke:#f87171,color:#fff;
    class S0,S4,S5 done;
    class S1,S2,S3,S6,S7 absent;
```

| Stage | Pipeline Function | Implemented Module | Current Reality | Verification Status | Real Pipeline Blockage |
|---|---|---|---|---|---|
| **0. Spec** | Workload & SLO contract specification | `src/slokern/contracts/` | Implemented; Pydantic v2 schemas valid. | `UNIT` (pass) | Operational. |
| **1. Serving** | Runtime configuration & preflight check | `src/slokern/engine/serving/` | **ABSENT.** Skeletons only; no fake or live adapter. | `NONE` | **PIPELINE STOPS HERE.** Cannot initialize serving runtime. |
| **2. Loadgen** | Traffic generation & raw JSONL capture | `src/slokern/engine/loadgen/` | **ABSENT.** Skeletons only; no dispatch loop. | `NONE` | Blocked by Stage 1. Cannot generate or record requests. |
| **3. Metrics** | Raw events to `MetricSet` aggregation | `src/slokern/core/metrics/` | **ABSENT.** Skeletons only; no percentile calculations. | `NONE` | Blocked by Stage 2. Cannot aggregate measurements. |
| **4. Evaluator**| Feasibility verdict vs hard SLO constraints | `src/slokern/core/evaluator/` | Implemented in memory; 24 unit tests pass. | `UNIT` (pass) | Operational in memory if passed pre-built `MetricSet`. |
| **5. Ranking** | Feasible candidate sorting by objective | `src/slokern/core/search/` | Implemented in memory; deterministic ranking verified. | `UNIT` (pass) | Operational in memory if passed evaluated candidates. |
| **6. Verification**| Independent rerun under fresh run ID | `src/slokern/core/verification/` | **ABSENT.** Skeletons only; no drift comparison logic. | `NONE` | Blocked by Stage 1 & Stage 5. No rerun orchestrator. |
| **7. Report** | Publish self-contained evidence artifact | `src/slokern/engine/reporting/` | **ABSENT.** Skeletons only; no Markdown builder. | `NONE` | Blocked by Stage 6. No report output. |

---

## 5. Claims Ledger

| Claim ID | Completion Claim Text | Source Document | Audit Finding | Verified Evidence / Reality |
|---|---|---|---|---|
| **CLM-01** | *"Fake Serving Adapter: IMPLEMENTED (src/slokern/engine/serving/fake.py generates deterministic synthetic runs)."* | `README.md:253` | **CONTRADICTED** | `fake.py` is a 4-line empty docstring (`L1-4@52a0889`). It generates zero synthetic runs. |
| **CLM-02** | *"Demo Dashboard UI: IMPLEMENTED (React + Vite command center in frontend/; offline fixtures labeled DEMO DATA)."* | `README.md:258` | **CONTRADICTED** | All 22 files in `frontend/` are 88–141 byte comment skeletons. `package.json` contains no dependencies or scripts. No mock data exists (P-20). |
| **CLM-03** | *"1. Model-Agnostic Core: VERIFIED (Contracts, evaluator, load generator, and search controllers are model-agnostic)."* | `README.md:181` | **CONTRADICTED** | Load generator is absent (`runner.py:L1-4@52a0889`). Search controller is ranker only. Not verified. |
| **CLM-04** | *"Subsystem Modules: IMPLEMENTED (STUBS) (api/, cli/, core/, engine/ scaffolded with clear typed signatures)."* | `README.md:252` | **CONTRADICTED** | Files in `api/`, `cli/`, `engine/` contain only 2-line module docstrings without class or function signatures. |
| **CLM-05** | *"Phase A (Oct 19) - Audit and Scope Freeze: DONE (Repository audit completed; working baseline established; core interfaces locked)."* | `README.md:370` | **CONTRADICTED** | Audit was never executed on Oct 19. Being executed today on Oct 21. |
| **CLM-06** | *"Phase A | Oct 19 | Audit and scope freeze | DONE / VERIFIED"* | `ROADMAP.md:236` | **CONTRADICTED** | Fake adapter claimed verified, but `fake.py` is an empty stub. |
| **CLM-07** | *"Gate A: Scope & Baseline Oct 19 DONE"* | `ROADMAP.md:441` | **CONTRADICTED** | Gate A was never verified with physical evidence. |
| **CLM-08** | *"- [x] Deterministic fake adapter verified for offline development."* | `ROADMAP.md:451` | **CONTRADICTED** | Checkbox checked in roadmap, but `fake.py` has no code and `test_pipeline_fake_adapter.py` is an empty stub. |
| **CLM-09** | *"Serving Adapter ... IN PROGRESS (Rajdeep)"* | `ROADMAP.md:507` | **CONTRADICTED** | All files in `src/slokern/engine/serving/` are 4-line empty stubs. Zero implementation commits exist. |
| **CLM-10** | *"Loadgen Subprocess ... IN PROGRESS (Rajdeep)"* | `ROADMAP.md:508` | **CONTRADICTED** | All files in `src/slokern/engine/loadgen/` are empty stubs. Zero implementation commits exist. |
| **CLM-11** | *"Search & Ranker ... IN PROGRESS (Rajdeep)"* | `ROADMAP.md:511` | **CONFIRMED** | `candidate_id.py`, `rank.py`, and `space.py` exist and pass unit tests (P-11 to P-16). |
| **CLM-12** | *"Data Contracts: IMPLEMENTED (Pydantic v2 schemas in src/slokern/contracts/)."* | `README.md:251` | **CONFIRMED** | All 11 models defined, exported, compile, pass schema generation and round-trip tests (P-17, P-18). |
| **CLM-13** | *"Adriraj active execution begins October 21, 2026."* | `docs/ownership.md:19` | **UNVERIFIABLE** | Claim of human availability cannot be verified from repository artifacts. |
| **CLM-14** | *"Daksh active execution begins October 24, 2026."* | `docs/ownership.md:20` | **UNVERIFIABLE** | Claim of human availability cannot be verified from repository artifacts. |

---

## 6. Blockers Register

| Blocker ID | Priority | Evidence | Actual Consequence | Affected Subsystems | Accountable Owner | Smallest Remediation | Closing Test |
|---|---|---|---|---|---|---|---|
| **BLK-01** | **P0** | `src/slokern/engine/serving/fake.py:L1-4@52a0889` & `nebius.py:L1-4` are empty docstrings. | System cannot execute any serving requests locally or live. Blocks Stage 1 & Stage 2. | SUB-05, SUB-08 | Rajdeep | Implement `FakeServingAdapter` generating deterministic synthetic responses. | `tests/integration/test_pipeline_fake_adapter.py` |
| **BLK-02** | **P0** | `src/slokern/engine/loadgen/runner.py:L1-4@52a0889` is an empty docstring. | Cannot dispatch requests or record raw `RawRequestMeasurement` event traces. Blocks Stage 2. | SUB-06, SUB-08 | Rajdeep | Implement minimal dispatch loop writing unaggregated JSONL recordings. | `tests/unit/engine/loadgen/test_runner.py` |
| **BLK-03** | **P0** | `src/slokern/core/metrics/percentiles.py:L1-4@52a0889` is an empty docstring. | Cannot calculate `MetricSet` from raw event traces. Blocks Stage 3 and feeds into Evaluator. | SUB-07, SUB-08 | Rajdeep | Implement standard library percentile and throughput calculators. | `tests/unit/core/metrics/test_percentiles.py` |
| **BLK-04** | **P0** | `tests/live/test_smoke_live.py:L12@52a0889` skips; exact Nebius API model string unverified. | Cannot run live compliance benchmark on Nebius Cloud. Blocks Stage 1 on live infra. | SUB-05 | Rajdeep | Execute live preflight probe using `curl` or single-request script with valid API key. | `tests/live/test_smoke_live.py` (live run) |
| **BLK-05** | **P1** | Probe P-05: `float('nan') <= 200.0` returns `False`, yielding `INFEASIBLE` with `TTFT_P95_EXCEEDED`. | Corrupted or uncalculable floating-point evidence is misclassified as an SLO threshold breach instead of inconclusive evidence. | SUB-03 | Rajdeep | Add `math.isnan(obs_val)` check in `evaluate.py` to route NaN to `INCONCLUSIVE`. | `tests/unit/core/test_evaluator.py::test_evaluator_nan_inconclusive` |
| **BLK-06** | **P1** | Probe P-06: `-10.0 <= 200.0` returns `True`, yielding `FEASIBLE` with `HARD_CONSTRAINTS_PASSED`. | Physically impossible negative latency passes feasibility checks without rejection. | SUB-03 | Rajdeep | Add physical non-negative constraint assertion (`obs_val >= 0`) in `evaluate.py`. | `tests/unit/core/test_evaluator.py::test_evaluator_negative_latency_invalid` |
| **BLK-07** | **P1** | `docs/ownership.md:L41-49@52a0889` lists Rajdeep as accountable for 9 of 13 subsystems (69% concentration). | Severe delivery bottleneck on Rajdeep; collaborator workstreams are delayed until Oct 21 and Oct 24. | SUB-01 through SUB-13 | Rajdeep | Freeze scope strictly to CLI + static Markdown report; defer API and Frontend. | Ratified `ROADMAP.md` with explicit deferred tags. |
| **BLK-08** | **P1** | `src/slokern/core/verification/compare.py:L1-4@52a0889` is an empty docstring. | Cannot independently verify selected winning candidates or compute metric drift ($\Delta M$). Blocks Stage 6. | SUB-09 | Rajdeep | Implement deterministic drift calculation and pass/fail evaluation comparing two `MetricSet`s. | `tests/unit/core/verification/test_compare.py` |
| **BLK-09** | **P1** | `src/slokern/engine/reporting/report_builder.py:L1-4@52a0889` is an empty docstring. | Cannot publish immutable `ReportArtifact` for hackathon submission evidence. Blocks Stage 7. | SUB-10 | Rajdeep | Implement Markdown builder serializing `ReportArtifact` into an inspectable document. | `tests/unit/engine/reporting/test_report_builder.py` |
| **BLK-10** | **P1** | `schemas/` contains only `.gitkeep`; `scripts/gen_contracts.py:L17@52a0889` is a gap notice. | No emitted JSON Schemas exist in source control; cannot validate external tooling against contracts. | SUB-02 | Rajdeep | Implement script exporting `model_json_schema()` for all 11 models into `schemas/`. | `tests/contract/test_generated_files_current.py` |
| **BLK-11** | **P2** | Probe P-12: `{"tensor_parallel_size": 1}` vs `1.0` produces different candidate IDs (`4fe93deaf8d0` vs `cd0ce0cb5b73`). | Inadvertent type coercion between float and integer changes candidate hash identity. | SUB-04 | Rajdeep | Enforce canonical integer/float normalization before hashing in `candidate_id.py`. | `tests/unit/core/test_ranker.py::test_candidate_id_float_int_equivalence` |
| **BLK-12** | **P2** | Probe P-19: All 11 models accept unrecognized fields silently (`extra='ignore'`). | Contracts do not strictly reject invalid or misspelled fields at system boundaries. | SUB-02 | Rajdeep | Add `model_config = ConfigDict(extra='forbid')` to all 11 contract classes. | `tests/contract/test_schemas.py::test_extra_fields_forbidden` |
| **BLK-13** | **P2** | `.github/workflows/ci.yml:L1-58@52a0889` lacks linting, type checks, schema drift, and secret scanning steps. | Code regressions, typing errors, or secret leaks can bypass CI unnoticed. | SUB-13 | Rajdeep | Add `ruff check`, `mypy --strict src/slokern`, and secret scanning checks to `ci.yml`. | `.github/workflows/ci.yml` execution in GitHub Actions |
| **BLK-14** | **P2** | Git preflight R-01: `README.md` is modified in the working tree (uncommitted badge modification). | Working tree baseline is not clean (`NOT CLEAN-BASELINE`), preventing clean clone verification. | SUB-13 | Rajdeep | Commit or revert the `README.md` change. | `git status --porcelain` returning clean |

---

## 7. Scope Freeze (The MVP Boundary)

### 7.1 Scope Matrix Per Pipeline Stage

| Stage | Capability Description | Subsystem | Status | Depends On | Acceptance Criterion | Scope Verdict |
|---|---|---|---|---|---|---|
| **0. Specification** | Declarative WorkloadSpec and hard SLOSpec via Pydantic v2 | SUB-02 | `IMPLEMENTED` | None | Schemas compile, roundtrip validate, and reject invalid enums. | **IN** |
| **1. Serving Preflight** | Deterministic FakeServingAdapter for offline synthetic testing | SUB-05 | `ABSENT` | DEC-01 | Single request returns synthetic completion and simulated timestamps labeled DEMO DATA. | **IN (CRITICAL)** |
| **1. Serving Runtime** | Nebius Cloud serving adapter for live benchmark execution | SUB-05 | `ABSENT` | DEC-01, BLK-04 | Authenticates via `NEBIUS_API_KEY`, issues request to `Nemotron-3-Nano-30B-A3B`, returns response. | **IN (CRITICAL)** |
| **2. Load Generation** | Subprocess load generator with Poisson and constant arrival | SUB-06 | `ABSENT` | BLK-02 | Dispatches requests according to target offered rate and records raw events to JSONL. | **IN (CRITICAL)** |
| **2. Client Saturation** | Client thread starvation and saturation detection | SUB-06 | `ABSENT` | BLK-02 | Flags `generator_saturated = True` when client loop lag exceeds 10% of dispatch interval. | **IN (CRITICAL)** |
| **3. Metrics Derivation** | Derive TTFT/ITL percentiles (p50, p95, p99), throughput, error rate | SUB-07 | `ABSENT` | BLK-03 | Produces valid `MetricSet` from unaggregated JSONL recordings. | **IN (CRITICAL)** |
| **4. Feasibility Audit** | Deterministic hard SLO constraint evaluation with reason codes | SUB-03 | `IMPLEMENTED` | BLK-05 | Emits `FeasibilityResult` with FEASIBLE, INFEASIBLE, or INCONCLUSIVE verdict. | **IN** |
| **5. Candidate Search** | Bounded 2×2 grid search (4 candidates + 1 baseline = 5 runs) | SUB-04, SUB-08 | `PARTIAL` | SUB-05 | Evaluates exactly 5 runs without exceeding declared 6-run experiment budget. | **IN (CRITICAL)** |
| **5. Ranking** | Deterministic candidate ranking by Mode B proxy or Mode A cost | SUB-04 | `IMPLEMENTED` | SUB-03 | Lowest cost/proxy feasible candidate selected with candidate-ID tie-breaking. | **IN** |
| **6. Verification** | Independent rerun of winning candidate under fresh run ID | SUB-09 | `ABSENT` | BLK-08 | Re-evaluates candidate under distinct `verification_run_id`, computes drift $\Delta M$. | **IN (CRITICAL)** |
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
4. Subprocess load generator executes each run, capturing unaggregated microsecond timings to JSONL traces.
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

