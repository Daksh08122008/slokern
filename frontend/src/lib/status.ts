/**
 * SLOKern 4-Dimension Status Model and Deterministic Verification Derivation
 * Strictly adheres to DEC-0014 and AGENTS.md § 1, 3, 5, 7.
 *
 * The 4 dimensions:
 * 1. ExecutionState: PENDING | RUNNING | COMPLETED | FAILED | CANCELLED
 * 2. EvidenceState: VALID | INVALID | CONTAMINATED | STALE
 * 3. FeasibilityState: FEASIBLE | INFEASIBLE | INCONCLUSIVE
 * 4. VerificationState: NOT_RUN | VERIFYING | VERIFIED | VERIFICATION_FAILED | VERIFICATION_INCONCLUSIVE
 */

import type {
  EvidenceValidity,
  FeasibilityVerdict,
  VerificationRecord,
} from '../types/contracts';

export type { ExecutionStatus, VerificationState } from '../types/contracts';

export type ExtendedEvidenceState = EvidenceValidity | 'STALE';

export interface CandidateStatusInput {
  candidateId: string;
  isFeasible: boolean;
  feasibilityVerdict?: FeasibilityVerdict | string;
  evidenceValidity?: ExtendedEvidenceState | string;
  isStale?: boolean;
}

export interface VerificationDerivationResult {
  isVerifiedWinner: boolean;
  statusType: 'verified' | 'feasible' | 'inconclusive' | 'infeasible' | 'error' | 'warning' | 'neutral';
  badgeLabel: string;
  reasonText: string;
  hasDistinctRunId: boolean;
  isDriftAcceptable: boolean;
  toleranceDeclared: boolean;
}

/**
 * Pure function to derive whether a candidate is genuinely a Verified Winner.
 *
 * Invariants:
 * 1. Candidate must be FEASIBLE with VALID evidence (never stale or contaminated).
 * 2. Verification run ID must be non-empty and strictly DIFFERENT from the search run ID.
 * 3. Verification record verdict must be VERIFIED.
 * 4. All relevant metric drifts must have declared tolerances and be strictly within tolerance.
 *    If tolerance is undeclared, it flags "Drift tolerance undeclared" and FAILS verification.
 */
