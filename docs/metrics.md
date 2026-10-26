# SLOKern Metric Definitions & Aggregation Rules

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Specification (Metrics Version: 1.0.0)  
> **Owner:** Rajdeep (Architecture, Benchmarking & Metrics; Historical design: Adriraj)  
> **Authority:** Aligned with [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [docs/ownership.md](ownership.md)

---

## 1. Metric Taxonomy & Principles

Every metric reported by SLOKern should be traceable to unaggregated raw request events logged during the active measurement window. Timestamps are recorded as floating-point epoch seconds; decimal precision in a timestamp is not a claim of microsecond clock accuracy.

### Non-Negotiable Rules

1. **Explicit Units:** Ambiguous terms like "latency" or "speed" are forbidden. Every metric must specify its units (`ms`, `s`, `req/s`, `tok/s`).
2. **Explicit Denominators:** Every rate or percentile must clearly define the sample population and exclusion criteria.
3. **Warm-Up Exclusion:** Requests initiated during the warm-up window (`warmup_duration_s`) are recorded but strictly excluded from all final metric aggregations.
4. **Offered vs. Achieved Separation:** Intended dispatch rate (`offered_load`) must never be conflated with the server's delivered completion rate (`achieved_load`).
5. **No Fabricated Precision:** Percentiles must not imply precision beyond the statistical power of the sample size.
6. **Monotonic Clocks for Elapsed Durations:** All duration measurements (TTFT, chunk gaps, E2E latency) must use monotonic clocks (`time.monotonic()`) to prevent NTP clock jumps. Wall-clock timestamps (`time.time()`) are retained solely for audit correlation.
7. **Provenance Separation & Honest Disclosure:** Local observations carry host metadata (never attributed to NVIDIA H100 or Nebius); fake data carry **`DEMO DATA`**; Nebius measurements require verified cloud provenance. Where evidence is missing, fields must be marked `unavailable` rather than fabricated.

---

## 2. Core Metric Specifications

### 2.1 Time to First Token (TTFT) & First-Content Latency
- **Definition:** Defined and measured as client-observed request-start-to-first-content latency using monotonic duration clocks (`time.monotonic()`). Because streaming chunks from serving runtimes may contain more than one token, this measures first-content-chunk receipt.
- **Start Event:** Timestamp recorded immediately prior to HTTP dispatch (`sent_at`). Socket-level wire transmission is not falsely claimed.
- **End Event:** Receipt timestamp of the first non-empty content chunk (`first_token_at`).
- **Units:** Milliseconds (`ms`).
- **Server Metadata Disambiguation:** Server-reported Ollama timing metadata (`prompt_eval_duration`, `eval_duration`) is preserved in separate metadata fields, converted from nanoseconds to milliseconds, without conflating with client-observed TTFT.
- **Population:** Valid, non-error, non-warmup records with `first_token_at` present and `output_tokens >= 1`.
- **Aggregations:** Median (`p50`), 90th percentile (`p90`), 95th percentile (`p95`), 99th percentile (`p99`), and arithmetic mean.
- **Missing Data Handling:** If a request aborts, times out, or fails before emitting a token, TTFT is recorded as `null` and the request increments the error count.

### 2.2 Inter-Token Latency (ITL) & Chunk-Gap Intervals
- **Definition:** Streaming chunk intervals are recorded as chunk-arrival gaps, not as guaranteed individual token-level ITL, because server chunks may carry multiple tokens. Inventing token-level timestamps from multi-token chunks is prohibited.
- **Source:** Mean of recorded chunk intervals (`itl_observations_ms`) for the request when present; otherwise `(completed_at - first_token_at) * 1000 / (output_tokens - 1)`.
- **Units:** Milliseconds per token (`ms/tok`) when token granularity is proven; otherwise milliseconds per chunk gap (`ms/chunk`).
- **Population:** One average per valid, non-error, non-warmup request with at least two output tokens.
- **Aggregations:** Percentiles are calculated across those per-request averages, not across every chunk interval globally.
- **Missing Data Handling:** Non-streaming runs or single-token responses omit ITL (`null`).

### 2.3 End-to-End Request Latency (E2E)
- **Definition:** Total round-trip time experienced by the client from initial dispatch to full response completion.
- **Start Event:** Client socket write timestamp (`sent_at`).
- **End Event:** Final stream closing or complete payload receipt (`completed_at`).
- **Units:** Milliseconds (`ms`).
- **Population:** All completed requests within the measurement window.
- **Aggregations:** `p50`, `p90`, `p95`, `p99`, arithmetic mean, min, max.

### 2.4 Request Throughput
- **Definition:** The rate of successfully completed requests delivered by the serving system.
- **Formula:**
  $$\text{Request Throughput} = \frac{N_{\text{completed\_valid\_requests}}}{\Delta t_{\text{measurement\_window}}}$$
- **Units:** Requests per second (`req/s`).
- **Population:** Valid completed requests within the active measurement window.

### 2.5 Output-Token Throughput
- **Definition:** The total rate of generated output tokens produced by the serving system across all concurrent streams.
- **Formula:**
  $$\text{Token Throughput} = \frac{\sum_{i=1}^{N} \text{output\_tokens}_i}{\Delta t_{\text{measurement\_window}}}$$
- **Units:** Tokens per second (`tok/s`).
- **Population:** Sum of output tokens generated by requests completed within the measurement window.

### 2.6 Offered Load vs. Achieved Load & Generator Saturation
- **Offered Load (`offered_load_rps`):** The rate at which the client load generator attempted to dispatch requests according to the declared arrival schedule (`WorkloadSpec`).
  $$\text{Offered Load} = \frac{N_{\text{dispatched\_requests}}}{\Delta t_{\text{measurement\_window}}}$$
  - **Units:** Requests per second (`req/s`).
- **Achieved Load (`achieved_load_rps`):** The rate of valid, completed requests received by the client across the declared active measurement window. It equals `request_throughput_rps` in the current implementation.
  $$\text{Achieved Load} = \frac{N_{\text{completed\_valid\_requests}}}{\Delta t_{\text{measurement\_window}}}$$
  - **Units:** Requests per second (`req/s`).
  - *Distinction:* Achieved load reflects server delivery rate under the offered pressure, whereas offered load reflects client dispatch fidelity.
- **Disambiguating Throughput, Load, and Hardware GPU Utilization:**
  - *Request Throughput:* Rate of completed valid requests over time ($N_{\text{valid}} / \Delta t$).
  - *Achieved Load:* Request completion rate under offered traffic schedule.
  - *GPU Utilization:* Hardware-level compute core or memory occupancy percentage (e.g. via NVML). **Do not confuse request throughput, achieved load, and GPU utilization.** A configuration may achieve high throughput with low GPU compute utilization, or saturate GPU memory while delivering low throughput.
- **Generator Saturation Flag (`generator_saturated`):** A critical boolean health indicator reflecting whether the benchmark client experienced thread starvation, event loop lag, or dispatch queue delays.
  - *Trigger Conditions:* Set to `True` if:
    1. Client dispatch latency (delay between scheduled time and socket write start) exceeds 10 ms; OR
    2. Delivered offered load deviates from the declared target arrival rate by more than 10%.
  - *Current trigger:* mean dispatch lag >10 ms, or computed offered rate <90% of target. This checks average lag, not p99 lateness; the proposed p99 ≤20 ms, CPU <70%, and achieved/offered ≥0.98 gates are not implemented.
  - *Current evaluator behavior:* `generator_saturated` yields `EvidenceValidity.CONTAMINATED` and `INCONCLUSIVE`. The ranker only checks the feasibility verdict; other run execution/record validity is not supplied to the evaluator.


### 2.7 Error Rate
- **Definition:** The fraction of non-warmup records whose `error_type` is set or whose HTTP status is present and not 200, divided by all non-warmup records. Invalid records with no error/status marker are not included in `failed_request_count` by the current implementation.
- **Formula:**
  $$\text{Error Rate} = \frac{N_{\text{failed\_requests}}}{N_{\text{total\_offered\_requests}}}$$
- **Units:** Dimensionless fraction ($0.0 \le \text{rate} \le 1.0$) or percentage (`%`).
- **Population:** All requests scheduled during the measurement window.

### 2.8 Cost Metrics & Unavailable Fallbacks
- **Mode B (Default):** Mode B (Non-Monetary Systems Proxy) is the default cost accounting mode until authoritative, verified cloud pricing is provided.
- **Monetary Cost Fallback:** When official, verified hourly pricing cannot be established reliably, monetary cost must be reported explicitly as **`unavailable`** (never fabricate or guess prices!).
  $$\text{Cost per 1k Requests (Mode A)} = \frac{\text{Hourly Rate}}{\text{Requests per Hour}} \times 1000 \quad [\text{or } \texttt{"unavailable"}]$$
- **GPU Seconds per Request Fallback:** When operating in Mode B on dedicated GPU instances with verifiable hardware allocation:
  $$\text{GPU Seconds per Request} = \frac{\Delta t_{\text{measurement\_window}} \times N_{\text{GPUs}}}{N_{\text{completed\_valid\_requests}}}$$
  - *Fallback Rule:* If the deployment environment cannot provide verified GPU count or dedicated instance residency (e.g., managed serverless endpoints where physical GPU allocation is abstracted), GPU-seconds per request cannot be reliably calculated and must be reported as **`unavailable`**.
  - In such cases, the system ranks feasible candidates by **Throughput Under SLO** (maximum output tokens per second or requests per second while satisfying all declared hard constraints).

---

## 3. Percentile Calculation Method

Percentiles are computed deterministically using the standard **linear interpolation method** (equivalent to NumPy/Pydantic `percentile(..., method='linear')`):

1. Sort valid sample values in ascending order: $v_1 \le v_2 \le \dots \le v_N$.
2. Compute index $i = (N - 1) \times \frac{p}{100}$.
3. Decompose $i$ into integer part $k$ and fraction $f$: $i = k + f$.
4. Value $P_p = v_k + f \times (v_{k+1} - v_k)$.

### Minimum Sample Thresholds
- The percentile helper computes p50/p90/p95/p99 for any non-empty sample vector; it does not implement per-percentile minimum counts or confidence intervals.
- `SLOSpec.min_sample_count` is the current general minimum valid request count used by the evaluator. If total `MetricSet.sample_count` is below this declared threshold, the evaluator returns `INCONCLUSIVE`.
- Proposed methodology: collect at least 2,000 measured requests and use p95 as the primary tail constraint. Keep p99 informational unless the pre-registered sample size provides enough tail observations. Bootstrap confidence intervals are a proposal; no bootstrap implementation exists.

### Metrics not currently represented
- **TPOT:** There is no `tpot_ms`/TPOT field in `MetricSet`; the proposed formula `(E2E - TTFT) / (completion_tokens - 1)` is not an implemented metric.
- **Queueing, GPU utilization, cache state, preemption, and client CPU:** These are not current `MetricSet` fields. Do not report them as measured unless a separate source and artifact are added.
- **Validity details:** `RawRequestMeasurement.is_valid` exists, but `MetricSet` does not expose invalid-record counts or a general run-validity summary. `RunRecord.execution_status` is a separate field, and current `evaluate_slo()` only sees `MetricSet` plus `SLOSpec`.

---

## 4. Related Documentation

- [System Architecture](architecture.md)
- [Decision Policy & Feasibility Semantics](decision-policy.md)
- [Experiment & Measurement Methodology](experiment-methodology.md)
- [ADR 0002: Dual-Mode Cost Accounting](adr/0002-cost-model.md)
