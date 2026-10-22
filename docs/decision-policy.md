<!--
Purpose: Versioned SLO feasibility and verdict policy.
Owner: Daksh
-->

# SLOKern — Decision Policy & Verdict Rules

## Core Philosophy
SLOKern evaluates LLM inference benchmark runs using versioned, deterministic logic. No LLM or non-deterministic heuristic may override a verdict.

## 1. Verdict States

A candidate run must be assigned exactly one of the following states:

1. **FEASIBLE**: Valid evidence proves that every required hard constraint passed.
2. **INFEASIBLE**: Valid evidence shows that at least one hard constraint failed.
3. **INCONCLUSIVE**: Measurements are invalid, missing, insufficient, or contaminated.

## 2. Hard Constraints Evaluated

Each run is checked against the following thresholds:
* **Time to First Token (TTFT)**: Measured P90 or P99 latencies must be <= Target TTFT (ms).
* **Inter-Token Latency (ITL)**: Measured P90 or P99 inter-token gap must be <= Target ITL (ms).
* **Error Rate**: Percentage of failed requests must be <= Maximum Allowed Error Rate (typically 0.0%).
* **Minimum Sample Count**: The run must record at least N valid completed requests (e.g., >= 50 requests).

## 3. Failure Reason Codes

When a run is evaluated as `INFEASIBLE` or `INCONCLUSIVE`, it must be accompanied by one or more explicit reason codes:

| Reason Code | Category | Meaning |
|---|---|---|
| `TTFT_EXCEEDED` | Infeasible | Measured TTFT percentile exceeded the target threshold. |
| `ITL_EXCEEDED` | Infeasible | Measured inter-token latency exceeded the target threshold. |
| `HIGH_ERROR_RATE` | Infeasible | Failed requests exceeded the maximum allowed error rate. |
| `OOM_CRASH` | Infeasible | GPU Out-Of-Memory exception detected during test. |
| `INSUFFICIENT_SAMPLES` | Inconclusive | Total completed request count is below the minimum valid sample threshold. |
| `MISSING_METRICS` | Inconclusive | One or more required metric fields were missing from the benchmark artifact. |
| `RUN_CONTAMINATED` | Inconclusive | Load generator saturation or clock drift flagged the run as invalid. |