export function deriveVerifiedWinner(
  candidate: CandidateStatusInput,
  searchRunId: string | null | undefined,
  verification: VerificationRecord | null | undefined
): VerificationDerivationResult {
  // 1. Check Feasibility
  const feasibility = candidate.feasibilityVerdict?.toUpperCase() || (candidate.isFeasible ? 'FEASIBLE' : 'INFEASIBLE');
  const evidence = (candidate.evidenceValidity?.toUpperCase() as ExtendedEvidenceState) || (candidate.isStale ? 'STALE' : 'VALID');

  if (candidate.isStale || evidence === 'STALE') {
    return {
      isVerifiedWinner: false,
      statusType: 'warning',
      badgeLabel: 'STALE EVIDENCE',
      reasonText: 'Measurements are older than the declared expiration horizon. Rerun required.',
      hasDistinctRunId: false,
      isDriftAcceptable: false,
      toleranceDeclared: false,
    };
  }

  if (evidence === 'INVALID' || evidence === 'CONTAMINATED') {
    return {
      isVerifiedWinner: false,
      statusType: 'error',
      badgeLabel: 'INVALID EVIDENCE',
      reasonText: `Telemetry evidence is marked ${evidence}. Discarded from evaluation.`,
      hasDistinctRunId: false,
      isDriftAcceptable: false,
      toleranceDeclared: false,
    };
  }

  if (feasibility === 'INFEASIBLE') {
    return {
      isVerifiedWinner: false,
      statusType: 'infeasible',
      badgeLabel: 'INFEASIBLE',
      reasonText: 'One or more hard SLO constraints breached.',
      hasDistinctRunId: false,
      isDriftAcceptable: false,
      toleranceDeclared: false,
    };
  }

  if (feasibility === 'INCONCLUSIVE') {
    return {
      isVerifiedWinner: false,
      statusType: 'inconclusive',
      badgeLabel: 'INCONCLUSIVE',
      reasonText: 'Insufficient or uncertain sample evidence to establish feasibility.',
      hasDistinctRunId: false,
      isDriftAcceptable: false,
      toleranceDeclared: false,
    };
  }

  // If candidate is FEASIBLE, check verification state
  if (!verification) {
    return {
      isVerifiedWinner: false,
      statusType: 'feasible',
      badgeLabel: 'FEASIBLE (UNVERIFIED)',
      reasonText: 'Candidate satisfies hard SLOs but has not completed independent verification.',
      hasDistinctRunId: false,
      isDriftAcceptable: false,
      toleranceDeclared: false,
    };
  }

  const origId = verification.original_run_id?.trim();
  const verifyId = verification.verification_run_id?.trim();

  // Run ID check: Must have distinct non-empty verification run ID
  if (!verifyId || verifyId.length === 0) {
    return {
      isVerifiedWinner: false,
      statusType: 'inconclusive',
      badgeLabel: 'VERIFICATION PENDING',
      reasonText: 'No independent verification run ID recorded.',
      hasDistinctRunId: false,
      isDriftAcceptable: false,
      toleranceDeclared: false,
    };
  }

  const effectiveSearchId = searchRunId?.trim() || origId;
  const isDistinct = Boolean(effectiveSearchId && verifyId && effectiveSearchId !== verifyId);

  if (!isDistinct) {
    return {
      isVerifiedWinner: false,
      statusType: 'error',
      badgeLabel: 'INVALID VERIFICATION',
      reasonText: `Verification run ID (${verifyId}) must not be identical to search run ID (${effectiveSearchId}).`,
      hasDistinctRunId: false,
      isDriftAcceptable: false,
      toleranceDeclared: false,
    };
  }

  // Drift Analysis & Tolerance Check
  const driftAnalysis = verification.drift_analysis;
  let toleranceDeclared = true;
  let isDriftAcceptable = true;
  let driftFailureNote = '';

  if (driftAnalysis) {
    if (driftAnalysis.slo_drift_detected || driftAnalysis.drift_exceeded) {
      isDriftAcceptable = false;
      driftFailureNote = 'Physical latency drift exceeded declared tolerance.';
    }

    // Check comparisons list or record
    const comparisons = driftAnalysis.comparisons || 
      (driftAnalysis.metric_comparisons ? Object.values(driftAnalysis.metric_comparisons) : []);

    for (const comp of comparisons) {
      const tol = comp.tolerance ?? comp.tolerance_threshold;
      if (tol === undefined || tol === null || Number.isNaN(tol)) {
        toleranceDeclared = false;
        isDriftAcceptable = false;
        driftFailureNote = `Drift tolerance not declared for metric ${comp.metric_name}.`;
        break;
      }
      if (comp.passed === false || comp.drift_acceptable === false) {
        isDriftAcceptable = false;
        driftFailureNote = comp.failure_reason || `${comp.metric_name} absolute drift of ${comp.absolute_drift} exceeded tolerance ${tol}.`;
        break;
      }
    }
  }

  if (!toleranceDeclared) {
    return {
      isVerifiedWinner: false,
      statusType: 'warning',
      badgeLabel: 'TOLERANCE UNDECLARED',
      reasonText: driftFailureNote || 'Drift tolerance threshold was not declared in verification policy.',
      hasDistinctRunId: true,
      isDriftAcceptable: false,
      toleranceDeclared: false,
    };
  }

  if (!isDriftAcceptable) {
    return {
      isVerifiedWinner: false,
      statusType: 'error',
      badgeLabel: 'DRIFT BREACH',
      reasonText: driftFailureNote || 'Verification run drifted outside declared tolerance.',
      hasDistinctRunId: true,
      isDriftAcceptable: false,
      toleranceDeclared: true,
    };
  }

  // Final Verdict check
  const verdict = verification.verification_verdict?.toUpperCase();
  if (verdict === 'VERIFIED') {
    return {
      isVerifiedWinner: true,
      statusType: 'verified',
      badgeLabel: 'VERIFIED WINNER',
      reasonText: 'Passed independent verification rerun under declared workload and drift tolerance.',
      hasDistinctRunId: true,
      isDriftAcceptable: true,
      toleranceDeclared: true,
    };
  }

  if (verdict === 'VERIFICATION_FAILED') {
    return {
      isVerifiedWinner: false,
      statusType: 'error',
      badgeLabel: 'VERIFICATION FAILED',
      reasonText: verification.final_decision_notes || 'Independent verification rerun failed SLO constraints.',
      hasDistinctRunId: true,
      isDriftAcceptable: false,
      toleranceDeclared: true,
    };
  }

  return {
    isVerifiedWinner: false,
    statusType: 'inconclusive',
    badgeLabel: 'INCONCLUSIVE',
    reasonText: verification.final_decision_notes || 'Verification results inconclusive.',
    hasDistinctRunId: true,
    isDriftAcceptable: false,
    toleranceDeclared: true,
  };
}
