# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

1. **LLM Infrastructure & Platform Engineers:** Deploying, rightsizing, and operating production inference serving clusters (vLLM on cloud accelerators including Nebius Cloud and NVIDIA GPUs, as well as local Ollama workstations). They operate under strict, business-critical latency SLAs (e.g., TTFT P95 ≤ 50 ms, Inter-Token Latency, and throughput floors) where tail-latency spikes degrade interactive user experience and over-provisioning GPUs wastes thousands of dollars in cloud spend.
2. **Hackathon Judges & Technical Evaluators:** Reviewing verifiable LLM inference optimization, proof of verification independence, and deterministic evaluation in a crisp, 3-minute decision-first demo.

## Product Purpose

SLOKern replaces trial-and-error guesswork in LLM inference serving with automated, deterministic systems optimization and verification. Given a declared workload traffic profile and non-negotiable hard service-level objectives (SLOs), SLOKern systematically measures a bounded set of serving configurations, identifies the lowest-cost configuration that satisfies all declared constraints, and independently verifies the recommendation under a fresh run ID before publishing deployment recommendations.

Success means finding and independently verifying the optimal serving configuration without guessing, exceeding experiment budgets, or masking constraint violations.

## Positioning

**"Do not guess the optimal configuration. Find it experimentally, then verify it."**

Unlike benchmark visualization tools or heuristic auto-scalers:
1. **Mandatory Independent Verification:** Feasibility is a candidate property; verification is a distinct physical experiment rerun (`verification_run_id`) with strict metric drift tolerances. A recommendation is never marked verified without passing this secondary run.
2. **Deterministic Evaluation:** Hard constraint evaluation and ranking are strictly owned by versioned, deterministic Python code. No LLM or heuristic scorer may override hard SLO thresholds or pass/fail verdicts.
3. **Four-Domain State Separation:** Clean decoupling between Execution state (Completed, Running, Failed), Telemetry state (live vs. simulated), Feasibility verdict (Feasible, Infeasible, Inconclusive), and Verification verdict (Verified, Failed, Stale, Pending).
4. **Honest Provenance & Pricing:** Absence of verifiable pricing falls back to a non-monetary systems proxy (e.g. throughput under SLO, GPU-seconds per request). Fixtures are persistently labeled `DEMO DATA`.

## Operating Context

- **Workflow:** Define workload traffic shape (arrival rate, mean prompt/output tokens) → specify hard SLO constraints (TTFT P95, minimum throughput, error rate) → preflight smoke test → measure baseline and candidate configurations → evaluate feasibility → rank by cost/throughput → trigger independent verification rerun → generate tamper-evident engineering dossier.
- **Environments & Runtime:** vLLM inference engine, NVIDIA A100/H100 GPUs, Nebius Cloud serverless/VMs, local Ollama runtime (`qwen3:4b-instruct-2507-q4_K_M`), OpenAI-compatible serving endpoints, Linux containerized workers.
- **Interface Surface:** High-density, Apple-grade macOS Pro Workstation dashboard (React 19 + TypeScript + Vite) and CLI (`slokern verify`, `slokern optimize`, `slokern smoke-test`).

## Capabilities and Constraints

- **Bounded Search Budget:** Experiment search space is strictly bounded to a fixed 2×2 configuration matrix (max batch size × max concurrency) plus 1 baseline run and 1 independent verification rerun (maximum 6 physical runs total).
- **Three-Valued Feasibility Logic:** Evaluator produces `FEASIBLE`, `INFEASIBLE`, or `INCONCLUSIVE` with explicit reason codes (`P95_BREACH`, `THROUGHPUT_FLOOR_BREACH`, `ERROR_RATE_BREACH`, `MISSING_METRIC`, `INSUFFICIENT_SAMPLES`). Missing or incomplete data is never treated as passing.
- **Microsecond Request Tracing:** Raw request events (`RawRequestMeasurement`) are captured as unaggregated JSONL traces before metric aggregation.
- **Non-Destructive Execution:** MVP does not automatically alter live production clusters; it outputs validated, verified configuration parameters for engineering review.

