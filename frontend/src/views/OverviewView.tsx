import React, { useState, useEffect } from 'react';
import { StageHero } from '../components/stage/StageHero';
import { VerifiedReveal } from '../components/stage/VerifiedReveal';
import { SloGauge } from '../components/stage/SloGauge';
import { TradeoffPlot } from '../components/charts/TradeoffPlot';
import { HeadToHeadDelta } from '../components/charts/HeadToHeadDelta';
import { ReasonBox } from '../components/common/ReasonBox';
import { MetricCard } from '../components/common/MetricCard';
import { DemoDataChip } from '../components/common/DemoDataChip';
import { Badge } from '../components/common/Badge';
import { formatNumber, formatLatency } from '../lib/format';
import type { HeadroomResult } from '../lib/format';
import type { VerificationDerivationResult } from '../lib/status';
import type { UICandidate, UIExperiment } from '../lib/adapters/viewModel';
import { mapSmokeTestEvidence } from '../lib/adapters/viewModel';
import type { SmokeTestArtifactResponse, RuntimeProfileResponse, PercentileDistribution } from '../types/contracts';

interface OverviewViewProps {
  recommendedCandidate: UICandidate;
  hasFeasibleCandidate: boolean;
  hasSelectedFeasibleWinner: boolean;
  baselineCandidate: UICandidate;
  candidates: UICandidate[];
  bindingHeadroom: HeadroomResult | null;
  verificationStatus: VerificationDerivationResult;
  smokeTest?: SmokeTestArtifactResponse | null;
  runtimeProfile?: RuntimeProfileResponse | null;
  activeExperiment?: UIExperiment | null;
  onOpenCandidateDrawer: (candidate: UICandidate) => void;
  onNavigateToVerification: () => void;
  onNavigateToExperiments: () => void;
  onNavigateToTuningLab: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  recommendedCandidate,
  hasFeasibleCandidate,
  hasSelectedFeasibleWinner,
  baselineCandidate,
  candidates,
  bindingHeadroom,
  verificationStatus,
  smokeTest,
  /* runtimeProfile */
  activeExperiment,
  onOpenCandidateDrawer,
  onNavigateToVerification,
  onNavigateToExperiments,
  onNavigateToTuningLab,
}) => {
  const isVerified = verificationStatus.isVerifiedWinner;
  const [replayKey, setReplayKey] = useState(0);

  // Global hotkey 'R' to replay reveal when on Overview
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) {
        return;
      }
      if (e.key === 'r' || e.key === 'R') {
        setReplayKey((k: number) => k + 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const smokeEvidenceData = mapSmokeTestEvidence(smokeTest);
  const smokeTtft = smokeEvidenceData.ttftMs;
  const smokeTotalLat = smokeEvidenceData.totalLatencyMs;
  const smokeModel = smokeTest?.model || 'Unavailable';
  const smokeHost = smokeTest?.endpoint_host || 'Unavailable';
  const smokeEvidence = smokeEvidenceData.evidenceClassification;

  return (
    <div className="view-overview workspace-enter" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Workspace Header / Context */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1
              style={{
                margin: 0,
                fontSize: '24px',
                fontWeight: 700,
                color: 'var(--text-primary, #F0F3EF)',
                letterSpacing: '-0.025em',
                textWrap: 'balance',
              }}
            >
              Inference Optimization & Verification
            </h1>
            <DemoDataChip size="sm" />
          </div>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', lineHeight: 1.45, textWrap: 'pretty', maxWidth: '75ch' }}>
            Experiment: <span style={{ color: 'var(--text-primary, #F0F3EF)', fontFamily: 'var(--font-mono, monospace)' }}>{activeExperiment?.id || 'exp-audit-offline-campaign'}</span> · {activeExperiment?.arrivalMode ? `${activeExperiment.arrivalMode} arrival @ ${activeExperiment.targetOfferedRateRps ?? '—'} rps` : 'Arrival metadata unavailable'} · {hasSelectedFeasibleWinner ? <>Winner: <span style={{ color: 'var(--primary-bright, #95D500)', fontFamily: 'var(--font-mono, monospace)', fontWeight: 600 }}>{recommendedCandidate.id}</span></> : hasFeasibleCandidate ? <strong>Feasible candidates exist; selected winner unavailable</strong> : <strong>No feasible candidate</strong>}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={onNavigateToVerification}
            style={{
              background: 'none',
              border: '1px solid var(--border-strong, #384635)',
              backgroundColor: 'var(--elevated, #1D251E)',
              color: 'var(--text-primary, #F0F3EF)',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              padding: '6px 14px',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Audit Verification Console →
          </button>
        </div>
      </div>

      {/* Prominent Live Nebius Smoke Test Observability Banner */}
      <div
        className="live-smoke-test-card"
        style={{
          padding: '16px 20px',
          backgroundColor: 'var(--surface, #0E120F)',
          border: '1px solid var(--border-strong, #384635)',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.4)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 700,
                fontFamily: 'var(--font-mono, monospace)',
                backgroundColor: 'rgba(118, 185, 0, 0.15)',
                color: 'var(--primary-bright, #95D500)',
                border: '1px solid var(--primary, #76B900)',
                letterSpacing: '0.04em',
              }}
            >
              <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--primary-bright, #95D500)' }} />
              {smokeEvidence} SMOKE TEST
            </span>
            <span style={{ fontSize: '12px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)', fontFamily: 'var(--font-mono, monospace)' }}>
              Nebius Token Factory · {smokeModel}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
              Endpoint: {smokeHost}
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '2px 8px',
                borderRadius: '3px',
                fontSize: '10px',
                fontWeight: 600,
                fontFamily: 'var(--font-mono, monospace)',
                backgroundColor: 'rgba(233, 185, 73, 0.12)',
                color: 'var(--warning, #E9B949)',
                border: '1px solid rgba(233, 185, 73, 0.3)',
              }}
            >
              {smokeTest?.status === 'PASSED' && smokeEvidence === 'LIVE' ? 'LIVE BASELINE RECORDED' : 'LIVE BASELINE NOT RECORDED'}
            </span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          <div style={{ padding: '10px 14px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>SMOKE PROBE TTFT</div>
            <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono, monospace)', color: 'var(--primary-bright, #95D500)', marginTop: '2px' }}>
              {smokeTtft != null ? `${smokeTtft.toFixed(1)} ms` : '—'}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted, #727D73)', marginTop: '2px' }}>Single probe measurement</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>TOTAL PROBE LATENCY</div>
            <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #F0F3EF)', marginTop: '2px' }}>
              {smokeTotalLat != null ? `${smokeTotalLat.toFixed(1)} ms` : '—'}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted, #727D73)', marginTop: '2px' }}>Input: {smokeEvidenceData.inputTokens ?? '—'} tok · Output: {smokeEvidenceData.outputTokens ?? '—'} tok</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>STREAMING PROBE</div>
            <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono, monospace)', color: 'var(--primary-bright, #95D500)', marginTop: '2px' }}>
              {smokeEvidenceData.streamStatus}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted, #727D73)', marginTop: '2px' }}>{smokeEvidenceData.streamChunkCount != null ? `${smokeEvidenceData.streamChunkCount} chunks · first TTFT ${smokeEvidenceData.streamFirstChunkTtftMs?.toFixed(1) ?? '—'} ms` : 'Streaming evidence unavailable'}</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>SERVING CONTROLS LIMITATION</div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary, #A0AAA0)', marginTop: '4px', lineHeight: 1.35 }}>
              Server-side vLLM scheduler controls unavailable through Token Factory endpoint.
            </div>
          </div>
        </div>
      </div>

      {/* Stage Hero with 1.4s Reveal Effect */}
      <VerifiedReveal isVerified={isVerified} replayKey={replayKey}>
        <StageHero
          candidateName={hasSelectedFeasibleWinner ? recommendedCandidate.name : hasFeasibleCandidate ? 'Selected winner unavailable' : 'No feasible candidate'}
          candidateId={hasSelectedFeasibleWinner ? recommendedCandidate.id : 'NO WINNER'}
          runtimeModel="Meta-Llama-3-8B-Instruct · vLLM (DEMO DATA · OFFLINE OPTIMIZATION)"
          bindingHeadroom={bindingHeadroom}
          verificationStatus={verificationStatus}
          throughputDelta={hasSelectedFeasibleWinner ? `${formatNumber(recommendedCandidate.throughput, 1)} tokens/s output throughput · Evaluator selected feasible candidate` : hasFeasibleCandidate ? 'Feasible candidates exist, but no selected winner was recorded' : 'No feasible candidate in the tested campaign'}
          onOpenDetails={() => onOpenCandidateDrawer(recommendedCandidate)}
          onReplay={() => setReplayKey((k: number) => k + 1)}
        />
      </VerifiedReveal>

      {/* Campaign Search Budget & Stopping Condition (Section 4.4 & AGENTS.md § 6) */}
      <div
        style={{
          padding: '16px 20px',
          backgroundColor: 'var(--surface, #0E120F)',
          border: '1px solid var(--border, #263124)',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #F0F3EF)', textTransform: 'uppercase' }}>
              Optimization Search Budget & Stopping Reason
            </span>
            <Badge tone="neutral" size="sm">{activeExperiment?.candidateEvaluationsCount ?? candidates.length} / {activeExperiment?.candidateBudget ?? candidates.length} evaluations consumed</Badge>
          </div>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            Stopping Reason: <span style={{ color: 'var(--primary-bright, #95D500)', fontWeight: 600 }}>{activeExperiment?.stoppingReason ?? 'Unavailable'}</span> ({activeExperiment?.searchSpaceCandidateCount ?? '—'} parameter configurations + baseline)
          </span>
        </div>

        {/* 5 Candidate Allocation Blocks */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>
          {candidates.map((c, i) => (
            <div
              key={c.id}
              onClick={() => onOpenCandidateDrawer(c)}
              style={{
                padding: '8px 10px',
                backgroundColor: c.tag === 'WINNER' ? 'rgba(118, 185, 0, 0.1)' : 'var(--raised, #151B15)',
                border: '1px solid',
                borderColor: c.tag === 'WINNER' ? 'var(--primary, #76B900)' : 'var(--border, #263124)',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              <div style={{ color: c.tag === 'WINNER' ? 'var(--primary-bright, #95D500)' : 'var(--text-muted, #727D73)', fontSize: '10px', fontWeight: 700 }}>
              {c.tag === 'WINNER' && c.feasible ? 'WINNER' : `RUN ${i + 1}`}
              </div>
              <div style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600, marginTop: '2px' }}>
                {c.id}
              </div>
              <div style={{ color: 'var(--text-secondary, #A0AAA0)', fontSize: '10px', marginTop: '2px' }}>
                {formatNumber(c.throughput, 1)} tok/s · {c.feasibilityVerdict}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Empirical Telemetry KPI Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
        <MetricCard
          label="TTFT (P95 First-Token)"
          value={formatLatency(recommendedCandidate.ttftP95)}
          tone={recommendedCandidate.ttftP95 == null ? 'warning' : recommendedCandidate.ttftP95 <= 2500 ? 'success' : 'danger'}
          delta={recommendedCandidate.ttftP95 == null ? 'Metric unavailable' : `+${(2500 - recommendedCandidate.ttftP95).toFixed(1)} ms margin`}
          subtext={`Hard ceiling: ${activeExperiment?.sloConstraints?.find((constraint) => constraint.metric_name === 'ttft_ms')?.threshold ?? '—'} ms · Observed: ${formatLatency(recommendedCandidate.ttftP95)}`}
        />

        <MetricCard
          label="ITL (P95 Inter-Token)"
          value={formatLatency(recommendedCandidate.itlP95)}
          tone={recommendedCandidate.itlP95 == null ? 'warning' : recommendedCandidate.itlP95 <= 30 ? 'success' : 'danger'}
          delta={recommendedCandidate.itlP95 == null ? 'Metric unavailable' : `Observed p95; SLO checks p50`}
          subtext="Observed metric; campaign SLO applies to ITL p50"
        />

        <MetricCard
          label="Output Token Throughput"
          value={`${formatNumber(recommendedCandidate.throughput, 1)} tok/s`}
          tone={recommendedCandidate.throughput == null ? 'warning' : 'success'}
          delta={hasFeasibleCandidate ? 'Evaluator selected feasible candidate' : 'No feasible candidate'}
          subtext="Ranking objective metric"
        />

        <MetricCard
          label="Request Error Rate"
          value={`${formatNumber(recommendedCandidate.error, 2)}%`}
          tone="success"
          delta="+5.00% margin"
          subtext="Hard ceiling: 5.00%"
        />
      </div>

      {/* Two Column Section: SLO Gauges + Head-to-Head Delta */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        {/* Left: SLO Gauges */}
        <div
          style={{
            backgroundColor: 'var(--surface, #0E120F)',
            border: '1px solid var(--border, #263124)',
            borderRadius: '6px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
              Declared SLO Constraints
            </h2>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
              evaluator: v1.0.0 · policy: slo-1.0.0
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {(activeExperiment?.sloConstraints ?? []).map((constraint) => {
              const distributions: Record<string, PercentileDistribution | undefined> = {
                ttft_ms: recommendedCandidate.metricSet?.ttft_ms ?? { p95: recommendedCandidate.ttftP95 },
                itl_ms: recommendedCandidate.metricSet?.itl_ms ?? { p95: recommendedCandidate.itlP95 },
                e2e_latency_ms: recommendedCandidate.metricSet?.e2e_latency_ms ?? { p95: recommendedCandidate.e2eP95 },
              };
              const observed = constraint.metric_name === 'error_rate'
                ? recommendedCandidate.metricSet?.error_rate ?? (recommendedCandidate.error != null ? recommendedCandidate.error / 100 : undefined)
                : distributions[constraint.metric_name]?.[constraint.statistic as keyof PercentileDistribution];
              return observed == null ? null : (
                <SloGauge
                  key={`${constraint.metric_name}.${constraint.statistic}`}
                  label={constraint.metric_name}
                  measured={observed}
                  threshold={constraint.threshold}
                  unit={constraint.unit}
                  isUpperBound={constraint.operator === '<=' || constraint.operator === '<'}
                  statistic={constraint.statistic}
                />
              );
            })}
          </div>

          <ReasonBox
            reasonCode={recommendedCandidate.reasonCodes?.[0]}
            detailText={recommendedCandidate.reason}
            isPassing={recommendedCandidate.feasible}
          />
        </div>

        {/* Right: Baseline vs Recommended Comparison using HeadToHeadDelta */}
        <div
          style={{
            backgroundColor: 'var(--surface, #0E120F)',
            border: '1px solid var(--border, #263124)',
            borderRadius: '6px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
              Head-to-Head Telemetry Delta
            </h2>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
              {hasSelectedFeasibleWinner ? `Baseline ${baselineCandidate.id} vs Selected ${recommendedCandidate.id}` : 'No selected feasible candidate for comparison'}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {hasSelectedFeasibleWinner && baselineCandidate.ttftP95 != null && recommendedCandidate.ttftP95 != null && <HeadToHeadDelta
              label="TTFT P95 Latency"
              baselineVal={baselineCandidate.ttftP95}
              candidateVal={recommendedCandidate.ttftP95}
              unit="ms"
              isLowerBetter={true}
            />}
            {hasSelectedFeasibleWinner && baselineCandidate.itlP95 != null && recommendedCandidate.itlP95 != null && <HeadToHeadDelta
              label="ITL P95 Latency"
              baselineVal={baselineCandidate.itlP95}
              candidateVal={recommendedCandidate.itlP95}
              unit="ms"
              isLowerBetter={true}
            />}
            {hasSelectedFeasibleWinner && baselineCandidate.e2eP95 != null && recommendedCandidate.e2eP95 != null && <HeadToHeadDelta
              label="End-to-End P95 Latency"
              baselineVal={baselineCandidate.e2eP95}
              candidateVal={recommendedCandidate.e2eP95}
              unit="ms"
              isLowerBetter={true}
            />}
            {hasSelectedFeasibleWinner && baselineCandidate.throughput != null && recommendedCandidate.throughput != null && <HeadToHeadDelta
              label="Output Token Throughput"
              baselineVal={baselineCandidate.throughput}
              candidateVal={recommendedCandidate.throughput}
              unit="tok/s"
              isLowerBetter={false}
            />}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '8px', borderTop: '1px solid var(--border, #263124)' }}>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
              All 5 campaign runs available with raw unaggregated event logs
            </span>
            <button
              type="button"
              onClick={onNavigateToExperiments}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--primary-bright, #95D500)',
                fontSize: '11px',
                fontFamily: 'var(--font-mono, monospace)',
                fontWeight: 600,
                cursor: 'pointer',
                padding: 0,
              }}
            >
              View All 5 Runs →
            </button>
          </div>
        </div>
      </div>

      {/* Primary 2D Latency vs. Throughput Pareto Visualization */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)' }}>
              Pareto Latency vs. Throughput Empirical Space
            </h2>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
              Tested candidate coordinates · DEMO DATA · OFFLINE OPTIMIZATION
            </span>
          </div>

          <button
            type="button"
            onClick={onNavigateToTuningLab}
            style={{
              background: 'none',
              border: '1px solid var(--border, #263124)',
              backgroundColor: 'var(--raised, #151B15)',
              color: 'var(--text-primary, #F0F3EF)',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              padding: '6px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Open Tuning Lab Matrix →
          </button>
        </div>

        <TradeoffPlot
          candidates={candidates}
          selectedCandidateId={recommendedCandidate.id}
          baselineCandidateId={baselineCandidate.id}
          onSelectCandidate={onOpenCandidateDrawer}
        />
      </div>
    </div>
  );
};
