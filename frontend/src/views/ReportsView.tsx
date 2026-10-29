import React, { useState } from 'react';
import { Badge } from '../components/common/Badge';
import { DemoDataChip } from '../components/common/DemoDataChip';
import type { UICandidate } from '../lib/adapters/viewModel';
import type { VerificationDerivationResult } from '../lib/status';

interface ReportsViewProps {
  recommendedCandidate: UICandidate;
  baselineCandidate: UICandidate;
  verificationStatus: VerificationDerivationResult;
  experimentId?: string;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  recommendedCandidate,
  baselineCandidate,
  verificationStatus,
  experimentId = 'EXP-0248',
}) => {
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  const reportMarkdown = `# SLOKern Verification Audit Report
**Experiment ID:** ${experimentId}  
**Generated At:** 2026-10-28T20:45:00Z  
**Runtime:** vLLM v0.6.3 on Nebius H100 SXM5  
**Model:** meta-llama/Llama-3-8B-Instruct  
**Workload:** chat-completions-prod (Poisson arrival @ 16 rps)  
**Evaluator Policy:** slo-prod-03 (Evaluator v0.4.2)

---

## 1. Executive Summary & Verdict
- **Recommended Candidate:** ${recommendedCandidate.id} (${recommendedCandidate.name})
- **Verification Verdict:** ${verificationStatus.badgeLabel}
- **Feasibility Verdict:** FEASIBLE
- **Verification Run ID:** verify_01HZX9K4 (Distinct from search run run_01HZX8F2)
- **Status Rationale:** ${verificationStatus.reasonText}

---

## 2. Head-to-Head Telemetry Comparison
| Metric | Baseline (${baselineCandidate.id}) | Recommended (${recommendedCandidate.id}) | Delta | Status |
|---|---|---|---|---|
| P95 Latency | ${baselineCandidate.p95} ms | ${recommendedCandidate.p95} ms | -30.9% | PASS (≤ 50 ms) |
| TTFT P95 | ${baselineCandidate.ttftP95} ms | ${recommendedCandidate.ttftP95} ms | -31.6% | PASS (≤ 50 ms) |
| ITL P95 | ${baselineCandidate.itlP95} ms | ${recommendedCandidate.itlP95} ms | -36.5% | PASS (≤ 15 ms) |
| Throughput | ${baselineCandidate.throughput}k tok/s | ${recommendedCandidate.throughput}k tok/s | +41.1% | PASS (≥ 50k tok/s) |
| Error Rate | ${baselineCandidate.error}% | ${recommendedCandidate.error}% | 0.00% | PASS (≤ 1.00%) |
| KV Cache | ${baselineCandidate.kvCache} | ${recommendedCandidate.kvCache} | -50% memory | APPLIED |

---

## 3. Drift Analysis & Gate Conformance
- **TTFT P95 Drift:** +1.2 ms (Gate: ±3.0 ms) -> PASSED
- **ITL P95 Drift:** +0.4 ms (Gate: ±1.5 ms) -> PASSED
- **Throughput Drift:** -0.6k tok/s (Gate: ±3.0k tok/s) -> PASSED
- **Physical Drift Detected:** false

---

## 4. Reproducibility & Provenance
- Unaggregated raw request events: \`artifacts/${experimentId}/raw_trace.jsonl\`
- Environment fingerprint: H100 SXM5 80GB, Driver 550.54.14, CUDA 12.4
- Deterministic decision: Verified by SLOKern Core Evaluator

---

## 5. Cost-Accounting Mode & Scope Limitations
- **Cost Mode:** Fixed hardware provisioned reservation (Nebius Cloud H100 SXM5 80GB at $2.95 / GPU-hr)
- **Marginal Token Price:** $0.00 (private instance; no per-token surcharge)
- **Economic Efficiency Gain:** +41.1% throughput under SLO ceiling reduces effective compute cost per million tokens from $0.0187 to $0.0133
- **Explicit Limitations:** Optimality guaranteed only within the bounded 2x2 parameter space tested under the declared Poisson arrival profile. Global optimality across all vLLM configurations is not claimed.
`;

  const handleDownloadMarkdown = () => {
    const blob = new Blob([reportMarkdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${experimentId}_audit_report.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setDownloadSuccess('md');
    setTimeout(() => setDownloadSuccess(null), 2500);
  };

  const handleDownloadJson = () => {
    const reportJson = {
      experiment_id: experimentId,
      timestamp: new Date().toISOString(),
      evaluator_version: 'v0.4.2',
      policy_version: 'slo-prod-03',
      cost_accounting: {
        mode: 'provisioned_reservation',
        provider: 'Nebius Cloud',
        hardware: 'H100 SXM5 80GB',
        hourly_rate_usd: 2.95,
        marginal_token_price: 0.0,
      },
      recommended_candidate: recommendedCandidate,
      baseline_candidate: baselineCandidate,
      verification: verificationStatus,
      provenance: 'DEMO DATA',
    };

    const blob = new Blob([JSON.stringify(reportJson, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${experimentId}_audit_report.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setDownloadSuccess('json');
    setTimeout(() => setDownloadSuccess(null), 2500);
  };

  return (
    <div className="view-reports workspace-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', letterSpacing: '-0.025em', textWrap: 'balance' }}>
              Verification Artifacts & Audit Package
            </h1>
            <DemoDataChip size="sm" />
          </div>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', lineHeight: 1.45, textWrap: 'pretty', maxWidth: '75ch' }}>
            Reproducible specifications, empirical telemetry evidence, and deterministic verdict explanations
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={handleDownloadMarkdown}
            style={{
              backgroundColor: 'var(--elevated, #1D251E)',
              border: '1px solid var(--border-strong, #384635)',
              color: downloadSuccess === 'md' ? 'var(--primary-bright, #95D500)' : 'var(--text-primary, #F0F3EF)',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              padding: '6px 14px',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {downloadSuccess === 'md' ? '✓ Downloaded Markdown!' : 'Export Report (.md)'}
          </button>

          <button
            type="button"
            onClick={handleDownloadJson}
            style={{
              backgroundColor: 'var(--raised, #151B15)',
              border: '1px solid var(--border, #263124)',
              color: downloadSuccess === 'json' ? 'var(--primary-bright, #95D500)' : 'var(--text-secondary, #A0AAA0)',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              padding: '6px 14px',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {downloadSuccess === 'json' ? '✓ Downloaded JSON!' : 'Export Structured (.json)'}
          </button>
        </div>
      </div>

      {/* Summary Box */}
      <div
        style={{
          padding: '20px 24px',
          backgroundColor: 'var(--surface, #0E120F)',
          border: '1px solid var(--border, #263124)',
          borderRadius: '6px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '15px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
              Artifact: {experimentId}_audit_report
            </span>
            <Badge tone={verificationStatus.statusType} size="sm">
              {verificationStatus.badgeLabel}
            </Badge>
          </div>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            Format: CommonMark + GFM Table
          </span>
        </div>

        {/* Markdown Preview Content */}
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--canvas, #080A09)',
            border: '1px solid var(--border, #263124)',
            borderRadius: '4px',
            fontFamily: 'var(--font-mono, monospace)',
            fontSize: '12px',
            color: 'var(--text-primary, #F0F3EF)',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.5,
            maxHeight: '480px',
            overflowY: 'auto',
          }}
        >
          {reportMarkdown}
        </div>
      </div>
    </div>
  );
};
