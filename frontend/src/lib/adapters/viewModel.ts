/**
 * View-Model Adapters
 * Bridges raw backend Pydantic contracts to clean, typed UI view-models.
 */

import type {
  CandidateConfig,
  MetricSet,
  FeasibilityResult,
  RunStatusResponse,
  SmokeTestArtifactResponse,
  SLOConstraint,
  VerificationRecord,
} from '../../types/contracts';

export type { VerificationRecord, SLOConstraint } from '../../types/contracts';

export interface UICandidate {
  id: string;
  name: string;
  subtitle: string;
  batch: number | null;
  concurrency: number | null;
  kvCache: string | null;
  p50: number | null;
  p95: number | null;
  p99: number | null;
  throughput: number | null;
  error: number | null;
  gpu: number | null;
  feasible: boolean;
  feasibilityVerdict: 'FEASIBLE' | 'INFEASIBLE' | 'INCONCLUSIVE';
  evidenceValidity: 'VALID' | 'INVALID' | 'CONTAMINATED' | 'STALE' | null;
  reason: string;
  tag: string;
  ttftP95: number | null;
  itlP95: number | null;
  e2eP95?: number | null;
  reasonCodes?: string[];
  isParetoDominated?: boolean;
  rawConfig?: CandidateConfig;
  metricSet?: MetricSet;
  feasibilityResult?: FeasibilityResult;
}

export interface UIExperiment {
  id: string;
  run: string;
  workload: string;
  model: string;
  state: 'Pending' | 'Running' | 'Completed' | 'Failed' | 'Needs review';
  feasibility: 'Feasible' | 'Infeasible' | 'Inconclusive' | 'Pending';
  verification: 'Verified' | 'Failed' | 'Inconclusive' | 'Not run' | 'Pending';
  updated: string;
  candidateId: string;
  baselineCandidateId?: string | null;
  metrics?: MetricSet;
  durationSeconds?: number;
  verificationDurationMultiplier?: number | null;
  requestedRateRps?: number | null;
  achievedRateRps?: number | null;
  measurementValidity?: 'VALID' | 'INVALID' | 'CONTAMINATED' | 'STALE' | null;
  clientSaturation?: boolean | null;
  errorRatePct?: number;
  exclusionsCount?: number | null;
  evidenceClassification?: string;
  runsCount?: number;
  arrivalMode?: 'poisson' | 'constant' | 'closed' | null;
  targetOfferedRateRps?: number | null;
  sloConstraints?: SLOConstraint[];
  candidateEvaluationsCount?: number;
  candidateBudget?: number;
  searchSpaceCandidateCount?: number;
  stoppingReason?: string;
  rankingObjective?: string | null;
}

export function mapRunStatusToCandidate(run: RunStatusResponse): UICandidate {
  const m = run.metric_set;
  const f = run.feasibility_result;
  const settings = run.applied_config?.effective_settings;
  const p95Latency = m?.ttft_ms?.p95 ?? null;
  const p50Latency = m?.ttft_ms?.p50 ?? null;
  const p99Latency = m?.ttft_ms?.p99 ?? null;
  const throughput = m?.token_throughput_tps ?? null;
  const verdict = f?.overall_verdict ?? 'INCONCLUSIVE';
  const isFeasible = verdict === 'FEASIBLE';

  return {
    id: run.candidate_id || 'C-??',
    name: `Candidate ${run.candidate_id || 'Unknown'}`,
    subtitle: run.run_id,
    batch: settings?.max_num_batched_tokens != null ? settings.max_num_batched_tokens / 512 : null,
    concurrency: settings?.max_num_seqs ?? null,
    kvCache: settings?.kv_cache_dtype?.toUpperCase() ?? null,
    p50: p50Latency,
    p95: p95Latency,
    p99: p99Latency,
    throughput,
    error: m?.error_rate != null ? m.error_rate * 100 : null,
    gpu: settings?.gpu_memory_utilization != null ? settings.gpu_memory_utilization * 100 : null,
    feasible: isFeasible,
    feasibilityVerdict: verdict,
    evidenceValidity: (f?.validity_status as UICandidate['evidenceValidity']) ?? null,
    reason: f?.audit_notes ?? f?.notes ?? 'Evaluator result unavailable.',
    reasonCodes: f?.constraint_evaluations.map((evaluation) => evaluation.reason_code ?? evaluation.reason) ?? [],
    tag: verdict,
    ttftP95: m?.ttft_ms?.p95 ?? null,
    itlP95: m?.itl_ms?.p95 ?? null,
    e2eP95: m?.e2e_latency_ms?.p95 ?? null,
  };
}

