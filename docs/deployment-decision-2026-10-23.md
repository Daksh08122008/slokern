# SLOKern deployment and model alternative study

> **Status:** Exploratory alternative, not the accepted deployment decision. This memo's 9B H100-VM recommendation conflicts with accepted ADR 0001-B's Nemotron 30B-A3B FP8 candidate. DEC-0013 in `docs/decision-log.md` records the conflict. The current user-provided proposal is 30B-A3B on Nebius Serverless AI with vLLM 0.12.0, pending owner ratification and preflight. Do not use this memo to override that accepted model-family decision.

**Research date:** 2026-10-23
**Purpose:** Research and planning only. No code, cloud resources, account settings, or credentials were changed.
**Evidence labels:** **Verified** = supported by current official documentation or repository source; **Estimate** = planning arithmetic, not measured; **Open** = account-specific or requires a preflight.

## 1. Executive recommendation

This alternative study compared deployment choices and recommended one **Nebius AI Cloud H100 80 GB GPU**, NVIDIA **Nemotron Nano 9B v2**, and a digest-pinned **vLLM OpenAI-compatible server**. That recommendation is **not the accepted project decision**: ADR 0001-B retains Nemotron-3-Nano-30B-A3B FP8 as the model-family candidate, and DEC-0013 leaves the newly proposed Serverless/vLLM 0.12.0 profile unresolved. The 9B VM path below is an option for owner review only; do not use it to provision resources or claim the active project profile.

