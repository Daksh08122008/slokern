import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mapRunStatusToCandidate, mapSmokeTestEvidence, mapVerificationComparisons, selectFeasibleRecommendation } from '../src/lib/adapters/viewModel.ts';
import type { UICandidate } from '../src/lib/adapters/viewModel.ts';

describe('decision integrity view-model adapters', () => {
  it('keeps TTFT and end-to-end percentiles separate and preserves throughput units', () => {
    const run = {
      run_id: 'run-01',
      experiment_id: 'exp-01',
      candidate_id: 'candidate-01',
      execution_status: 'COMPLETED',
      is_completed: true,
      is_feasible: false,
      raw_measurements_count: 30,
      metric_set: {
        ttft_ms: { p50: 12.4, p95: 12.5, p99: 12.6 },
        itl_ms: { p50: 8.0, p95: 8.1, p99: 8.2 },
        e2e_latency_ms: { p50: 510, p95: 518, p99: 520 },
        token_throughput_tps: 160,
        error_rate: 0,
      },
      feasibility_result: {
        overall_verdict: 'INFEASIBLE',
        validity_status: 'VALID',
        audit_notes: 'Constraint failed: e2e_latency_ms p95 <= 500.0',
        constraint_evaluations: [
          { reason_code: 'E2E_LATENCY_EXCEEDED' },
        ],
      },
    } as any;

    const candidate = mapRunStatusToCandidate(run);

    assert.equal(candidate.ttftP95, 12.5);
    assert.equal(candidate.e2eP95, 518);
    assert.equal(candidate.p95, 12.5);
    assert.equal(candidate.throughput, 160);
    assert.equal(candidate.feasible, false);
    assert.equal(candidate.tag, 'INFEASIBLE');
    assert.equal(candidate.reason, 'Constraint failed: e2e_latency_ms p95 <= 500.0');
    assert.deepEqual(candidate.reasonCodes, ['E2E_LATENCY_EXCEEDED']);
  });

  it('does not replace an infeasible selected winner with another feasible candidate', () => {
    const infeasibleWinner = { id: 'candidate-a', tag: 'WINNER', feasible: false } as UICandidate;
    const feasibleCandidate = { id: 'candidate-b', tag: 'FEASIBLE', feasible: true } as UICandidate;
    assert.equal(selectFeasibleRecommendation([infeasibleWinner, feasibleCandidate]), null);
  });

  it('returns no recommendation when all candidates are infeasible', () => {
    const infeasibleWinner = { id: 'candidate-a', tag: 'WINNER', feasible: false } as UICandidate;
    assert.equal(selectFeasibleRecommendation([infeasibleWinner]), null);
  });

  it('keeps missing smoke evidence pending instead of inventing live measurements', () => {
    const evidence = mapSmokeTestEvidence(null);
    assert.equal(evidence.evidenceClassification, 'PENDING');
    assert.equal(evidence.ttftMs, null);
    assert.equal(evidence.totalLatencyMs, null);
    assert.equal(evidence.streamStatus, 'NOT RECORDED');
  });

  it('does not invent verification deltas when comparison artifacts are absent', () => {
    assert.deepEqual(mapVerificationComparisons(null), []);
    const [comparison] = mapVerificationComparisons({
      drift_analysis: {
        slo_drift_detected: false,
        comparisons: [{
          metric_name: 'ttft_ms.p95',
          reference_value: 12.5,
          verification_value: 13,
          absolute_drift: 0.5,
          tolerance: 3,
          comparison_method: 'absolute_difference',
          unit: 'ms',
          passed: true,
        }],
      },
    } as any);
    assert.equal(comparison.searchVal, 12.5);
    assert.equal(comparison.verifyVal, 13);
    assert.equal(comparison.drift, 0.5);
    assert.equal(comparison.tolerance, 3);
  });
});