export function selectFeasibleRecommendation(candidates: UICandidate[]): UICandidate | null {
  return candidates.find((candidate) => candidate.tag === 'WINNER' && candidate.feasible) ?? null;
}

export function mapSmokeTestEvidence(smokeTest: SmokeTestArtifactResponse | null | undefined) {
  return {
    evidenceClassification: smokeTest?.evidence_classification ?? 'PENDING',
    status: smokeTest?.status ?? 'NONE',
    ttftMs: smokeTest?.probe_request?.ttft_ms ?? null,
    totalLatencyMs: smokeTest?.probe_request?.total_latency_ms ?? null,
    inputTokens: smokeTest?.probe_request?.input_tokens ?? null,
    outputTokens: smokeTest?.probe_request?.output_tokens ?? null,
    streamStatus: smokeTest?.streaming_probe
      ? smokeTest.streaming_probe.stream_success ? 'PASSED' : 'FAILED'
      : 'NOT RECORDED',
    streamChunkCount: smokeTest?.streaming_probe?.chunk_count ?? null,
    streamFirstChunkTtftMs: smokeTest?.streaming_probe?.first_chunk_ttft_ms ?? null,
  };
}

export function mapVerificationComparisons(record: VerificationRecord | null | undefined) {
  const inlineComparisons = record?.drift_analysis?.comparisons;
  const comparisons = inlineComparisons?.length
    ? inlineComparisons
    : Object.values(record?.drift_analysis?.metric_comparisons ?? {});
  return comparisons.map((comparison) => ({
    name: `${comparison.metric_name}${comparison.statistic ? ` (${comparison.statistic})` : ''}`,
    searchVal: comparison.reference_value,
    verifyVal: comparison.verification_value,
    drift: comparison.absolute_drift,
    tolerance: comparison.tolerance,
    unit: comparison.unit,
    passed: comparison.passed,
  }));
}

/**
 * Computes non-dominated (Pareto-optimal) points in a set of candidates.
 * Minimizing P95 latency, maximizing throughput.
 */
export function identifyParetoFrontier(candidates: UICandidate[]): {
  paretoIds: Set<string>;
  sortedCandidates: UICandidate[];
} {
  const paretoIds = new Set<string>();

  // Only feasible candidates are candidates for Pareto efficiency
  const feasibleOnes = candidates.filter(
    (c): c is UICandidate & { p95: number; throughput: number } =>
      c.feasible && c.p95 != null && c.throughput != null
  );

  for (const c1 of feasibleOnes) {
    let dominated = false;
    for (const c2 of feasibleOnes) {
      if (c1.id === c2.id) continue;
      // c2 dominates c1 if c2 has <= latency AND >= throughput, with at least one strict inequality
      const c2BetterOrEqualLatency = c2.p95 <= c1.p95;
      const c2BetterOrEqualThroughput = c2.throughput >= c1.throughput;
      const c2StrictlyBetter = c2.p95 < c1.p95 || c2.throughput > c1.throughput;

      if (c2BetterOrEqualLatency && c2BetterOrEqualThroughput && c2StrictlyBetter) {
        dominated = true;
        break;
      }
    }
    if (!dominated) {
      paretoIds.add(c1.id);
    }
  }

  const sortedCandidates = candidates.map(c => ({
    ...c,
    isParetoDominated: c.feasible ? !paretoIds.has(c.id) : true,
  }));

  return { paretoIds, sortedCandidates };
}
