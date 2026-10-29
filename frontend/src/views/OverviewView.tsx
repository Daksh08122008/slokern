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
import { formatNumber, formatLatency, formatThroughput } from '../lib/format';
import type { HeadroomResult } from '../lib/format';
import type { VerificationDerivationResult } from '../lib/status';
import type { UICandidate } from '../lib/adapters/viewModel';

interface OverviewViewProps {
  recommendedCandidate: UICandidate;
  baselineCandidate: UICandidate;
  candidates: UICandidate[];
  bindingHeadroom: HeadroomResult | null;
  verificationStatus: VerificationDerivationResult;
  onOpenCandidateDrawer: (candidate: UICandidate) => void;
  onNavigateToVerification: () => void;
  onNavigateToExperiments: () => void;
  onNavigateToTuningLab: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  recommendedCandidate,
  baselineCandidate,
  candidates,
  bindingHeadroom,
  verificationStatus,
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
            Workload: <span style={{ color: 'var(--text-primary, #F0F3EF)', fontFamily: 'var(--font-mono, monospace)' }}>chat-completions-prod</span> · Poisson arrival @ 16 rps · Llama-3-8B-Instruct on Nebius H100
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

      {/* Stage Hero with 1.4s Reveal Effect */}
      <VerifiedReveal isVerified={isVerified} replayKey={replayKey}>
        <StageHero
          candidateName={recommendedCandidate.name}
          candidateId={recommendedCandidate.id}
          runtimeModel="Llama-3-8B-Instruct · vLLM v0.6.3 (FP8 KV Cache)"
          bindingHeadroom={bindingHeadroom}
          verificationStatus={verificationStatus}
          throughputDelta="+41.1% throughput vs baseline (61.8k vs 43.8k tok/s)"
          onOpenDetails={() => onOpenCandidateDrawer(recommendedCandidate)}
          onReplay={() => setReplayKey((k: number) => k + 1)}
        />
      </VerifiedReveal>

      {/* Strict Six-Run Experiment Budget Status (AGENTS.md § 3.2 & 5.1) */}
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
              Experiment Budget (Strict 6-Run Limit)
            </span>
            <Badge tone="neutral" size="sm">6 / 6 Runs Consumed · 0 Remaining</Badge>
          </div>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            Preflight smoke probe separate · Zero budget leak guaranteed
          </span>
        </div>

        {/* 6 Run Allocation Progress Blocks */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>
          <div style={{ padding: '8px 10px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ color: 'var(--text-muted, #727D73)', fontSize: '11px' }}>RUN 1 (BASELINE)</div>
            <div style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600, marginTop: '2px' }}>C-01 · FP16</div>
            <div style={{ color: 'var(--primary-bright, #95D500)', fontSize: '11px', marginTop: '2px' }}>✓ Completed</div>
          </div>

          <div style={{ padding: '8px 10px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--primary, #76B900)', borderRadius: '4px' }}>
            <div style={{ color: 'var(--primary-bright, #95D500)', fontSize: '11px', fontWeight: 650 }}>RUN 2 (RECOMMENDED)</div>
            <div style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600, marginTop: '2px' }}>C-02 · FP8</div>
            <div style={{ color: 'var(--primary-bright, #95D500)', fontSize: '11px', marginTop: '2px' }}>✓ Completed</div>
          </div>

