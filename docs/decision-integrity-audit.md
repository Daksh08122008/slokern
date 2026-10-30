# SLOKern Decision Integrity Audit

**Date:** 2026-10-30  
**Scope:** `exp-audit-offline-campaign`, its persisted fixture/artifacts, evaluator and search implementation, experiment API, and dashboard paths.  
**Result:** The selected `audit-offline-validation` campaign artifacts, evaluator verdicts, corrected API response, and corrected UI agree for the five DEMO DATA search runs. The stored raw-artifact URIs still point to missing paths, so artifact provenance is not fully reconciled and this audit does not claim complete acceptance.

## Executive findings

| Observation | Root cause | Classification | Corrective action |
|---|---|---|---|
| `15594344d2bf` was shown as `INFEASIBLE` and as winner | The old demo scenario overrode feasibility for presentation, while recommendation selection fell back to the first candidate even when none was feasible. | Frontend | Recommendation selection now requires `FEASIBLE`; the no-feasible state has an explicit UI. The selected artifact says this candidate is `FEASIBLE`. |
| Evaluator said `HARD_CONSTRAINTS_PASSED` alongside an 18 ms p95 breach | The 18 ms message was a presentation-only hardcoded scenario explanation, not generated from metrics or evaluator output. | Frontend | Removed the fabricated breach. The UI now shows evaluator audit notes and reason codes from the run artifact. |
| TTFT p95 12.5 ms appeared as end-to-end p95 under a 500 ms ceiling | The adapter reused TTFT p95 for generic latency, and Overview reused that value for the end-to-end gauge. The persisted spec declares no end-to-end SLO; 500 ms was an invented UI ceiling. | Frontend | Kept TTFT, ITL, and end-to-end distributions separate. SLO cards now show only declared constraints. |
| All candidates showed 160 tokens/s | This is the measured value in the selected DEMO DATA artifacts: each 2 s run generated 20 measured requests × 16 output tokens. The matching value is real for these synthetic runs, but is not evidence of configuration-sensitive live throughput. | Artifact / DEMO DATA | Preserve the value and label its provenance. Do not manufacture candidate differences. |
| Dashboard said Poisson @ 10 rps | Arrival mode was hardcoded in the old dashboard. The persisted campaign fixture says `constant`, target 10.0 rps. | Frontend | API reads workload mode/rate from the matching persisted fixture; UI displays those response fields. |
| Overview showed an 813.8 ms smoke probe and HTTP 200 as LIVE without an artifact | The smoke card used fabricated fallback numbers/status when no `SmokeTestArtifactResponse` was loaded. | Frontend | Missing smoke evidence now renders as unavailable/PENDING; classification and probe/stream values come only from the smoke artifact. |
| Verification view showed synthetic drift/protocol values | The page generated comparison offsets/tolerances and claimed a 2× rerun with constant/Poisson arrival; this campaign specifies a 1× duration multiplier and has no verification run. | Frontend / API | Comparison rows now come only from persisted drift comparisons; absent evidence is empty/PENDING. Protocol and original run ID now use campaign/run artifacts. |
| Five evaluations said `space_exhausted` against a 2×2 grid | `max_candidates=5` counts one baseline plus up to four grid candidates. The 2×2 grid has four unique configurations; all four were evaluated after the baseline. | Search semantics / display | API returns evaluation count, budget, grid size, and stopping reason from artifacts/spec. UI presents “4 parameter configurations + baseline”. |
| Head-to-head did not identify its comparison reference | The old display named baseline and selected values without a durable reference label. | Frontend | Comparison now identifies `Baseline <id> vs Selected <id>`. |
| Raw trace references in run records are stale | Five `raw_artifact_uri` fields point under `artifacts/experiments/...`, but the actual JSONL files are under `artifacts/audit-offline-validation/experiments/...`. | Artifact | Requires an authorized correction to the five persisted run records; no existing artifact was overwritten during this audit. |

## Authoritative campaign evidence

The API's selected experiment directory is `artifacts/audit-offline-validation/experiments/exp-audit-offline-campaign` (the route explicitly prioritizes this directory). The corresponding original spec is `fixtures/campaigns/audit_offline_campaign.json`.

The fixture declares:

- `arrival_mode`: `constant`; `target_offered_rate`: `10.0` rps; `measurement_duration_s`: 2 s.
- Constraints: TTFT p95 ≤ 2500 ms; ITL p50 ≤ 30 ms; error-rate mean ≤ 0.05 (fraction). There is no end-to-end latency constraint, so the displayed 500 ms ceiling was not authoritative.
- Search grid: `max_num_batched_tokens ∈ {1024, 2048}` and `max_num_seqs ∈ {16, 64}`: four unique legal grid configurations.
- `budget.max_candidates`: 5. In this controller, this yields baseline + at most four grid candidates.

`search_result.json` lists five candidate IDs, all with `FEASIBLE` and ranking metric 160.0. It selects `15594344d2bf`, objective `max_throughput_under_slo`, rationale “highest finite output-token throughput … among FEASIBLE tested candidates; ties are broken by candidate ID”, and stopping reason `space_exhausted`. The baseline is the selected candidate; its effective config is the baseline default (32 sequences, 2048 batched tokens), which is not one of the four grid points.

