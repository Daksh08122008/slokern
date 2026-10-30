import React, { useState } from 'react';
import { TradeoffPlot } from '../components/charts/TradeoffPlot';
import { Badge } from '../components/common/Badge';
import { ReasonBox } from '../components/common/ReasonBox';
import { DemoDataChip } from '../components/common/DemoDataChip';
import { formatNumber, formatLatency } from '../lib/format';
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
  baselineCandidate: _baselineCandidate,
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
            Comparing {candidates.length} bounded serving profiles against baseline reference · Search objective: <span style={{ fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #F0F3EF)' }}>max_throughput_under_slo</span> · DEMO DATA · OFFLINE OPTIMIZATION
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
            latencyCeilingMs={2500}
            throughputFloorTps={50}
          />

          {/* Candidate Matrix List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 650, color: 'var(--text-secondary, #A0AAA0)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Tested Configurations ({candidates.length} Candidates · DEMO DATA)
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
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #F0F3EF)' }}>
                        {c.id}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted, #727D73)' }}>
                        {c.subtitle}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {paretoIds.has(c.id) && (
                        <span
                          style={{
                            fontSize: '9px',
                            fontFamily: 'var(--font-mono, monospace)',
                            fontWeight: 700,
                            padding: '2px 5px',
                            borderRadius: '2px',
                            backgroundColor: 'rgba(118, 185, 0, 0.15)',
                            color: 'var(--primary-bright, #95D500)',
                            border: '1px solid var(--primary, #76B900)',
                          }}
                        >
                          PARETO
                        </span>
                      )}
                      <Badge tone={c.feasible ? (c.tag === 'WINNER' ? 'verified' : 'feasible') : 'infeasible'} size="sm">
                        {c.tag}
                      </Badge>
                    </div>
                  </div>

                  {/* Settings + Metrics Pills */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>
                    <div style={{ padding: '4px 6px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                      <span style={{ color: 'var(--text-muted, #727D73)' }}>Seqs: </span>
                      <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{c.concurrency}</span>
                    </div>
                    <div style={{ padding: '4px 6px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                      <span style={{ color: 'var(--text-muted, #727D73)' }}>Batch: </span>
                      <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{c.batch * 512} tok</span>
                    </div>
                    <div style={{ padding: '4px 6px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                      <span style={{ color: 'var(--text-muted, #727D73)' }}>TTFT P95: </span>
                      <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{formatLatency(c.ttftP95)}</span>
                    </div>
                    <div style={{ padding: '4px 6px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                      <span style={{ color: 'var(--text-muted, #727D73)' }}>Throughput: </span>
                      <span style={{ color: 'var(--primary-bright, #95D500)', fontWeight: 700 }}>{c.throughput.toFixed(1)} tok/s</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Detail Pane: Candidate Deep Dive */}
        <div
          style={{
            backgroundColor: 'var(--surface, #0E120F)',
            border: '1px solid var(--border-strong, #384635)',
            borderRadius: '6px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '18px',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', fontFamily: 'var(--font-mono, monospace)' }}>
                  {selectedCandidate.id}
                </h2>
                <DemoDataChip size="sm" />
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted, #727D73)', fontFamily: 'var(--font-mono, monospace)' }}>
                {selectedCandidate.subtitle}
              </span>
            </div>

            <Badge tone={selectedCandidate.feasible ? (selectedCandidate.tag === 'WINNER' ? 'verified' : 'feasible') : 'infeasible'}>
              {selectedCandidate.tag}
            </Badge>
          </div>

          {/* Token Factory Limitation Callout */}
          <div style={{ padding: '10px 12px', backgroundColor: 'rgba(233, 185, 73, 0.08)', border: '1px solid rgba(233, 185, 73, 0.3)', borderRadius: '4px', fontSize: '11px', color: 'var(--warning, #E9B949)', fontFamily: 'var(--font-mono, monospace)', lineHeight: 1.4 }}>
            <strong>Token Factory Limitation:</strong> Server-side vLLM scheduler controls unavailable through this endpoint. Evaluated in offline simulated environment.
          </div>

          {/* Reason Code Clinical Box */}
          <ReasonBox
            reasonCode={selectedCandidate.feasible ? 'HARD_CONSTRAINTS_PASSED' : 'P95_LATENCY_EXCEEDED'}
            detailText={selectedCandidate.reason}
            isPassing={selectedCandidate.feasible}
          />

          {/* Parameter Settings */}
          <div>
            <div style={{ fontSize: '12px', fontWeight: 650, color: 'var(--text-secondary, #A0AAA0)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
              Parameter Configuration
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', fontFamily: 'var(--font-mono, monospace)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Max Concurrency (max_num_seqs)</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{selectedCandidate.concurrency} streams</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Batch Tokens (max_num_batched_tokens)</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{selectedCandidate.batch * 512} tokens</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>KV Cache Dtype</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{selectedCandidate.kvCache}</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>GPU Memory Load</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{selectedCandidate.gpu}% VRAM</span>
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
                <span style={{ color: 'var(--text-muted, #727D73)' }}>OUTPUT THROUGHPUT</span>
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--primary-bright, #95D500)', marginTop: '2px' }}>
                  {selectedCandidate.throughput.toFixed(1)} tok/s
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