The strongest reason to select the VM is measurement control: it allows SLOKern to restart the same engine/model/GPU with candidate startup flags, capture the effective command, and keep the model cache on persistent disk. Nebius documents a one-GPU H100 configuration (16 vCPUs, 200 GB host RAM) and self-service H100 access. Actual project quota, region/preset availability, and capacity must still be checked. [Nebius H100](https://nebius.com/h100), [VM platform listing](https://docs.nebius.com/compute/virtual-machines/list-platforms), [capacity advisor](https://docs.nebius.com/compute/virtual-machines/capacity-advisor).

**Hackathon qualification caveat:** the official rules define “runs on Nebius AI Cloud” by naming Serverless Jobs, Serverless Endpoints, and DevPods. They do not explicitly name a self-managed GPU VM in that definition. Safest options are (a) obtain organizer confirmation that a Nebius H100 VM qualifies, or (b) include a genuine Token Factory runtime call as part of the product, with a user-visible Nemotron explanation feature that is strictly advisory. Do not let that model determine SLO verdicts, ranks, or numeric claims. The latter is the recommended compliance bridge if a quick rules clarification is unavailable. [Official rules](https://nebiusglobalaihackathon.devpost.com/rules).

Do not implement two benchmark tracks for the submission window. Ship the controlled H100/vLLM experiment first. Defer a separate managed-endpoint benchmark; keep Token Factory available for a clearly identified managed-service baseline or the optional explanation feature.

## 2. Verified Nebius options and limitations

| Option | Verified capability | What it does not establish | Decision |
|---|---|---|---|
| Token Factory public inference | OpenAI-compatible API; current project model list is available at `GET /v1/models`; request-time generation parameters are supported. The inference docs say API callers get the full vLLM request-parameter set. | The public API does not document control/read-back of vLLM process-start settings such as `--max-num-batched-tokens` and `--max-num-seqs`. Shared service routing, batching, capacity changes, and autoscaling can confound comparisons. Exact models and access must be queried with the project key. | Use for an explicitly managed baseline or explanation call, not the engine-knob search. [API overview](https://docs.tokenfactory.nebius.com/ai-models-inference/overview), [List models API](https://docs.tokenfactory.nebius.com/api-reference/models/list-models). |
| Token Factory Dedicated Endpoints | Nebius describes isolated deployments with selectable region, GPU type/count per replica, replica bounds/autoscaling, lifecycle controls, and separate endpoint routing keys. | Public docs reviewed do not prove support for the two scheduler flags in SLOKern’s grid. Dedicated endpoint template/model availability, pricing, and capacity are project-dependent. | Strong future managed option if SLOKern later searches deployment size/replicas; not a substitute for demonstrated vLLM scheduler controls. [Nebius announcement](https://nebius.com/blog/posts/dedicated-endpoints-and-custom-weights-hub), [Token Factory docs](https://docs.tokenfactory.nebius.com/llms.txt). |
| Nebius Serverless AI Endpoint | Custom containers, image, entrypoint/arguments, environment/secrets, GPU platform/preset, disk, and network are configurable. Nebius shows an H100 preset example and a vLLM-compatible endpoint. This is a plausible low-operations way to host custom vLLM and is explicitly named by the hackathon rules. | A model endpoint’s lifecycle and model-cache persistence add complexity when the process must be restarted for each candidate. Stopping releases its VM and disk; a mounted volume persists separately and is billed. | Good alternate if VM-only hackathon eligibility is not accepted. Prefer one endpoint whose process can be restarted without tearing down the endpoint; otherwise plan for update/recreate, readiness checks, and persistent model storage. [Endpoint management](https://docs.nebius.com/serverless/endpoints/manage), [LLM endpoint tutorial](https://docs.nebius.com/serverless/tutorials/deploy-model), [lifecycle and billing](https://docs.nebius.com/serverless/maintenance/stop-start). |
| Nebius H100 VM | H100 is offered as self-service; the current catalog includes `gpu-h100-sxm` / `1gpu-16vcpu-200gb` and 80 GB GPU memory. A normal VM provides the simplest persistent cache and direct server-process control. | Public listing is not proof that this project has a quota or available capacity in a given region. The current docs list project/region-specific platform and preset checks. | **Primary controlled track.** Query quota, preset list, and Capacity Advisor before launch. No Kubernetes, Slurm, or multi-node configuration is needed. [H100 offering](https://nebius.com/self-service), [VM types](https://docs.nebius.com/compute/virtual-machines/types), [project presets](https://docs.nebius.com/compute/virtual-machines/list-platforms), [capacity advisor](https://docs.nebius.com/compute/virtual-machines/capacity-advisor). |
| Serverless Jobs | Nebius supports custom container jobs for tasks that run to completion. | A job is not a persistent OpenAI-compatible serving endpoint for the workload generator. | Not the serving runtime. Could host an offline SLOKern benchmark worker later. [Serverless overview](https://docs.nebius.com/serverless/overview). |

The Nebius H100 product page documents self-service and an H100 80 GB configuration; the VM type catalog currently associates the H100 SXM platform with `eu-north1`. This is platform availability, not confirmation of the user’s account’s quotas or free capacity. Check the project’s region-specific preset list and Capacity Advisor immediately before provisioning.

## 3. Model comparison and decision

| Candidate | Current ID / revision evidence | License / serving evidence | Fit and decision |
|---|---|---|---|
| **NVIDIA Nemotron Nano 9B v2** | `nvidia/NVIDIA-Nemotron-Nano-9B-v2`; current HF revision observed as `6533e8de2c68e4536bf7c411d7a3ce5734111476`. Pin this exact commit after rechecking it at launch. | NVIDIA Open Model License; publisher lists BF16 weights, H100-80GB support, vLLM support, and a vLLM command. It requires `--trust-remote-code` and `--mamba_ssm_cache_dtype float32`; the model card warns that omitting the latter may reduce accuracy. | **Primary.** Fits one H100 with useful cache headroom, directly demonstrates an NVIDIA open model, and is large/complex enough for a credible serving experiment. The short-context concurrency behavior still needs preflight measurement. [Model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2), [pinned revision](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2/tree/6533e8de2c68e4536bf7c411d7a3ce5734111476), [license](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/). |
| **Qwen3-8B** | `Qwen/Qwen3-8B`; observed revision `a0809d1efaf104a46bbc2acaecd69617e9696312`. Recheck and pin the model and tokenizer revisions together. | Apache-2.0; publisher documents vLLM serving. Config has 36 layers, 8 KV heads, 128-dimensional heads, and max position 40,960. | **Fallback.** Simplest permissively licensed non-NVIDIA comparison if Nemotron remote-code/kernel integration fails. If used as the main benchmark model, retain a separate real NVIDIA-model use in the product for hackathon compliance. [Model card](https://huggingface.co/Qwen/Qwen3-8B), [pinned revision](https://huggingface.co/Qwen/Qwen3-8B/tree/a0809d1efaf104a46bbc2acaecd69617e9696312). |
| Mistral-7B-Instruct-v0.3 | `mistralai/Mistral-7B-Instruct-v0.3`; pin a current commit before use. | Apache-2.0; vLLM-compatible. | Rejected as first fallback: technically simple but does not meet the NVIDIA-model condition by itself and offers less value than the selected Qwen fallback. [Model card](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3). |
| Meta-Llama-3-8B-Instruct | `meta-llama/Meta-Llama-3-8B-Instruct`; gated HF access. | Meta Llama 3 Community License, not an OSI-style permissive license; HF requires access agreement. | Rejected for schedule and licensing friction; it is also an older 8B candidate than the available Llama 3.1 family. [Model card and license](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct). |
| Nemotron 3 Nano 30B-A3B (existing ADR candidate) | Exact hosted model string and project access are not verified by a live model-list request. | The 30B total-parameter FP8 deployment has more complex hybrid/MoE memory and runtime requirements than a 9B dense-ish target; exact current vLLM image pairing needs extra validation. | Defer as the initial target. It remains a possible later stress target, not a prerequisite for demonstrating the optimization loop. Do not treat its appearance in older project docs or catalog material as account availability evidence. |

The primary model card reports 8,888,227,328 BF16 parameters and approximately 17.8 GB of checkpoint storage. The model supports up to 128K context, but that is not the benchmark target: cap context at 4K for the first experiment. All performance/quality numbers in model cards are publisher results, not SLOKern measurements.

## 4. Primary and fallback model

- **Primary controlled target:** `nvidia/NVIDIA-Nemotron-Nano-9B-v2`, pinned revision `6533e8de2c68e4536bf7c411d7a3ce5734111476` after an execution-time recheck. Freeze tokenizer revision separately and store both hashes.
- **Fallback controlled target:** `Qwen/Qwen3-8B`, pinned model revision `a0809d1efaf104a46bbc2acaecd69617e9696312` after a current recheck; use the tokenizer from that same revision.
- **Optional Token Factory explainer:** query the project’s `GET /v1/models`; select an NVIDIA Nemotron model returned by that account, then use it only to turn already-computed results into a natural-language explanation. The current public Nebius example is `nvidia/Nemotron-3_5-Lightning`, but model route and access must be confirmed in the project catalog. [Nemotron catalog page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference), [List models API](https://docs.tokenfactory.nebius.com/api-reference/models/list-models).

## 5. Serving engine and pinned-version recommendation

Use vLLM only for the first iteration. Nebius documents the `vllm/vllm-openai` container and custom endpoint arguments; NVIDIA’s card documents vLLM serving and a minimum `vllm>=0.10.1`. Nebius’s current Serverless tutorial example uses `v0.18.0-cu130`. Start compatibility validation with that documented tag, then record the resolved immutable container digest and exact package/runtime versions. The tag is a candidate, **not yet verified** for this model’s custom code, CUDA, or `mamba_ssm_cache_dtype` path. If the smoke test fails, test NVIDIA’s card example `v0.10.1` as fallback; pin whichever image actually passes, by digest. Do not deploy a floating `latest` tag. [Nebius vLLM tutorial](https://docs.nebius.com/serverless/tutorials/deploy-model), [NVIDIA vLLM instructions](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2), [vLLM serve CLI](https://docs.vllm.ai/en/stable/cli/serve/).

SGLang is not recommended for the first submission: it would add another engine/version matrix without helping test SLOKern’s existing vLLM-oriented knob contract. No tensor parallelism, quantization, prefix-cache search, or speculative decoding in the initial campaign.

## 6. GPU and memory feasibility

- **Hardware:** 1× H100 SXM, 80 GB GPU memory, one GPU per VM, 16 vCPU/200 GB host RAM preset. Do not add another GPU; the selected 9B model does not require tensor parallelism.
- **Weight memory estimate:** 8.888B BF16 parameters × 2 bytes ≈ 17.8 GB decimal (about 16.6 GiB) for raw weight tensors. This leaves nominal room for CUDA/vLLM runtime, activations, and request state, but it is not a prediction of usable KV/cache capacity.
- **Context:** hard-cap server context at 4,096 tokens; fixture requests target roughly 512 input + 128 output tokens. The model’s 128K advertised context would consume cache and undermine the concurrency question.
- **Hybrid-state limitation:** Nemotron Nano is a hybrid Mamba/attention model, so a simple full-attention KV-per-token estimate is not representative. The required FP32 Mamba cache may consume material memory. Verify with the server startup log, `nvidia-smi`, and actual 16/64 sequence preflight. Reject OOM/crash as an execution error, never an SLO failure.
- **Fallback arithmetic:** Qwen3-8B’s published config implies about 144 KiB BF16 attention KV per token. At 4,096 tokens, that is about 0.56 GiB per sequence: roughly 9 GiB for 16 full-length sequences and 36 GiB for 64, before weights/runtime/fragmentation. This is a configuration-derived estimate, not measured usage.

## 7. Deployment architecture and steps

1. Confirm Nebius project, region, H100 quota, platform/preset, current physical capacity, VM quota, subnet/allocation, storage quota, and billing/credit limit. Query platform availability and Capacity Advisor; do not infer it from a public SKU page.
2. Provision a single `gpu-h100-sxm` / `1gpu-16vcpu-200gb` Linux instance with enough persistent SSD for the container, approximately 18 GB model checkpoint, tokenizer, and cache. Nebius’s host-an-LLM example uses a 300 GiB SSD; treat it as a sizing example, not a required minimum. [Host an LLM](https://docs.nebius.com/compute/quickstart-host-model).
3. Launch an immutable vLLM OpenAI server container with the fixed model/tokenizer revisions, `--trust-remote-code`, `--mamba_ssm_cache_dtype float32`, `--max-model-len 4096`, and fixed memory utilization. Capture the container digest, full command, env allowlist, `vllm --version`, driver/CUDA, GPU model, and model/tokenizer hashes.
4. Put a small local process supervisor around vLLM. For each candidate it stops the server process, starts the same image and model with the new two flags, waits for `/v1/models` and readiness, records the active arguments, and returns effective settings. One VM and persistent model cache avoid six model downloads. Do not permit remote user input to become shell arguments.
5. Point the existing adapter at the actual OpenAI-compatible endpoint (`NEBIUS_BASE_URL` ending in `/v1`) and set `NEBIUS_MODEL_ID`; keep credentials only in environment/secret management. If using the Token Factory explainer, give it a distinct adapter/config and API base URL.
6. Run a preflight request and verify actual model ID, streaming, response headers, tokenizer counts, settings read-back, and safe errors. Preflight is health validation, not benchmark evidence.
7. Execute the fixed six-run campaign, then copy artifacts off the VM. Stop the VM through Nebius control plane, then delete it and review disks, volumes, public IPs, and other billable resources.

## 8. Bounded tunable space

Keep the repository’s fixed 2×2 matrix and vary only settings the vLLM process actually receives and reports:

| Variable | Search values / mechanism | Restart? | Expected trade-off and evidence |
|---|---|---|---|
| `max_num_batched_tokens` | `--max-num-batched-tokens {1024, 2048}` | Yes; scheduler startup setting. | Higher token budget may improve prefill throughput and batching but increase memory pressure and TTFT/tail queuing; lower may improve responsiveness at lower throughput. Compare TTFT p95, ITL p95, achieved requests/s and output tokens/s, queue/error rates, GPU memory. |
| `max_num_seqs` | `--max-num-seqs {16, 64}` | Yes; scheduler/model-runner startup setting. | Higher limit can admit more sequences and raise throughput but consumes buffers/cache and may worsen ITL/tails or OOM. Lower may protect latency but throttle throughput. `max_num_seqs` is per iteration, not a promise of user concurrency. |

The official vLLM CLI defines `max-num-batched-tokens` as tokens processed in a scheduler iteration and `max-num-seqs` as sequences processed per iteration. These are process settings, not OpenAI request fields. The docs distinguish a separate `--max-num-active-seqs` admission cap; do not substitute that for the existing grid silently. [vLLM CLI semantics](https://docs.vllm.ai/en/stable/cli/serve/).

Hold fixed: `--max-model-len 4096`, `--gpu-memory-utilization 0.90` (initial proposal; confirm memory headroom), model/tokenizer revision, Mamba cache dtype, dtype BF16, all other engine flags, client workload concurrency, request parameters, server image/digest, GPU, and arrival profile. The vLLM docs’ default GPU utilization is 0.92; choosing 0.90 is a conservative starting policy, not a universal optimum. Keep `temperature=0`, output cap, stop conditions, and any model reasoning mode identical. Do not add `max_tokens`, temperature, or client concurrency to the search matrix: those change the workload, not hidden server batching.

## 9. Reproducible benchmark protocol

**Pre-register before the first benchmark:** experiment ID; model/tokenizer commits; container digest; exact GPU SKU/region; OS/kernel/driver/CUDA; full startup args; prompt fixture hash; true tokenizer-measured lengths; temperature/reasoning mode/output cap; workload arrival seed/rate/concurrency; warm-up and active windows; SLOs; ranking objective; run order; budget; and stop/invalidity criteria.

- Use an open-loop **constant-rate** workload at one fixed offered rate for all six runs. The repository already implements reproducible open-loop constant and seeded Poisson arrivals; choose constant rate for this first comparison to simplify arrival parity. Keep the exact same prompt ordering, request lengths, output cap, and concurrency cap.
- Use one fixed fixture with recorded tokenizer counts, e.g. 512 input and at most 128 output tokens. The current load generator estimates input token count from whitespace (`len(prompt.split()) * 1.3`); correct that evidence source or label it approximate before claiming exact token lengths.
- Proposed protocol: 60-second warm-up + 300-second active window per run, or 360 seconds × 6 = 36 minutes of pure benchmark runtime. The durations remain unvalidated in current `docs/deployment.md`; calibrate them in the separate preflight and record the actual duration. Never shorten only selected candidates.
- Capture every request in raw JSONL: scheduled/sent/TTFT/completion timestamps, status/error, actual token counts, output count, ITL observations, warm-up flag, and validity. Compare offered and achieved load; fail evidence validity if generator dispatch lag exceeds the current 10 ms threshold or offered rate is below 90% of target.
- Keep request generation on a separate client machine/process or otherwise prove it is not CPU/network saturated. Record dispatch lag and network RTT; the measured TTFT includes network/client cost and should be described as client-observed.
- Fix server state with one process, fixed cache state, fixed worker/CPU resources, identical request order, no concurrent workloads, and the same warmed server policy. Note that the six-run order is not randomized/interleaved and run-to-run drift is a limitation.
- Preserve timeout, 429/5xx, OOM, process crash, partial generation, and canceled request records. An OOM or invalid deployment is an execution error/inconclusive run, not a measured SLO violation. Do not drop failed requests from error-rate/throughput denominators.
- Show p95 with sample count and bootstrap confidence interval. Treat p99 as inconclusive unless the prespecified sample minimum yields enough tail observations. The six-run cap provides one run per candidate and only one winner verification; it does not establish between-run variance or robust causal superiority.
- Rerun the winner with a distinct verification run ID and new raw JSONL. The result statement is “best observed feasible candidate in this tested matrix, independently remeasured once,” never “globally optimal.”

## 10. SLO definitions and experiment budget

Suggested first product profile (targets to ratify before the run, not claimed achieved performance):

| Hard constraint | Initial demo value | Notes |
|---|---:|---|
| TTFT p95 | ≤ 1,000 ms | Interactive text workload; use measured tokenizer lengths and client-observed TTFT. |
| ITL p95 | ≤ 100 ms | Decode smoothness; only available for streamed token responses. |
| Error rate | ≤ 1% | Includes HTTP errors, timeouts, incomplete generations; define denominator before run. |
| Offered-load target | 1 request/s | Require achieved load ≥ 90% target and unsaturated loadgen; report both offered and achieved. |
| Minimum valid samples | 200 requests per run (provisional) | If not met, verdict is INCONCLUSIVE. p95 remains noisy at this n; provide CI and do not claim stable tails. p99 should be INCONCLUSIVE. |

These values are an initial interactive benchmark profile, not existing user workload facts. If the product workload requires another target rate/latency, choose that before measurement. The evaluator already handles missing metrics, minimum samples, hard thresholds, and generator saturation; use its existing FEASIBLE / INFEASIBLE / INCONCLUSIVE meanings.

The fixed budget is six benchmark runs: one baseline + four grid candidates + one independent verification. The separate smoke probe is a connectivity check, not performance evidence. Do not silently use additional benchmark runs. Current `BudgetLimiter` default behavior preserves a verification slot, but source inspection found its configurable constructor can permit six search runs and zero verification; `BLK-15` remains open until fixed. Current ranking also has the documented missing-objective-evidence issue (`BLK-16`); do not use a winner as authoritative until both are fixed.

## 11. SLOKern integration map and minimum implementation plan

| Existing area | Current role / finding | Minimum needed for controlled vLLM |
|---|---|---|
| `src/slokern/engine/serving/base.py` | `BaseServingAdapter` contract has `apply_config`, health, capabilities, environment fingerprint, sync/streaming generation. | Preserve interface. Implement a process/endpoint-control adapter or a supervisor-backed adapter. |
| `src/slokern/engine/serving/fake.py` | Deterministic synthetic adapter for offline tests. | Keep all its outputs labeled `DEMO DATA`; do not use it as live evidence. |
| `src/slokern/engine/serving/nebius.py` | Standard-library `urllib` OpenAI-compatible HTTP/SSE transport and secret redaction. Current default URL/model point at legacy Studio/Llama values. `apply_config()` classifies local declared capabilities but does not transmit/read back vLLM scheduler flags. | Make base URL/model explicit. Add an adapter lifecycle operation that applies the actual startup flags and waits for readiness; reject if `requested != effective`. Sanitize endpoint control errors and omit credentials from artifacts. |
| `src/slokern/engine/runner/run_executor.py` | Applies config, health-checks, runs loadgen, derives metrics/evaluates SLO, persists run artifacts including raw traces. | Use after actual supervisor read-back is implemented; preserve startup logs/config hash and errors as artifacts. |
| `src/slokern/engine/loadgen/runner.py` | Open-loop dispatch, timestamps, JSONL, streaming ITL, offered/achieved throughput and saturation detection. | Replace approximate input-token counting for audited workload with tokenizer measurements; preserve generation-specific input/output token counts. |
| `src/slokern/contracts/{config.py,evidence.py,spec.py,metrics.py}` | Candidate/workload/SLO/raw measurement/metrics types. | Preserve contracts unless a concrete field gap requires explicit ADR. Record revisions/config hashes in existing metadata where safe; do not misrepresent approximate token counts as exact. |
| `src/slokern/core/metrics/aggregate.py`, `core/evaluator/evaluate.py` | Deterministic percentiles/throughput and hard constraint verdicts. | Reuse; add no cost inference absent verified source. Execution failures remain separate. |
| `src/slokern/core/search/{space.py,budget.py,grid.py,rank.py}` | Fixed matrix and search orchestration. | Fix `BLK-15`, `BLK-16`, then connect the real supervisor. Baseline and candidates must store effective flags. |
| `src/slokern/core/verification/` | `protocol.py` and `compare.py` are currently stubs/partial; independent verification engine not complete. | Implement a fresh run ID, new raw measurement file, same frozen config/protocol, independent metric/evaluator pass, and drift report before calling the recommendation verified. |

Required execution sequence: validate request/allowed knobs → start/reconfigure vLLM → inspect actual process args and runtime readiness → issue fixed workload → persist raw JSONL → calculate metrics → evaluate hard SLOs → persist candidate evidence and config/fingerprint → select only valid feasible candidates with objective evidence → rerun winner under a fresh run ID and independently evaluate.

## 12. Cost, time, prerequisites, and cleanup

**Verified current public price:** Nebius’s live public page lists H100 on-demand at **$4.50/GPU-hour** and preemptible from **$0.79/GPU-hour**. Spot prices are dynamic and can change during use; use on-demand for this bounded campaign to avoid preemption. Taxes/storage are additional, and the public prices page states a $25 minimum first payment. The actual account may have hackathon credits or negotiated pricing; verify before launch. [Current Nebius price page](https://nebius.com/prices).

**Estimate:** 36 minutes of pure benchmark windows at $4.50/hour is about **$2.70 GPU compute**. Allow up to **3 H100 hours / $13.50 compute** for quota checks, model/image download, smoke, server restarts, and the benchmark. This is a proposed hard planning cap, not a quote; persistent disk, mounted volumes, egress, and taxes are extra. If startup or download exceeds the cap, stop and re-plan before continuing. vLLM/model cold-start duration has not been measured.

Prerequisites: Nebius project and billing/credit; editor access; one GPU H100 quota; VM/preset capacity; subnet/network allocation; enough disk; outbound access to fetch the image and Hugging Face model; model license compliance; a securely managed Hugging Face token only if required; and an API key if using the optional Token Factory explanation. Do not store any key in source, benchmark JSON, command logs, Git, or screenshots.

Cleanup: save artifacts locally; stop the VM through Nebius API/UI (not guest `poweroff` alone); delete the VM when finished; inspect and delete retained disks, mounted volumes, and public IP allocations unless intentionally retained. For Serverless Endpoint fallback, stop/delete the endpoint and separately inspect mounted bucket/filesystem charges; stopping an endpoint releases its VM/disk, but mounted persistent storage may still bill. [Serverless billing](https://docs.nebius.com/serverless/pricing-quotas), [endpoint stop/restart](https://docs.nebius.com/serverless/maintenance/stop-start).

## 13. Hackathon compliance assessment

The official rules require a working app that runs on Token Factory or Nebius AI Cloud and uses at least one NVIDIA open-source model. They require a public open-source project repository/license and README, a working demo/test build, and a public YouTube demo under three minutes. Pre-existing projects need an explanation of significant changes made during the submission period. The Best Apps and Agents track specifically calls for Nemotron models on Nebius through Token Factory. Judging has a pass/fail viability screen, then equally weights implementation, design, impact, and idea. [Rules](https://nebiusglobalaihackathon.devpost.com/rules).

Recommended evidence: show the Nebius H100 model-serving path; baseline and four candidate settings with their actual startup flags; raw run IDs; offered vs achieved rate; SLO pass/fail/inconclusive reasons; selected feasible candidate; new verification run; and an artifact report. Show a Token Factory Nemotron explanation only as a user-facing summary of already-fixed numeric results. State that it cannot select candidates or change verdicts. Do not claim global optimality, guaranteed performance, or a Token Factory server-knob optimization.

Eligibility risk to resolve: the formal rule’s parenthetical lists Serverless Jobs, Serverless Endpoints, and DevPods as AI Cloud execution examples; it does not name VMs. A VM is clearly a Nebius AI Cloud product technically, but confirm the interpretation with organizers or retain the genuine Token Factory feature as the qualifying runtime call. The repository is already Apache-2.0, but the submission still needs a demo/test build, <3-minute public YouTube video, significant-update explanation, and up-to-date submission descriptions.

## 14. Prioritized implementation plan and acceptance criteria

1. **P0 — Resolve decisions and access.** Confirm project model access, H100 quota/capacity, billing ceiling, and hackathon VM interpretation. Acceptance: written decision or the Token Factory Nemotron explanation path selected; no infrastructure provisioned before approval.
2. **P0 — Fix search policy blockers.** Make the six-run allocation impossible to override; enforce one baseline + four candidate maximum + one reserved verification. Reject feasible rows without a valid declared-objective metric; resolve Mode A missing price behavior. Acceptance: constructor boundary tests cover malicious/invalid budget combinations; ranking returns no winner if objective evidence is missing.
3. **P0 — Implement actual vLLM control.** Pin a tested image digest; launch one model/one H100; map candidate keys to exact startup flags; read back the active process arguments; fail strict mode if either knob is not actually applied. Acceptance: a fake supervisor test and a single live preflight demonstrate requested/effective equality, readiness, streaming, and redaction.
4. **P1 — Evidence integrity.** Tokenize fixture inputs with the pinned tokenizer; capture true input/output counts, environment and config fingerprints; use an open-loop fixed profile and persist all raw JSONL. Acceptance: raw evidence reproduces aggregate metrics and no approximate token counts are labeled exact.
5. **P1 — Verification.** Implement a new verification run, recompute metrics and verdict from new raw evidence, compare to search result; classify crashes/invalidity separately. Acceptance: distinct run ID and raw file, and the winner is called verified only if the fresh run is FEASIBLE.
6. **P1 — Demonstration and report.** Display baseline, matrix, all candidate verdicts, selection objective, verification, limitations, cost scope, and model/runtime/license details. Acceptance: repeatable demo with a public repo, clear DEMO DATA for all fake runs, and a public video under three minutes.

## 15. Sources, estimates, and unresolved questions

**Verified from official current sources:** Nebius H100 80 GB offering and compute price; current Serverless custom-container endpoint path; Token Factory OpenAI-compatible API and model-list operation; vLLM scheduler flags and meanings; Nemotron model ID/revision/license/H100/vLLM instructions; Qwen3-8B license and serving instructions; hackathon rules. Main links are embedded above.

**Verified from repository source (read-only):** adapter abstractions and HTTP transport; grid/budget files; loadgen, metrics, evaluator and contracts. The graph coverage check showed `metadata_changed` for these paths, so the conclusion is based on direct source inspection, not graph completeness. Key files: `src/slokern/engine/serving/{base.py,nebius.py,fake.py}`, `src/slokern/engine/runner/run_executor.py`, `src/slokern/engine/loadgen/runner.py`, `src/slokern/core/{search,metrics,evaluator,verification}/`, and `src/slokern/contracts/`.

**Estimates:** raw weight memory, Qwen KV arithmetic, 36-minute pure benchmark windows, 3-hour deployment budget, and example SLO thresholds. None is an achieved SLOKern result.

**Open before a live run:** project-specific H100 quota/physical capacity and region; exact vLLM+CUDA+custom-code compatibility; optional Token Factory model ID/pricing under the user’s key; exact tokenizer commit; actual model load/start duration; usable disk/network throughput; whether hackathon staff interpret VM-only execution as compliant; and final workload/SLO thresholds from the intended user profile.

## Alternative-study conclusion (not the active project recommendation)

The following values summarize this 9B VM study only. They do not supersede ADR 0001-B, the user's unratified 30B Serverless proposal, or the current implementation's 2×2 search space. Resolve DEC-0013 and the listed implementation blockers before treating any deployment profile as executable.

- **Recommended deployment path in this study only:** One Nebius AI Cloud H100 VM for controlled vLLM benchmarking; this is not ratified for SLOKern. The accepted deployment profile remains unresolved.
- **Recommended model:** NVIDIA `nvidia/NVIDIA-Nemotron-Nano-9B-v2` at the pinned revision above.
- **Fallback model:** `Qwen/Qwen3-8B`, Apache-2.0, pinned model and tokenizer revision.
- **Recommended serving engine:** vLLM OpenAI server, exact image pinned by digest after one live compatibility smoke.
- **GPU configuration:** One H100 SXM, 80 GB, `1gpu-16vcpu-200gb`; no tensor parallelism.
- **Tunable parameters:** startup `--max-num-batched-tokens` ∈ {1024, 2048}; `--max-num-seqs` ∈ {16, 64}; all other runtime/workload settings fixed.
- **Initial experiment matrix:** Baseline + 4 grid candidates + one fresh winner verification; same open-loop constant-rate workload, model revision, tokenizer, request fixture, GPU, and runtime image.
- **Primary SLOs:** initial demo targets TTFT p95 ≤1,000 ms, ITL p95 ≤100 ms, error rate ≤1%, and ≥90% of 1 request/s offered load; at least 200 valid measured requests per run. Targets are proposals and require ratification.
- **Estimated experiment budget:** 36 minutes pure run windows under the proposed 60s/300s schedule; reserve at most 3 H100 hours (about $13.50 GPU compute at published on-demand price), plus storage/tax.
- **Critical unknowns:** account quota/capacity, vLLM/model compatibility, exact model/API availability under credentials, strict budget/ranking blockers, and VM hackathon interpretation.
- **First implementation milestone proposed by this study:** close budget/ranking blockers, then run one credentialed preflight proving vLLM starts on the selected H100 and effective server flags are independently observable. Current `apply_config` does not change/read back remote flags (`BLK-17`).
- **Reasons this is the best trade-off for SLOKern:** one GPU is enough, the primary model satisfies NVIDIA usage and is documented for H100/vLLM, the VM preserves exact startup control and model cache, and the workload stays within the six-run budget. The resulting claim remains narrow: best observed feasible configuration in this tested 2×2 space, independently remeasured once.