### Candidate results

Values below are read from the corresponding `metrics.json` and `feasibility.json` in the selected artifact tree. Percentiles are milliseconds; throughput is output tokens/second. The table shows the two grid dimensions; every `applied_config.json` also records `gpu_memory_utilization=0.9`, `max_model_len=2048`, `kv_cache_dtype=auto`, and `tensor_parallel_size=1`. Each run record's `requested_config` is null; the effective applied config is recorded in `applied_config.json`.

| Candidate | Run | Effective config (`max_num_seqs`, `max_num_batched_tokens`) | TTFT p95 | ITL p50 | ITL p95 | End-to-end p95 | Throughput | Evaluator |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `15594344d2bf` | `run-83697f4a197e` | 32, 2048 (baseline) | 12.500548 | 8.052333 | 8.071767 | 133.499086 | 160.0 | FEASIBLE |
| `370359a9c14b` | `run-370a3c4cf59f` | 16, 1024 | 12.523568 | 8.030333 | 8.048167 | 133.166385 | 160.0 | FEASIBLE |
| `369e9bc42eb7` | `run-d80541ee06d8` | 64, 1024 | 14.170432 | 8.103000 | 8.116333 | 135.833430 | 160.0 | FEASIBLE |
| `565eb88bb613` | `run-7d1716b0bc3c` | 16, 2048 | 12.580419 | 8.027333 | 8.050067 | 133.284032 | 160.0 | FEASIBLE |
| `c3d86d00124b` | `run-05f4e30163c8` | 64, 2048 | 14.150405 | 8.103667 | 8.129600 | 136.092317 | 160.0 | FEASIBLE |

Each run has 30 raw JSONL records: 10 warm-up and 20 measured, zero failed requests. The metric engine was rerun against each raw JSONL with the fixture's 10 rps target and 2 s measurement duration. All persisted metric fields matched recomputation within 1e-9; `evaluate_slo` independently returned `FEASIBLE` for all five. The 160.0 tok/s values equal 20 × 16 / 2 seconds. These are DEMO DATA measurements from the fake adapter, not LIVE performance evidence.

The active campaign has no independent verification record in the selected audit artifact directory. Verification remains **PENDING**. An identically named historical tree under `artifacts/experiments/` contains additional runs and verification files; it is not the directory selected by this API path and was not merged into the authoritative table above.

## Root-cause trace

### Evaluator and reason codes

The evaluator compares declared metric/statistic/threshold tuples against their matching `MetricSet` fields and produces constraint evaluations, reason codes, and audit notes (`src/slokern/core/evaluator/evaluate.py`, `src/slokern/core/metrics/aggregate.py`, `src/slokern/core/metrics/percentiles.py`). The artifact's TTFT p95 is about 12.5 ms against 2500 ms, ITL p50 is about 8.0 ms against 30 ms, and error rate is zero against 0.05. Thus every declared hard constraint passes. The “18 ms” breach has no corresponding metric or failed constraint in any selected `metrics.json`/`feasibility.json`; it was not a unit conversion or stale metric. It was a hardcoded UI explanation attached to a demo infeasibility scenario.

The corrected candidate route derives `feasibilityVerdict`, failed reason codes, and audit text from `feasibility.json`, and emits `WINNER` only when the selected candidate is also `FEASIBLE`. It no longer supplies default numeric metrics or a default feasible status when artifacts are missing.

### Ranking and stopping

The grid controller uses the declared 2×2 product space, caps grid candidates at four, evaluates the baseline separately, and records the stop condition (`src/slokern/core/search/grid.py`, especially the candidate limit and completion branch). The ranker excludes non-feasible candidates, then sorts by objective metric and candidate ID (`src/slokern/core/search/ranking.py`). With five equal-throughput feasible records, the selected ID is the tie-break result recorded in `search_result.json`. Five evaluations are not five distinct grid points: they are one baseline plus four unique grid points.

### Backend-to-frontend path

The experiment API selects the audit artifact tree, reads `search_result.json`, run status/metrics/feasibility/applied config, and resolves the campaign fixture by `experiment_id` (`src/slokern/api/routes/experiments.py`). Its corrected response carries actual arrival mode/rate, SLO constraints, objective, evaluation count, budget, grid size, stopping reason, candidate metrics, feasibility, reason codes, and verification state. Missing data is represented as unavailable rather than fabricated numeric defaults.

`frontend/src/lib/adapters/viewModel.ts` keeps TTFT p95 distinct from ITL and end-to-end p95, preserves throughput units, treats absent feasibility as `INCONCLUSIVE`, and exposes only a feasible selected recommendation. Overview uses fixture-backed constraints/workload fields and artifact-backed smoke evidence; missing smoke evidence stays PENDING. Tuning Lab uses the API ranking objective and candidate artifacts. Candidate chart domains come from displayed measurements and have no invented SLO threshold region. Head-to-head text identifies the baseline and selected candidate. Verification comparison rows now use persisted drift evidence only; no synthetic deltas or protocol assumptions are shown. The no-feasible demo scenario explicitly says it overrides feasibility for presentation and is not an evaluator result. DEMO DATA and PENDING provenance remain distinct.

