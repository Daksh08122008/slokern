import React, { useState } from 'react';
import { Badge } from '../components/common/Badge';
import { DemoDataChip } from '../components/common/DemoDataChip';
import { DriftGateBar } from '../components/charts/DriftGateBar';
import { formatNumber, formatLatency, formatThroughput } from '../lib/format';
import type { VerificationDerivationResult } from '../lib/status';
import type { UICandidate } from '../lib/adapters/viewModel';

interface VerificationViewProps {
  recommendedCandidate: UICandidate;
  verificationStatus: VerificationDerivationResult;
  searchRunId?: string;
  verificationRunId?: string;
}

export const VerificationView: React.FC<VerificationViewProps> = ({
  recommendedCandidate,
  verificationStatus,
  searchRunId = 'run_01HZX8F2',
  verificationRunId = 'verify_01HZX9K4',
}) => {
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const isVerified = verificationStatus.isVerifiedWinner;

  // Comparison metrics between search run and independent verification rerun
  const metricsComparison = [
    {
      name: 'Time to First Token (TTFT P95)',
      searchVal: recommendedCandidate.ttftP95,
      verifyVal: recommendedCandidate.ttftP95 + (isVerified ? 1.2 : 12.8),
      drift: isVerified ? 1.2 : 12.8,
      tolerance: 3.0,
      unit: 'ms',
      format: (v: number) => formatLatency(v),
    },
    {
      name: 'Inter-Token Latency (ITL P95)',
      searchVal: recommendedCandidate.itlP95,
      verifyVal: recommendedCandidate.itlP95 + (isVerified ? 0.4 : 3.6),
      drift: isVerified ? 0.4 : 3.6,
      tolerance: 1.5,
      unit: 'ms',
      format: (v: number) => formatLatency(v),
    },
    {
      name: 'End-to-End Latency (P95)',
      searchVal: recommendedCandidate.p95,
      verifyVal: recommendedCandidate.p95 + (isVerified ? 1.1 : 14.2),
      drift: isVerified ? 1.1 : 14.2,
      tolerance: 4.0,
      unit: 'ms',
      format: (v: number) => formatLatency(v),
    },
    {
      name: 'Output Token Throughput',
      searchVal: recommendedCandidate.throughput,
      verifyVal: recommendedCandidate.throughput - (isVerified ? 0.6 : 8.4),
      drift: isVerified ? -0.6 : -8.4,
      tolerance: 3.0,
      unit: 'k tok/s',
      format: (v: number) => formatThroughput(v * 1000),
    },
    {
      name: 'Request Error Rate',
      searchVal: recommendedCandidate.error,
      verifyVal: recommendedCandidate.error + (isVerified ? 0.01 : 0.42),
      drift: isVerified ? 0.01 : 0.42,
      tolerance: 0.20,
      unit: '%',
      format: (v: number) => `${formatNumber(v, 2)}%`,
    },
  ];

  const handleDownloadTrace = () => {
    // Generate synthetic JSONL trace matching RawRequestMeasurement schema
    const lines: string[] = [];
    const baseTime = Date.now() - 180000;
    for (let i = 0; i < 50; i++) {
      const scheduled = baseTime + i * 62;
      const sent = scheduled + 1;
      const ttft = sent + 24 + Math.random() * 4;
      const completed = ttft + 140 + Math.random() * 20;
      const rec = {
        request_id: `req_ver_${i.toString().padStart(4, '0')}`,
        run_id: verificationRunId,
        scheduled_at: scheduled,
        sent_at: sent,
        first_token_at: ttft,
        completed_at: completed,
        http_status: 200,
        input_tokens: 512,
        output_tokens: 128,
        itl_observations_ms: [9.1, 9.4, 9.2, 9.5, 9.3],
        is_valid: true,
        is_warmup: i < 5,
      };
      lines.push(JSON.stringify(rec));
    }

    const blob = new Blob([lines.join('\n')], { type: 'application/x-ndjson' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${verificationRunId}_raw_trace.jsonl`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 2500);
  };

  return (
    <div className="view-verification workspace-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Workspace Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', letterSpacing: '-0.025em', textWrap: 'balance' }}>
              Independent Decision Verification & Drift Auditing
            </h1>
            <DemoDataChip size="sm" />
          </div>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', lineHeight: 1.45, textWrap: 'pretty', maxWidth: '75ch' }}>
            Fresh execution protocol verifying candidate recommendation under identical arrival distribution
          </p>
        </div>

        <button
          type="button"
          onClick={handleDownloadTrace}
          style={{
            background: 'none',
            border: '1px solid var(--border-strong, #384635)',
            backgroundColor: 'var(--elevated, #1D251E)',
            color: downloadSuccess ? 'var(--primary-bright, #95D500)' : 'var(--text-primary, #F0F3EF)',
            fontSize: '12px',
            fontFamily: 'var(--font-mono, monospace)',
            fontWeight: 600,
            padding: '6px 14px',
            borderRadius: '4px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span>{downloadSuccess ? '✓ Downloaded JSONL!' : 'Export Raw Verification Trace (.jsonl)'}</span>
        </button>
      </div>

      {/* Verification Independence Card: Search Run ID vs Verification Run ID */}
      <div
        style={{
          padding: '20px 24px',
          backgroundColor: 'var(--surface, #0E120F)',
          border: '1px solid',
          borderColor: isVerified ? 'var(--border-strong, #384635)' : 'var(--border, #263124)',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: isVerified ? 'var(--glow-winner)' : 'none',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Badge tone={verificationStatus.statusType} size="md">
              {verificationStatus.badgeLabel}
            </Badge>
            <span style={{ fontSize: '14px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
              Candidate: {recommendedCandidate.id} · {recommendedCandidate.name}
            </span>
          </div>

          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            Protocol: 2× duration rerun · Poisson arrival · Seed: 42918
          </div>
        </div>

        {/* Side-by-Side Run IDs */}
        <div className="verification-runs-grid" style={{ fontSize: '12px', fontFamily: 'var(--font-mono, monospace)' }}>
          {/* Search Run */}
          <div style={{ padding: '12px 14px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '4px', border: '1px solid var(--border, #263124)' }}>
            <div style={{ color: 'var(--text-muted, #727D73)', fontSize: '11px', marginBottom: '4px' }}>ORIGINAL SEARCH RUN ID</div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)' }}>{searchRunId}</div>
            <div style={{ color: 'var(--text-secondary, #A0AAA0)', fontSize: '11px', marginTop: '4px' }}>Completed: 14:42:18 UTC · Budget: Run 2/6</div>
          </div>

          {/* Verification Run */}
          <div style={{ padding: '12px 14px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '4px', border: '1px solid', borderColor: isVerified ? 'var(--primary, #76B900)' : 'var(--border, #263124)' }}>
            <div style={{ color: 'var(--text-muted, #727D73)', fontSize: '11px', marginBottom: '4px' }}>INDEPENDENT VERIFICATION RUN ID</div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: isVerified ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)' }}>
              {verificationRunId}
            </div>
            <div style={{ color: 'var(--text-secondary, #A0AAA0)', fontSize: '11px', marginTop: '4px' }}>
              Completed: 14:45:02 UTC · Distinct execution guaranteed
            </div>
          </div>
        </div>

        {/* Reason / Clinical verdict note */}
        <div style={{ fontSize: '12px', color: 'var(--text-secondary, #A0AAA0)', borderTop: '1px solid var(--border, #263124)', paddingTop: '10px' }}>
          <strong>Verdict Rationale:</strong> {verificationStatus.reasonText}
        </div>
      </div>

      {/* Drift Gate Gauges Section */}
      <div>
        <h2 style={{ fontSize: '14px', fontWeight: 650, color: 'var(--text-secondary, #A0AAA0)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '12px' }}>
          Declared Drift Gate Meters
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
          {metricsComparison.map((m) => (
            <DriftGateBar
              key={m.name}
              metricName={m.name.split('(')[0].trim()}
              measuredDrift={m.drift}
              toleranceThreshold={m.tolerance}
              unit={m.unit}
            />
          ))}
        </div>
      </div>

      {/* Detailed Metrics Comparison Table */}
      <div
        style={{
          backgroundColor: 'var(--surface, #0E120F)',
          border: '1px solid var(--border, #263124)',
          borderRadius: '6px',
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border, #263124)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
            Metric Comparison Ledger
          </h3>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            policy: slo-prod-03 · evaluator: v0.4.2
          </span>
        </div>

        <div className="table-scroll" style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', fontFamily: 'var(--font-mono, monospace)', textAlign: 'left' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--raised, #151B15)', borderBottom: '1px solid var(--border, #263124)', color: 'var(--text-secondary, #A0AAA0)' }}>
                <th style={{ padding: '10px 16px' }}>METRIC</th>
                <th style={{ padding: '10px 16px' }}>SEARCH VALUE</th>
                <th style={{ padding: '10px 16px' }}>VERIFY VALUE</th>
                <th style={{ padding: '10px 16px' }}>ABSOLUTE DRIFT</th>
                <th style={{ padding: '10px 16px' }}>DECLARED GATE</th>
                <th style={{ padding: '10px 16px' }}>VERDICT</th>
              </tr>
            </thead>
            <tbody>
              {metricsComparison.map((m, idx) => {
                const passed = Math.abs(m.drift) <= m.tolerance;
                return (
                  <tr
                    key={m.name}
                    style={{
                      borderBottom: idx === metricsComparison.length - 1 ? 'none' : '1px solid var(--border, #263124)',
                      backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
                    }}
                  >
                    <td style={{ padding: '10px 16px', color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{m.name}</td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-secondary, #A0AAA0)' }}>{m.format(m.searchVal)}</td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{m.format(m.verifyVal)}</td>
                    <td style={{ padding: '10px 16px', color: passed ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)' }}>
                      {m.drift > 0 ? `+${formatNumber(m.drift, 2)}` : formatNumber(m.drift, 2)} {m.unit}
                    </td>
                    <td style={{ padding: '10px 16px', color: 'var(--text-muted, #727D73)' }}>±{m.tolerance} {m.unit}</td>
                    <td style={{ padding: '10px 16px' }}>
                      <Badge tone={passed ? 'verified' : 'infeasible'} size="sm">
                        {passed ? 'PASSED' : 'DRIFT BREACH'}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
