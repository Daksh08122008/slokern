# SLOKern MVP Scope & Acceptance Checklist

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Reference / Scope Boundary  
> **Owner:** Rajdeep (Technical Lead / Architecture)  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

---

## 1. Product Promise & Mission Boundary

SLOKern accepts a declared workload profile and service-level objectives (SLOs), benchmarks a bounded set of legal serving configurations, identifies the lowest-cost configuration that satisfies the declared constraints, and independently verifies the recommendation.

### Core Operating Principle

> **One model, one serving environment, a small configuration space, reproducible experiments.**

Every task in the project is evaluated against whether it advances this core end-to-end chain. Features outside this chain are deferred.

---

## 2. In-Scope vs. Out-of-Scope (Non-Goals)

### In-Scope for the Hackathon MVP

1. **One Permitted Model:** A single NVIDIA open-source model supported by the hackathon environment (e.g., Llama-3-8B-Instruct or Mistral-7B).
2. **One Serving Runtime:** A single dedicated serving backend (e.g., vLLM or TensorRT-LLM on Nebius Cloud GPU infrastructure).
3. **One Reproducible Workload Protocol:** A fixed prompt fixture with explicit arrival distributions (Poisson or constant rate) and separate warm-up and measurement windows.
4. **Small Legal Search Space:** A bounded set of 2–4 tunable parameters that the serving adapter can actively apply, observe, and read back.
5. **Offered vs. Achieved Load Separation:** Clear architectural distinction and measurement of intended traffic rate versus actual delivered rate.
6. **Key Inference Metrics:** Deterministic calculation of TTFT, ITL (with defined aggregation), end-to-end latency, request throughput, output-token throughput, error rate, and percentiles (p50, p90, p95, p99).
7. **Deterministic Feasibility Evaluator:** Auditable constraint-by-constraint rule engine returning `FEASIBLE`, `INFEASIBLE`, or `INCONCLUSIVE` with structured reason codes.
8. **Baseline + Bounded Search:** Reference run compared against a transparent, budget-capped search controller (grid or random search).
9. **Independent Verification Run:** Mandatory rerun of the selected candidate under a fresh `run_id` to confirm reproducibility.
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

### Gate A — Scope Locked (Target: End of Oct 13)
- [ ] One model/runtime path selected or blocker escalated to leadership.
- [ ] MVP scope, non-goals, and operating principles written and acknowledged.
- [ ] Shared schemas (`WorkloadSpec`, `SLOSpec`, `CandidateConfig`, `RunRecord`, `MetricSet`, `FeasibilityResult`, `SearchResult`, `VerificationRecord`, `ReportArtifact`) agreed across all 5 owners.
- [ ] Experiment budget and stopping limits defined.
- [ ] All 5 components assigned to unambiguous single owners.

### Gate B — Serving Path Works (Target: End of Oct 15)
- [ ] Dedicated model endpoint responds reliably to a smoke inference request.
- [ ] Effective runtime, model revision, and hardware environment fingerprint captured.
- [ ] Table of mutable serving parameters documented and confirmed by read-back tests.
- [ ] Configuration apply, read-back, timeout, and failure behaviors verified.
- [ ] Zero API keys, tokens, or private endpoint credentials committed to source control or logs.

### Gate C — Measurement & Evaluator Complete (Target: End of Oct 17)
- [ ] Subprocess load generator logs granular `RawRequestMeasurement` records (JSONL) with client timestamps.
- [ ] Metrics engine derives documented metrics with explicit units and sample counts.
- [ ] Offered load and achieved load are reported separately; generator saturation is detected.
- [ ] Deterministic feasibility evaluator produces `FEASIBLE`, `INFEASIBLE`, and `INCONCLUSIVE` verdicts with structured reason codes.
- [ ] Unit tests pass for exact-boundary, below-threshold, above-threshold, missing-metric, and contaminated-run cases.

### Gate D — Bounded Search Works (Target: End of Oct 20)
- [ ] Baseline configuration executed under the standard workload protocol and recorded.
- [ ] Automated search controller runs multiple legal candidates within declared budgets.
- [ ] Candidate configurations are legal, canonicalized, and reconstructable from stable IDs.
- [ ] Infeasible, invalid, and failed candidates remain visible in search history.
- [ ] Selection policy ranks feasible candidates by the declared objective; handles the "no feasible candidate" scenario honestly.
- [ ] Search stops cleanly upon budget exhaustion or candidate completion.

### Gate E — Winner Verified Independently (Target: End of Oct 21)
- [ ] Selected winning candidate configuration is frozen.
- [ ] Verification runner dispatches a fresh run with a new, distinct `run_id`.
- [ ] Identical workload protocol and environment conditions are applied.
- [ ] Metrics are recomputed independently from fresh raw measurements (no search-run caching).
- [ ] Final verdict is emitted: `VERIFIED`, `VERIFICATION_FAILED`, or `VERIFICATION_INCONCLUSIVE`.

### Gate F — Dashboard Integrated (Target: End of Oct 24)
- [ ] Workload & SLO builder validates inputs against canonical backend schemas.
- [ ] Overview command center displays real lifecycle states or explicitly labelled **DEMO DATA**.
- [ ] Candidate comparison table uses actual result fields and explains selection rationale.
- [ ] Verification view clearly separates search run ID from verification run ID.
- [ ] Loading, empty, error, and no-feasible-candidate states render cleanly.
- [ ] All charts display explicit units, sample sizes, and data-window boundaries.

### Gate G — Release Candidate & Rehearsal (Target: End of Oct 29)
- [ ] Clean setup from repository documentation succeeds on an independent machine.
- [ ] Critical test suite passes across contracts, evaluator, search, and load generator.
- [ ] All headline performance and cost figures reconcile with raw source artifacts.
- [ ] Full 3–5 minute presentation and demo rehearsed with a documented fallback plan.
- [ ] Final submission package verified against official hackathon criteria.

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

The team must pause and escalate to the Technical Lead (Rajdeep) immediately if:

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
- [Ownership & Team Matrix](ownership.md)
- [Architecture Decision Log](decision-log.md)
- [Daily Integration Checklist](integration-checklist.md)
- [ADR 0001: MVP Scope & Evidence Policy](adr/0001-mvp-scope-and-evidence.md)