## Files and line locations

Line numbers below refer to the audited working tree on 2026-10-30.

- Backend artifact selection, fixture lookup, campaign summary: `src/slokern/api/routes/experiments.py:17-55`, `:66-216`.
- Candidate artifact mapping and winner/evaluator behavior: `src/slokern/api/routes/experiments.py:280-390`.
- Verification run identity and pending state: `src/slokern/api/routes/experiments.py:392-456`.
- Search grid and baseline/budget semantics: `src/slokern/core/search/grid.py:247-248`, `:320-354`; legal space: `src/slokern/core/search/space.py:13-49`.
- Metrics aggregation/percentile calculation: `src/slokern/core/metrics/aggregate.py:27-96`, `src/slokern/core/metrics/percentiles.py:38-79`; evaluator: `src/slokern/core/evaluator/evaluate.py:101-156`.
- Frontend mapping and feasible recommendation: `frontend/src/lib/adapters/viewModel.ts:74-117`.
- Explicit demo-only infeasibility scenario and recommendation selection: `frontend/src/App.tsx:350-388`.
- Workload, winner/no-winner, SLO, budget, and baseline-reference rendering: `frontend/src/views/OverviewView.tsx:90-100`, `:251-255`, `:287-352`, `:480-510`.
- Tuning Lab feasibility and objective display: `frontend/src/views/TuningLabView.tsx:18-70`, `:195-212`.
- Metric-based tradeoff axes without hardcoded constraint regions: `frontend/src/components/charts/TradeoffPlot.tsx:1-105`.
- Artifact-backed verification comparisons and protocol labels: `frontend/src/views/VerificationView.tsx:18-80`, `:150-160`, `:226-300`.

## Minimal corrections made

1. API campaign summaries and candidate responses now use artifact/spec values, including workload mode, target rate, SLOs, objective, budget semantics, metrics, applied settings, evaluator results, and selection rationale. Missing artifact fields stay missing.
2. Candidate winner status requires both selected ID and `FEASIBLE`; candidate ordering and frontend recommendation cannot turn an infeasible candidate into a winner. An empty feasible set renders “No feasible candidate”.
3. TTFT, ITL, and end-to-end distributions remain separate through the adapter and Overview. SLO cards follow the declared statistic and metric mapping.
4. Removed the fabricated 18 ms breach; reason code and breach text come only from evaluator output.
5. Workload arrival mode/rate, objective, search counts, stopping reason, and head-to-head baseline reference now flow from backend data.
6. Missing metric/config/smoke/verification values render unavailable instead of fabricated values. LIVE smoke-test and PENDING verification provenance remain distinct from DEMO DATA search results.

## Regression coverage and validation

- `tests/unit/api/routes/test_experiments.py`: selected infeasible candidate is not winner; evaluator reason and end-to-end p95 are artifact-backed; fixture arrival mode/rate/budget/grid size/count are reported correctly.
- `frontend/test/decisionIntegrity.test.ts` and `frontend/test/status.test.ts`: TTFT/E2E separation, throughput unit preservation, evaluator reason-code mapping, rejection of infeasible winner, empty feasible set, missing smoke artifact stays pending, absent verification comparisons stay empty, and missing evidence validity cannot produce a verified recommendation.
- **Verified:** `.venv\Scripts\python.exe -m pytest tests/unit/api/routes/test_experiments.py -q` — 3 passed.
- **Verified:** `npm test` from `frontend/` — 19 passed, 0 failed (includes missing-evidence, smoke-pending, and no-synthetic-verification handling).
- **Verified:** `npm run build` from `frontend/` — TypeScript build and Vite production build succeeded.
- **Verified:** raw trace recomputation and SLO reevaluation as described above.
- **Not run:** live endpoint or live GPU experiment. The selected campaign is DEMO DATA and has no independent verification record.

## Unresolved artifact integrity item

For all five selected run records, `raw_artifact_uri` points to `artifacts/experiments/exp-audit-offline-campaign/runs/<run-id>/raw_measurements.jsonl`, which does not exist. The JSONL file exists at `artifacts/audit-offline-validation/experiments/exp-audit-offline-campaign/runs/<run-id>/raw_measurements.jsonl`. API reads currently locate the local run directory and tests recompute from the existing JSONL, but the stored URI itself is stale and weakens portable traceability.

Affected run records are `run-83697f4a197e`, `run-370a3c4cf59f`, `run-d80541ee06d8`, `run-7d1716b0bc3c`, and `run-05f4e30163c8`, each in the corresponding `artifacts/audit-offline-validation/experiments/exp-audit-offline-campaign/runs/<run-id>/run_record.json`. Correcting them requires changing persisted artifact files. Per repository filesystem-safety instructions, they were left untouched pending explicit approval. No campaign rerun or verification rerun was performed.
