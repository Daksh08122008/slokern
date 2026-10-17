# SLOKern
### Optimize inference. Verify performance.

> **SLOKern is an SLO-aware LLM inference optimization system that measures a bounded set of serving configurations, identifies the lowest-cost configuration that satisfies a declared workload and service-level objective (SLO), and independently verifies the recommendation.**

**Hackathon:** Nebius × NVIDIA Global AI Hackathon  
**Domain:** LLM inference serving, systems performance, SLO-aware optimization  
**Working name history:** ServeWise → **SLOKern**  
**CLI concept:** `slokern verify`  
**Product principle:** **One model, one serving environment, a small configuration space, reproducible experiments.**

> [!IMPORTANT]
> This repository plan describes the intended system. Do not present a feature, command, model, deployment, price, or benchmark result as implemented until it has been tested in the actual repository and target environment. Mock dashboard data must be labelled **DEMO DATA**.

---

## Contents

- [Why SLOKern?](#why-slokern)
- [What it does](#what-it-does)
- [MVP scope](#mvp-scope)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Metrics and decision policy](#metrics-and-decision-policy)
- [Dashboard](#dashboard)
- [Team and ownership](#team-and-ownership)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Validation and reproducibility](#validation-and-reproducibility)
- [Roadmap](#roadmap)
- [Hackathon deliverables](#hackathon-deliverables)
- [Known decisions to finalize](#known-decisions-to-finalize)

## Why SLOKern?

LLM serving is a constrained optimization problem. A configuration can deliver impressive throughput while violating the latency users experience; another may satisfy latency targets but cost more than necessary. Manual tuning is slow, measurements are noisy, and a single lucky benchmark run can produce a false winner.

SLOKern answers:

> **What is the maximum sustainable request rate—and the associated cost—at which a serving configuration can satisfy the specified SLO for a defined workload?**

The product is more than a benchmark script. It connects workload specification, controlled experiments, bounded search, deterministic feasibility decisions, cost-aware ranking, and an independent verification run.

## What it does

1. Accepts a workload profile and explicit SLO requirements.
2. Validates the specification and experiment budget before expensive work begins.
3. Establishes a baseline using the same workload protocol as candidate configurations.
4. Benchmarks a bounded set of legal serving configurations.
5. Preserves raw measurements and calculates documented metrics.
6. Excludes candidates that fail hard constraints or lack valid evidence.
7. Selects a candidate using a declared objective, preferably measured cost at the required load.
8. reruns the selected candidate under a new run ID.
9. Produces an inspectable report containing the verdict, environment, configuration, measurements, assumptions, and limitations.

An AI-assisted layer may help draft specifications or explain results, but **deterministic code—not an LLM—owns metric calculation, SLO verdicts, budget enforcement, and final verification**.

## MVP scope

### In scope

- One NVIDIA open-source model supported by the chosen hackathon environment.
- One serving runtime/environment.
- One reproducible workload fixture or small set of named profiles.
- A small configuration space containing only parameters the adapter can actually apply.
- Controlled load generation, with offered and achieved load reported separately.
- TTFT, inter-token latency (ITL), throughput, errors, and latency percentiles.
- A deterministic feasibility evaluator.
- Baseline plus bounded search.
- Independent verification of the selected candidate.
- Machine-readable artifacts, a readable report, and a polished dashboard.

### Out of scope for the MVP

- Universal support for all models, runtimes, clouds, and GPU types.
- Unbounded search or a claim of global optimality.
- Automatic changes to production deployments.
- Treating one run as statistically conclusive.
- Adding complex AI/optimizer features before the measurement pipeline works.
- Fabricating performance or cost numbers to make the demo look stronger.

## How it works

```text
Workload + SLO
     ↓
Validate specification and budget
     ↓
Run baseline
     ↓
Generate legal candidate configurations
     ↓
Apply configuration → warm up → generate controlled load
     ↓
Save raw measurements and environment metadata
     ↓
Calculate metrics → evaluate each hard constraint
     ↓
Search and rank evidenced feasible candidates
     ↓
Rerun selected candidate independently
     ↓
Publish report, charts, verdict, and artifacts
```

### Architecture at a glance

| Component | Responsibility |
|---|---|
| Dashboard | Specification builder, tuning controls, progress, comparison, verification and reports |
| API/control plane | Validation, experiment lifecycle, state, cancellation and artifact access |
| Serving adapter | Applies supported settings and communicates with the chosen runtime |
| Load generator | Creates the declared request-arrival pattern and records request-level timing |
| Metrics engine | Calculates documented metrics from raw measurements |
| Feasibility evaluator | Applies versioned, deterministic SLO rules |
| Search controller | Chooses legal next candidates and enforces stopping conditions |
| Verification runner | Repeats the selected configuration in a separate run |
| Report generator | Makes the experiment inspectable and reproducible |
| Optional AI planner | Helps draft or explain; cannot override deterministic verdicts |

For the MVP, use a **modular monolith plus a controlled experiment worker**. Keep the control plane separate from the request-generation path so dashboard/API work does not contaminate measurements. The API process starts and observes an experiment worker; the worker isolates load generation in its own subprocess.

### Stack defaults

The README previously left implementation choices open. These defaults are selected for the five-person hackathon team and can be revised based on what Aman confirms about the serving environment on **October 14**. They describe the intended stack; they do not imply that the corresponding components are already implemented.

| Area | Default | Reason |
|---|---|---|
| Core language and packaging | Python 3.11+, one package managed with `uv` | Keeps the team on one backend toolchain and uses mature API and load-generation libraries. |
| Shared contracts | Pydantic v2 is the source of truth; generate JSON Schema and TypeScript types | Keeps API, worker, CLI, fixtures, and frontend contracts aligned. |
| API | FastAPI, with server-sent events (SSE) for dashboard progress | Provides OpenAPI documentation and a straightforward progress stream. |
| Frontend | React, TypeScript, and Vite, using the existing dashboard as the starting point | Fits the proposed dashboard and enables typed API integration. |
| Artifact storage | Filesystem JSON and JSONL artifacts; no database initially | Keeps experiment evidence inspectable and reproducible. Add SQLite only if run listing becomes a bottleneck. |
| Process model | API/control-plane process plus a separate experiment worker; load generation isolated in a subprocess | Keeps API and dashboard work out of the measured request path without requiring Celery or Redis. |

Revisit a default if endpoint discovery or a verified environment requirement makes it unsuitable, and record material changes in an architecture decision record.

## Metrics and decision policy

| Metric | Meaning | Typical unit |
|---|---|---|
| TTFT | Time from request initiation to first generated token | ms |
| ITL | Time between successive generated tokens; aggregation must be defined | ms |
| End-to-end latency | Request start to completion | ms or s |
| Request throughput | Completed requests per elapsed second | requests/s |
| Output-token throughput | Generated output tokens per elapsed second | tokens/s |
| Offered / achieved load | Intended arrival rate / actual delivered rate | requests/s |
| Error rate | Failed requests divided by the declared population | fraction or % |
| Cost per request/token | Estimate based on measured usage and disclosed price assumptions | currency/unit |

A candidate is **FEASIBLE** only when valid evidence supports every required hard constraint passing. It is **INFEASIBLE** when valid evidence shows at least one hard constraint failing, and **INCONCLUSIVE** when measurements are invalid, insufficient, or too uncertain. Execution failure is tracked separately from SLO failure.

The final claim is deliberately bounded:

> “Best verified candidate among the configurations tested in the declared search space and environment.”

SLOKern does not claim global optimality.

## Dashboard

The proposed cyberpunk-inspired command center uses midnight/near-black surfaces, electric cyan accents, restrained violet, legible technical typography, subtle grid/glow effects, accessible contrast, and clear state labels. Aesthetics must never imply evidence the backend has not produced.

Proposed views:

1. **Overview / Command Center** — current experiment, progress, SLO status and budget.
2. **Workload & SLO Builder** — request profile, target rate, thresholds and validation.
3. **Search Space / Tuning Lab** — legal parameters, ranges, candidate budget and search policy.
4. **Live Experiment Monitor** — candidate progress, load, timings, errors and run validity.
5. **Results / Candidate Comparison** — candidate table, trade-offs, baseline and selection rationale.
6. **Verification / Evidence** — search-run versus fresh verification metrics and final verdict.
7. **Run Detail / Report** — immutable specification, environment, artifacts and limitations.

The frontend-only prototype may simulate interactions, but synthetic results must be visibly labelled **DEMO DATA** and must never be presented as a live benchmark.

## Team and ownership

| Owner | Primary responsibility | Deliverable |
|---|---|---|
| **Rajdeep — Technical Lead / Architecture** | Scope, architecture, contracts, deterministic decision policy, integration and final narrative | Working end-to-end system and coherent technical story |
| **Aman — Serving / GPU Infrastructure** | Model/runtime setup, serving adapter, supported settings, environment metadata | Reliable endpoint and verified configuration application |
| **Daksh — Verification / Evaluation** | Constraint evaluator, verification protocol, edge cases and evidence audit | Deterministic verdicts and independent verification |
| **Adriraj — Benchmarking** | Workload fixtures, load generation, raw timings, metric aggregation and run validity | Reproducible benchmark artifacts |
| **Rohan — Optimization / Search** | Candidate space, baseline search, adaptive strategy and selection rationale | Bounded optimizer with transparent decisions |

Each component has one accountable owner. Pairing and review are welcome; ambiguous shared ownership is not. See **[ROADMAP.md](ROADMAP.md)** for the daily sprint plan, task handoffs, dependencies, and acceptance gates.

## Repository layout

Proposed layout; create only directories needed by the implementation.

```text
slokern/
├── README.md
├── ROADMAP.md
├── docs/
│   ├── architecture.md
│   ├── experiment-methodology.md
│   ├── metrics.md
│   ├── decision-policy.md
│   ├── deployment.md
│   ├── demo-script.md
│   └── adr/
├── frontend/
├── backend/
├── slokern/
│   ├── cli/
│   ├── config/
│   ├── workload/
│   ├── serving/
│   ├── loadgen/
│   ├── metrics/
│   ├── evaluator/
│   ├── search/
│   ├── verification/
│   ├── cost/
│   └── reporting/
├── adapters/
├── fixtures/
├── experiments/
├── tests/
├── scripts/
└── artifacts/             # generated locally; do not commit secrets or huge raw runs
```

## Quick start

> **Status:** Replace this template with commands that have been verified in the repository. Do not claim the commands below exist until implemented.

### Prerequisites

- Access to the permitted Nebius model/serving environment.
- Required credentials stored locally or in the platform's secret mechanism.
- Python 3.11+, `uv`, and Node.js for the planned frontend toolchain.
- Sufficient quota for a small smoke test.

### Intended workflow

```bash
# Validate the experiment specification
slokern validate experiments/configs/example.yaml

# Test endpoint and measurement path
slokern smoke-test --config experiments/configs/example.yaml

# Run a bounded experiment
slokern optimize --config experiments/configs/example.yaml

# Independently verify a selected run
slokern verify --run <run-id>

# Export an evidence-backed report
slokern report --run <run-id> --output reports/<run-id>/
```

The first experiment should use one model, one fixture, one baseline configuration, a low target rate, a small candidate budget, and short smoke-test windows. Pipeline correctness comes before performance claims.

## Validation and reproducibility

Every report should preserve or reference:

- the exact workload and SLO specification;
- model/runtime/environment versions and relevant resource metadata;
- effective configuration for each candidate;
- raw request-level measurements;
- metric definitions, units, sample counts and aggregation policy;
- offered and achieved load;
- failed, invalid, or contaminated runs;
- search decisions, stopping reason and cost assumptions;
- independent verification run and its separate verdict.

Use fixed fixtures, explicit warm-up, controlled arrival patterns, stable metric definitions, and bounded budgets. Never quietly drop failed candidates. If the load generator cannot maintain the declared arrival pattern, flag the run as invalid or contaminated rather than crediting the server with a pass.

## Roadmap

The implementation plan is in **[ROADMAP.md](ROADMAP.md)**. It includes:

- a dated sprint through the hackathon submission window;
- daily task assignments for all five members;
- component dependencies and handoff contracts;
- phase exit gates and definition of done;
- contingency plans for model/runtime access, noisy results, and demo failure.

## Hackathon deliverables

- [ ] Working permitted model/serving path.
- [ ] Reproducible workload and SLO specification.
- [ ] Benchmark engine and raw artifacts.
- [ ] Deterministic SLO evaluator.
- [ ] Bounded search and baseline comparison.
- [ ] Independent verification.
- [ ] Dashboard that reflects actual backend state, with mock states labelled.
- [ ] Machine-readable results and readable report.
- [ ] Tests for key decision and failure paths.
- [ ] Setup and reproduction instructions.
- [ ] Architecture diagram, concise presentation and rehearsed demo.
- [ ] Final performance/cost claims checked against the same source artifacts.
- [ ] Official eligibility, model/platform rules, deadline and submission format rechecked.

The project context records **October 30, 2026, at 10:00 AM PDT** as the target deadline (October 30, 10:30 PM India Standard Time). Verify this against the official event page and submission portal; official rules override this planning document.

## Known decisions to finalize

Before running expensive experiments, record these in a short architecture decision record:

- exact model and revision;
- exact Nebius service, serving runtime and version;
- configuration controls the runtime truly supports;
- exact serving adapter and runtime interface after environment discovery;
- workload fixture and arrival policy;
- SLO thresholds and percentile definitions;
- measurement budget, timeouts and retry behavior;
- cost data source and accounting assumptions;
- search algorithm in the shipped version;
- artifact retention/redaction policy;
- authentication and API contract;
- whether optional AI-assisted planning belongs in the MVP.

Do not assume a model is available because it is NVIDIA-branded, a parameter is tunable because it exists in another runtime, or a price is known because the platform is cloud-hosted.

---

## Final principle

SLOKern should earn trust by making a difficult engineering decision **measurable, reproducible, explainable, and independently verifiable**.

**Optimize inference. Verify performance.**
