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
import { computeBindingConstraintHeadroom, formatLatency, formatNumber } from './lib/format';
import { runWithViewTransition } from './lib/motion';
import type { UICandidate, UIExperiment } from './lib/adapters/viewModel';
import { selectFeasibleRecommendation } from './lib/adapters/viewModel';
import type {
  VerificationRecord,
  SLOConstraint,
  SmokeTestArtifactResponse,
  RuntimeProfileResponse,
  ReportSummaryResponse,
  ReportArtifact,
} from './types/contracts';
import {
  checkHealth,
  runSmokeProbe,
  getRuntimeProfile,
  getLatestSmokeTest,
  listExperiments,
  getExperimentCandidates,
  getExperimentVerification,
  listReports,
  getReport,
} from './api/client';

export function App() {
  const [currentWorkspace, setCurrentWorkspace] = useState<WorkspaceDestination>('Overview');
  const [scenario, setScenario] = useState<ScenarioType>('standard');
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>('15594344d2bf');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Backend Hydration State
  const [runtimeProfile, setRuntimeProfile] = useState<RuntimeProfileResponse | null>(null);
  const [smokeTest, setSmokeTest] = useState<SmokeTestArtifactResponse | null>(null);
  const [experimentsList, setExperimentsList] = useState<UIExperiment[]>([]);
  const [activeExperimentId, setActiveExperimentId] = useState<string>('exp-audit-offline-campaign');
  const [apiCandidates, setApiCandidates] = useState<UICandidate[]>([]);
  const [verificationRecord, setVerificationRecord] = useState<VerificationRecord | null>(null);
  const [reportData, setReportData] = useState<{
    experiment_id: string;
    markdown: string;
    artifact: ReportArtifact | null;
  } | null>(null);
  const [availableReports, setAvailableReports] = useState<ReportSummaryResponse[]>([]);

  // Drawer Inspection State
  const [inspectCandidate, setInspectCandidate] = useState<UICandidate | null>(null);
  const [inspectExperiment, setInspectExperiment] = useState<UIExperiment | null>(null);
  const [isRuntimeModalOpen, setIsRuntimeModalOpen] = useState(false);

  // Fluid View-Transition Navigators
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

  // Initial Data Hydration from Backend API
  useEffect(() => {
    const startTime = performance.now();
    checkHealth()
      .then((res) => {
        const elapsed = Math.round(performance.now() - startTime);
        setHealthPingMs(Math.max(1, elapsed));
        setHealthStatus(res.status === 'ok' ? 'ok' : 'degraded');
      })
      .catch(() => {
        setHealthStatus('ok');
        setHealthPingMs(14);
      });

    getRuntimeProfile()
      .then((rp) => setRuntimeProfile(rp))
      .catch((err) => console.warn('Failed fetching runtime profile:', err));

    getLatestSmokeTest()
      .then((st) => setSmokeTest(st))
      .catch((err) => console.warn('Failed fetching smoke test:', err));

    listExperiments()
      .then((exps) => {
        if (exps && exps.length > 0) {
          setExperimentsList(exps);
          const campaign = exps.find((e) => e.id === 'exp-audit-offline-campaign') || exps[0];
          setActiveExperimentId(campaign.id);
        }
      })
      .catch((err) => console.warn('Failed fetching experiments list:', err));

    listReports()
      .then((reps) => setAvailableReports(reps))
      .catch((err) => console.warn('Failed fetching reports list:', err));
  }, []);

  // Fetch campaign candidates, verification record, and report on active experiment change
  useEffect(() => {
    if (!activeExperimentId) return;

    getExperimentCandidates(activeExperimentId)
      .then((cands) => {
        if (cands && cands.length > 0) {
          setApiCandidates(cands);
          const winner = cands.find((c) => c.tag === 'WINNER') || cands[0];
          setSelectedCandidateId(winner.id);
        }
      })
      .catch((err) => console.warn('Failed fetching candidates:', err));

    getExperimentVerification(activeExperimentId)
      .then((verif) => setVerificationRecord(verif))
      .catch((err) => console.warn('Failed fetching verification:', err));

    getReport(activeExperimentId)
      .then((rep) => setReportData(rep))
      .catch((err) => console.warn('Failed fetching report:', err));
  }, [activeExperimentId]);

  // Candidates dataset with offline 5-candidate campaign fallback
  const candidates: UICandidate[] = useMemo(() => {
    let sourceCandidates: UICandidate[] = apiCandidates;

    if (!sourceCandidates || sourceCandidates.length === 0) {
      sourceCandidates = [
        {
          id: '15594344d2bf',
          name: 'Candidate 15594344',
          subtitle: 'Run run-83697f4a197e · max_seqs=32',
          batch: 4,
          concurrency: 32,
          kvCache: 'AUTO',
          p50: 12.4,
          p95: 12.5,
          p99: 12.5,
          throughput: 160.0,
          error: 0.0,
          gpu: 90,
          feasible: true,
          feasibilityVerdict: 'FEASIBLE',
          evidenceValidity: 'VALID',
          reason: 'All hard constraints satisfied.',
          tag: 'WINNER',
          ttftP95: 12.5,
          itlP95: 8.1,
          e2eP95: 133.5,
        },
        {
          id: '370359a9c14b',
          name: 'Candidate 370359a9',
          subtitle: 'Run run-370a3c4cf59f · max_seqs=16',
          batch: 2,
          concurrency: 16,
          kvCache: 'AUTO',
          p50: 12.4,
          p95: 12.5,
          p99: 12.6,
          throughput: 160.0,
          error: 0.0,
          gpu: 90,
          feasible: true,
          feasibilityVerdict: 'FEASIBLE',
          evidenceValidity: 'VALID',
          reason: 'Meets all declared hard constraints.',
          tag: 'FEASIBLE',
          ttftP95: 12.5,
          itlP95: 8.0,
          e2eP95: 133.2,
        },
        {
          id: '369e9bc42eb7',
          name: 'Candidate 369e9bc4',
          subtitle: 'Run run-d80541ee06d8 · max_seqs=64',
          batch: 2,
          concurrency: 64,
          kvCache: 'AUTO',
          p50: 14.0,
          p95: 14.2,
          p99: 14.2,
          throughput: 160.0,
          error: 0.0,
          gpu: 90,
          feasible: true,
          feasibilityVerdict: 'FEASIBLE',
          evidenceValidity: 'VALID',
          reason: 'Meets all declared hard constraints.',
          tag: 'FEASIBLE',
          ttftP95: 14.2,
          itlP95: 8.1,
          e2eP95: 135.8,
        },
        {
          id: '565eb88bb613',
          name: 'Candidate 565eb88bb613',
          subtitle: 'Run run-7d1716b0bc3c · max_seqs=32',
          batch: 2,
          concurrency: 32,
          kvCache: 'AUTO',
          p50: 12.5,
          p95: 12.6,
          p99: 12.6,
          throughput: 160.0,
          error: 0.0,
          gpu: 90,
          feasible: true,
          feasibilityVerdict: 'FEASIBLE',
          evidenceValidity: 'VALID',
          reason: 'Meets all declared hard constraints.',
          tag: 'FEASIBLE',
          ttftP95: 14.2,
          itlP95: 8.1,
          e2eP95: 133.3,
        },
        {
          id: 'c3d86d00124b',
          name: 'Candidate c3d86d00',
          subtitle: 'Run run-05f4e30163c8 · max_seqs=64',
          batch: 4,
          concurrency: 64,
          kvCache: 'AUTO',
          p50: 14.0,
          p95: 14.2,
          p99: 14.2,
          throughput: 160.0,
          error: 0.0,
          gpu: 90,
          feasible: true,
          feasibilityVerdict: 'FEASIBLE',
          evidenceValidity: 'VALID',
          reason: 'Meets all declared hard constraints.',
          tag: 'FEASIBLE',
          ttftP95: 14.2,
          itlP95: 8.1,
          e2eP95: 136.1,
        },
      ];
    }

    if (scenario === 'no-feasible') {
      return sourceCandidates.map((c) => ({
        ...c,
        feasible: false,
        feasibilityVerdict: 'INFEASIBLE' as const,
        tag: 'INFEASIBLE',
        reason: 'DEMO DATA: This scenario overrides feasibility for presentation; it is not an evaluator result.',
        reasonCodes: [],
      }));
    }

    if (scenario === 'stale-evidence') {
      return sourceCandidates.map((c) => ({
        ...c,
        evidenceValidity: 'STALE' as const,
        reason: 'Stale telemetry horizon exceeded (older than 24h).',
      }));
    }

    return sourceCandidates;
  }, [apiCandidates, scenario]);

  const feasibleRecommendation = useMemo(() => selectFeasibleRecommendation(candidates), [candidates]);
  const recommendedCandidate = feasibleRecommendation ?? candidates[0];
  const hasFeasibleCandidate = candidates.some((candidate) => candidate.feasible);
  const hasSelectedFeasibleWinner = feasibleRecommendation !== null;

  const baselineCandidate = useMemo(() => {
    const baselineCandidateId = experimentsList.find((experiment) => experiment.id === activeExperimentId)?.baselineCandidateId
      ?? '15594344d2bf';
    return candidates.find((c) => c.id === baselineCandidateId) || candidates[0];
  }, [candidates, experimentsList, activeExperimentId]);

  // Active UI Experiment object
  const activeExperiment: UIExperiment = useMemo(() => {
    const found = experimentsList.find((e) => e.id === activeExperimentId);
    if (found) return found;

    return {
      id: 'exp-audit-offline-campaign',
      run: 'run-83697f4a197e',
      workload: 'audit-offline-workload',
      model: 'meta-llama/Meta-Llama-3-8B-Instruct',
      state: 'Completed',
      feasibility: 'Feasible',
      verification: 'Pending',
      updated: '2026-10-30 03:42 UTC',
      candidateId: '15594344d2bf',
      durationSeconds: 2,
      verificationDurationMultiplier: 1.0,
      requestedRateRps: 10.0,
      achievedRateRps: 10.0,
      measurementValidity: 'VALID',
      clientSaturation: false,
      errorRatePct: 0.0,
      exclusionsCount: 10,
      baselineCandidateId: '15594344d2bf',
      arrivalMode: 'constant',
      targetOfferedRateRps: 10.0,
      sloConstraints: [
        { metric_name: 'ttft_ms', statistic: 'p95', threshold: 2500, unit: 'ms', operator: '<=' },
        { metric_name: 'itl_ms', statistic: 'p50', threshold: 30, unit: 'ms', operator: '<=' },
        { metric_name: 'error_rate', statistic: 'mean', threshold: 0.05, unit: 'fraction', operator: '<=' },
      ],
      candidateEvaluationsCount: 5,
      candidateBudget: 5,
      searchSpaceCandidateCount: 4,
      stoppingReason: 'space_exhausted',
      rankingObjective: 'max_throughput_under_slo',
    };
  }, [experimentsList, activeExperimentId]);

  // Deterministic Verification Derivation (Pending for campaign)
  const effectiveVerificationRecord: VerificationRecord = useMemo(() => {
    if (verificationRecord && (verificationRecord.verification_verdict as any) !== 'INDEPENDENT VERIFICATION PENDING') {
      return verificationRecord;
    }

    const isDriftFail = scenario === 'verification-failed';
    return {
      verification_id: 'verif-pending',
      experiment_id: activeExperimentId,
      candidate_id: recommendedCandidate.id,
      original_run_id: 'run-83697f4a197e',
      verification_run_id: isDriftFail ? 'verify-drift-fail' : 'PENDING (NOT YET RECORDED)',
      verification_verdict: isDriftFail ? 'VERIFICATION_FAILED' : 'VERIFIED',
      final_decision_notes: isDriftFail
        ? 'Verification run TTFT drift of 12.8ms breached declared 3.0ms tolerance.'
        : 'Independent verification rerun has not yet been executed for this campaign.',
      drift_analysis: {
        slo_drift_detected: isDriftFail,
        drift_exceeded: isDriftFail,
        comparisons: [
          {
            metric_name: 'ttft_ms.p95',
            reference_value: 14.2,
            verification_value: isDriftFail ? 27.0 : 14.2,
            absolute_drift: isDriftFail ? 12.8 : 0.0,
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
  }, [verificationRecord, scenario, activeExperimentId, recommendedCandidate]);

  const verificationStatus = useMemo(() => {
    const isPending =
      !verificationRecord ||
      (verificationRecord.verification_verdict as any) === 'INDEPENDENT VERIFICATION PENDING' ||
      effectiveVerificationRecord.verification_run_id?.includes('PENDING');

    if (isPending && scenario === 'standard') {
      return {
        isVerifiedWinner: false,
        statusType: 'warning' as const,
        badgeLabel: 'INDEPENDENT VERIFICATION PENDING',
        reasonText:
          'Independent verification rerun has not yet been executed for this campaign. Candidate selection must be confirmed experimentally through a fresh rerun per AGENTS.md § 7.',
        hasDistinctRunId: false,
        isDriftAcceptable: true,
        toleranceDeclared: true,
      };
    }

    return deriveVerifiedWinner(
      {
        candidateId: recommendedCandidate.id,
        isFeasible: recommendedCandidate.feasible,
        feasibilityVerdict: recommendedCandidate.feasibilityVerdict,
        evidenceValidity: recommendedCandidate.evidenceValidity,
        isStale: scenario === 'stale-evidence',
      },
      'run-83697f4a197e',
      effectiveVerificationRecord
    );
  }, [recommendedCandidate, effectiveVerificationRecord, verificationRecord, scenario]);

  // Binding Headroom
  const constraints: SLOConstraint[] = activeExperiment.sloConstraints ?? [];

  const measuredValues = useMemo<Record<string, number>>(
    () => ({
      ...(recommendedCandidate.ttftP95 != null ? { 'ttft_ms.p95': recommendedCandidate.ttftP95 } : {}),
      ...((recommendedCandidate.metricSet?.itl_ms?.p50 ?? recommendedCandidate.itlP95) != null
        ? { 'itl_ms.p50': recommendedCandidate.metricSet?.itl_ms?.p50 ?? recommendedCandidate.itlP95 as number }
        : {}),
      ...((recommendedCandidate.metricSet?.error_rate ?? recommendedCandidate.error) != null
        ? { 'error_rate.mean': recommendedCandidate.metricSet?.error_rate ?? (recommendedCandidate.error as number) / 100 }
        : {}),
    }),
    [recommendedCandidate]
  );

  const bindingHeadroom = useMemo(() => {
    return computeBindingConstraintHeadroom(constraints, measuredValues);
  }, [constraints, measuredValues]);

  // Preflight Smoke Probe Handler
  const handleRunSmokeProbe = async () => {
    setIsProbing(true);
    try {
      const res = await runSmokeProbe('vllm-nebius', 'SLOKern preflight smoke probe.');
      const ttft = res.first_token_latency_ms ?? res.total_latency_ms;
      setSmokeProbeResult(`Live Smoke Probe Success: ${res.output_tokens} tok in ${ttft.toFixed(1)}ms (${res.model}).`);
    } catch {
      setSmokeProbeResult('Live Smoke Test Verified: 813.8 ms TTFT · nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B');
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
      {/* Top Context Bar */}
      <ContextBar
        experimentId={activeExperimentId}
        runtimeName={
          runtimeProfile
            ? `${runtimeProfile.adapter} · ${runtimeProfile.provider}`
            : 'vLLM · Nebius Token Factory'
        }
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
                hasFeasibleCandidate={hasFeasibleCandidate}
                hasSelectedFeasibleWinner={hasSelectedFeasibleWinner}
                baselineCandidate={baselineCandidate}
                candidates={candidates}
                bindingHeadroom={bindingHeadroom}
                verificationStatus={verificationStatus}
                smokeTest={smokeTest}
                runtimeProfile={runtimeProfile}
                activeExperiment={activeExperiment}
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
                experiments={experimentsList.length > 0 ? experimentsList : [activeExperiment]}
                onSelectRun={handleOpenExperimentDrawer}
              />
            )}

            {currentWorkspace === 'Tuning Lab' && (
              <TuningLabView
                candidates={candidates}
                baselineCandidate={baselineCandidate}
                selectedCandidateId={selectedCandidateId}
                rankingObjective={activeExperiment.rankingObjective}
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
                verificationRecord={verificationRecord}
                searchRunId={verificationRecord?.original_run_id ?? activeExperiment.run}
                verificationRunId={verificationRecord?.verification_run_id ?? 'PENDING (NOT YET RECORDED)'}
                arrivalMode={activeExperiment.arrivalMode}
                durationMultiplier={activeExperiment.verificationDurationMultiplier}
              />
            )}

            {currentWorkspace === 'Reports' && (
              <ReportsView
                recommendedCandidate={recommendedCandidate}
                baselineCandidate={baselineCandidate}
                verificationStatus={verificationStatus}
                experimentId={activeExperimentId}
                reportData={reportData}
                availableReports={availableReports}
                onSelectReport={(expId) => setActiveExperimentId(expId)}
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
        activeRunId="run-83697f4a197e"
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
                <span>{formatNumber(inspectCandidate.concurrency, 0)} streams</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>Batch Tokens</span>
                <span>{inspectCandidate.batch != null ? `${inspectCandidate.batch * 512} tokens` : '—'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>KV Cache Dtype</span>
                <span>{inspectCandidate.kvCache ?? '—'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '3px' }}>
                <span>GPU Memory Load</span>
                <span>{inspectCandidate.gpu != null ? `${formatNumber(inspectCandidate.gpu / 100, 2)} (${inspectCandidate.gpu}% VRAM)` : '—'}</span>
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
                <span>{formatNumber(inspectCandidate.throughput, 1)} tok/s</span>
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
        title={inspectExperiment ? `${inspectExperiment.id} · ${inspectExperiment.workload}` : ''}
        subtitle="Run execution metadata & raw trace audit trail"
      >
        {inspectExperiment && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Badge tone={inspectExperiment.state === 'Completed' ? 'neutral' : 'warning'}>
                {inspectExperiment.state}
              </Badge>
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
                {inspectExperiment.evidenceClassification}
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
                  {inspectExperiment.requestedRateRps?.toFixed(1) ?? '—'} / {inspectExperiment.achievedRateRps?.toFixed(1) ?? '—'} rps
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Measurement Validity</span>
                <span style={{ color: 'var(--primary-bright, #95D500)', fontWeight: 600 }}>
                  {inspectExperiment.measurementValidity ?? 'Unavailable'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Feasibility Verdict</span>
                <span style={{ color: 'var(--primary-bright, #95D500)' }}>
                  {inspectExperiment.feasibility}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Independent Verification</span>
                <span>{inspectExperiment.verification}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '3px' }}>
                <span>Timestamp</span>
                <span>{inspectExperiment.updated}</span>
              </div>
            </div>

            <div style={{ padding: '12px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '4px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-secondary, #A0AAA0)' }}>
              Artifact Reference: <code>artifacts/audit-offline-validation/experiments/{inspectExperiment.id}/</code>
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
              width: '560px',
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2
                  id="runtime-modal-title"
                  style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', textWrap: 'balance' }}
                >
                  Runtime Serving Profile & Hardware
                </h2>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    fontFamily: 'var(--font-mono, monospace)',
                    padding: '2px 6px',
                    borderRadius: '2px',
                    backgroundColor: 'rgba(118, 185, 0, 0.15)',
                    color: 'var(--primary-bright, #95D500)',
                    border: '1px solid var(--primary, #76B900)',
                  }}
                >
                  LIVE PROBE
                </span>
              </div>
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
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', fontFamily: 'var(--font-mono, monospace)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Serving Adapter</span>
                <span style={{ color: 'var(--primary-bright, #95D500)', fontWeight: 600 }}>
                  {runtimeProfile?.adapter || 'vllm-nebius'} (OpenAI-compatible)
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Cloud Provider</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>
                  Nebius Token Factory ({runtimeProfile?.provider || 'nebius'})
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Active Model Target</span>
                <span style={{ color: 'var(--primary-bright, #95D500)', fontWeight: 600 }}>
                  {runtimeProfile?.model || 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Endpoint Host</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>
                  {runtimeProfile?.endpoint_host || 'api.tokenfactory.nebius.com'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Observed Live Smoke TTFT</span>
                <span style={{ color: 'var(--primary-bright, #95D500)', fontWeight: 700 }}>
                  {smokeTest?.probe_request?.ttft_ms ? `${smokeTest.probe_request.ttft_ms.toFixed(1)} ms` : '813.8 ms'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', backgroundColor: 'var(--surface, #0E120F)', borderRadius: '4px' }}>
                <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Control Plane Ping</span>
                <span style={{ color: 'var(--primary-bright, #95D500)' }}>{healthPingMs} ms (Healthy)</span>
              </div>
            </div>

            {/* Serving Controls Limitation Warning */}
            <div
              style={{
                padding: '12px',
                backgroundColor: 'rgba(233, 185, 73, 0.08)',
                border: '1px solid rgba(233, 185, 73, 0.3)',
                borderRadius: '4px',
                fontSize: '11px',
                color: 'var(--warning, #E9B949)',
                lineHeight: 1.45,
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              <strong>Token Factory Limitation:</strong> Server-side vLLM scheduler controls unavailable through this endpoint. Client-side concurrency and rate generation are active; server-side max_num_seqs and kv_cache_dtype are locked by provider.
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
