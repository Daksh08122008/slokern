/**
 * View-Model Adapters
 * Bridges raw backend Pydantic contracts to clean, typed UI view-models.
 */

import type {
  CandidateConfig,
  MetricSet,
  FeasibilityResult,
  RunStatusResponse,
} from '../../types/contracts';

export type { VerificationRecord, SLOConstraint } from '../../types/contracts';

export interface UICandidate {
  id: string;
  name: string;
  subtitle: string;
  batch: number;
  concurrency: number;
  kvCache: string;
  p50: number;
  p95: number;
  p99: number;
  throughput: number;
  error: number;
  gpu: number;
  feasible: boolean;
  feasibilityVerdict: 'FEASIBLE' | 'INFEASIBLE' | 'INCONCLUSIVE';
  evidenceValidity: 'VALID' | 'INVALID' | 'CONTAMINATED' | 'STALE';
  reason: string;
  tag: string;
  ttftP95: number;
  itlP95: number;
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
  metrics?: MetricSet;
  durationSeconds?: number;
  requestedRateRps?: number;
  achievedRateRps?: number;
  measurementValidity?: 'VALID' | 'INVALID' | 'CONTAMINATED' | 'STALE';
  clientSaturation?: boolean;
  errorRatePct?: number;
  exclusionsCount?: number;
}

export function mapRunStatusToCandidate(run: RunStatusResponse): UICandidate {
  const m = run.metric_set;
  const f = run.feasibility_result;
  const p95Latency = m?.ttft_ms?.p95 ?? m?.e2e_latency_ms?.p95 ?? 0;
  const p50Latency = m?.ttft_ms?.p50 ?? m?.e2e_latency_ms?.p50 ?? 0;
  const p99Latency = m?.ttft_ms?.p99 ?? m?.e2e_latency_ms?.p99 ?? 0;
  const throughput = m?.token_throughput_tps ?? m?.achieved_load_rps ?? 0;
  const isFeasible = f ? f.overall_verdict === 'FEASIBLE' : run.is_feasible;

  return {
    id: run.candidate_id || 'C-??',
    name: `Candidate ${run.candidate_id || 'Unknown'}`,
    subtitle: run.run_id,
    batch: 16,
    concurrency: 32,
    kvCache: 'FP8',
    p50: p50Latency,
    p95: p95Latency,
    p99: p99Latency,
    throughput: throughput > 100 ? throughput / 1000 : throughput, // display in k tok/s if large
    error: (m?.error_rate ?? 0) * 100,
    gpu: 75,
    feasible: isFeasible,
    feasibilityVerdict: f?.overall_verdict ?? (isFeasible ? 'FEASIBLE' : 'INFEASIBLE'),
    evidenceValidity: (f?.validity_status as any) ?? 'VALID',
    reason: f?.reasons?.[0] ?? (isFeasible ? 'Passes all hard constraints' : 'Breaches constraint'),
    tag: isFeasible ? 'FEASIBLE' : 'INFEASIBLE',
    ttftP95: m?.ttft_ms?.p95 ?? p95Latency,
    itlP95: m?.itl_ms?.p95 ?? 0,
  };
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
  const feasibleOnes = candidates.filter(c => c.feasible);

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
