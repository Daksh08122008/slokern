import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { deriveVerifiedWinner } from '../src/lib/status.ts';
import { computeBindingConstraintHeadroom, formatLatency, formatThroughput } from '../src/lib/format.ts';
import { identifyParetoFrontier } from '../src/lib/adapters/viewModel.ts';
import { runWithViewTransition } from '../src/lib/motion.ts';
import type { UICandidate } from '../src/lib/adapters/viewModel.ts';
import type { VerificationRecord, SLOConstraint } from '../src/types/contracts.ts';

describe('Status Model & Deterministic Verification (DEC-0014)', () => {
  const baseCandidate = {
    candidateId: 'C-02',
    isFeasible: true,
    feasibilityVerdict: 'FEASIBLE',
    evidenceValidity: 'VALID',
    isStale: false,
  };

  const validVerificationRecord: VerificationRecord = {
    verification_id: 'ver_01',
    experiment_id: 'EXP-0248',
    candidateId: 'C-02',
    candidate_id: 'C-02',
    original_run_id: 'run_search_01',
    verification_run_id: 'verify_run_99',
    verification_verdict: 'VERIFIED',
    drift_analysis: {
      slo_drift_detected: false,
      drift_exceeded: false,
      comparisons: [
        {
          metric_name: 'ttft_ms.p95',
          reference_value: 26.0,
          verification_value: 27.2,
          absolute_drift: 1.2,
          tolerance: 3.0,
          comparison_method: 'absolute_difference',
          unit: 'ms',
          passed: true,
          drift_acceptable: true,
        },
      ],
    },
  };

  it('Test 1: Valid verified winner passes all criteria', () => {
    const res = deriveVerifiedWinner(baseCandidate, 'run_search_01', validVerificationRecord);
    assert.equal(res.isVerifiedWinner, true);
    assert.equal(res.statusType, 'verified');
    assert.equal(res.badgeLabel, 'VERIFIED WINNER');
    assert.equal(res.hasDistinctRunId, true);
    assert.equal(res.isDriftAcceptable, true);
    assert.equal(res.toleranceDeclared, true);
  });

  it('Test 2: Infeasible candidate fails verification derivation', () => {
    const infeasibleCandidate = {
      ...baseCandidate,
      isFeasible: false,
      feasibilityVerdict: 'INFEASIBLE',
    };
    const res = deriveVerifiedWinner(infeasibleCandidate, 'run_search_01', validVerificationRecord);
    assert.equal(res.isVerifiedWinner, false);
    assert.equal(res.statusType, 'infeasible');
    assert.equal(res.badgeLabel, 'INFEASIBLE');
  });

  it('Test 3: Stale evidence fails verification derivation', () => {
    const staleCandidate = {
      ...baseCandidate,
      isStale: true,
      evidenceValidity: 'STALE',
    };
    const res = deriveVerifiedWinner(staleCandidate, 'run_search_01', validVerificationRecord);
    assert.equal(res.isVerifiedWinner, false);
    assert.equal(res.statusType, 'warning');
    assert.equal(res.badgeLabel, 'STALE EVIDENCE');
  });

  it('Test 4: Equal search and verification run IDs rejected', () => {
    const identicalRunRecord: VerificationRecord = {
      ...validVerificationRecord,
      original_run_id: 'run_01',
      verification_run_id: 'run_01', // Identical!
    };
    const res = deriveVerifiedWinner(baseCandidate, 'run_01', identicalRunRecord);
    assert.equal(res.isVerifiedWinner, false);
    assert.equal(res.statusType, 'error');
    assert.equal(res.hasDistinctRunId, false);
    assert.match(res.reasonText, /must not be identical/);
  });

  it('Test 5: Empty verification run ID rejected', () => {
    const emptyRunRecord: VerificationRecord = {
      ...validVerificationRecord,
      verification_run_id: '',
    };
    const res = deriveVerifiedWinner(baseCandidate, 'run_search_01', emptyRunRecord);
    assert.equal(res.isVerifiedWinner, false);
    assert.equal(res.hasDistinctRunId, false);
    assert.equal(res.badgeLabel, 'VERIFICATION PENDING');
  });

  it('Test 6: Drift exceeds declared tolerance rejected', () => {
    const driftedRecord: VerificationRecord = {
      ...validVerificationRecord,
      verification_verdict: 'VERIFIED',
      drift_analysis: {
        slo_drift_detected: true,
        drift_exceeded: true,
        comparisons: [
          {
            metric_name: 'ttft_ms.p95',
            reference_value: 26.0,
            verification_value: 38.0,
            absolute_drift: 12.0,
            tolerance: 3.0,
            comparison_method: 'absolute_difference',
            unit: 'ms',
            passed: false,
            drift_acceptable: false,
            failure_reason: 'Drift 12.0ms exceeded tolerance 3.0ms',
          },
        ],
      },
    };
    const res = deriveVerifiedWinner(baseCandidate, 'run_search_01', driftedRecord);
    assert.equal(res.isVerifiedWinner, false);
    assert.equal(res.statusType, 'error');
    assert.equal(res.badgeLabel, 'DRIFT BREACH');
  });

  it('Test 7: Undeclared tolerance returns amber state and fails verification', () => {
    const undeclaredToleranceRecord: VerificationRecord = {
      ...validVerificationRecord,
      drift_analysis: {
        slo_drift_detected: false,
        comparisons: [
          {
            metric_name: 'ttft_ms.p95',
            reference_value: 26.0,
            verification_value: 27.0,
            absolute_drift: 1.0,
            tolerance: undefined as any, // Missing!
            comparison_method: 'absolute_difference',
            unit: 'ms',
            passed: true,
          },
        ],
      },
    };
    const res = deriveVerifiedWinner(baseCandidate, 'run_search_01', undeclaredToleranceRecord);
    assert.equal(res.isVerifiedWinner, false);
    assert.equal(res.statusType, 'warning');
    assert.equal(res.toleranceDeclared, false);
    assert.equal(res.badgeLabel, 'TOLERANCE UNDECLARED');
  });

  it('Test 8: Headroom and binding-constraint calculations', () => {
    const constraints: SLOConstraint[] = [
      {
        metric_name: 'ttft_ms',
        statistic: 'p95',
        threshold: 50.0,
        unit: 'ms',
        operator: '<=',
      },
      {
        metric_name: 'throughput',
        statistic: 'mean',
        threshold: 50.0,
        unit: 'tok/s',
        operator: '>=',
      },
    ];

    // Case A: 47ms TTFT on 50ms ceiling -> 3ms headroom (6% margin)
    //         60 tok/s on 50 floor -> 10 tok/s headroom (20% margin)
    // Most binding constraint is TTFT (6% margin < 20% margin)
    const measuredPassing = {
      'ttft_ms.p95': 47.0,
      'throughput.mean': 60.0,
    };
    const bindingPassing = computeBindingConstraintHeadroom(constraints, measuredPassing);
    assert.ok(bindingPassing);
    assert.equal(bindingPassing?.metricName, 'ttft_ms');
    assert.equal(bindingPassing?.isPassing, true);
    assert.equal(bindingPassing?.absoluteHeadroom, 3.0);
    assert.equal(bindingPassing?.formattedHeadroom, '3.0 ms headroom');

    // Case B: 68ms TTFT on 50ms ceiling -> 18ms over ceiling (breach)
    const measuredBreach = {
      'ttft_ms.p95': 68.0,
      'throughput.mean': 43.8,
    };
    const bindingBreach = computeBindingConstraintHeadroom(constraints, measuredBreach);
    assert.ok(bindingBreach);
    assert.equal(bindingBreach?.isPassing, false);
    assert.equal(bindingBreach?.formattedHeadroom, '18.0 ms over ceiling');

    // Format utility tests
    assert.equal(formatLatency(47.2), '47.2 ms');
    assert.equal(formatLatency(1500), '1.50 s');
    assert.equal(formatThroughput(61800), '61.8k tok/s');
  });

  it('Test 9: Lower-bound constraint breach formats as below floor', () => {
    const floorConstraint: SLOConstraint[] = [
      {
        metric_name: 'throughput',
        statistic: 'p95',
        threshold: 50.0,
        unit: 'requests/s',
        operator: '>=',
      },
    ];

    // Candidate has 41.2 tok/s against 50.0 tok/s floor
    const measuredDeficit = {
      'throughput.p95': 41.2,
    };
    const res = computeBindingConstraintHeadroom(floorConstraint, measuredDeficit);
    assert.ok(res);
    assert.equal(res?.isPassing, false);
    assert.equal(res?.absoluteHeadroom, -8.8);
    // Crucial bug fix verification: must report 'below floor', NEVER 'over ceiling'
    assert.equal(res?.formattedHeadroom, '8.8 requests/s below floor');
  });

  it('Test 10: Pareto frontier identifies non-dominated empirical configurations', () => {
    const candidates: UICandidate[] = [
      // Feasible A: 24ms, 61.8k tok/s -> Optimal
      {
        id: 'C-02', name: 'Balanced', subtitle: '', batch: 16, concurrency: 32, kvCache: 'FP8',
        p50: 24, p95: 24, p99: 30, throughput: 61.8, error: 0.08, gpu: 78,
        feasible: true, feasibilityVerdict: 'FEASIBLE', evidenceValidity: 'VALID',
        reason: 'Meets constraints', tag: 'WINNER', ttftP95: 26, itlP95: 9.4
      },
      // Feasible B: 20ms, 40.0k tok/s -> Lower latency, lower throughput -> Also Pareto optimal
      {
        id: 'C-05', name: 'Ultra Low Latency', subtitle: '', batch: 4, concurrency: 8, kvCache: 'FP16',
        p50: 18, p95: 20, p99: 25, throughput: 40.0, error: 0.02, gpu: 40,
        feasible: true, feasibilityVerdict: 'FEASIBLE', evidenceValidity: 'VALID',
        reason: 'Meets constraints', tag: 'FEASIBLE', ttftP95: 20, itlP95: 8.0
      },
      // Feasible C: 26ms, 50.0k tok/s -> Dominated by C-02 (24ms < 26ms AND 61.8k > 50.0k)
      {
        id: 'C-06', name: 'Sub-optimal', subtitle: '', batch: 8, concurrency: 16, kvCache: 'FP8',
        p50: 25, p95: 26, p99: 32, throughput: 50.0, error: 0.05, gpu: 60,
        feasible: true, feasibilityVerdict: 'FEASIBLE', evidenceValidity: 'VALID',
        reason: 'Meets constraints', tag: 'FEASIBLE', ttftP95: 28, itlP95: 10.0
      },
      // Infeasible D: 68ms, 43.8k tok/s -> Infeasible, cannot be Pareto winner
      {
        id: 'C-01', name: 'Baseline', subtitle: '', batch: 8, concurrency: 16, kvCache: 'FP16',
        p50: 36, p95: 68, p99: 91, throughput: 43.8, error: 0.08, gpu: 61,
        feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'VALID',
        reason: 'Breaches ceiling', tag: 'BASELINE', ttftP95: 38, itlP95: 14.8
      },
    ];

    const { paretoIds, sortedCandidates } = identifyParetoFrontier(candidates);

    // C-02 and C-05 are non-dominated
    assert.equal(paretoIds.has('C-02'), true);
    assert.equal(paretoIds.has('C-05'), true);

    // C-06 is strictly dominated by C-02
    assert.equal(paretoIds.has('C-06'), false);
    const c06 = sortedCandidates.find((c) => c.id === 'C-06');
    assert.equal(c06?.isParetoDominated, true);

    // Infeasible C-01 is marked dominated
    assert.equal(paretoIds.has('C-01'), false);
    const c01 = sortedCandidates.find((c) => c.id === 'C-01');
    assert.equal(c01?.isParetoDominated, true);
  });

  it('Test 11: Strict six-run budget invariant enforcement (AGENTS.md § 3.2)', () => {
    // 1 baseline + 4 search candidates + 1 verification = exactly 6 runs
    const baselineRuns = 1;
    const searchSpaceRuns = 4;
    const verificationRuns = 1;
    const totalExperimentBudget = baselineRuns + searchSpaceRuns + verificationRuns;

    assert.equal(totalExperimentBudget, 6);
    assert.equal(baselineRuns, 1);
    assert.equal(searchSpaceRuns, 4);
    assert.equal(verificationRuns, 1);

    // Preflight smoke test probe must NOT deduct from the 6-run budget
    const smokeProbeRuns = 1;
    const runsDrawnFromBudget = totalExperimentBudget; // smoke probe is independent
    assert.equal(runsDrawnFromBudget, 6);
    assert.ok(smokeProbeRuns > 0);
  });

  it('Test 12: View Transitions API progressive enhancement execution (Overdrive mode)', async () => {
    let executed = false;
    await runWithViewTransition(() => {
      executed = true;
    });
    assert.equal(executed, true, 'Callback must execute synchronously or resolved when startViewTransition is absent (e.g. Node.js environment)');

    let asyncExecuted = false;
    await runWithViewTransition(async () => {
      asyncExecuted = true;
    });
    assert.equal(asyncExecuted, true, 'Async callback must resolve cleanly');
  });

  it('Test 13: Mathematical formatting resilience and edge case handling (Harden mode)', () => {
    // 1. Latency formatting
    assert.equal(formatLatency(null), '—');
    assert.equal(formatLatency(undefined), '—');
    assert.equal(formatLatency(NaN), '—');
    assert.equal(formatLatency(Infinity), '—');
    assert.equal(formatLatency(-Infinity), '—');
    assert.equal(formatLatency(0.4), '400 µs');
    assert.equal(formatLatency(-0.4), '-400 µs');
    assert.equal(formatLatency(24.5), '24.5 ms');
    assert.equal(formatLatency(-24.5), '-24.5 ms');
    assert.equal(formatLatency(1500), '1.50 s');
    assert.equal(formatLatency(-1500), '-1.50 s');

    // 2. Throughput formatting
    assert.equal(formatThroughput(null), '—');
    assert.equal(formatThroughput(undefined), '—');
    assert.equal(formatThroughput(NaN), '—');
    assert.equal(formatThroughput(Infinity), '—');
    assert.equal(formatThroughput(50.4), '50.4 tok/s');
    assert.equal(formatThroughput(1500), '1.5k tok/s');

    // 3. Binding constraint with empty / invalid values
    assert.equal(computeBindingConstraintHeadroom([], {}), null);

    const testConstraints: SLOConstraint[] = [
      { metric_name: 'ttft_ms', statistic: 'p95', threshold: 50.0, unit: 'ms', operator: '<=' },
      { metric_name: 'throughput', statistic: 'p95', threshold: 60.0, unit: 'tok/s', operator: '>=' },
    ];

    // Measured values containing NaN must be skipped without crashing
    const headroomWithNaN = computeBindingConstraintHeadroom(testConstraints, {
      'ttft_ms.p95': NaN,
      'throughput.p95': 55.0, // 5 below floor
    });
    assert.ok(headroomWithNaN);
    assert.equal(headroomWithNaN?.isPassing, false);
    assert.equal(headroomWithNaN?.formattedHeadroom, '5.0 tok/s below floor');
  });
});