## Brand Commitments

- **Name:** SLOKern (SLO Kernel)
- **Tagline:** *Optimize inference. Verify performance.*
- **Visual Identity:** "Obsidian Black × NVIDIA Green" design language. Near-black foundations (`#080A09`, `#0E120F`), restrained neon green accents (`#76B900`, `#95D500`), subtle edge illumination, crisp monospace data typography (`DM Mono`), high tabular numeric density, and strong information hierarchy.
- **Voice:** Authoritative, disciplined, systems-engineering tone. Zero marketing fluff, zero unearned claims, transparent disclosures of measurement boundaries.

## Evidence on Hand

- **Deterministic Contracts:** Pydantic models in `src/slokern/contracts/` (`workload.py`, `slo.py`, `measurements.py`, `metrics.py`, `feasibility.py`).
- **Core Engine:** Feasibility evaluator (`src/slokern/core/evaluator/`), deterministic ranker (`src/slokern/core/ranker/`), verification runner (`src/slokern/core/verification/`).
- **Validated Test Suite:** 435 passing tests across 67 test files (`tests/unit/`, `tests/contract/`, `tests/cli/`), with contract schemas 100% verified.
- **Demo Fixtures:** Realistic multi-run experiment records in `fixtures/demo/demo_experiment.json` and offline campaign validation artifacts.
- **Verified Frontend:** High-density control plane in `frontend/src/` with zero console errors and clean responsive layouts down to 360px.
- **Absences:** Live cloud GPU endpoints are not currently active in this workspace; all UI and benchmark runs in the local demonstration are honestly labeled `DEMO DATA`.

## Product Principles

1. **Evidence Over Theory:** Never guess the optimal configuration. Bounded empirical evidence and physical measurements outrank theoretical models or vendor marketing claims.
2. **Verification is a Hard Gate:** A candidate configuration marked feasible during exploration is never awarded verified status without passing a secondary, independent run under fresh run conditions.
3. **Deterministic Governance:** Metrics calculation, constraint evaluation, candidate ranking, and verification verdicts are governed exclusively by deterministic algorithms.
4. **Transparent Provenance:** Every metric links to microsecond-accurate raw traces; synthetic demo fixtures and simulation states are persistently and unmistakably identified.
5. **Operational Restraint:** Prioritize density, scanability, keyboard efficiency, and reliable systems control over decorative visual distraction.

## Accessibility & Inclusion

- Full compliance with WCAG 2.1 AA contrast requirements across all dark surfaces (minimum 4.5:1 for muted text, >7:1 for primary text, and luminous neon accents for focus rings).
- Dual-layer reduced motion support: respects both OS-level `prefers-reduced-motion: reduce` and in-app `.reduce-motion` user preferences.
- Accessible semantic names, ARIA states (`aria-pressed`, `aria-checked`, `aria-selected`, `aria-label`), keyboard scrubbing (Arrows, Home, End, Escape), and visible 2px neon focus rings.

## Hardening & Resilience

- **Fail-Safe Component Isolation:** Global `<ErrorBoundary>` wrapping active workspace views intercepts uncaught exceptions with clinical `EXECUTION_RENDER_ERROR` metadata disclosure and view recovery without crashing sidebar navigation or control-plane telemetry.
- **Mathematical Boundary Defense:** Latency, throughput, and headroom formatters strictly guard against `NaN`, `Infinity`, negative durations, and IEEE 754 precision artifacts.
- **Input Sanitization:** Workload & SLO configuration fields enforce numerical finiteness, positive rate floors, and integer stepping.
- **Zero Antipattern Footprint:** 100% compliance with Impeccable detector checks (0 blocking, 0 advisory issues).
