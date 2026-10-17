# SLOKern — Execution Roadmap
### Daily work plan, ownership, dependencies, acceptance gates, and submission readiness

> **Mission:** Deliver a defensible end-to-end SLO-aware inference optimizer—not merely a polished dashboard—by proving that a bounded search can measure candidates, apply deterministic SLO rules, select a candidate, and independently verify it.

**Planning window:** October 13–30, 2026  
**Primary implementation window:** October 13–29  
**Submission-day buffer:** October 30  
**Owners:** Rajdeep (technical lead/architecture), Aman (serving/GPU infrastructure), Daksh (verification/evaluation), Adriraj (benchmarking), Rohan (optimization/search)

> [!IMPORTANT]
> Dates are a proposed sprint plan based on the project context and recorded hackathon deadline. Confirm the official deadline, timezone, platform requirements, model rules, and submission format immediately. The deadline recorded by the team is **October 30, 2026, 10:00 AM PDT = October 30, 2026, 10:30 PM IST**. If the official deadline differs, rebase this schedule.
>
> This plan does **not** assert that the listed implementation work is already complete. At the start of each day, mark each task `TODO`, `IN PROGRESS`, `BLOCKED`, or `DONE` with a PR, commit, artifact, or test as evidence.

---

## Contents

1. [Operating rules](#1-operating-rules)
2. [Roles and non-overlapping ownership](#2-roles-and-non-overlapping-ownership)
3. [Critical path](#3-critical-path)
4. [Phase map](#4-phase-map)
5. [Daily sprint plan](#5-daily-sprint-plan)
6. [Daily integration ritual](#6-daily-integration-ritual)
7. [Shared contracts and handoffs](#7-shared-contracts-and-handoffs)
8. [Acceptance gates](#8-acceptance-gates)
9. [Experiment protocol and proof of value](#9-experiment-protocol-and-proof-of-value)
10. [Testing matrix](#10-testing-matrix)
11. [Demo and submission plan](#11-demo-and-submission-plan)
12. [Risk register and contingency decisions](#12-risk-register-and-contingency-decisions)
13. [Definition of done](#13-definition-of-done)
14. [Daily stand-up template](#14-daily-stand-up-template)
15. [Decision log template](#15-decision-log-template)

---

## 1. Operating rules

### 1.1 The product promise is the scope boundary

SLOKern accepts a defined workload and SLO, measures a bounded set of legal serving configurations, identifies the best evidenced feasible candidate under a declared objective, and independently verifies it—or reports that no tested configuration was proven feasible.

The core promise requires:

1. one supported model;
2. one working serving environment;
3. one reproducible workload;
4. a small configuration space;
5. raw measurement artifacts;
6. deterministic feasibility evaluation;
7. candidate search and selection;
8. a fresh verification run;
9. a report that makes the result inspectable.

Everything else is secondary until this chain works.

### 1.2 Work in dependency order

The order is non-negotiable:

`Serving smoke test → valid single-run measurements → deterministic evaluator → baseline → bounded candidate search → selection → independent verification → dashboard/report integration → polished demo`

The dashboard may be developed in parallel with mock fixtures, but it must not delay the real measurement path. AI-assisted planning is optional and should be cut before any core milestone.

### 1.3 No unsupported claims

- Do not invent benchmark numbers.
- Do not call synthetic fixtures “live results.”
- Do not claim cost savings without a disclosed cost source and assumptions.
- Do not call a candidate “verified” before an independent run passes.
- Do not call the result globally optimal.
- Do not expose a tuning control unless the serving adapter can apply and confirm it.
- Do not hide failed candidates or contaminated runs.

### 1.4 Definition of a task being done

A task is `DONE` only when the deliverable exists, runs or validates, and has evidence. “Code written” is not enough.

Acceptable evidence includes:
- a merged pull request or commit;
- a passing test command and output;
- a reproducible artifact;
- a screenshot for visual-only work;
- a documented blocker and fallback decision for unavailable external infrastructure.

### 1.5 Daily effort allocation

Each person should aim for one primary deliverable and one review/integration duty per day. Avoid five people editing the same files. A short end-of-day integration window is mandatory.

Recommended daily rhythm:
- **Start (10–15 min):** blockers, today's single highest-value deliverable, dependency check.
- **Build block:** individual ownership work.
- **Integration checkpoint (15–25 min):** interface review, PRs, tests, smoke check.
- **End-of-day update (5–10 min):** evidence, remaining risks, next handoff.

---

## 2. Roles and non-overlapping ownership

| Owner | Accountable for | Owns | Must hand off |
|---|---|---|---|
| **Rajdeep — Technical Lead / Architecture** | System coherence and final product promise | Scope, architecture decisions, shared schemas, deterministic policy contract, integration, API/dashboard alignment, final demo narrative | Stable interfaces, acceptance criteria, integrated build, final claims/evidence review |
| **Aman — Serving / GPU Infrastructure** | Reliable model execution and configuration application | Model/runtime selection, deployment, serving adapter, environment fingerprint, supported tuning controls, resource cleanup | Healthy endpoint, verified configuration apply/read-back, environment metadata and failure modes |
| **Daksh — Verification / Evaluation** | Correctness of SLO decisions and winner verification | Feasibility evaluator, reason codes, boundary tests, verification-run orchestration/policy, evidence audit | Versioned verdict schema, evaluator tests, independent verification report |
| **Adriraj — Benchmarking** | Trustworthiness of workload generation and measurements | Workload fixtures, arrival pattern, load generator, request-level timings, metric calculations, run-validity flags | Raw measurement schema, benchmark artifacts, metric definitions and test fixtures |
| **Rohan — Optimization / Search** | Candidate generation and search policy | Legal search-space definition, candidate IDs, baseline search, adaptive strategy if justified, stopping conditions and selection rationale | Candidate manifest, search history, reproducible ranking and strategy comparison |

### Ownership guardrails

- Rajdeep owns architecture and integration, not every implementation detail.
- Aman alone decides which serving parameters are actually supported; Rohan may propose candidates but cannot invent controls.
- Adriraj owns measurement definitions and raw data quality; Daksh consumes those definitions to evaluate constraints.
- Daksh owns verdict semantics; Rohan cannot change pass/fail rules to make the optimizer look better.
- The frontend must consume shared schemas; it must not define its own incompatible interpretation of metrics.
- Every cross-component change requires notifying affected owners and updating contract tests.

---

## 3. Critical path

```text
[Freeze model/runtime + MVP]
              |
              v
[Stable shared contracts] <------ Rajdeep coordinates all owners
              |
              v
[Aman: endpoint + adapter]
              |
              v
[Adriraj: one valid benchmark artifact]
              |
              v
[Daksh: deterministic verdict]
              |
              v
[Rohan: multiple candidates + ranking]
              |
              v
[Daksh + Aman: fresh independent verification]
              |
              v
[Rajdeep: integrate UI/report + validate claims]
              |
              v
[Full rehearsal, fallback, submission]
```

### Parallel lanes that are safe

- Rajdeep can develop the dashboard against stable example contracts while Aman proves serving.
- Adriraj can implement metric calculations against synthetic test fixtures before the endpoint is available.
- Daksh can write evaluator boundary tests before real data arrives.
- Rohan can implement candidate canonicalization and search orchestration with a fake measurement adapter, then swap in the real adapter.
- No one should make synthetic values appear to be measured production data.

### Stop-the-line conditions

Escalate immediately if:
- the selected model/runtime is not accessible;
- the runtime cannot expose the required timing data;
- candidate settings cannot be applied and confirmed;
- the load generator cannot maintain the declared arrival pattern;
- cost inputs are unavailable but cost is being presented as measured fact;
- verification cannot run independently;
- the dashboard is consuming more time than the working experiment pipeline.

---

## 4. Phase map

The original 15 implementation phases are grouped into 10 delivery phases to fit the sprint without losing their intent.

| Delivery phase | Dates | Covers original phases | Exit condition |
|---|---|---|---|
| **P0 — Scope and contracts** | Oct 13 | 0–1 | Model/runtime target, MVP, schemas, owners and budget are explicit |
| **P1 — Serving path** | Oct 14–15 | 2 | A permitted model answers a smoke request; effective settings and environment can be recorded |
| **P2 — Measurement + evaluator** | Oct 16–17 | 3–4 | One benchmark produces raw data and a deterministic per-constraint verdict |
| **P3 — Baseline + candidate space** | Oct 18 | 5–6 | Baseline saved; legal candidates and stable IDs generated within budget |
| **P4 — Search + selection** | Oct 19–20 | 7–8 | Multi-candidate run produces a transparent ranking; adaptive search only if time/evidence justify it |
| **P5 — Independent verification + cost** | Oct 21 | 9–10 | Winner rerun under a new run ID; cost reported only if inputs support it |
| **P6 — Dashboard integration** | Oct 22–24 | 11 | Primary pages connected to actual contracts/state; demo data clearly labelled |
| **P7 — AI extras (conditional)** | Oct 25 | 12 | Optional AI-assisted draft/explanation only if all core gates already pass |
| **P8 — Hardening and reproducibility** | Oct 26–27 | 13 | Clean setup, tests, failure paths and demo rehearsal pass |
| **P9 — Submission and storytelling** | Oct 28–30 | 14 | Evidence checked, demo ready, submission sent before official deadline |

### Deadline policy

The final day is not for core architecture rewrites. By October 28, the team should have a feature freeze for the MVP. October 29 is for rehearsal and fixes. October 30 is reserved for final validation, upload, and submission buffer.

---

## 5. Daily sprint plan

Every day assigns a concrete responsibility to **all five members**. If a task is blocked by an external dependency, the owner must produce a testable mock, contract, or fallback—not wait silently.

### Day 1 — Tuesday, October 13
## P0: Freeze scope, runtime decision, and contracts

**Day outcome:** The team knows exactly what it is building and can work in parallel without incompatible assumptions.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Run a 30-minute scope lock. 2. Write the one-sentence product promise and MVP/non-goals. 3. Define initial lifecycle states and shared object names. 4. Create the decision log and integration checklist. 5. Assign file ownership and branch/PR rules. | `docs/architecture.md` draft, MVP checklist, owners, and decision log committed |
| **Aman** | 1. Verify access to the intended Nebius environment. 2. List viable permitted models/runtimes. 3. Select the lowest-risk supported path based on availability, API, and measurable timings. 4. Identify configurable parameters and known limitations. | Model/runtime decision proposal, access proof or explicit blocker, minimal environment notes |
| **Daksh** | 1. Define required SLO fields and verdict states. 2. Draft per-constraint reason codes. 3. Identify boundary cases: missing metrics, exact threshold, invalid run, noisy evidence. 4. Draft the independent-verification semantics. | `docs/decision-policy.md` outline and evaluator test cases |
| **Adriraj** | 1. Define workload fields and raw request record. 2. Choose the first fixed prompt fixture. 3. Specify warm-up/measurement windows and offered-vs-achieved load. 4. Draft metric definitions with units. | `docs/experiment-methodology.md` draft, fixture plan, raw event schema |
| **Rohan** | 1. Propose 2–4 realistic tunable dimensions, conditional on Aman confirming support. 2. Bound candidate count and total runtime. 3. Define canonical candidate identity. 4. Draft baseline-search behavior and stopping rules. | Search-space proposal with ranges, legality constraints, and budget |
| **Joint gate** | 20-minute review: agree model/runtime direction, MVP SLOs, schemas to freeze first, and exact blockers. | All five owners acknowledge interfaces; no unowned critical dependency |

**Do not do today:** build elaborate dashboard animations, add broad model support, or choose an optimizer before the measurement path is understood.

---

### Day 2 — Wednesday, October 14
## P1: Establish serving and schema skeleton

**Day outcome:** A minimal endpoint path exists, and shared contracts are concrete enough for implementation.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Finalize workload, configuration, run, benchmark-result, verdict, and verification object shapes. 2. Add schema versioning and status enums. 3. Create a minimal repository structure and CI/test entry points. 4. Review naming and units across contracts. | Contract files and one valid/one invalid fixture; CI runs basic validation |
| **Aman** | 1. Provision/configure the selected runtime. 2. Make one inference request. 3. Capture effective model/runtime identifiers and resource metadata. 4. Document auth, health check, timeout, and cleanup. | Smoke-test log with secret values redacted; exact runtime/model recorded |
| **Daksh** | 1. Write unit tests for verdict shape and reason codes. 2. Define execution states separately from feasibility states. 3. Add tests for missing required metrics and unsupported SLO fields. | Passing evaluator-contract tests |
| **Adriraj** | 1. Build a small versioned workload fixture. 2. Implement raw request-record serialization. 3. Add unit tests for request start, first-token, completion, errors and timeouts. | Fixture file and valid JSONL sample records |
| **Rohan** | 1. Define the first candidate schema. 2. Implement canonical configuration serialization and stable candidate IDs. 3. Add parameter validation scaffolding without assuming unsupported controls. | Candidate generator unit tests and sample candidate manifest |
| **Joint gate** | Review contract compatibility. Each owner demonstrates a serialized object or test. | No duplicate or contradictory field definitions |

---

### Day 3 — Thursday, October 15
## P1: Make serving reproducible and prove settings apply

**Day outcome:** A healthy endpoint can be called repeatedly, and the adapter can record the effective configuration.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Integrate contract validation into the main application path. 2. Add a small end-to-end skeleton that accepts a spec and returns a run state. 3. Review environment/secret handling. | Valid spec can be accepted; invalid spec rejected before execution |
| **Aman** | 1. Implement the smallest serving adapter. 2. Add health check and one-request smoke command. 3. Confirm which tuning values are truly mutable and how they are read back. 4. Record failure/timeout behavior. | Adapter smoke test; supported-control table; environment fingerprint |
| **Daksh** | 1. Implement the initial deterministic feasibility evaluator interface using test data. 2. Add exact-boundary tests. 3. Ensure unavailable measurements return inconclusive rather than false pass. | Unit tests pass for feasible/infeasible/inconclusive examples |
| **Adriraj** | 1. Implement a minimal load runner for a small number of requests. 2. Capture timestamps, status, input/output tokens when available, and errors. 3. Save raw records before aggregation. | A real endpoint run produces a raw artifact |
| **Rohan** | 1. Implement legal candidate validation and candidate manifest output. 2. Add a hard maximum candidate count. 3. Ensure unsupported parameter combinations are rejected before execution. | Candidate list reproducible from the same config |
| **Joint gate** | Run one real request through the adapter and save all metadata. | Smoke test passes twice from a clean process |

**Fallback if blocked:** If the intended hosted runtime is unavailable, immediately test an allowed alternate route that still satisfies the hackathon rules. Do not spend the rest of the sprint building against a fictional endpoint.

---

### Day 4 — Friday, October 16
## P2: Build the first valid benchmark

**Day outcome:** A single configuration produces raw measurements, aggregate metrics, and a run-validity assessment.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Wire spec → run creation → adapter → artifact path. 2. Add run IDs and immutable config snapshots. 3. Make failures visible in lifecycle state. | One run is traceable from specification to artifact |
| **Aman** | 1. Add adapter safeguards around timeouts and retries. 2. Verify effective configuration before/after each run where possible. 3. Capture runtime restart or configuration-apply failures. | Run metadata includes actual effective settings and failure state |
| **Daksh** | 1. Complete deterministic per-constraint evaluation. 2. Add tests for timeout and invalid measurements. 3. Return structured reason codes and evidence references. | Evaluator passes synthetic boundary suite |
| **Adriraj** | 1. Add warm-up and measurement windows. 2. Calculate TTFT, ITL if available, end-to-end latency, throughput, error rate, and percentiles. 3. Report offered and achieved request rate separately. 4. Detect generator saturation. | First complete benchmark artifact with raw and aggregate outputs |
| **Rohan** | 1. Connect candidate manifest to a single-run executor interface. 2. Define search controller inputs/outputs. 3. Build a fake measurement adapter for fast search unit tests. | Search orchestration can execute a candidate against fake measurements |
| **Joint gate** | Inspect the raw artifact manually and recalculate one metric independently. | One valid real benchmark is produced; metric units and denominators are documented |

---

### Day 5 — Saturday, October 17
## P2: Harden measurement and evaluator semantics

**Day outcome:** The system distinguishes a measured SLO failure from invalid evidence or execution failure.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Integrate run states and verdict states into one API response contract. 2. Add a minimal report serialization path. 3. Review status naming across UI/API/engine. | Consistent run/verdict state contract |
| **Aman** | 1. Test endpoint unavailability, timeout, restart, and configuration failure. 2. Document environment limitations and any runtime-specific measurement gaps. | Failure-mode notes and reproducible smoke tests |
| **Daksh** | 1. Add comprehensive threshold tests (equal, just under, just over). 2. Test missing percentile, small sample count, high error rate, and contaminated run. 3. Add inconclusive policy where evidence is insufficient. | Passing evaluator suite with reason-code assertions |
| **Adriraj** | 1. Add percentile edge cases, missing timestamps, zero completed requests, retries and failed-request accounting. 2. Preserve failed samples and invalid-run notes. 3. Add sample count to every aggregate. | Metric tests and sample report |
| **Rohan** | 1. Connect real result shape to candidate-result records. 2. Implement graceful handling of failed candidates. 3. Ensure failed candidates remain in history and do not crash search. | Multi-result manifest includes success and failure cases |
| **Joint gate** | Review a valid pass, a valid fail, an invalid measurement, and a runtime failure. | Each state produces the correct distinct explanation |

---

### Day 6 — Sunday, October 18
## P3: Baseline and legal search space

**Day outcome:** Baseline is saved, candidate generation is bounded, and each candidate is reconstructable.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Freeze first demo workload/SLO specification. 2. Define experiment-level budgets and stop conditions. 3. Ensure the report references spec, environment and raw artifacts. | Versioned demo spec and budget policy |
| **Aman** | 1. Run the reference/default serving configuration. 2. Confirm each proposed tuning parameter changes the effective configuration. 3. Record memory/resource constraints. | Baseline run and verified parameter support matrix |
| **Daksh** | 1. Evaluate baseline against every required hard constraint. 2. Review the verdict against raw evidence. 3. Check that missing/unsupported SLOs are not silently passed. | Baseline verdict and audit notes |
| **Adriraj** | 1. Run the baseline with the finalized workload protocol. 2. Save raw samples, metrics and run-validity flags. 3. Repeat if time/quota allows to estimate variability. | Baseline artifacts with sample counts and methodology |
| **Rohan** | 1. Finalize the small legal configuration space using Aman’s confirmed controls. 2. Generate stable candidate IDs. 3. Enforce max candidate and runtime budgets. 4. Estimate run count and wall-clock needs. | Reproducible candidate manifest within budget |
| **Joint gate** | Baseline and at least two legal candidates are available for the next phase. | No candidate changes the workload silently |

---

### Day 7 — Monday, October 19
## P4: First automated multi-candidate search

**Day outcome:** A single command or API request runs multiple candidates and returns a defensible ranking.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Integrate the experiment controller with candidate execution. 2. Add budget tracking and terminal states. 3. Ensure the dashboard/API can read experiment progress. | End-to-end multi-candidate experiment starts and reaches a terminal state |
| **Aman** | 1. Validate safe configuration application between candidates. 2. Detect stale configuration, endpoint restart and residual state. 3. Ensure cleanup occurs after failed runs. | Two different candidates can be applied and confirmed reliably |
| **Daksh** | 1. Evaluate every candidate result using the same policy version. 2. Check ranking never includes infeasible candidates as feasible winners. 3. Add evaluator integration tests. | Per-candidate verdicts with reason codes |
| **Adriraj** | 1. Run identical workload fixtures/protocol across candidates. 2. Check load-generator validity for every candidate. 3. Produce consistent metric records. | Comparable results with the same metric definitions |
| **Rohan** | 1. Implement bounded grid/random baseline search. 2. Persist search decisions and stopping reason. 3. Rank feasible candidates by declared objective; keep inconclusive candidates out of the verified-winner set. | Search manifest, candidate history and selection rationale |
| **Joint gate** | Run baseline plus multiple candidates automatically, then inspect the ranking and artifacts. | Multi-candidate run completes within the declared budget |

---

### Day 8 — Tuesday, October 20
## P4: Search quality, selection policy, and optional adaptive comparison

**Day outcome:** The team can explain why the selected candidate won and what the search does not prove.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Review selection objective and product claim. 2. Ensure reports distinguish measured values, estimates and assumptions. 3. Make the final scope call on adaptive search. | Signed-off objective and claim language |
| **Aman** | 1. Recheck candidate effects on the actual runtime. 2. Record configuration drift or runtime limitations. 3. Identify any candidate that changes quality/semantics rather than only performance. | Verified effective-setting records and limitation notes |
| **Daksh** | 1. Audit the winner-selection path against adversarial fixtures. 2. Test the case where every candidate is infeasible. 3. Test tie handling and inconclusive candidates. | Tests prove no false winner is emitted |
| **Adriraj** | 1. Compare repeats for the most promising candidates if budget permits. 2. Summarize variance and possible contamination. 3. Recommend additional repetitions when results are threshold-adjacent. | Variability summary and repeat-run artifacts |
| **Rohan** | 1. Compare baseline search with a small adaptive policy only if core search is stable. 2. Keep budgets and workload protocol comparable. 3. Record why each next candidate was selected. 4. Drop adaptive complexity if no meaningful advantage is shown. | Search comparison or documented decision to retain simpler search |
| **Joint gate** | Freeze the algorithm for the demo. | Search works reproducibly; no last-minute optimizer redesign |

**Important:** A sophisticated optimizer is not a deliverable by itself. A transparent bounded search with real evidence is preferable to a more complex policy that has not been fairly evaluated.

---

### Day 9 — Wednesday, October 21
## P5: Independent verification and cost policy

**Day outcome:** The selected candidate is rerun under a fresh identity, and cost claims are honest.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Define report language for verified, verification failed, inconclusive, and not run. 2. Review end-to-end state transitions. 3. Freeze claims that the demo is allowed to make. | Approved verdict copy and report structure |
| **Aman** | 1. Reapply the frozen candidate in a fresh run. 2. Confirm the effective config and environment. 3. Avoid reusing cached search measurements as verification. | New verification run ID and effective config snapshot |
| **Daksh** | 1. Implement/complete verification orchestration. 2. Recalculate metrics from fresh data. 3. Apply the same policy version. 4. Compare search versus verification metrics and mark drift. | Independent verification record with per-constraint outcome |
| **Adriraj** | 1. Run the same workload protocol for verification. 2. Preserve raw data and validity flags. 3. Calculate comparable metrics and sample counts. | Fresh verification raw measurements and aggregates |
| **Rohan** | 1. Freeze candidate settings and selection rationale. 2. Implement post-verification failure handling. 3. If verification fails and budget remains, allow a documented return to search; otherwise report failure honestly. | Frozen candidate record and fallback logic |
| **Joint gate** | Demonstrate a selected candidate passing or failing an independent run. | Verification is a separate experiment, not a reused search result |

### Cost policy

- If actual price/resource accounting is available, document source, units and assumptions.
- If not, report cost as **unavailable** and optimize against a declared non-monetary fallback (for example, resource-time or throughput under SLO).
- Never invent provider prices.
- Do not compare cost estimates that use different accounting boundaries.

---

### Day 10 — Thursday, October 22
## P6: Dashboard foundation and command center

**Day outcome:** The frontend has a coherent shell and consumes the same state/metric contracts as the backend.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Define the page hierarchy and shared UI/API data contract. 2. Integrate the overview with real experiment state or an explicit adapter. 3. Review all visible metric labels/units. | Working overview wired to the contract |
| **Aman** | 1. Expose runtime health and environment metadata to the API/UI. 2. Help define truthful connection/loading/error states. 3. Validate endpoint state display. | Runtime status can be rendered without exposing secrets |
| **Daksh** | 1. Define UI semantics for feasible/infeasible/inconclusive and verification states. 2. Review warning and error copy. 3. Ensure the UI never turns an inconclusive result green. | State-label acceptance checklist |
| **Adriraj** | 1. Provide stable sample datasets with synthetic labels. 2. Define chart fields and time-series units. 3. Check offered versus achieved load visual distinction. | UI fixture data and chart contract |
| **Rohan** | 1. Provide candidate manifest/result data for comparison tables. 2. Define which search metadata should be visible. 3. Ensure candidate labels map to stable IDs. | Candidate table data contract |
| **Joint gate** | Walk through Overview → run state → candidate list. | Page hierarchy is understandable without decorative polish |

---

### Day 11 — Friday, October 23
## P6: Workload builder, tuning lab, and live monitor

**Day outcome:** Core controls make it difficult to submit invalid or misleading experiments.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Integrate workload/SLO form with schema validation. 2. Preserve form state during navigation. 3. Ensure advanced options are progressively disclosed. | Valid and invalid form scenarios pass |
| **Aman** | 1. Supply supported model/runtime and tuning options. 2. Mark unsupported parameters explicitly. 3. Confirm UI choices map to effective adapter settings. | No fake tuning control is exposed as functional |
| **Daksh** | 1. Add field-level validation copy for contradictory SLOs and missing requirements. 2. Check hard constraints remain hard constraints. 3. Review error/inconclusive states. | Validation cases and status copy reviewed |
| **Adriraj** | 1. Wire load and latency charts to the result schema. 2. Add units, sample counts and provisional/final state labels. 3. Provide accessible table/text alternatives. | Charts correctly display fixture and/or live values |
| **Rohan** | 1. Wire search-space controls and candidate-budget estimate. 2. Display candidate count and stopping/budget constraints. 3. Show why candidate settings are legal. | Tuning lab maps to actual candidate schema |
| **Joint gate** | Submit a valid specification, reject an invalid one, and inspect a candidate plan. | UI inputs round-trip to the backend contract without silent mutation |

---

### Day 12 — Saturday, October 24
## P6: Results, verification, and report views

**Day outcome:** Users can understand the outcome and inspect the evidence behind it.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Integrate candidate comparison, selection rationale and report view. 2. Make artifacts accessible. 3. Check all result copy against real output. | Complete UI path from experiment to report |
| **Aman** | 1. Confirm environment and runtime metadata are visible in run detail. 2. Remove credentials/private endpoint secrets from output. 3. Validate environment fingerprint accuracy. | Safe, useful environment panel |
| **Daksh** | 1. Build verification comparison with constraint-by-constraint results. 2. Show separate search and verification run IDs. 3. Ensure failed verification invalidates the verified badge. | Verification view passes acceptance scenarios |
| **Adriraj** | 1. Check metric charts against raw artifact calculations. 2. Add sample counts and data-window labels. 3. Ensure failed requests and invalid runs are not hidden. | Chart/table values reconcile with artifacts |
| **Rohan** | 1. Build candidate filters and comparison table. 2. Display feasibility and cost/objective values with clear unavailable states. 3. Show search strategy and stopping reason. | Candidate comparison explains the winner without opaque score alone |
| **Joint gate** | Demonstrate Overview → Builder → Monitor → Results → Verification → Report. | End-to-end UI path works; mock data is visibly labelled |

---

### Day 13 — Sunday, October 25
## P7: Optional AI-assisted planning and explanation

**Day outcome:** Optional AI work is included only if every core milestone is already working.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Make a go/no-go decision based on the critical path. 2. If green-lit, define one narrow AI use case and its guardrails. 3. Verify deterministic evaluation remains authoritative. | Written go/no-go decision |
| **Aman** | 1. Review any AI-proposed configuration against the supported parameter allowlist. 2. Ensure AI cannot invoke arbitrary infrastructure operations. | Allowlist enforcement test |
| **Daksh** | 1. Add tests that AI explanations cannot alter verdicts. 2. Require explanations to cite actual metric/evaluator fields. 3. Test unsupported claims. | Verdict isolation tests |
| **Adriraj** | 1. Provide real artifact fields for evidence-grounded summaries. 2. Ensure summaries distinguish measured and estimated values. | Example summary grounded in artifact data |
| **Rohan** | 1. If justified, add candidate-priority suggestions—not an unconstrained optimizer. 2. Validate suggestions against candidate schema and budget. 3. Keep the deterministic search fallback. | Validated suggestion or documented decision to defer |
| **Joint gate** | If core work is not green, use this day for integration, repeatability and bug fixes instead. | No optional AI feature blocks the MVP |

**Default decision:** defer AI extras if the end-to-end experiment, verification, or report is still unreliable.

---

### Day 14 — Monday, October 26
## P8: Clean-environment setup and failure-path testing

**Day outcome:** Another teammate can reproduce the main workflow from the documentation.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Run setup from a clean checkout/environment. 2. Fix integration defects. 3. Ensure CI checks schemas/tests. 4. Audit README against actual commands. | Clean setup record and accurate docs |
| **Aman** | 1. Test endpoint outage, timeout, restart and cleanup. 2. Verify secrets are redacted. 3. Ensure jobs/resources are released after cancellation/failure. | Runtime failure/recovery checklist |
| **Daksh** | 1. Run acceptance scenarios for feasible, infeasible, inconclusive, invalid and verification-failed. 2. Audit every verdict against evidence. | Acceptance test results |
| **Adriraj** | 1. Re-run benchmark protocol and compare repeated outcomes. 2. Inspect offered/achieved load and contamination flags. 3. Validate raw artifact completeness. | Repeatability summary and raw artifact audit |
| **Rohan** | 1. Test candidate budget exhaustion, no legal candidates and all-infeasible outcomes. 2. Confirm search stops safely. 3. Ensure candidate history survives partial failure. | Search edge-case tests |
| **Joint gate** | A teammate who did not author the setup follows it and completes a small run. | Reproduction test passes or blockers are explicitly documented |

---

### Day 15 — Tuesday, October 27
## P8: Performance claim audit, UI polish, and freeze candidate

**Day outcome:** Core features freeze; remaining changes are limited to correctness, clarity, and critical bugs.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Freeze MVP scope and API contracts. 2. Audit every percentage, chart and headline claim. 3. Review architecture diagram and project narrative. | Feature-freeze note and claims audit |
| **Aman** | 1. Re-run the exact demo endpoint preflight. 2. Confirm selected model/runtime is still available. 3. Record current resource/runtime versions. | Demo environment fingerprint and preflight result |
| **Daksh** | 1. Review final report for verdict consistency. 2. Verify search-run and verification-run are distinct. 3. Remove misleading success states. | Signed-off verification/report checklist |
| **Adriraj** | 1. Freeze the main workload fixture and measurement protocol. 2. Recalculate final report metrics from raw data. 3. Record uncertainty/limitations. | Final benchmark bundle with source artifacts |
| **Rohan** | 1. Freeze search policy and configuration space. 2. Re-run the final bounded experiment. 3. Save the complete candidate history and stopping reason. | Final search bundle and reproducible ranking |
| **Joint gate** | No new feature enters after this point unless it fixes a submission-blocking defect. | All headline numbers reconcile with saved artifacts |

---

### Day 16 — Wednesday, October 28
## P9: Final experiment, narrative, and demo rehearsal

**Day outcome:** The team can deliver the complete story in one clean, rehearsed path.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Write the 3–5 minute demo script. 2. Finalize architecture diagram and technical narrative. 3. Coordinate one full rehearsal. 4. Check hackathon submission criteria against official rules. | Demo script, diagram, submission checklist |
| **Aman** | 1. Run environment preflight. 2. Confirm endpoint credentials/quota and startup path. 3. Prepare recovery instructions for a failed live run. | One-page environment runbook |
| **Daksh** | 1. Select the verification evidence to show. 2. Prepare a concise explanation of verdict semantics and failure behavior. 3. Audit the final claims. | Verification evidence and claim checklist |
| **Adriraj** | 1. Prepare the benchmark methodology slide/table. 2. Ensure all shown metrics come from saved raw data. 3. Prepare a clearly labelled previously-measured fallback report. | Reconciled benchmark table and fallback artifacts |
| **Rohan** | 1. Prepare the search-space and candidate-selection explanation. 2. Show why infeasible candidates were excluded. 3. Prepare the search-history evidence. | Candidate comparison and selection narrative |
| **Joint gate** | Run the full demo from a clean state, time it, and record failures. | Full rehearsal completed; no unexplained state or fabricated live data |

---

### Day 17 — Thursday, October 29
## P9: Release candidate, documentation freeze, and final rehearsal

**Day outcome:** Submission package is complete one day early; only critical fixes remain.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Freeze the release candidate. 2. Review README/ROADMAP consistency. 3. Confirm links, screenshots, diagram, and demo sequence. 4. Assign final submission ownership. | Release checklist signed off |
| **Aman** | 1. Re-run smoke test and, if feasible, final verification preflight. 2. Confirm cleanup and fallback procedure. 3. Check no credentials are present in repository or artifacts. | Final environment checklist |
| **Daksh** | 1. Run all critical evaluator/verification tests. 2. Confirm report verdict matches saved evidence. 3. Check no candidate is labelled verified without a passing fresh run. | Final test results and verdict audit |
| **Adriraj** | 1. Validate final raw data and report calculations. 2. Confirm workload/version/environment match the final demo. 3. Archive the evidence bundle. | Final benchmark evidence bundle |
| **Rohan** | 1. Run the final search or confirm the saved run is the exact one being presented. 2. Verify candidate settings and stopping reason. 3. Freeze search outputs. | Final search manifest and candidate table |
| **Joint gate** | Rehearse the final demo once; no feature additions after sign-off. | Release candidate tagged/identified, package ready to submit |

---

### Day 18 — Friday, October 30
## Submission day — only final checks and delivery

**Day outcome:** Submit a consistent, evidence-backed package before the official deadline.

| Owner | Daily tasks | Required evidence |
|---|---|---|
| **Rajdeep** | 1. Confirm official deadline/timezone and required fields. 2. Coordinate final submission. 3. Check project narrative and claims one last time. 4. Save submission confirmation. | Submission confirmation and final package |
| **Aman** | 1. Perform a brief endpoint smoke test if live demo is required. 2. Confirm no environment outage invalidates the chosen fallback. | Final health status or documented fallback |
| **Daksh** | 1. Verify the final report/record has the correct verification status. 2. Check that claims do not exceed evidence. | Final evidence sign-off |
| **Adriraj** | 1. Confirm all displayed benchmark figures match the archived artifact. 2. Ensure mock/fallback results are labelled correctly. | Final metric consistency check |
| **Rohan** | 1. Confirm candidate history and search rationale are included. 2. Check the tested search-space boundaries are disclosed. | Final optimizer evidence check |
| **Joint gate** | Submit with a buffer; do not wait until the last minutes. Keep confirmation and a copy of the exact submitted artifacts. | Submission accepted |

---

## 6. Daily integration ritual

Run this short ritual every day, preferably at a consistent time.

### Start of day

Each owner answers:
1. What is the single deliverable that will move the critical path today?
2. What dependency or decision could block it?
3. What is the fallback if that dependency is not resolved by midday?

### End of day

Each owner posts:
- **Done:** exact file/PR/artifact/test;
- **Not done:** what remains and why;
- **Blocked by:** person/system/decision;
- **Next handoff:** named receiver and expected format;
- **Risk:** whether the critical path or demo is threatened.

### Integration rules

- Merge small changes daily rather than creating a giant end-of-sprint merge.
- Require a contract/test update when data fields change.
- Keep a known-good main branch.
- Do not commit secrets, large raw benchmark dumps, or generated artifacts without an explicit repository policy.
- Save experiment artifacts outside the source tree when large or sensitive.
- Any owner may flag a stop-the-line issue; Rajdeep makes the cross-workstream priority call.

---

## 7. Shared contracts and handoffs

These are the interfaces that prevent integration chaos.

### 7.1 Workload/SLO specification — Rajdeep owns the contract

Must include:
- schema version;
- model/runtime reference;
- workload fixture and arrival mode;
- target/offered request rate;
- warm-up and measurement duration;
- concurrency and token policy;
- required SLO dimensions and units;
- experiment budget and stopping limits;
- verification policy.

**Consumer:** frontend, planner, load generator, evaluator and report generator.

### 7.2 Effective configuration — Aman supplies reality, Rohan supplies candidate intent

Must include:
- candidate ID;
- requested settings;
- effective/read-back settings where supported;
- supported/unsupported parameter status;
- environment/runtime identity;
- validation result.

**Rule:** a requested setting is not considered applied until the adapter can confirm it or the runtime has an authoritative equivalent.

### 7.3 Raw measurements — Adriraj owns

Each request record should contain, where available:
- experiment/run/candidate IDs;
- request ID;
- scheduled, sent, first-token and completion timestamps;
- status/error/timeout;
- input/output token counts;
- per-token timing or ITL observations where available;
- validity/contamination annotations.

Never store only aggregates. Preserve enough raw information to recompute metrics.

### 7.4 Metrics — Adriraj defines; Daksh consumes

Each metric must define:
- field name;
- start/end events;
- units;
- population/denominator;
- aggregation/percentile method;
- missing-data behavior;
- sample count.

### 7.5 Feasibility verdict — Daksh owns

Must include:
- `FEASIBLE`, `INFEASIBLE`, or `INCONCLUSIVE`;
- separate execution status;
- per-constraint result;
- observed value and threshold;
- reason code;
- policy version;
- evidence references.

### 7.6 Candidate/search history — Rohan owns

Must include:
- legal candidate configuration and stable ID;
- candidate proposal order;
- run result reference;
- failure/invalid status;
- why the candidate was proposed;
- ranking objective and tie-breaking policy;
- stopping reason and budget consumption.

### 7.7 Final report — Rajdeep integrates all owners

Must include:
- immutable spec;
- model/runtime/environment fingerprint;
- baseline and candidate table;
- metric definitions and sample counts;
- selection rationale;
- cost source/assumptions or `unavailable`;
- independent verification run and verdict;
- raw artifact references;
- limitations and tested search-space boundaries.

---

## 8. Acceptance gates

Do not advance based only on elapsed days. Advance when the evidence exists.

### Gate A — Scope locked (end of Oct 13)

- [ ] One model/runtime path selected or blocker escalated.
- [ ] MVP and non-goals written.
- [ ] SLO/workload/config/result/verdict schemas agreed.
- [ ] Experiment budget defined.
- [ ] Every critical component has one owner.

### Gate B — Serving path works (end of Oct 15)

- [ ] Endpoint responds to a known request.
- [ ] Runtime/model identity recorded.
- [ ] Supported settings documented.
- [ ] Configuration apply/read-back behavior tested.
- [ ] Credentials are not logged or committed.

### Gate C — Measurement and evaluator work (end of Oct 17)

- [ ] Raw request records saved.
- [ ] Metrics have explicit units and definitions.
- [ ] Offered and achieved load are separate.
- [ ] Invalid/contaminated run detection exists.
- [ ] Evaluator returns deterministic pass/fail/inconclusive outcomes.
- [ ] Boundary tests pass.

### Gate D — Search works (end of Oct 20)

- [ ] Baseline recorded.
- [ ] More than one candidate tested automatically.
- [ ] Candidate configurations are legal and reconstructable.
- [ ] Failed candidates remain visible.
- [ ] Selection objective is declared.
- [ ] No feasible candidate is handled honestly.
- [ ] Search stops within budget.

### Gate E — Winner verified (end of Oct 21)

- [ ] Selected configuration frozen.
- [ ] Verification has a new run ID.
- [ ] Same workload protocol is used.
- [ ] Metrics recalculated from fresh raw data.
- [ ] Final status is verified, failed, or inconclusive.
- [ ] Search-run evidence is not reused as verification.

### Gate F — Dashboard integrated (end of Oct 24)

- [ ] Builder validates the shared schema.
- [ ] Overview shows real lifecycle state or clearly labelled fixture data.
- [ ] Candidate comparison uses actual result fields.
- [ ] Verification view distinguishes run IDs and states.
- [ ] Empty/loading/error/no-feasible states exist.
- [ ] Charts show units and sample context.
- [ ] No mock value is presented as a live measurement.

### Gate G — Release candidate (end of Oct 29)

- [ ] Clean setup works.
- [ ] Critical tests pass.
- [ ] Final claims match raw artifacts.
- [ ] Demo rehearsed.
- [ ] Fallback report is labelled.
- [ ] Official submission rules and deadline confirmed.
- [ ] Release package is ready before submission day.

---

## 9. Experiment protocol and proof of value

### Research question

Under a fixed model, serving environment, workload and experiment budget, does SLOKern identify a configuration that satisfies the declared SLO at lower measured cost—or discover feasibility more efficiently—than the reference configuration or a simple baseline search?

### Minimum evidence

| Condition | Why it exists |
|---|---|
| Default/reference configuration | Establishes the starting point |
| Bounded baseline search | Provides a transparent comparison |
| Adaptive search, only if implemented | Tests whether extra complexity is useful |
| Fresh independent verification | Tests whether the winner survives a new run |

### Fairness controls

Keep the following constant where feasible:
- model and revision;
- serving runtime/version;
- prompt fixture and input/output token policy;
- offered load and arrival process;
- warm-up and measurement duration;
- timeouts/retry policy;
- metric definitions;
- resource allocation.

Randomize/interleave candidate order if time permits and resource drift is a concern. Repeat threshold-adjacent candidates if budget allows.

### Results to report

1. Did any candidate pass every required hard constraint?
2. What was the best verified objective among feasible candidates?
3. How did it compare with baseline?
4. How many candidates and how much wall-clock time were needed?
5. Did adaptive search improve outcome or budget efficiency?
6. Did the winner pass independent verification?
7. How variable were the search and verification runs?
8. What was tested, and what was outside the search space?

### Final results table

Populate only with real measurements.

| Candidate | Valid? | TTFT p95 | ITL p95 | Requests/s | Output tokens/s | Error rate | Cost/unit | SLO verdict | Verified? |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Baseline | — | — | — | — | — | — | — | — | — |
| Candidate A | — | — | — | — | — | — | — | — | — |
| Candidate B | — | — | — | — | — | — | — | — | — |
| Selected candidate | — | — | — | — | — | — | — | — | — |

Do not make percentage-improvement claims until the compared values are drawn from comparable runs and the calculation is checked.

---

## 10. Testing matrix

| Test area | Owner | Required cases |
|---|---|---|
| Schema/contract | Rajdeep | Valid spec, invalid spec, missing fields, schema version |
| Serving adapter | Aman | Healthy request, timeout, unavailable endpoint, apply/read-back, cleanup |
| Workload/load generator | Adriraj | Arrival schedule, generator saturation, timeout, errors, missing timestamps |
| Metric calculations | Adriraj | Percentiles, zero samples, failed requests, denominators, units, missing values |
| Feasibility policy | Daksh | Exact threshold, below/above threshold, missing metric, unsupported constraint |
| Verdict semantics | Daksh | Feasible, infeasible, inconclusive, execution failure |
| Candidate generation | Rohan | Stable ID, invalid combination, candidate cap, reproducible manifest |
| Search | Rohan | Multiple candidates, candidate failure, all-infeasible, budget exhausted, stopping reason |
| Verification | Daksh + Aman + Adriraj | Fresh run ID, same workload, failed verification, inconclusive verification |
| Frontend contracts | Rajdeep + all owners | Loading, empty, invalid, running, failed, no feasible candidate, verified |
| Report/evidence | Rajdeep + Daksh + Adriraj | Artifact references resolve; numbers reconcile with raw measurements |
| Security/reliability | Aman + Rajdeep | Secret redaction, bounded workload, cancellation, cleanup, no arbitrary command execution |

### End-to-end acceptance scenarios

- **Feasible:** at least one candidate passes all hard constraints and verification succeeds.
- **No feasible candidate:** every tested candidate fails; system reports the tested boundary without inventing a winner.
- **Inconclusive:** data is insufficient/noisy/invalid; no green pass is shown.
- **Execution failure:** endpoint is unavailable; system does not label it as a measured SLO failure.
- **Budget exhausted:** experiment stops safely and reports partial evidence.
- **Verification failure:** fresh run fails; candidate is not marked verified.
- **Invalid spec:** rejected before expensive work begins.
- **Mock UI:** interactions work and synthetic data is unmistakably labelled.

---

## 11. Demo and submission plan

### Recommended 3–5 minute story

1. **Problem (20–30 sec):** raw throughput is not enough; serving must satisfy latency/reliability targets.
2. **Specify (30–45 sec):** show model/runtime, workload, offered rate and SLOs.
3. **Baseline (30–45 sec):** show reference metrics and constraint results.
4. **Search (45–60 sec):** show candidates, valid measurements, and rejected configurations.
5. **Select (30–45 sec):** explain the declared objective and why the winner was chosen.
6. **Verify (30–45 sec):** show the fresh run ID and independent verdict.
7. **Evidence (20–30 sec):** inspect report, environment metadata and raw artifacts.

### Demo rules

- Use real measured values for performance claims.
- Label previously measured data as previously measured.
- Label synthetic dashboard fixtures as `DEMO DATA`.
- Do not imply a saved report is a live run.
- Show one rejected/failed candidate if possible.
- Keep a known-good fallback report and disclose when it is used.
- Rehearse the same sequence, environment and credentials intended for the final presentation.

### Submission checklist

- [ ] Official rules, eligibility, model requirements, environment requirements, format and deadline rechecked.
- [ ] README and this roadmap match the shipped implementation.
- [ ] Architecture diagram and demo script are ready.
- [ ] Final table uses real measurements and traceable artifacts.
- [ ] Search-space boundaries and limitations are disclosed.
- [ ] No unsupported “optimal,” “X% faster,” or “Y% cheaper” claims remain.
- [ ] No secrets are in source, logs, screenshots or reports.
- [ ] Links/artifacts work in a clean session.
- [ ] Demo fallback is labelled and tested.
- [ ] Submission confirmation is saved.

---

## 12. Risk register and contingency decisions

| Risk | Trigger | Owner | Immediate response |
|---|---|---|---|
| Model/runtime inaccessible | No successful smoke test by Oct 15 | Aman, escalated to Rajdeep | Switch to a rules-compliant supported path; freeze scope immediately |
| Runtime lacks required timing fields | TTFT/ITL cannot be measured reliably | Aman + Adriraj | Reduce supported SLO set honestly or choose another supported runtime; do not fake fields |
| Benchmark generator saturates | Achieved load diverges from offered load | Adriraj | Flag run invalid/contaminated; lower rate or fix generator before comparing candidates |
| Candidate setting is not actually applied | Read-back/effective config does not match | Aman + Rohan | Remove that dimension from search space |
| Search complexity consumes time | Baseline multi-candidate search not stable by Oct 20 | Rohan + Rajdeep | Drop adaptive search; retain bounded transparent search |
| Verification fails | Fresh run violates a hard SLO | Daksh | Mark verification failed; preserve both runs; re-search only if budget remains |
| Cost data unavailable | No authoritative price/accounting source | Rajdeep + Aman | Mark monetary cost unavailable; use a clearly labelled non-monetary objective |
| Frontend consumes critical-path time | Core run pipeline incomplete by Oct 21 | Rajdeep | Freeze UI to a small integrated set of views; cut decorative work |
| Dashboard/backend drift | Contract mismatch | Rajdeep + affected owner | Fix shared schema and contract test, not a one-off frontend patch |
| Demo live path fails | Endpoint or quota issue at rehearsal | Aman + Adriraj | Use archived evidence bundle with explicit “previously measured” label |
| Claims exceed evidence | Report/slide value lacks artifact | Rajdeep + Daksh + Adriraj | Remove or qualify claim; no exceptions |
| Team overlap causes duplicate work | Multiple owners edit same component without handoff | Rajdeep | Reassign one accountable owner and define review interface |

### Cut order if time is lost

Cut in this order:
1. optional AI features;
2. adaptive search if not proven useful;
3. extra dashboard pages/visual effects;
4. secondary metrics that are not measurable reliably;
5. repeated experiments beyond the minimum needed for honest reporting.

Do **not** cut:
- a working serving path;
- raw measurement retention;
- deterministic SLO evaluation;
- bounded experiment execution;
- independent verification;
- honest evidence/limitations;
- final submission validation.

---

## 13. Definition of done

The MVP is done only when:

- [ ] A valid workload/SLO specification can be created and validated.
- [ ] The selected permitted model responds through the chosen serving path.
- [ ] The effective serving configuration is recorded.
- [ ] A baseline produces raw measurements and reproducible metadata.
- [ ] Metrics are calculated according to documented definitions.
- [ ] Offered and achieved load are distinct.
- [ ] Deterministic evaluation yields per-constraint verdicts.
- [ ] More than one candidate can be run automatically within a bounded budget.
- [ ] Failed and invalid runs remain visible.
- [ ] Search selection uses a declared objective.
- [ ] The system can report no feasible candidate honestly.
- [ ] The winner receives a separate verification run.
- [ ] Verification can pass, fail, or be inconclusive.
- [ ] Dashboard states and metrics agree with backend artifacts.
- [ ] Synthetic data is clearly labelled.
- [ ] Final report links to specification, configuration, environment and raw evidence.
- [ ] Critical tests pass and setup works from a clean checkout.
- [ ] Every performance/cost claim is supported by evidence and stated assumptions.
- [ ] A teammate can reproduce the demo from the docs.
- [ ] Submission is complete before the verified official deadline.

---

## 14. Daily stand-up template

Copy this for each member at the start/end of a day.

```text
Date:
Owner:
Status: TODO / IN PROGRESS / BLOCKED / DONE

Today's single deliverable:
Dependency/blocker:
Fallback if blocked:
Files/PRs/artifacts:
Tests/evidence:
Handoff to:
Risk to critical path:
Tomorrow's next action:
```

A task is not done because someone says “almost done.” Link the evidence.

---

## 15. Decision log template

Use one record per decision that affects architecture, scope, measurement, or claims.

```text
Decision ID:
Date:
Question:
Options considered:
Decision:
Reason:
Owner:
Affected contracts/components:
Evidence:
Trade-offs:
Revisit condition:
```

High-priority decisions to log:
- exact model/runtime and hosting path;
- supported tuning dimensions;
- workload arrival model and fixture;
- metric definitions and percentiles;
- SLO feasibility/uncertainty policy;
- search algorithm and budget;
- cost accounting method;
- artifact retention and redaction;
- optional AI scope;
- official submission requirements.

---

## Final operating principle

Build the smallest complete system that can **measure, decide, verify, and explain**. Then polish it.

SLOKern does not need to test every configuration or claim universal optimality. It needs to demonstrate that its recommendation follows from controlled measurements, deterministic rules, a declared objective, and a fresh verification run.

**Optimize inference. Verify performance.**
