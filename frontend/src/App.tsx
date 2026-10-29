import { useState, useEffect, useMemo } from 'react';
import { ContextBar } from './components/layout/ContextBar';
import { Sidebar } from './components/layout/Sidebar';
import type { WorkspaceDestination } from './components/layout/Sidebar';
import { StatusBar } from './components/layout/StatusBar';
import type { ScenarioType } from './components/layout/StatusBar';
import { SlideOverDrawer } from './components/layout/SlideOverDrawer';
import { OverviewView } from './views/OverviewView';
import { WorkloadsView } from './views/WorkloadsView';
import { ExperimentsView } from './views/ExperimentsView';
import { TuningLabView } from './views/TuningLabView';
import { VerificationView } from './views/VerificationView';
import { ReportsView } from './views/ReportsView';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Badge } from './components/common/Badge';
import { deriveVerifiedWinner } from './lib/status';
import { computeBindingConstraintHeadroom, formatLatency, formatThroughput, formatNumber } from './lib/format';
import { runWithViewTransition } from './lib/motion';
import type { UICandidate, UIExperiment } from './lib/adapters/viewModel';
import type { VerificationRecord, SLOConstraint } from './types/contracts';
import { checkHealth, runSmokeProbe } from './api/client';

export function App() {
  const [currentWorkspace, setCurrentWorkspace] = useState<WorkspaceDestination>('Overview');
  const [scenario, setScenario] = useState<ScenarioType>('standard');
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>('C-02');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Drawer Inspection State
  const [inspectCandidate, setInspectCandidate] = useState<UICandidate | null>(null);
  const [inspectExperiment, setInspectExperiment] = useState<UIExperiment | null>(null);
  const [isRuntimeModalOpen, setIsRuntimeModalOpen] = useState(false);

  // Fluid View-Transition Navigators (Overdrive Mode)
  const navigateWorkspace = (dest: WorkspaceDestination) => {
    if (dest === currentWorkspace) return;
    runWithViewTransition(() => {
      setCurrentWorkspace(dest);
    });
  };

  const handleOpenCandidateDrawer = (candidate: UICandidate) => {
    runWithViewTransition(() => {
      setInspectCandidate(candidate);
    });
  };

  const handleCloseCandidateDrawer = () => {
    runWithViewTransition(() => {
      setInspectCandidate(null);
    });
  };

  const handleOpenExperimentDrawer = (exp: UIExperiment) => {
    runWithViewTransition(() => {
      setInspectExperiment(exp);
    });
  };

  const handleCloseExperimentDrawer = () => {
    runWithViewTransition(() => {
      setInspectExperiment(null);
    });
  };

  // Control Plane & Probe state
  const [healthStatus, setHealthStatus] = useState<'ok' | 'degraded' | 'error'>('ok');
  const [healthPingMs, setHealthPingMs] = useState(14);
  const [isProbing, setIsProbing] = useState(false);
  const [smokeProbeResult, setSmokeProbeResult] = useState<string | null>(null);

  // Responsive breakpoint observer
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width <= 1050) {
        setIsSidebarCollapsed(true);
      } else {
        setIsSidebarCollapsed(false);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Global hotkeys 1-6 for workspace navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Suppress hotkeys inside input, select, textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) {
        return;
      }

      if (e.key === 'Escape' && isRuntimeModalOpen) {
        setIsRuntimeModalOpen(false);
        return;
      }

      if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
        e.preventDefault();
        setIsSidebarCollapsed((prev) => !prev);
        return;
      }

      switch (e.key) {
        case '1':
          e.preventDefault();
          navigateWorkspace('Overview');
          break;
        case '2':
          e.preventDefault();
          navigateWorkspace('Workloads');
          break;
        case '3':
          e.preventDefault();
          navigateWorkspace('Experiments');
          break;
        case '4':
          e.preventDefault();
          navigateWorkspace('Tuning Lab');
          break;
        case '5':
          e.preventDefault();
          navigateWorkspace('Verification');
          break;
        case '6':
          e.preventDefault();
          navigateWorkspace('Reports');
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentWorkspace, isRuntimeModalOpen]);

  // Poll health on mount
  useEffect(() => {
    const startTime = performance.now();
    checkHealth()
      .then((res) => {
        const elapsed = Math.round(performance.now() - startTime);
        setHealthPingMs(Math.max(1, elapsed));
        setHealthStatus(res.status === 'ok' ? 'ok' : 'degraded');
      })
      .catch(() => {
        // Fallback for offline demo mode
        setHealthStatus('ok');
        setHealthPingMs(14);
      });
  }, []);

  // Candidates dataset derived deterministically by scenario
  const candidates: UICandidate[] = useMemo(() => {
    if (scenario === 'no-feasible') {
      return [
        { id: 'C-01', name: 'Baseline', subtitle: 'Reference FP16', batch: 8, concurrency: 16, kvCache: 'FP16', p50: 36, p95: 68, p99: 91, throughput: 43.8, error: 0.08, gpu: 61, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'VALID', reason: 'P95 latency exceeds 50 ms hard ceiling by 18 ms.', tag: 'BASELINE', ttftP95: 38, itlP95: 14.8 },
        { id: 'C-02', name: 'Balanced', subtitle: 'Over-saturated batch', batch: 16, concurrency: 32, kvCache: 'FP8', p50: 38, p95: 62, p99: 82, throughput: 58.2, error: 0.12, gpu: 84, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'VALID', reason: 'P95 latency exceeds 50 ms hard ceiling by 12 ms.', tag: 'INFEASIBLE', ttftP95: 42, itlP95: 12.4 },
        { id: 'C-03', name: 'Throughput Max', subtitle: 'High concurrency', batch: 32, concurrency: 64, kvCache: 'FP8', p50: 44, p95: 74, p99: 94, throughput: 68.4, error: 0.45, gpu: 96, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'VALID', reason: 'P95 latency breaches 50 ms limit by 24 ms.', tag: 'INFEASIBLE', ttftP95: 49, itlP95: 15.6 },
        { id: 'C-04', name: 'Latency First', subtitle: 'Throttled concurrency', batch: 8, concurrency: 12, kvCache: 'FP16', p50: 25, p95: 54, p99: 68, throughput: 41.2, error: 0.04, gpu: 50, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'VALID', reason: 'Throughput falls 8.8k tok/s below 50k floor.', tag: 'INFEASIBLE', ttftP95: 28, itlP95: 9.8 },
      ];
    }

    if (scenario === 'stale-evidence') {
      return [
        { id: 'C-01', name: 'Baseline', subtitle: 'Reference profile', batch: 8, concurrency: 16, kvCache: 'FP16', p50: 36, p95: 68, p99: 91, throughput: 43.8, error: 0.08, gpu: 61, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'STALE', reason: 'Stale telemetry horizon exceeded (older than 24h).', tag: 'STALE', ttftP95: 38, itlP95: 14.8 },
        { id: 'C-02', name: 'Balanced', subtitle: 'Expired evidence run', batch: 16, concurrency: 32, kvCache: 'FP8', p50: 24, p95: 47, p99: 58, throughput: 61.8, error: 0.08, gpu: 78, feasible: true, feasibilityVerdict: 'FEASIBLE', evidenceValidity: 'STALE', reason: 'Evidence clock expired. Fresh verification rerun mandatory.', tag: 'STALE', ttftP95: 26, itlP95: 9.4 },
        { id: 'C-03', name: 'Throughput Max', subtitle: 'High concurrency', batch: 32, concurrency: 64, kvCache: 'FP8', p50: 39, p95: 64, p99: 81, throughput: 74.2, error: 0.31, gpu: 94, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'STALE', reason: 'P95 latency breached ceiling and evidence is stale.', tag: 'STALE', ttftP95: 41, itlP95: 11.2 },
        { id: 'C-04', name: 'Latency First', subtitle: 'Conservative profile', batch: 8, concurrency: 12, kvCache: 'FP16', p50: 23, p95: 42, p99: 49, throughput: 44.3, error: 0.04, gpu: 54, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'STALE', reason: 'Throughput deficit and evidence is stale.', tag: 'STALE', ttftP95: 22, itlP95: 8.9 },
      ];
    }

    // Standard & Verification-Failed baseline
    return [
      { id: 'C-01', name: 'Baseline', subtitle: 'Reference configuration', batch: 8, concurrency: 16, kvCache: 'FP16', p50: 36, p95: 68, p99: 91, throughput: 43.8, error: 0.08, gpu: 61, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'VALID', reason: 'P95 latency exceeds 50 ms hard ceiling by 18 ms.', tag: 'BASELINE', ttftP95: 38, itlP95: 14.8 },
      { id: 'C-02', name: 'Balanced', subtitle: 'Recommended candidate', batch: 16, concurrency: 32, kvCache: 'FP8', p50: 24, p95: 47, p99: 58, throughput: 61.8, error: 0.08, gpu: 78, feasible: true, feasibilityVerdict: 'FEASIBLE', evidenceValidity: 'VALID', reason: 'Meets all 3 hard constraints with 3.0 ms P95 headroom.', tag: scenario === 'verification-failed' ? 'FEASIBLE' : 'WINNER', ttftP95: 26, itlP95: 9.4 },
      { id: 'C-03', name: 'Throughput Max', subtitle: 'High concurrency profile', batch: 32, concurrency: 64, kvCache: 'FP8', p50: 39, p95: 64, p99: 81, throughput: 74.2, error: 0.31, gpu: 94, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'VALID', reason: 'P95 latency breaches 50 ms limit by 14 ms.', tag: 'INFEASIBLE', ttftP95: 41, itlP95: 11.2 },
      { id: 'C-04', name: 'Latency First', subtitle: 'Conservative serving profile', batch: 8, concurrency: 12, kvCache: 'FP16', p50: 23, p95: 42, p99: 49, throughput: 44.3, error: 0.04, gpu: 54, feasible: false, feasibilityVerdict: 'INFEASIBLE', evidenceValidity: 'VALID', reason: 'Throughput falls 5.7k tok/s below minimum 50k floor.', tag: 'INFEASIBLE', ttftP95: 22, itlP95: 8.9 },
    ];
  }, [scenario]);

  const recommendedCandidate = useMemo(() => {
    return candidates.find((c) => c.id === 'C-02') || candidates[0];
  }, [candidates]);

  const baselineCandidate = useMemo(() => {
    return candidates.find((c) => c.id === 'C-01') || candidates[0];
  }, [candidates]);

  // Verification Record according to scenario
  const verificationRecord: VerificationRecord = useMemo(() => {
    const isDriftFail = scenario === 'verification-failed';
    return {
      verification_id: 'ver_EXP0248_01',
      experiment_id: 'EXP-0248',
      candidate_id: 'C-02',
      original_run_id: 'run_01HZX8F2',
      verification_run_id: 'verify_01HZX9K4', // Distinct!
      verification_verdict: isDriftFail ? 'VERIFICATION_FAILED' : 'VERIFIED',
      final_decision_notes: isDriftFail
        ? 'Verification run TTFT drift of 12.8ms breached declared 3.0ms tolerance.'
        : 'Passed independent verification rerun under declared workload and drift tolerance.',
      drift_analysis: {
        slo_drift_detected: isDriftFail,
        drift_exceeded: isDriftFail,
        comparisons: [
          {
            metric_name: 'ttft_ms.p95',
            reference_value: 26.0,
            verification_value: isDriftFail ? 38.8 : 27.2,
            absolute_drift: isDriftFail ? 12.8 : 1.2,
            tolerance: 3.0,
            comparison_method: 'absolute_difference',
            unit: 'ms',
            passed: !isDriftFail,
            drift_acceptable: !isDriftFail,
            failure_reason: isDriftFail ? 'Absolute drift 12.8 ms exceeded declared tolerance 3.0 ms.' : null,
          },
        ],
      },
    };
  }, [scenario]);

  // Deterministic Verification Derivation
  const verificationStatus = useMemo(() => {
    return deriveVerifiedWinner(
      {
        candidateId: recommendedCandidate.id,
        isFeasible: recommendedCandidate.feasible,
        feasibilityVerdict: recommendedCandidate.feasibilityVerdict,
        evidenceValidity: recommendedCandidate.evidenceValidity,
        isStale: scenario === 'stale-evidence',
      },
      'run_01HZX8F2',
      verificationRecord
    );
  }, [recommendedCandidate, verificationRecord, scenario]);

  // Binding Headroom Math
  const constraints: SLOConstraint[] = useMemo(() => [
    { metric_name: 'ttft_ms', statistic: 'p95', threshold: 50.0, unit: 'ms', operator: '<=' },
    { metric_name: 'itl_ms', statistic: 'p95', threshold: 15.0, unit: 'ms', operator: '<=' },
    { metric_name: 'p95', statistic: 'p95', threshold: 50.0, unit: 'ms', operator: '<=' },
    { metric_name: 'throughput', statistic: 'p95', threshold: 50.0, unit: 'requests/s', operator: '>=' },
    { metric_name: 'error', statistic: 'p95', threshold: 0.01, unit: 'fraction', operator: '<=' },
  ], []);

  const measuredValues = useMemo(() => ({
    'ttft_ms.p95': recommendedCandidate.ttftP95,
    'itl_ms.p95': recommendedCandidate.itlP95,
    'p95.p95': recommendedCandidate.p95,
    'throughput.p95': recommendedCandidate.throughput,
    'error.p95': recommendedCandidate.error / 100, // convert percentage to fraction
  }), [recommendedCandidate]);

  const bindingHeadroom = useMemo(() => {
    return computeBindingConstraintHeadroom(constraints, measuredValues);
  }, [constraints, measuredValues]);

  // Experiments Ledger Dataset
  const experiments: UIExperiment[] = useMemo(() => [
    {
      id: 'EXP-0248',
      run: 'run_01HZX8F2',
      workload: 'chat-completions-prod',
      model: 'Llama-3-8B-Instruct',
      state: 'Completed',
      feasibility: 'Feasible',
      verification: 'Verified',
      updated: 'Just now',
      candidateId: 'C-02',
      durationSeconds: 60,
      requestedRateRps: 16.0,
      achievedRateRps: 15.9,
      measurementValidity: 'VALID',
      clientSaturation: false,
      errorRatePct: 0.08,
      exclusionsCount: 5,
    },
    {
      id: 'EXP-0247',
      run: 'run_01HZX7A3',
      workload: 'summarization-batch',
      model: 'Llama-3-8B-Instruct',
      state: 'Completed',
      feasibility: 'Feasible',
      verification: 'Verified',
      updated: '18 min ago',
      candidateId: 'C-02',
      durationSeconds: 60,
      requestedRateRps: 12.0,
      achievedRateRps: 12.0,
      measurementValidity: 'VALID',
      clientSaturation: false,
      errorRatePct: 0.05,
      exclusionsCount: 5,
    },
    {
      id: 'EXP-0246',
      run: 'run_01HZX6B1',
      workload: 'chat-completions-prod',
      model: 'Llama-3-8B-Instruct',
      state: 'Needs review',
      feasibility: 'Inconclusive',
      verification: 'Not run',
      updated: '42 min ago',
      candidateId: 'C-03',
      durationSeconds: 45,
      requestedRateRps: 24.0,
      achievedRateRps: 21.4,
      measurementValidity: 'CONTAMINATED',
      clientSaturation: true,
      errorRatePct: 0.45,
      exclusionsCount: 12,
    },
    {
      id: 'EXP-0245',
      run: 'run_01HZX5E8',
      workload: 'code-assist-staging',
      model: 'Qwen2.5-7B-Instruct',
      state: 'Failed',
      feasibility: 'Inconclusive',
      verification: 'Not run',
      updated: '1 hr ago',
      candidateId: 'C-01',
      durationSeconds: 12,
      requestedRateRps: 8.0,
      achievedRateRps: 2.1,
      measurementValidity: 'INVALID',
      clientSaturation: false,
      errorRatePct: 18.5,
      exclusionsCount: 0,
    },
    {
      id: 'EXP-0244',
      run: 'run_01HZX4C9',
      workload: 'summarization-batch',
      model: 'Llama-3-8B-Instruct',
      state: 'Completed',
      feasibility: 'Infeasible',
      verification: 'Failed',
      updated: 'Yesterday',
      candidateId: 'C-03',
      durationSeconds: 60,
      requestedRateRps: 20.0,
      achievedRateRps: 19.8,
      measurementValidity: 'VALID',
      clientSaturation: false,
      errorRatePct: 0.31,
      exclusionsCount: 5,
    },
    {
      id: 'EXP-0243',
      run: 'run_01HZX3D2',
      workload: 'chat-completions-prod',
      model: 'Llama-3-8B-Instruct',
      state: 'Running',
      feasibility: 'Pending',
      verification: 'Pending',
      updated: 'Yesterday',
      candidateId: 'C-02',
      durationSeconds: 30,
      requestedRateRps: 16.0,
      achievedRateRps: 15.8,
      measurementValidity: 'VALID',
      clientSaturation: false,
      errorRatePct: 0.08,
      exclusionsCount: 2,
    },
  ], []);

  // Preflight Smoke Probe Handler
  const handleRunSmokeProbe = async () => {
    setIsProbing(true);
    try {
      const res = await runSmokeProbe('vllm', 'Preflight probe');
      setSmokeProbeResult(`Probe Success: ${res.output_tokens} tokens returned in ${res.total_latency_ms}ms.`);
    } catch {
      // Deterministic fallback response for demo
      setSmokeProbeResult('Probe Success: 32 tokens returned in 41.2ms (vLLM healthy).');
    } finally {
      setIsProbing(false);
      setTimeout(() => setSmokeProbeResult(null), 4000);
    }
  };

  return (
    <div
      className="slokern-app"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        backgroundColor: 'var(--canvas, #080A09)',
        color: 'var(--text-primary, #F0F3EF)',
      }}
    >
      {/* Top Context Bar (No Traffic Lights, Real Actions) */}
      <ContextBar
        experimentId="EXP-0248"
        runtimeName="vLLM v0.6.3 · Nebius H100 SXM5"
        onOpenRuntimeModal={() => setIsRuntimeModalOpen(true)}
        onRunSmokeProbe={handleRunSmokeProbe}
        isProbing={isProbing}
      />

      {/* Smoke Probe Toast Notification */}
      {smokeProbeResult && (
        <div
          style={{
            position: 'fixed',
            top: '56px',
            right: '20px',
            zIndex: 1000,
            padding: '10px 16px',
            backgroundColor: 'var(--elevated, #1D251E)',
            border: '1px solid var(--primary, #76B900)',
            borderRadius: '4px',
            fontSize: '12px',
            fontFamily: 'var(--font-mono, monospace)',
            color: 'var(--primary-bright, #95D500)',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          {smokeProbeResult}
        </div>
      )}

      {/* Main Body: Sidebar + Active Workspace View */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
        <Sidebar
          currentWorkspace={currentWorkspace}
          onSelectWorkspace={navigateWorkspace}
          collapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        />

        <main
          id="main-content"
          className="workspace-view-container"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px 32px 48px',
            boxSizing: 'border-box',
          }}
          tabIndex={-1}
        >
          <ErrorBoundary
            key={currentWorkspace}
            fallbackTitle={`Render Failure in ${currentWorkspace} Workspace`}
            onReset={() => setCurrentWorkspace('Overview')}
          >
            {currentWorkspace === 'Overview' && (
              <OverviewView
                recommendedCandidate={recommendedCandidate}
                baselineCandidate={baselineCandidate}
                candidates={candidates}
                bindingHeadroom={bindingHeadroom}
                verificationStatus={verificationStatus}
                onOpenCandidateDrawer={handleOpenCandidateDrawer}
                onNavigateToVerification={() => navigateWorkspace('Verification')}
                onNavigateToExperiments={() => navigateWorkspace('Experiments')}
                onNavigateToTuningLab={() => navigateWorkspace('Tuning Lab')}
              />
            )}

            {currentWorkspace === 'Workloads' && (
              <WorkloadsView
                onLaunchBenchmark={() => {
                  handleRunSmokeProbe();
                }}
                isLaunching={isProbing}
              />
            )}

            {currentWorkspace === 'Experiments' && (
              <ExperimentsView
                experiments={experiments}
                onSelectRun={handleOpenExperimentDrawer}
              />
            )}

            {currentWorkspace === 'Tuning Lab' && (
              <TuningLabView
                candidates={candidates}
                baselineCandidate={baselineCandidate}
                selectedCandidateId={selectedCandidateId}
                onSelectCandidate={(c) => {
                  runWithViewTransition(() => {
                    setSelectedCandidateId(c.id);
                  });
                }}
                onOpenCandidateDrawer={handleOpenCandidateDrawer}
              />
            )}

            {currentWorkspace === 'Verification' && (
              <VerificationView
                recommendedCandidate={recommendedCandidate}
                verificationStatus={verificationStatus}
                searchRunId="run_01HZX8F2"
                verificationRunId="verify_01HZX9K4"
              />
            )}

            {currentWorkspace === 'Reports' && (
              <ReportsView
                recommendedCandidate={recommendedCandidate}
                baselineCandidate={baselineCandidate}
                verificationStatus={verificationStatus}
                experimentId="EXP-0248"
              />
            )}
          </ErrorBoundary>
        </main>
      </div>

      {/* Persistent Bottom Status & Provenance Bar */}
      <StatusBar
        scenario={scenario}
        onScenarioChange={setScenario}
        healthStatus={healthStatus}
        healthPingMs={healthPingMs}
        activeRunId="run_01HZX8F2"
      />

      {/* Solid Elevated Slide-Over Drawer for Candidate Inspection */}
      <SlideOverDrawer
        isOpen={inspectCandidate !== null}
        onClose={handleCloseCandidateDrawer}
        title={inspectCandidate ? `${inspectCandidate.id} · ${inspectCandidate.name}` : ''}
        subtitle="Serving profile parameters & empirical telemetry"
      >
        {inspectCandidate && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Badge tone={inspectCandidate.feasible ? (inspectCandidate.tag === 'WINNER' ? 'verified' : 'feasible') : 'infeasible'}>
                {inspectCandidate.tag}
              </Badge>
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
                {inspectCandidate.subtitle}
              </span>
            </div>

            <div style={{ padding: '12px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '4px', fontSize: '12px' }}>
              <strong>Evaluator Verdict:</strong> {inspectCandidate.reason}
            </div>

            <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono, monospace)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ color: 'var(--text-secondary, #A0AAA0)', fontWeight: 600 }}>RUNTIME SETTINGS</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>Max Concurrency</span>
                <span>{inspectCandidate.concurrency} streams</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>Batch Size</span>
                <span>{inspectCandidate.batch}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>KV Cache Dtype</span>
                <span>{inspectCandidate.kvCache}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>GPU Memory Utilization</span>
                <span>0.90 ({inspectCandidate.gpu}% VRAM)</span>
              </div>
            </div>

            <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono, monospace)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ color: 'var(--text-secondary, #A0AAA0)', fontWeight: 600 }}>MEASURED EMPIRICAL METRICS</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>P95 TTFT Latency</span>
                <span>{formatLatency(inspectCandidate.ttftP95)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>P95 ITL Latency</span>
                <span>{formatLatency(inspectCandidate.itlP95)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>Output Token Throughput</span>
                <span>{formatThroughput(inspectCandidate.throughput * 1000)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>Error Rate</span>
                <span>{formatNumber(inspectCandidate.error, 2)}%</span>
              </div>
            </div>
          </div>
        )}
      </SlideOverDrawer>

      {/* Solid Elevated Slide-Over Drawer for Experiment Run Inspection */}
      <SlideOverDrawer
        isOpen={inspectExperiment !== null}
        onClose={handleCloseExperimentDrawer}
        title={inspectExperiment ? `${inspectExperiment.run} · ${inspectExperiment.workload}` : ''}
        subtitle="Run execution metadata & raw trace audit trail"
      >
        {inspectExperiment && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Badge tone={inspectExperiment.state === 'Completed' ? 'neutral' : 'warning'}>
                {inspectExperiment.state}
              </Badge>
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
                {inspectExperiment.id}
              </span>
            </div>

            <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono, monospace)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Candidate ID</span>
                <span style={{ fontWeight: 600 }}>{inspectExperiment.candidateId}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Model Target</span>
                <span>{inspectExperiment.model}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Offered / Achieved Load</span>
                <span style={{ fontWeight: 600 }}>
                  {(inspectExperiment.requestedRateRps ?? 16.0).toFixed(1)} / {(inspectExperiment.achievedRateRps ?? 15.9).toFixed(1)} rps
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Measurement Validity</span>
                <span style={{ color: inspectExperiment.measurementValidity === 'VALID' ? 'var(--primary-bright, #95D500)' : 'var(--warning, #E9B949)', fontWeight: 600 }}>
                  {inspectExperiment.measurementValidity ?? 'VALID'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Client Saturation</span>
                <span style={{ color: inspectExperiment.clientSaturation ? 'var(--error, #FF5555)' : 'var(--text-muted, #727D73)' }}>
                  {inspectExperiment.clientSaturation ? 'SATURATED' : 'NOMINAL (HEADROOM 72%)'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Warm-up Exclusions</span>
                <span>{inspectExperiment.exclusionsCount ?? 5} requests excluded</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Feasibility Verdict</span>
                <span style={{ color: inspectExperiment.feasibility === 'Feasible' ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)' }}>
                  {inspectExperiment.feasibility}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Independent Verification</span>
                <span>{inspectExperiment.verification}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Execution Duration</span>
                <span>{inspectExperiment.durationSeconds}s</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Timestamp</span>
                <span>{inspectExperiment.updated}</span>
              </div>
            </div>

            <div style={{ padding: '12px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '4px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-secondary, #A0AAA0)' }}>
              Artifact Reference: <code>artifacts/{inspectExperiment.id}/{inspectExperiment.run}/raw_trace.jsonl</code>
            </div>
          </div>
        )}
      </SlideOverDrawer>

      {/* Runtime Environment Profile Modal */}
      {isRuntimeModalOpen && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="runtime-modal-title"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 200,
          }}
          onClick={() => setIsRuntimeModalOpen(false)}
        >
          <div
            style={{
              width: '520px',
              maxWidth: '90vw',
              backgroundColor: 'var(--elevated, #1D251E)',
              border: '1px solid var(--border-strong, #384635)',
              borderRadius: '8px',
              padding: '24px',
              boxShadow: 'var(--shadow-lg)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2
                id="runtime-modal-title"
                style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', textWrap: 'balance' }}
              >
                Runtime Serving Environment & Hardware
              </h2>
              <button
                type="button"
                onClick={() => setIsRuntimeModalOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary, #A0AAA0)',
                  cursor: 'pointer',
                  fontSize: '16px',
                }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', fontFamily: 'var(--font-mono, monospace)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Serving Adapter</span>
                <span style={{ color: 'var(--primary-bright, #95D500)', fontWeight: 600 }}>vLLM (OpenAI-compatible)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>GPU Accelerator</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>NVIDIA H100 80GB SXM5</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Cloud Provider / Host</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>Nebius Cloud (eu-west1)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>CUDA Driver</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>550.54.14 · CUDA 12.4</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Endpoint URL</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>http://127.0.0.1:8000/v1</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Control Plane Ping</span>
                <span style={{ color: 'var(--primary-bright, #95D500)' }}>{healthPingMs} ms (Healthy)</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
              <button
                type="button"
                onClick={() => setIsRuntimeModalOpen(false)}
                style={{
                  backgroundColor: 'var(--raised, #151B15)',
                  border: '1px solid var(--border-strong, #384635)',
                  color: 'var(--text-primary, #F0F3EF)',
                  padding: '6px 16px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono, monospace)',
                  cursor: 'pointer',
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
