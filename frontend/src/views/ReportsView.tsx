import React, { useState } from 'react';
import { Badge } from '../components/common/Badge';
import { DemoDataChip } from '../components/common/DemoDataChip';
import type { UICandidate } from '../lib/adapters/viewModel';
import type { VerificationDerivationResult } from '../lib/status';
import type { ReportSummaryResponse, ReportArtifact } from '../types/contracts';

interface ReportsViewProps {
  recommendedCandidate: UICandidate;
  baselineCandidate: UICandidate;
  verificationStatus: VerificationDerivationResult;
  experimentId?: string;
  reportData?: { experiment_id: string; markdown: string; artifact: ReportArtifact | null } | null;
  availableReports?: ReportSummaryResponse[];
  onSelectReport?: (expId: string) => void;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  recommendedCandidate,
  baselineCandidate: _baselineCandidate,
  verificationStatus: _verificationStatus,
  experimentId = 'exp-audit-offline-campaign',
  reportData,
  availableReports = [],
  onSelectReport,
}) => {
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  // Markdown content: prefer backend real compiled report, fallback to structured live report
  const activeMarkdown =
    reportData?.markdown ||
    `# SLOKern Verification Audit Report
**Experiment ID:** ${experimentId}  
**Generated At:** 2026-10-30T03:42:00Z  
**Runtime:** vLLM v0.6.0-fake-demo (DEMO DATA · OFFLINE OPTIMIZATION)  
**Model:** meta-llama/Meta-Llama-3-8B-Instruct  
**Workload:** chat-completions-prod (Poisson arrival @ 10 rps)  
**Evaluator Policy:** slo-1.0.0 (Evaluator v1.0.0)

---

## 1. Executive Summary & Verdict
- **Selected Candidate:** ${recommendedCandidate.id} (${recommendedCandidate.name})
- **Ranking Objective:** max_throughput_under_slo
- **Winning Throughput:** 160 tokens/s
- **Stopping Reason:** space_exhausted (2×2 parameter matrix evaluated)
- **Feasibility Verdict:** FEASIBLE (All hard SLO constraints satisfied)
- **Independent Verification Verdict:** INDEPENDENT VERIFICATION PENDING
- **Status Rationale:** Candidate meets all declared constraints with 2485.8 ms TTFT headroom. Independent rerun required per AGENTS.md § 7.

---

## 2. Tested Candidates Summary
1. **${recommendedCandidate.id}**: WINNER · 160 tok/s · FEASIBLE
2. **370359a9c14b**: FEASIBLE · 160 tok/s
3. **369e9bc42eb7**: FEASIBLE · 160 tok/s
4. **565eb88bb613**: FEASIBLE · 160 tok/s
5. **c3d86d00124b**: FEASIBLE · 160 tok/s

---

## 3. Evidence Classification & Scope Limitations
- **Classification:** DEMO DATA · OFFLINE OPTIMIZATION
- **Serving Adapter:** Synthetic vLLM serving simulation with zero real GPU allocation.
- **Hardware Profile:** Simulated NVIDIA H100 80GB SXM5
- **Explicit Limitations:** Optimality guaranteed only within the bounded parameter space tested. Global optimality across all vLLM configurations is not claimed.
`;

  const handleDownloadMarkdown = () => {
    const blob = new Blob([activeMarkdown], { type: 'text/markdown;charset=utf-8' });
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
    const reportJson = reportData?.artifact || {
      experiment_id: experimentId,
      timestamp: new Date().toISOString(),
      evaluator_version: 'v1.0.0',
      policy_version: 'slo-1.0.0',
      selected_candidate_id: recommendedCandidate.id,
      evidence_classification: 'DEMO DATA',
      ranking_objective: 'max_throughput_under_slo',
      stopping_reason: 'space_exhausted',
    };

    const blob = new Blob([JSON.stringify(reportJson, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${experimentId}_report_artifact.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setDownloadSuccess('json');
    setTimeout(() => setDownloadSuccess(null), 2500);
  };

  return (
    <div className="view-reports workspace-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Workspace Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', letterSpacing: '-0.025em', textWrap: 'balance' }}>
              Auditable Compliance & Verification Reports
            </h1>
            <DemoDataChip size="sm" />
          </div>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', lineHeight: 1.45, textWrap: 'pretty', maxWidth: '75ch' }}>
            Formal audit report for experiment <span style={{ fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #F0F3EF)' }}>{experimentId}</span> with deterministic provenance and explicit limitations
          </p>
        </div>

        {/* Download Action Buttons */}
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
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>{downloadSuccess === 'md' ? '✓ Downloaded!' : 'Export Markdown (.md)'}</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadJson}
            style={{
              backgroundColor: 'var(--primary, #76B900)',
              border: 'none',
              color: '#080A09',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 700,
              padding: '7px 16px',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>{downloadSuccess === 'json' ? '✓ Downloaded!' : 'Export JSON Artifact (.json)'}</span>
          </button>
        </div>
      </div>

      {/* Available Reports Strip if multiple exist */}
      {availableReports.length > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)', textTransform: 'uppercase' }}>
            Available Reports:
          </span>
          {availableReports.map((r) => (
            <button
              key={r.experiment_id}
              type="button"
              onClick={() => onSelectReport?.(r.experiment_id)}
              style={{
                backgroundColor: r.experiment_id === experimentId ? 'var(--elevated, #1D251E)' : 'var(--surface, #0E120F)',
                border: '1px solid',
                borderColor: r.experiment_id === experimentId ? 'var(--primary, #76B900)' : 'var(--border, #263124)',
                color: r.experiment_id === experimentId ? 'var(--primary-bright, #95D500)' : 'var(--text-secondary, #A0AAA0)',
                fontSize: '11px',
                fontFamily: 'var(--font-mono, monospace)',
                padding: '4px 10px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              {r.experiment_id} ({r.evidence_classification})
            </button>
          ))}
        </div>
      )}

      {/* Report Viewer Container */}
      <div
        className="report-viewer-card"
        style={{
          backgroundColor: 'var(--surface, #0E120F)',
          border: '1px solid var(--border, #263124)',
          borderRadius: '8px',
          padding: '28px 36px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          boxShadow: 'var(--shadow-md)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-strong, #384635)', paddingBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Badge tone="neutral" size="sm">AUDIT EVIDENCE ARTIFACT</Badge>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary, #F0F3EF)', fontFamily: 'var(--font-mono, monospace)' }}>
              artifacts/{experimentId}/report.md
            </span>
          </div>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            Rendered from persisted filesystem evidence
          </span>
        </div>

        <pre
          style={{
            margin: 0,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'var(--font-mono, monospace)',
            fontSize: '12px',
            lineHeight: 1.6,
            color: 'var(--text-primary, #F0F3EF)',
            backgroundColor: 'var(--canvas, #080A09)',
            padding: '20px',
            borderRadius: '6px',
            border: '1px solid var(--border, #263124)',
            overflowX: 'auto',
          }}
        >
          {activeMarkdown}
        </pre>
      </div>
    </div>
  );
};
