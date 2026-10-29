import React, { useState } from 'react';
import { TradeoffPlot } from '../components/charts/TradeoffPlot';
import { Badge } from '../components/common/Badge';
import { ReasonBox } from '../components/common/ReasonBox';
import { DemoDataChip } from '../components/common/DemoDataChip';
import { formatNumber, formatLatency, formatThroughput } from '../lib/format';
import type { UICandidate } from '../lib/adapters/viewModel';
import { identifyParetoFrontier } from '../lib/adapters/viewModel';

interface TuningLabViewProps {
  candidates: UICandidate[];
  baselineCandidate: UICandidate;
  selectedCandidateId: string;
  onSelectCandidate: (candidate: UICandidate) => void;
  onOpenCandidateDrawer: (candidate: UICandidate) => void;
}

export const TuningLabView: React.FC<TuningLabViewProps> = ({
  candidates,
  baselineCandidate,
  selectedCandidateId,
  onSelectCandidate,
  onOpenCandidateDrawer,
}) => {
  const [copyFeedback, setCopyFeedback] = useState(false);

  const { paretoIds } = React.useMemo(() => identifyParetoFrontier(candidates), [candidates]);
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId) || candidates[0];

  const handleCopyCliFlags = () => {
    const flags = `--max-num-seqs ${selectedCandidate.concurrency} --max-num-batched-tokens ${selectedCandidate.batch * 512} --kv-cache-dtype ${selectedCandidate.kvCache.toLowerCase()} --gpu-memory-utilization 0.90`;
    navigator.clipboard.writeText(flags);
    setCopyFeedback(true);
    setTimeout(() => setCopyFeedback(false), 2000);
  };

  return (
    <div className="view-tuning-lab workspace-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Workspace Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', letterSpacing: '-0.025em', textWrap: 'balance' }}>
              Candidate Search Space & Feasibility Inspector
            </h1>
            <DemoDataChip size="sm" />
          </div>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', lineHeight: 1.45, textWrap: 'pretty', maxWidth: '75ch' }}>
            Comparing 4 bounded serving profiles against baseline reference · Search objective: <span style={{ fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #F0F3EF)' }}>max_throughput_under_slo</span>
          </p>
        </div>
      </div>

      {/* Master-Detail Layout */}
      <div className="tuning-lab-grid">
        {/* Left Master Pane: TradeoffPlot + Candidate List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* 2D Tradeoff Plot */}
          <TradeoffPlot
            candidates={candidates}
            selectedCandidateId={selectedCandidate.id}
            onSelectCandidate={onSelectCandidate}
            latencyCeilingMs={50}
            throughputFloorTps={50}
          />

          {/* Candidate Matrix List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 650, color: 'var(--text-secondary, #A0AAA0)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Tested Configurations (4 Candidates + 1 Baseline)
              </span>
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
                Click to inspect details
              </span>
            </div>

            {candidates.map((c) => {
              const isSelected = c.id === selectedCandidate.id;
              const isWinner = c.tag === 'WINNER';

              return (
                <div
                  key={c.id}
                  onClick={() => onSelectCandidate(c)}
                  style={{
                    padding: '14px 16px',
                    backgroundColor: isSelected ? 'var(--elevated, #1D251E)' : 'var(--surface, #0E120F)',
                    border: '1px solid',
                    borderColor: isWinner
                      ? 'var(--primary, #76B900)'
                      : isSelected
                      ? 'var(--border-strong, #384635)'
                      : 'var(--border, #263124)',
                    boxShadow: isWinner ? 'var(--glow-winner)' : 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    transition: 'border-color 140ms ease, background-color 140ms ease',
                  }}
                  role="button"
                  tabIndex={0}
                  aria-pressed={isSelected}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      onSelectCandidate(c);
                    }
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #F0F3EF)' }}>
                        {c.id}
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary, #F0F3EF)' }}>
                        {c.name}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted, #727D73)' }}>
                        ({c.subtitle})
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {paretoIds.has(c.id) && (
                        <Badge tone="verified" size="sm">PARETO</Badge>
                      )}
                      <Badge tone={c.feasible ? (isWinner ? 'verified' : 'feasible') : 'infeasible'} size="sm">
                        {c.tag}
                      </Badge>
                    </div>
                  </div>

                  {/* Telemetry Metrics Row */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>
                    <div>
                      <div style={{ color: 'var(--text-muted, #727D73)' }}>P95 LATENCY</div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: c.p95 <= 50 ? 'var(--text-primary, #F0F3EF)' : 'var(--error, #FF5555)' }}>
                        {formatLatency(c.p95)}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-muted, #727D73)' }}>THROUGHPUT</div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: c.throughput >= 50 ? 'var(--text-primary, #F0F3EF)' : 'var(--error, #FF5555)' }}>
                        {formatThroughput(c.throughput * 1000)}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-muted, #727D73)' }}>KV CACHE</div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary, #F0F3EF)' }}>
                        {c.kvCache}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-muted, #727D73)' }}>BATCH / CONC</div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary, #F0F3EF)' }}>
                        {c.batch} / {c.concurrency}
                      </div>
                    </div>
                  </div>

                  {/* Reason Summary */}
                  <div style={{ fontSize: '11px', color: c.feasible ? 'var(--text-secondary, #A0AAA0)' : 'var(--error, #FF5555)', borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '6px' }}>
                    {c.reason}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Detail Inspector Pane */}
        <div
          className="tuning-inspector-pane"
          style={{
            position: 'sticky',
            top: '20px',
            backgroundColor: 'var(--surface, #0E120F)',
            border: '1px solid var(--border-strong, #384635)',
            borderRadius: '6px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)', textTransform: 'uppercase' }}>
                Candidate Inspector
              </div>
              <h2 style={{ margin: '4px 0 0', fontSize: '18px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)' }}>
                {selectedCandidate.id} · {selectedCandidate.name}
              </h2>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary, #A0AAA0)', marginTop: '2px' }}>
                {selectedCandidate.subtitle}
              </div>
            </div>

            <Badge tone={selectedCandidate.feasible ? (selectedCandidate.tag === 'WINNER' ? 'verified' : 'feasible') : 'infeasible'}>
              {selectedCandidate.tag}
            </Badge>
          </div>

          {/* Reason Code Clinical Box */}
          <ReasonBox
            reasonCode={selectedCandidate.feasible ? 'HARD_CONSTRAINTS_PASSED' : 'P95_LATENCY_EXCEEDED'}
            detailText={selectedCandidate.reason}
            isPassing={selectedCandidate.feasible}
          />

          {/* Parameter Differences vs Baseline */}
          <div>
            <div style={{ fontSize: '12px', fontWeight: 650, color: 'var(--text-secondary, #A0AAA0)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
              Parameter Delta vs. Baseline ({baselineCandidate.id})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', fontFamily: 'var(--font-mono, monospace)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Max Concurrency</span>
                <div>
                  <span style={{ color: 'var(--text-muted, #727D73)' }}>{baselineCandidate.concurrency}</span>
                  <span style={{ margin: '0 6px' }}>→</span>
                  <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{selectedCandidate.concurrency}</span>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Batch Size</span>
                <div>
                  <span style={{ color: 'var(--text-muted, #727D73)' }}>{baselineCandidate.batch}</span>
                  <span style={{ margin: '0 6px' }}>→</span>
                  <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{selectedCandidate.batch}</span>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>KV Cache Quant</span>
                <div>
                  <span style={{ color: 'var(--text-muted, #727D73)' }}>{baselineCandidate.kvCache}</span>
                  <span style={{ margin: '0 6px' }}>→</span>
                  <span style={{ color: selectedCandidate.kvCache === 'FP8' ? 'var(--primary-bright, #95D500)' : 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>
                    {selectedCandidate.kvCache}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>GPU Memory Load</span>
                <div>
                  <span style={{ color: 'var(--text-muted, #727D73)' }}>{baselineCandidate.gpu}%</span>
                  <span style={{ margin: '0 6px' }}>→</span>
                  <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{selectedCandidate.gpu}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Measured Telemetry */}
          <div>
            <div style={{ fontSize: '12px', fontWeight: 650, color: 'var(--text-secondary, #A0AAA0)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
              Measured Telemetry Summary
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>
              <div style={{ padding: '8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-muted, #727D73)' }}>TTFT (P95)</span>
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', marginTop: '2px' }}>
                  {formatLatency(selectedCandidate.ttftP95)}
                </div>
              </div>

              <div style={{ padding: '8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-muted, #727D73)' }}>ITL (P95)</span>
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', marginTop: '2px' }}>
                  {formatLatency(selectedCandidate.itlP95)}
                </div>
              </div>

              <div style={{ padding: '8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-muted, #727D73)' }}>E2E LATENCY P95</span>
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', marginTop: '2px' }}>
                  {formatLatency(selectedCandidate.p95)}
                </div>
              </div>

              <div style={{ padding: '8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-muted, #727D73)' }}>ERROR RATE</span>
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', marginTop: '2px' }}>
                  {formatNumber(selectedCandidate.error, 2)}%
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
            <button
              type="button"
              onClick={handleCopyCliFlags}
              style={{
                width: '100%',
                padding: '8px 14px',
                backgroundColor: 'var(--elevated, #1D251E)',
                border: '1px solid var(--border-strong, #384635)',
                borderRadius: '4px',
                color: copyFeedback ? 'var(--primary-bright, #95D500)' : 'var(--text-primary, #F0F3EF)',
                fontSize: '12px',
                fontFamily: 'var(--font-mono, monospace)',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              <span>{copyFeedback ? '✓ Copied to Clipboard!' : 'Copy vLLM CLI Flags'}</span>
            </button>

            <button
              type="button"
              onClick={() => onOpenCandidateDrawer(selectedCandidate)}
              style={{
                width: '100%',
                padding: '8px 14px',
                backgroundColor: 'var(--raised, #151B15)',
                border: '1px solid var(--border, #263124)',
                borderRadius: '4px',
                color: 'var(--text-secondary, #A0AAA0)',
                fontSize: '12px',
                fontFamily: 'var(--font-mono, monospace)',
                cursor: 'pointer',
              }}
            >
              Open Full Run Artifacts Inspector →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
