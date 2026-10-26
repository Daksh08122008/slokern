# SLOKern MVP Scope & Acceptance Checklist

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Reference / Scope Boundary (Strict Solo Execution)  
> **Sole Accountable Owner:** Rajdeep  
> **Authority:** Aligned with [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [docs/ownership.md](ownership.md)

---

## 1. Product Promise & Mission Boundary

SLOKern accepts a declared workload profile and service-level objectives (SLOs), benchmarks a bounded set of legal serving configurations, identifies the lowest-cost configuration that satisfies the declared constraints, and independently verifies the recommendation.

### Core Operating Principle

> **One model, one serving environment, a small configuration space, reproducible experiments.**

Every task in the project is evaluated against whether it advances this core end-to-end chain. Features outside this chain are deferred.

---

## 2. In-Scope vs. Out-of-Scope (Non-Goals)

### In-Scope for the Hackathon MVP

1. **One Permitted Model:** Accepted model-family candidate is `Nemotron-3-Nano-30B-A3B` FP8; exact checkpoint/tokenizer revision and endpoint identifier remain pending. `meta-llama/Meta-Llama-3-8B-Instruct` is an internal pipeline baseline only.
2. **One Serving Runtime:** Proposed Nebius AI Cloud Serverless custom container running vLLM 0.12.0 on H100; Docker GPU VM is a fallback. Both require account, image, model, and effective-flag preflight before being called operational.
3. **One Reproducible Workload Protocol:** A fixed prompt fixture with explicit arrival distributions (Poisson or constant rate) and separate warm-up and measurement windows.
4. **Small Legal Search Space:** The proposed 5-point profile is baseline `(max_num_seqs=128, max_num_batched_tokens=8192)` plus four corners `{64, 256} × {2048, 16384}`. Current code instead generates four candidates `{16, 64} × {1024, 2048}`; do not mark the proposed profile accepted until DEC-0013 and adapter read-back are resolved.
5. **Offered vs. Achieved Load Separation:** Clear architectural distinction and measurement of intended traffic rate versus actual delivered rate.
6. **Key Inference Metrics:** Deterministic calculation of TTFT, ITL (with defined aggregation), end-to-end latency, request throughput, output-token throughput, error rate, and percentiles (p50, p90, p95, p99).
7. **Deterministic Feasibility Evaluator:** Auditable constraint-by-constraint rule engine returning `FEASIBLE`, `INFEASIBLE`, or `INCONCLUSIVE` with structured reason codes.
8. **Baseline + Bounded Search:** Reference run compared against a transparent, budget-capped search controller (6 benchmark runs total).
9. **Independent Verification Run:** Mandatory rerun of the selected candidate under a fresh `verification_run_id` to confirm reproducibility.
10. **Evidence Artifacts & Dashboard:** Structured JSON/JSONL raw measurement records, an inspectable Markdown/JSON report, and a command center dashboard reflecting actual backend state (with prototype fixtures clearly labelled **DEMO DATA**).

### Explicit Non-Goals (Out of Scope for MVP)

- **No Universal Serving Support:** No support for multiple disparate runtimes, heterogeneous multi-cloud deployments, or arbitrary model architectures.
- **No Unbounded Search or Global Optimality Claims:** No heuristic searching over infinite parameter spaces; no claims that the selected configuration is universally optimal for all future workloads.
- **No Production Auto-Tuning:** No automatic modification of live production deployments or cluster autoscaling.
- **No Statistical Over-Claiming:** No claiming that a single benchmark sample represents universal ground truth without disclosing uncertainty.
- **No Priority Inversion for AI Extras:** No work on LLM-based prompt planners or natural language explainers until the deterministic measurement, search, and verification pipeline works end-to-end.
- **No Fabricated Data or Numbers:** Never presenting mock fixtures, synthetic test results, or estimated cost numbers as measured live facts.

---

## 3. Acceptance Gates (Phase Exit Criteria)

Project advancement is governed by evidence, not elapsed calendar days. A gate is passed only when its required evidence is committed and verified.

### Gate A — Scope Locked & Baseline Established (Completed: Oct 19 Baseline)
- [x] One model/runtime path selected as compliance target (`Nemotron-3-Nano-30B-A3B` FP8 on Nebius; pending smoke test).
- [x] MVP scope, non-goals, and operating principles written and acknowledged.
- [x] Shared schemas (`WorkloadSpec`, `SLOSpec`, `CandidateConfig`, `RunRecord`, `MetricSet`, `FeasibilityResult`, `SearchResult`, `VerificationRecord`, `ReportArtifact`) defined in `src/slokern/contracts/`.
- [x] Experiment budget (strict 6 benchmark runs) and stopping limits defined.
- [x] Consolidated strict solo-development and solo-execution model established in `docs/ownership.md`.

### Gate B — Serving Path & Baseline Measured (Target: End of Oct 22 — Offline Complete, Live Pending)
- [ ] Dedicated model endpoint responds reliably to live preflight smoke inference request (`scripts/smoke.py`) (HTTP client in `nebius.py` implemented; live run pending credentials).
- [ ] Effective runtime, model revision, and hardware environment fingerprint captured.
- [ ] Mutable serving parameters documented and confirmed by runtime read-back tests (`BLK-17`).
- [x] Single-run execution pipeline operational with deterministic fake adapter (`SingleRunExecutor` writes JSON metadata and JSONL raw traces).
- [ ] Live empirical baseline run executed on Nebius GPU instance; raw JSONL stream and metrics captured.
- [x] Automated benchmark integrity validation suite operational on result records (`test_fixtures_validate.py`).
- [x] Zero API keys, tokens, or private endpoint credentials committed to source control or logs.

### Gate C — Bounded Optimization Validated (Target: End of Oct 25 — Active / In Progress)
- [x] Bounded 2×2 search space controller implemented (`GridSearchController`, `SearchSpace`, `BudgetLimiter`, 33 unit tests; caveat `BLK-15`).
- [x] Subprocess load generator logs granular `RawRequestMeasurement` records (JSONL) with client timestamps.
- [x] Metrics engine derives documented metrics with explicit units and sample counts.
- [x] Offered load and achieved load are reported separately; generator saturation is detected.
- [x] Deterministic feasibility evaluator produces `FEASIBLE`, `INFEASIBLE`, and `INCONCLUSIVE` verdicts with structured reason codes.
- [x] Lowest-cost feasible candidate selected under declared objective (`CandidateRanker`).
- [x] Automated decision-verification contract test suite operational on hard SLO boundaries (16 passed tests in `tests/contract/test_verification_independence.py`).


### Gate D — Independent Evidence Reviewed (Target: End of Oct 27)
- [ ] Selected winning candidate configuration rerun independently under a fresh, distinct `verification_run_id`.
- [ ] Identical workload protocol and environment conditions applied; metrics computed afresh without caching.
- [ ] Drift analysis computed ($\Delta M$); final verification verdict emitted (`VERIFIED` or failed).
- [ ] Critical correctness defects closed with automated regression tests.
- [ ] Complete `ReportArtifact` compiled with raw evidence links.

### Gate E — Release Candidate & Demo Frozen (Target: End of Oct 29)
- [ ] Clean setup from repository documentation succeeds on an independent machine (`pip install -e .`).
- [ ] Full automated test suite passes across contracts, evaluator, search, and load generator.
- [ ] All headline performance and cost figures reconcile with raw source artifacts.
- [ ] Full $\le 3\text{-minute}$ walkthrough presentation and demo recorded and uploaded.
- [ ] Demo fallback runbook verified with persistent **`DEMO DATA`** labels.

### Gate F — Final Submission Delivered (Target: Oct 30)
- [ ] Final repository audit completed (no secrets, Apache 2.0 license).
- [ ] Devpost form submitted with demo video, repo link, and mandatory Nebius/NVIDIA tool feedback.
- [ ] Submission confirmed prior to **October 30, 2026, 10:00 AM PDT (10:30 PM IST)** with 4-hour buffer.

---

## 4. Definition of Done (DoD)

A deliverable or milestone is marked **DONE** only when:

1. **Contract Conformance:** Data models match the agreed Pydantic v2 schemas in `src/slokern/contracts/`.
2. **Defensive Validation:** Inputs are validated at system boundaries; malformed payloads fail safely with actionable errors.
3. **Automated Test Evidence:** Relevant unit or contract tests pass, with test outputs recorded.
4. **Deterministic Auditing:** Feasibility verdicts and rankings are derived mathematically from evidence, not opaque scores.
5. **Traceable Provenance:** Every metric in a report links to raw event measurements and an environment fingerprint.
6. **No Fabricated Success:** Inconclusive runs and failed runs are never colored green; synthetic prototype data is labelled **DEMO DATA**.
7. **Clean Secrets:** No credentials, private IP addresses, or secrets exist in source code, fixtures, or committed artifacts.
8. **Reproducibility:** A teammate can execute the workflow following only repository documentation.

---

## 5. Stop-the-Line Escalation Triggers
 
Execution must pause and trigger immediate remediation if:

1. **Endpoint Inaccessible:** The serving runtime cannot be contacted or deployed by the milestone deadline (switch to compliant fallback).
2. **Missing Timings:** The runtime API does not expose first-token or per-token timings required for TTFT/ITL (restrict SLO scope honestly; do not invent values).
3. **Unconfirmed Parameters:** A serving parameter in the search space does not produce an observable effect in read-back or benchmark behavior (remove parameter from search space).
4. **Generator Saturation:** The load generator cannot deliver the target arrival rate (reduce rate or fix loadgen; do not credit the server with low latency under deflated load).
5. **Cost Source Missing:** Verifiable monetary pricing is unavailable (declare monetary cost `unavailable` and optimize for resource-time or throughput under SLO).
6. **Verification Collapsed:** Verification is implemented as a cache read of the search run rather than a true independent execution.
7. **Frontend Distraction:** Dashboard aesthetic polish threatens the completion of the core measurement and verification pipeline.

---

## 6. Related Documentation

- [System Architecture](architecture.md)
- [Engineering Ownership & Execution Model](ownership.md)
- [Architecture Decision Log](decision-log.md)
- [Daily Integration Checklist](integration-checklist.md)
- [ADR 0001: MVP Scope & Evidence Policy](adr/0001-mvp-scope-and-evidence.md)