          <div style={{ padding: '8px 10px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ color: 'var(--text-muted, #727D73)', fontSize: '11px' }}>RUN 3 (SEARCH)</div>
            <div style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600, marginTop: '2px' }}>C-03 · FP8</div>
            <div style={{ color: 'var(--primary-bright, #95D500)', fontSize: '11px', marginTop: '2px' }}>✓ Completed</div>
          </div>

          <div style={{ padding: '8px 10px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ color: 'var(--text-muted, #727D73)', fontSize: '11px' }}>RUN 4 (SEARCH)</div>
            <div style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600, marginTop: '2px' }}>C-04 · FP16</div>
            <div style={{ color: 'var(--primary-bright, #95D500)', fontSize: '11px', marginTop: '2px' }}>✓ Completed</div>
          </div>

          <div style={{ padding: '8px 10px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ color: 'var(--text-muted, #727D73)', fontSize: '11px' }}>RUN 5 (SEARCH)</div>
            <div style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600, marginTop: '2px' }}>Boundary Scan</div>
            <div style={{ color: 'var(--primary-bright, #95D500)', fontSize: '11px', marginTop: '2px' }}>✓ Completed</div>
          </div>

          <div style={{ padding: '8px 10px', backgroundColor: 'var(--raised, #151B15)', border: '1px solid', borderColor: isVerified ? 'var(--primary-bright, #95D500)' : 'var(--border, #263124)', borderRadius: '4px' }}>
            <div style={{ color: isVerified ? 'var(--primary-bright, #95D500)' : 'var(--warning, #E9B949)', fontSize: '11px', fontWeight: 650 }}>RUN 6 (VERIFICATION)</div>
            <div style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600, marginTop: '2px' }}>verify_01HZX9K4</div>
            <div style={{ color: isVerified ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)', fontSize: '11px', marginTop: '2px' }}>
              {isVerified ? '✓ Verified Rerun' : 'Rerun Drift Fail'}
            </div>
          </div>
        </div>
      </div>

      {/* 4 Primary Telemetry Instruments using MetricCard */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '14px',
        }}
      >
        <MetricCard
          label="TTFT (P95 Latency)"
          value={formatLatency(recommendedCandidate.ttftP95)}
          tone={recommendedCandidate.ttftP95 <= 50 ? 'success' : 'danger'}
          delta={`+${(50 - recommendedCandidate.ttftP95).toFixed(1)} ms margin`}
          subtext="Hard ceiling: 50.0 ms"
        />

        <MetricCard
          label="ITL (P95 Decode Latency)"
          value={formatLatency(recommendedCandidate.itlP95)}
          tone={recommendedCandidate.itlP95 <= 15 ? 'success' : 'danger'}
          delta={`+${(15 - recommendedCandidate.itlP95).toFixed(1)} ms margin`}
          subtext="Hard ceiling: 15.0 ms"
        />

        <MetricCard
          label="Output Token Throughput"
          value={formatThroughput(recommendedCandidate.throughput * 1000)}
          tone={recommendedCandidate.throughput >= 50 ? 'success' : 'danger'}
          delta={`+${(recommendedCandidate.throughput - 50).toFixed(1)}k margin`}
          subtext="Hard floor: 50.0k tok/s"
        />

        <MetricCard
          label="Request Error Rate"
          value={`${formatNumber(recommendedCandidate.error, 2)}%`}
          tone={recommendedCandidate.error <= 1.0 ? 'success' : 'danger'}
          delta={`+${(1.0 - recommendedCandidate.error).toFixed(2)}% margin`}
          subtext="Hard ceiling: 1.00%"
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
              evaluator: v0.4.2 · policy: slo-prod-03
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <SloGauge
              label="Time to First Token (TTFT)"
              measured={recommendedCandidate.ttftP95}
              threshold={50.0}
              unit="ms"
              isUpperBound={true}
              statistic="p95"
            />
            <SloGauge
              label="Inter-Token Latency (ITL)"
              measured={recommendedCandidate.itlP95}
              threshold={15.0}
              unit="ms"
              isUpperBound={true}
              statistic="p95"
            />
            <SloGauge
              label="End-to-End Latency"
              measured={recommendedCandidate.p95}
              threshold={50.0}
              unit="ms"
              isUpperBound={true}
              statistic="p95"
            />
          </div>

          <ReasonBox
            reasonCode={recommendedCandidate.feasible ? (verificationStatus.isVerifiedWinner ? 'VERIFIED_WINNER_OPTIMAL' : 'FEASIBLE_CANDIDATE') : 'HARD_CONSTRAINTS_BREACHED'}
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
              Head-to-Head vs Baseline
            </h2>
            <Badge tone="neutral" size="sm">C-01 vs C-02</Badge>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <HeadToHeadDelta
              label="P95 Latency"
              baselineVal={baselineCandidate.p95}
              candidateVal={recommendedCandidate.p95}
              unit="ms"
              isLowerBetter={true}
            />
            <HeadToHeadDelta
              label="TTFT (P95)"
              baselineVal={baselineCandidate.ttftP95}
              candidateVal={recommendedCandidate.ttftP95}
              unit="ms"
              isLowerBetter={true}
            />
            <HeadToHeadDelta
              label="ITL (P95)"
              baselineVal={baselineCandidate.itlP95}
              candidateVal={recommendedCandidate.itlP95}
              unit="ms"
              isLowerBetter={true}
            />
            <HeadToHeadDelta
              label="Output Throughput"
              baselineVal={baselineCandidate.throughput}
              candidateVal={recommendedCandidate.throughput}
              unit="k tok/s"
              isLowerBetter={false}
            />
            <HeadToHeadDelta
              label="Request Error Rate"
              baselineVal={baselineCandidate.error}
              candidateVal={recommendedCandidate.error}
              unit="%"
              isLowerBetter={true}
            />
          </div>

          <div style={{ borderTop: '1px solid var(--border, #263124)', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
              Experiment Run Ledger
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
              View All 6 Runs →
            </button>
          </div>
        </div>
      </div>

      {/* Primary 2D Latency vs. Throughput Pareto Visualization (Section 5.1 & 9) */}
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
              Measured configuration coordinates relative to declared SLO boundaries
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
          onSelectCandidate={onOpenCandidateDrawer}
          latencyCeilingMs={50}
          throughputFloorTps={50}
        />
      </div>
    </div>
  );
};
