import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';

type Page = 'Command Center' | 'Experiments' | 'Workload & SLO Builder' | 'Tuning Lab' | 'Live Monitor' | 'Verification' | 'Evidence & Reports' | 'Runtime Profile' | 'Settings' | 'Run Detail';
type Scenario = 'standard' | 'verification-failed' | 'no-feasible' | 'stale-evidence';
type Candidate = {
  id: string; name: string; subtitle: string; batch: number; concurrency: number; kvCache: string;
  p50: number; p95: number; p99: number; throughput: number; error: number; gpu: number;
  feasible: boolean; reason: string; tag: string;
  ttftP95: number; itlP95: number;
};
type ExperimentRecord = { id: string; run: string; work: string; model: string; state: string; feasibility: string; verification: string; updated: string; candidateId: string };

const NAV: { label: Page; navLabel: string; icon: string; section: string }[] = [
  { label: 'Command Center', navLabel: 'Overview', icon: 'grid', section: 'WORKFLOW' },
  { label: 'Experiments', navLabel: 'Experiments', icon: 'layers', section: 'WORKFLOW' },
  { label: 'Workload & SLO Builder', navLabel: 'Specify', icon: 'sliders', section: 'WORKFLOW' },
  { label: 'Tuning Lab', navLabel: 'Evaluate & Optimize', icon: 'activity', section: 'WORKFLOW' },
  { label: 'Live Monitor', navLabel: 'Measure', icon: 'chart', section: 'OBSERVABILITY' },
  { label: 'Verification', navLabel: 'Verify', icon: 'shield', section: 'OBSERVABILITY' },
  { label: 'Evidence & Reports', navLabel: 'Reports', icon: 'file', section: 'OBSERVABILITY' },
  { label: 'Runtime Profile', navLabel: 'Runtime Profile', icon: 'cpu', section: 'SYSTEM' },
  { label: 'Settings', navLabel: 'Settings', icon: 'settings', section: 'SYSTEM' },
];

const BASE_CANDIDATES: Candidate[] = [
  { id: 'C-01', name: 'Baseline', subtitle: 'Reference configuration', batch: 8, concurrency: 16, kvCache: 'FP16', p50: 36, p95: 68, p99: 91, throughput: 43.8, error: 0.08, gpu: 61, feasible: false, reason: 'P95 latency exceeds the 50 ms hard limit by 18 ms.', tag: 'BASELINE', ttftP95: 38, itlP95: 14.8 },
  { id: 'C-02', name: 'Balanced', subtitle: 'Recommended candidate', batch: 16, concurrency: 32, kvCache: 'FP8', p50: 24, p95: 47, p99: 58, throughput: 61.8, error: 0.08, gpu: 78, feasible: true, reason: 'Meets all three hard SLO constraints with 3 ms P95 headroom.', tag: 'WINNER', ttftP95: 26, itlP95: 9.4 },
  { id: 'C-03', name: 'Throughput Max', subtitle: 'High concurrency profile', batch: 32, concurrency: 64, kvCache: 'FP8', p50: 39, p95: 64, p99: 81, throughput: 74.2, error: 0.31, gpu: 94, feasible: false, reason: 'P95 latency breaches the hard limit by 14 ms.', tag: 'INFEASIBLE', ttftP95: 41, itlP95: 11.2 },
  { id: 'C-04', name: 'Latency First', subtitle: 'Conservative serving profile', batch: 8, concurrency: 12, kvCache: 'FP16', p50: 23, p95: 42, p99: 49, throughput: 44.3, error: 0.04, gpu: 54, feasible: false, reason: 'Throughput falls 5.7k tok/s below the minimum target.', tag: 'INFEASIBLE', ttftP95: 22, itlP95: 8.9 },
];

const BASE_EXPERIMENTS: ExperimentRecord[] = [
  { id: 'EXP-0248', run: 'run_01HZX8F2', work: 'chat-completions-prod', model: 'Llama-3-8B-Instruct', state: 'Completed', feasibility: 'Feasible', verification: 'Pending', updated: 'Just now', candidateId: 'C-02' },
  { id: 'EXP-0247', run: 'run_01HZX7A3', work: 'summarization-batch', model: 'Llama-3-8B-Instruct', state: 'Completed', feasibility: 'Feasible', verification: 'Verified', updated: '18 min ago', candidateId: 'C-02' },
  { id: 'EXP-0246', run: 'run_01HZX6B1', work: 'chat-completions-prod', model: 'Llama-3-8B-Instruct', state: 'Needs review', feasibility: 'Inconclusive', verification: 'Not run', updated: '42 min ago', candidateId: 'C-03' },
  { id: 'EXP-0245', run: 'run_01HZX5E8', work: 'code-assist-staging', model: 'Qwen2.5-7B-Instruct', state: 'Failed', feasibility: 'Inconclusive', verification: 'Not run', updated: '1 hr ago', candidateId: 'C-01' },
  { id: 'EXP-0244', run: 'run_01HZX4C9', work: 'summarization-batch', model: 'Llama-3-8B-Instruct', state: 'Completed', feasibility: 'Infeasible', verification: 'Failed', updated: 'Yesterday', candidateId: 'C-03' },
  { id: 'EXP-0243', run: 'run_01HZX3D2', work: 'chat-completions-prod', model: 'Llama-3-8B-Instruct', state: 'Running', feasibility: 'Pending', verification: 'Not run', updated: 'Yesterday', candidateId: 'C-02' },
];

const EVENTS = [
  { time: '14:42:18.204', type: 'success', title: 'Candidate C-02 satisfies all hard SLOs', detail: 'Evaluator v0.4.2 · policy set slo-prod-03' },
  { time: '14:42:17.891', type: 'info', title: 'Candidate ranking finalized', detail: '4 candidates evaluated · deterministic ranking' },
  { time: '14:41:58.122', type: 'warning', title: 'C-03 rejected by latency constraint', detail: 'P95 measured 64 ms · maximum 50 ms' },
  { time: '14:41:24.017', type: 'info', title: 'Baseline measurements captured', detail: 'Run run_01HZX8F2 · 120 second sample window' },
];

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true as const };
  const paths: Record<string, ReactNode> = {
    grid: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.3"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.3"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.3"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.3"/></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
    sliders: <><path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2" fill="#111a0c"/><circle cx="15" cy="12" r="2" fill="#111a0c"/><circle cx="8" cy="18" r="2" fill="#111a0c"/></>,
    activity: <><path d="M3 12h4l2.4-7 4.2 14 2.4-7H21"/></>,
    chart: <><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 5-7"/><circle cx="19" cy="6" r="1"/></>,
    shield: <><path d="M12 3 20 6v5c0 5-3.4 8-8 10-4.6-2-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></>,
    file: <><path d="M6 3.5h8l4 4v13H6z"/><path d="M14 3.5v4h4M9 12h6M9 16h6"/></>,
    cpu: <><rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2.5v3M15 2.5v3M9 18.5v3M15 18.5v3M2.5 9h3M2.5 15h3M18.5 9h3M18.5 15h3"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1 1.7-1.8 3.1-2-.5a7 7 0 0 1-1.7 1l-.4 2.1h-3.6l-.4-2.1a7 7 0 0 1-1.7-1l-2 .5-1.8-3.1 1.1-1.8a7 7 0 0 1 0-2l-1.1-1.8 1.8-3.1 2 .5a7 7 0 0 1 1.7-1l.4-2.1h3.6l.4 2.1a7 7 0 0 1 1.7 1l2-.5 1.8 3.1-1.1 1.8a7 7 0 0 1 0 2Z" transform="translate(-.3 -1) scale(.92)"/></>,
    search: <><circle cx="10.8" cy="10.8" r="6.6"/><path d="m16 16 4.5 4.5"/></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    download: <><path d="M12 3v12M7 10l5 5 5-5M4 20h16"/></>,
    play: <path d="m8 5 11 7-11 7z" fill="currentColor" stroke="none"/>,
    pause: <><path d="M8 5v14M16 5v14" strokeWidth="3"/></>,
    check: <path d="m5 12 4.3 4.3L19 6.5"/>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    external: <><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    alert: <><path d="m12 3 9 17H3L12 3Z"/><path d="M12 9v4M12 16.5h.01"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5h.01"/></>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.6 9A7 7 0 0 1 18 6l2 6M4 12l2 6a7 7 0 0 0 12.4-3"/></>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/></>,
    command: <><path d="M8 9V5a3 3 0 1 0-3 3h14a3 3 0 1 0-3-3v14a3 3 0 1 0 3-3H5a3 3 0 1 0 3 3V9Z"/></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16"/></>,
  };
  return <svg {...common}>{paths[name] ?? <circle cx="12" cy="12" r="8" />}</svg>;
}

function Status({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'accent' }) {
  return <span className={`status status-${tone}`}><span className="status-dot" />{children}</span>;
}

function SectionTitle({ eyebrow, title, detail, right }: { eyebrow?: string; title: string; detail?: string; right?: ReactNode }) {
  return <div className="section-title"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2>{detail && <p>{detail}</p>}</div>{right && <div className="section-title-right">{right}</div>}</div>;
}

function MetricCard({ label, value, unit, delta, tone = 'neutral', icon }: { label: string; value: string; unit?: string; delta?: string; tone?: string; icon?: string }) {
  return <div className="metric-card"><div className="metric-top"><span>{label}</span>{icon && <span className="metric-icon"><Icon name={icon} size={15}/></span>}</div><div className="metric-value">{value}<small>{unit}</small></div>{delta && <div className={`metric-delta ${tone}`}>{delta}</div>}</div>;
}

function LatencyInstruments({
  ttftP95,
  itlP95,
  compact = false,
}: {
  ttftP95: number
  itlP95: number
  compact?: boolean
}) {
  return (
    <div className={`telemetry-latency-grid ${compact ? 'is-compact' : ''}`}>
      <div className="telemetry-cell">
        <span
          className="telemetry-label"
          title="Time to First Token (prefill phase latency at 95th percentile)"
        >
          TTFT P95
        </span>
        <div className="telemetry-value-pair">
          <strong className="telemetry-number">{ttftP95}</strong>
          <span className="telemetry-unit">ms</span>
        </div>
      </div>
      <div className="telemetry-divider" aria-hidden="true" />
      <div className="telemetry-cell">
        <span
          className="telemetry-label"
          title="Inter-Token Latency (decode phase generation speed at 95th percentile)"
        >
          ITL P95
        </span>
        <div className="telemetry-value-pair">
          <strong className="telemetry-number">{itlP95}</strong>
          <span className="telemetry-unit">ms/token</span>
        </div>
      </div>
    </div>
  )
}

type SamplePoint = { time: string; x: number; y: number; val: number; unit: string; delta: string };

const LATENCY_SAMPLES: SamplePoint[] = [
  { time: '14:40:00', x: 0, y: 50, val: 50, unit: 'ms', delta: 'At 50 ms limit' },
  { time: '14:40:08', x: 25, y: 45, val: 45, unit: 'ms', delta: '-5 ms headroom' },
  { time: '14:40:16', x: 50, y: 48, val: 48, unit: 'ms', delta: '-2 ms headroom' },
  { time: '14:40:24', x: 75, y: 32, val: 32, unit: 'ms', delta: '-18 ms headroom' },
  { time: '14:40:32', x: 100, y: 35, val: 35, unit: 'ms', delta: '-15 ms headroom' },
  { time: '14:40:40', x: 125, y: 39, val: 39, unit: 'ms', delta: '-11 ms headroom' },
  { time: '14:40:48', x: 150, y: 30, val: 30, unit: 'ms', delta: '-20 ms headroom' },
  { time: '14:40:56', x: 175, y: 35, val: 35, unit: 'ms', delta: '-15 ms headroom' },
  { time: '14:41:04', x: 200, y: 21, val: 21, unit: 'ms', delta: '-29 ms headroom' },
  { time: '14:41:12', x: 225, y: 27, val: 27, unit: 'ms', delta: '-23 ms headroom' },
  { time: '14:41:20', x: 250, y: 18, val: 18, unit: 'ms', delta: '-32 ms headroom' },
  { time: '14:41:28', x: 275, y: 25, val: 25, unit: 'ms', delta: '-25 ms headroom' },
  { time: '14:41:36', x: 300, y: 19, val: 19, unit: 'ms', delta: '-31 ms headroom' },
  { time: '14:41:44', x: 325, y: 16, val: 16, unit: 'ms', delta: '-34 ms headroom' },
  { time: '14:41:52', x: 350, y: 20, val: 20, unit: 'ms', delta: '-30 ms headroom' },
  { time: '14:42:00', x: 375, y: 13, val: 13, unit: 'ms', delta: '-37 ms headroom' },
];

const THROUGHPUT_SAMPLES: SamplePoint[] = [
  { time: '14:40:00', x: 0, y: 86, val: 43.8, unit: 'k tok/s', delta: '-6.2k vs target' },
  { time: '14:40:08', x: 25, y: 76, val: 46.2, unit: 'k tok/s', delta: '-3.8k vs target' },
  { time: '14:40:16', x: 50, y: 79, val: 45.4, unit: 'k tok/s', delta: '-4.6k vs target' },
  { time: '14:40:24', x: 75, y: 51, val: 52.1, unit: 'k tok/s', delta: '+2.1k above target' },
  { time: '14:40:32', x: 100, y: 59, val: 50.3, unit: 'k tok/s', delta: '+0.3k above target' },
  { time: '14:40:40', x: 125, y: 39, val: 55.4, unit: 'k tok/s', delta: '+5.4k above target' },
  { time: '14:40:48', x: 150, y: 48, val: 53.2, unit: 'k tok/s', delta: '+3.2k above target' },
  { time: '14:40:56', x: 175, y: 33, val: 56.8, unit: 'k tok/s', delta: '+6.8k above target' },
  { time: '14:41:04', x: 200, y: 43, val: 54.4, unit: 'k tok/s', delta: '+4.4k above target' },
  { time: '14:41:12', x: 225, y: 21, val: 59.8, unit: 'k tok/s', delta: '+9.8k above target' },
  { time: '14:41:20', x: 250, y: 28, val: 58.1, unit: 'k tok/s', delta: '+8.1k above target' },
  { time: '14:41:28', x: 275, y: 14, val: 61.4, unit: 'k tok/s', delta: '+11.4k above target' },
  { time: '14:41:36', x: 300, y: 22, val: 59.5, unit: 'k tok/s', delta: '+9.5k above target' },
  { time: '14:41:44', x: 325, y: 12, val: 62.0, unit: 'k tok/s', delta: '+12.0k above target' },
  { time: '14:41:52', x: 350, y: 18, val: 60.5, unit: 'k tok/s', delta: '+10.5k above target' },
  { time: '14:42:00', x: 375, y: 8, val: 61.8, unit: 'k tok/s', delta: '+11.8k above target' },
];

const VERIFICATION_SAMPLES: SamplePoint[] = [
  { time: '14:40:00', x: 0, y: 64, val: 52, unit: 'ms', delta: '+2 ms drift' },
  { time: '14:40:08', x: 25, y: 61, val: 53, unit: 'ms', delta: '+3 ms drift' },
  { time: '14:40:16', x: 50, y: 58, val: 54, unit: 'ms', delta: '+4 ms drift' },
  { time: '14:40:24', x: 75, y: 60, val: 53, unit: 'ms', delta: '+3 ms drift' },
  { time: '14:40:32', x: 100, y: 49, val: 56, unit: 'ms', delta: '+6 ms drift (fail)' },
  { time: '14:40:40', x: 125, y: 52, val: 55, unit: 'ms', delta: '+5 ms drift' },
  { time: '14:40:48', x: 150, y: 45, val: 57, unit: 'ms', delta: '+7 ms drift (fail)' },
  { time: '14:40:56', x: 175, y: 43, val: 57, unit: 'ms', delta: '+7 ms drift (fail)' },
  { time: '14:41:04', x: 200, y: 47, val: 56, unit: 'ms', delta: '+6 ms drift (fail)' },
  { time: '14:41:12', x: 225, y: 40, val: 58, unit: 'ms', delta: '+8 ms drift (fail)' },
  { time: '14:41:20', x: 250, y: 43, val: 57, unit: 'ms', delta: '+7 ms drift (fail)' },
  { time: '14:41:28', x: 275, y: 35, val: 59, unit: 'ms', delta: '+9 ms drift (fail)' },
  { time: '14:41:36', x: 300, y: 38, val: 58, unit: 'ms', delta: '+8 ms drift (fail)' },
  { time: '14:41:44', x: 325, y: 34, val: 59, unit: 'ms', delta: '+9 ms drift (fail)' },
  { time: '14:41:52', x: 350, y: 31, val: 60, unit: 'ms', delta: '+10 ms drift (fail)' },
  { time: '14:42:00', x: 375, y: 32, val: 58, unit: 'ms', delta: '+11 ms drift (fail)' },
];

function LineChart({ variant = 'latency', compact = false, paused = false }: { variant?: 'latency' | 'throughput' | 'verification'; compact?: boolean; paused?: boolean }) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const samples = variant === 'throughput' ? THROUGHPUT_SAMPLES : variant === 'verification' ? VERIFICATION_SAMPLES : LATENCY_SAMPLES;
  const points = samples.map(s => `${s.x},${s.y}`).join(' ');

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const sampleX = relX * 380;
    const idx = Math.max(0, Math.min(samples.length - 1, Math.round(sampleX / 25)));
    setHoverIndex(idx);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setHoverIndex(prev => (prev === null ? samples.length - 1 : Math.max(0, prev - 1)));
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      setHoverIndex(prev => (prev === null ? 0 : Math.min(samples.length - 1, prev + 1)));
    } else if (e.key === 'Home') {
      e.preventDefault();
      setHoverIndex(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      setHoverIndex(samples.length - 1);
    } else if (e.key === 'Escape') {
      setHoverIndex(null);
    }
  };

  const activeSample = hoverIndex !== null ? samples[hoverIndex] : null;

  return (
    <div
      className={`chart-wrap ${compact ? 'chart-compact' : ''} ${paused ? 'chart-paused' : ''}`}
      tabIndex={0}
      role="region"
      aria-label={`${variant} telemetry time series. Use arrow keys to scrub discrete sample measurements.`}
      onKeyDown={handleKeyDown}
      onBlur={() => setHoverIndex(null)}
    >
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {activeSample ? `${variant} measurement at ${activeSample.time}: ${activeSample.val} ${activeSample.unit}, ${activeSample.delta}` : ''}
      </div>
      <svg
        viewBox="0 0 395 112"
        preserveAspectRatio="none"
        role="img"
        aria-label={`${variant} deterministic demo time series`}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverIndex(null)}
        onTouchStart={(e) => {
          if (e.touches[0]) {
            const rect = e.currentTarget.getBoundingClientRect();
            const relX = Math.max(0, Math.min(1, (e.touches[0].clientX - rect.left) / rect.width));
            const idx = Math.max(0, Math.min(samples.length - 1, Math.round((relX * 380) / 25)));
            setHoverIndex(idx);
          }
        }}
        onTouchMove={(e) => {
          if (e.touches[0]) {
            const rect = e.currentTarget.getBoundingClientRect();
            const relX = Math.max(0, Math.min(1, (e.touches[0].clientX - rect.left) / rect.width));
            const idx = Math.max(0, Math.min(samples.length - 1, Math.round((relX * 380) / 25)));
            setHoverIndex(idx);
          }
        }}
        onTouchEnd={() => setHoverIndex(null)}
      >
        {[18, 42, 66, 90].map(y => (
          <line key={y} x1="0" y1={y} x2="395" y2={y} className="chart-grid" />
        ))}
        {variant === 'latency' && (
          <>
            <line x1="0" y1="38" x2="395" y2="38" className="chart-threshold" />
            <text x="390" y="32" textAnchor="end" className="chart-label">50 ms SLO</text>
          </>
        )}
        <polyline points={points} transform="translate(5 9)" className="chart-line" />
        {activeSample ? (
          <>
            <line
              x1={activeSample.x + 5}
              y1="0"
              x2={activeSample.x + 5}
              y2="105"
              className="chart-crosshair"
            />
            <circle
              cx={activeSample.x + 5}
              cy={activeSample.y + 9}
              r="4.5"
              className="chart-inspect-dot"
            />
          </>
        ) : (
          <circle
            cx="385"
            cy={variant === 'throughput' ? 17 : variant === 'verification' ? 41 : 22}
            r="3"
            className="chart-end"
          />
        )}
      </svg>
      {activeSample && (
        <div
          className="chart-hud"
          style={{
            left: `${Math.max(16, Math.min(84, ((activeSample.x + 5) / 390) * 100))}%`,
          }}
        >
          <span>{activeSample.time}</span>
          <strong>{activeSample.val} {activeSample.unit}</strong>
          <span>({activeSample.delta})</span>
        </div>
      )}
      <div className="chart-axis">
        <span>14:40:00</span>
        <span>14:40:30</span>
        <span>14:41:00</span>
        <span>14:41:30</span>
        <span>14:42:00</span>
      </div>
    </div>
  );
}

function ParetoFrontier({
  candidates,
  selectedId,
  onSelect,
  p95Ceiling,
  minThroughput,
}: {
  candidates: Candidate[];
  selectedId: string;
  onSelect: (id: string) => void;
  p95Ceiling: number;
  minThroughput: number;
}) {
  const [hoveredCandidate, setHoveredCandidate] = useState<Candidate | null>(null);

  const minX = 20, maxX = 80;
  const minY = 15, maxY = 85;
  const svgWidth = 420, svgHeight = 160;
  const padL = 48, padR = 24, padT = 20, padB = 30;
  const plotW = svgWidth - padL - padR;
  const plotH = svgHeight - padT - padB;

  const toX = (p95: number) => padL + Math.max(0, Math.min(plotW, ((p95 - minX) / (maxX - minX)) * plotW));
  const toY = (tput: number) => padT + plotH - Math.max(0, Math.min(plotH, ((tput - minY) / (maxY - minY)) * plotH));

  const ceilingX = toX(p95Ceiling);
  const floorY = toY(minThroughput);

  return (
    <section className="pareto-card panel">
      <div className="pareto-header">
        <div>
          <div className="eyebrow">TRADE-OFF ENVELOPE</div>
          <h3>2D Pareto Frontier Visualizer</h3>
          <p>Interactive multi-objective trade-off: Output throughput vs. P95 latency ceiling.</p>
        </div>
        <div className="pareto-legend">
          <span className="legend-feasible"><i /> Feasible Zone</span>
          <span className="legend-winner"><i /> Winner (C-02)</span>
          <span className="legend-infeasible"><i /> Infeasible</span>
        </div>
      </div>

      <div className="pareto-plot-wrap">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="pareto-svg"
          role="img"
          aria-label="2D Pareto frontier chart. Output throughput versus P95 latency for all 4 candidate configurations."
        >
          {/* Feasible Zone Shading (X <= ceilingX, Y <= floorY) */}
          <rect
            x={padL}
            y={padT}
            width={Math.max(0, ceilingX - padL)}
            height={Math.max(0, floorY - padT)}
            className="pareto-zone-feasible"
          />

          {/* Grid lines */}
          {[30, 45, 60, 75].map(lat => (
            <line key={`gx-${lat}`} x1={toX(lat)} y1={padT} x2={toX(lat)} y2={padT + plotH} className="pareto-grid-line" />
          ))}
          {[30, 50, 70].map(tput => (
            <line key={`gy-${tput}`} x1={padL} y1={toY(tput)} x2={padL + plotW} y2={toY(tput)} className="pareto-grid-line" />
          ))}

          {/* Hard SLO Ceiling Line (Vertical) */}
          <line x1={ceilingX} y1={padT} x2={ceilingX} y2={padT + plotH} className="pareto-threshold-x" />
          <text x={ceilingX - 4} y={padT + 12} textAnchor="end" className="pareto-threshold-label">
            SLO ≤ {p95Ceiling} ms
          </text>

          {/* Minimum Throughput Floor Line (Horizontal) */}
          <line x1={padL} y1={floorY} x2={padL + plotW} y2={floorY} className="pareto-threshold-y" />
          <text x={padL + plotW - 4} y={floorY - 4} textAnchor="end" className="pareto-threshold-label">
            FLOOR ≥ {minThroughput}k tok/s
          </text>

          {/* Axis titles */}
          <text x={padL + plotW / 2} y={svgHeight - 6} textAnchor="middle" className="pareto-axis-title">
            P95 LATENCY (ms) → LOWER IS BETTER
          </text>
          <text x={12} y={padT + plotH / 2} textAnchor="middle" transform={`rotate(-90 12 ${padT + plotH / 2})`} className="pareto-axis-title">
            THROUGHPUT (k tok/s) ↑ HIGHER IS BETTER
          </text>

          {/* X Axis ticks */}
          {[20, 35, 50, 65, 80].map(val => (
            <text key={`tx-${val}`} x={toX(val)} y={padT + plotH + 16} textAnchor="middle" className="pareto-tick">
              {val}ms
            </text>
          ))}

          {/* Candidate Points */}
          {candidates.map(c => {
            const cx = toX(c.p95);
            const cy = toY(c.throughput);
            const isSelected = selectedId === c.id;
            const isFeasible = c.feasible;

            return (
              <g
                key={c.id}
                className={`pareto-node ${isSelected ? 'is-selected' : ''} ${isFeasible ? 'is-feasible' : 'is-infeasible'}`}
                tabIndex={0}
                role="button"
                aria-label={`Candidate ${c.id}: ${c.name}, P95 ${c.p95} ms, Throughput ${c.throughput}k tokens per second. Status: ${c.feasible ? 'Feasible' : 'Infeasible'}.`}
                onClick={() => onSelect(c.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelect(c.id);
                  }
                }}
                onMouseEnter={() => setHoveredCandidate(c)}
                onMouseLeave={() => setHoveredCandidate(null)}
              >
                {isSelected && (
                  <circle cx={cx} cy={cy} r="12" className="pareto-halo" />
                )}
                <circle cx={cx} cy={cy} r={isSelected ? 6 : 4.5} className="pareto-circle" />
                <text
                  x={cx + (c.id === 'C-04' ? -10 : 8)}
                  y={cy - 6}
                  textAnchor={c.id === 'C-04' ? 'end' : 'start'}
                  className="pareto-point-label"
                >
                  {c.id} {c.tag === 'WINNER' ? '★' : ''}
                </text>
              </g>
            );
          })}
        </svg>

        {hoveredCandidate && (
          <div
            className="pareto-tooltip"
            style={{
              left: `${Math.max(10, Math.min(80, (toX(hoveredCandidate.p95) / svgWidth) * 100))}%`,
              top: `${Math.max(5, (toY(hoveredCandidate.throughput) / svgHeight) * 100 - 32)}%`,
            }}
          >
            <strong>{hoveredCandidate.id} · {hoveredCandidate.name}</strong>
            <span>P95: {hoveredCandidate.p95} ms · {hoveredCandidate.throughput}k tok/s</span>
            <small>{hoveredCandidate.feasible ? 'FEASIBLE CANDIDATE' : hoveredCandidate.reason}</small>
          </div>
        )}
      </div>
    </section>
  );
}

function ProgressBar({ value, tone = 'accent' }: { value: number; tone?: string }) {
  return <div className="progress-track"><div className={`progress-fill fill-${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>;
}

function Button({
  children,
  onClick,
  variant = 'secondary',
  icon,
  disabled = false,
  className = '',
  loading = false,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  icon?: string;
  disabled?: boolean;
  className?: string;
  loading?: boolean;
}) {
  return (
    <button
      className={`btn btn-${variant} ${loading ? 'btn-loading' : ''} ${className}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? (
        <span className="btn-spinner"><Icon name="refresh" size={14} /></span>
      ) : icon ? (
        <Icon name={icon} size={15} />
      ) : null}
      <span>{children}</span>
    </button>
  );
}

function MiniTag({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) { return <span className={`mini-tag mini-${tone}`}>{children}</span>; }

export default function App() {
  const [page, setPage] = useState<Page>('Command Center');
  const [selectedCandidate, setSelectedCandidate] = useState('C-02');
  const [scenario, setScenario] = useState<Scenario>(() => {
    try { return (localStorage.getItem('slokern-scenario') as Scenario) || 'standard'; } catch { return 'standard'; }
  });
  const [toast, setToast] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All statuses');
  const [monitorPaused, setMonitorPaused] = useState(false);
  const [monitorRange, setMonitorRange] = useState('5 minutes');
  const [reportTab, setReportTab] = useState('Overview');
  const [settings, setSettings] = useState(() => {
    try { return { reducedMotion: localStorage.getItem('slokern-reduced-motion') === 'true', compactTables: localStorage.getItem('slokern-compact') === 'true', showAmbient: localStorage.getItem('slokern-ambient') !== 'false' }; } catch { return { reducedMotion: false, compactTables: false, showAmbient: true }; }
  });
  const [builder, setBuilder] = useState({ workload: 'chat-completions-prod', model: 'Llama-3-8B-Instruct', inputRate: 1200, inputTokens: 768, outputTokens: 256, p95: 50, minThroughput: 50, maxError: 0.5, batch: 16, concurrency: 32, kvCache: 'FP8' });
  const [showReview, setShowReview] = useState(false);
  const [demoRunCreated, setDemoRunCreated] = useState(false);
  const [activeRun, setActiveRun] = useState('run_01HZX8F2');
  const [activeRunMeta, setActiveRunMeta] = useState<ExperimentRecord>(BASE_EXPERIMENTS[0]);

  // Micro-interaction states
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  const handleCopyCli = (c: Candidate) => {
    const flags = `vllm serve ${builder.model} --max-num-seqs ${c.concurrency} --max-model-len 4096 --kv-cache-dtype ${c.kvCache.toLowerCase()} --gpu-memory-utilization ${(c.gpu / 100).toFixed(2)}`;
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(flags).then(() => {
        notify(`Copied vLLM serving flags for ${c.id} to clipboard.`);
      }).catch(() => {
        notify(`vLLM flags: ${flags}`);
      });
    } else {
      notify(`vLLM flags: ${flags}`);
    }
  };

  useEffect(() => { try { localStorage.setItem('slokern-scenario', scenario); } catch { /* storage may be unavailable */ } }, [scenario]);
  useEffect(() => { try { localStorage.setItem('slokern-reduced-motion', String(settings.reducedMotion)); localStorage.setItem('slokern-compact', String(settings.compactTables)); localStorage.setItem('slokern-ambient', String(settings.showAmbient)); } catch { /* storage may be unavailable */ } }, [settings]);
  useEffect(() => { if (!toast) return; const id = window.setTimeout(() => setToast(''), 3600); return () => window.clearTimeout(id); }, [toast]);

  // Global keyboard shortcuts (Escape dismisses modal review, toast, search filter)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showReview) {
          setShowReview(false);
        } else if (toast) {
          setToast('');
        } else if (search) {
          setSearch('');
        }
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [showReview, toast, search]);

  const candidates = useMemo(() => {
    const evaluated = BASE_CANDIDATES.map(base => {
      const c = { ...base };
      if (scenario === 'no-feasible' && c.id === 'C-02') c.p95 = 55;
      const violations: string[] = [];
      if (c.p95 > builder.p95) violations.push(`P95 latency ${c.p95} ms exceeds the ${builder.p95} ms ceiling`);
      if (c.throughput < builder.minThroughput) violations.push(`throughput ${c.throughput}k tok/s is below the ${builder.minThroughput}k minimum`);
      if (c.error > builder.maxError) violations.push(`error rate ${c.error}% exceeds the ${builder.maxError}% ceiling`);
      const forcedNoFeasible = scenario === 'no-feasible';
      c.feasible = !forcedNoFeasible && violations.length === 0;
      c.tag = c.feasible ? 'FEASIBLE' : c.id === 'C-01' ? 'BASELINE' : 'INFEASIBLE';
      c.reason = forcedNoFeasible
        ? (violations[0] ?? 'This deterministic edge-case scenario intentionally contains no feasible candidate.')
        : (violations.length ? `${violations[0]}.` : `Meets all hard constraints with ${Math.max(0, builder.p95 - c.p95)} ms P95 headroom.`);
      return c;
    });
    const score = (c: Candidate) => (c.throughput / Math.max(builder.minThroughput, 0.01)) - (c.p95 / Math.max(builder.p95, 0.01)) - (c.error / Math.max(builder.maxError, 0.01));
    return evaluated.sort((a, b) => Number(b.feasible) - Number(a.feasible) || score(b) - score(a) || a.id.localeCompare(b.id));
  }, [scenario, builder.p95, builder.minThroughput, builder.maxError]);

  const evidenceStale = scenario === 'stale-evidence';
  const winner = scenario === 'no-feasible' || evidenceStale ? undefined : candidates.find(c => c.feasible);
  const currentCandidate = candidates.find(c => c.id === selectedCandidate) ?? candidates[0];
  const verificationState = scenario === 'verification-failed' ? 'Failed' : scenario === 'stale-evidence' ? 'Stale' : 'Pending';

  const builderErrors = [
    ...(builder.inputRate <= 0 ? ['Offered request rate must be greater than zero.'] : []),
    ...(builder.inputTokens <= 0 ? ['Mean input tokens must be greater than zero.'] : []),
    ...(builder.outputTokens <= 0 ? ['Mean output tokens must be greater than zero.'] : []),
    ...(builder.p95 <= 0 ? ['P95 latency ceiling must be greater than zero.'] : []),
    ...(builder.minThroughput <= 0 ? ['Minimum throughput must be greater than zero.'] : []),
    ...(builder.maxError < 0 || builder.maxError > 100 ? ['Maximum error rate must be between 0 and 100%.'] : []),
    ...(builder.batch < 1 || builder.batch > 128 ? ['Batch size must be between 1 and 128.'] : []),
    ...(builder.concurrency < 1 || builder.concurrency > 256 ? ['Concurrency must be between 1 and 256.'] : []),
  ];
  const builderValid = builderErrors.length === 0;
  const constraintCandidate = winner ?? candidates.find(c => c.id === selectedCandidate) ?? candidates[0];
  const displayCandidate = evidenceStale ? undefined : winner ?? constraintCandidate;
  const activeRunDetails: ExperimentRecord = activeRunMeta.id === 'EXP-0248'
    ? { ...activeRunMeta, feasibility: evidenceStale ? 'Inconclusive' : winner ? 'Feasible' : 'Infeasible', verification: verificationState, candidateId: winner?.id ?? activeRunMeta.candidateId }
    : activeRunMeta;
  const activeExperimentId = activeRunDetails.id;
  const activeWorkload = activeRunDetails.work;
  const activeModel = activeRunDetails.model;
  const detailCandidate = activeRunDetails.id === 'EXP-0248' || activeRunDetails.id === 'EXP-0249'
    ? candidates.find(c => c.id === activeRunDetails.candidateId) ?? constraintCandidate
    : BASE_CANDIDATES.find(c => c.id === activeRunDetails.candidateId) ?? constraintCandidate;

  const constraintChecks = [
    { name: 'P95 latency', actual: `${constraintCandidate.p95} ms`, limit: `≤ ${builder.p95} ms`, pass: constraintCandidate.p95 <= builder.p95, sub: constraintCandidate.p95 <= builder.p95 ? `${builder.p95 - constraintCandidate.p95} ms headroom` : `${constraintCandidate.p95 - builder.p95} ms over the limit` },
    { name: 'Throughput', actual: `${constraintCandidate.throughput}k`, limit: `≥ ${builder.minThroughput}k tok/s`, pass: constraintCandidate.throughput >= builder.minThroughput, sub: constraintCandidate.throughput >= builder.minThroughput ? `${(constraintCandidate.throughput - builder.minThroughput).toFixed(1)}k above minimum` : `${(builder.minThroughput - constraintCandidate.throughput).toFixed(1)}k below target` },
    { name: 'Error rate', actual: `${constraintCandidate.error.toFixed(2)}%`, limit: `≤ ${builder.maxError}%`, pass: constraintCandidate.error <= builder.maxError, sub: constraintCandidate.error <= builder.maxError ? 'Within policy ceiling' : 'Above hard ceiling' },
  ];

  const experimentRecords = useMemo(() => {
    const records = BASE_EXPERIMENTS.map(record => record.id === 'EXP-0248'
      ? { ...record, feasibility: evidenceStale ? 'Inconclusive' : winner ? 'Feasible' : 'Infeasible', verification: verificationState, updated: 'Just now' }
      : record);
    if (demoRunCreated) records.unshift({ id: 'EXP-0249', run: 'demo_EXP0249', work: builder.workload, model: builder.model, state: 'Completed', feasibility: evidenceStale ? 'Inconclusive' : winner ? 'Feasible' : 'Infeasible', verification: verificationState, updated: 'Just now', candidateId: winner?.id ?? 'C-02' });
    return records;
  }, [demoRunCreated, builder.workload, builder.model, evidenceStale, winner, verificationState]);

  const visibleExperiments = useMemo(() => {
    return experimentRecords.filter(record =>
      `${record.id} ${record.run} ${record.work} ${record.model}`.toLowerCase().includes(search.toLowerCase()) &&
      (statusFilter === 'All statuses' || (statusFilter === 'Needs review' ? record.state === 'Needs review' : record.state === statusFilter))
    );
  }, [experimentRecords, search, statusFilter]);

  const navigate = (next: Page) => { setPage(next); setShowReview(false); };
  const notify = (message: string) => setToast(message);
  const openCandidate = (id: string) => { setSelectedCandidate(id); setPage('Tuning Lab'); };
  const candidateStatusTone = (c: Candidate) => c.feasible ? 'success' : 'danger';

  // Tactile Copy Handler
  const handleCopyId = (id: string) => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(id).catch(() => {});
    }
    setCopiedId(id);
    notify(`Candidate identifier ${id} copied to clipboard.`);
    setTimeout(() => setCopiedId(null), 1800);
  };

  // Tactile Re-evaluate Handler
  const handleReevaluate = () => {
    setIsEvaluating(true);
    setTimeout(() => {
      setIsEvaluating(false);
      notify('Deterministic evaluator rerun complete. Candidate rankings verified.');
    }, 380);
  };

  // Tactile Verification Rerun Handler
  const handleRunVerification = () => {
    setIsVerifying(true);
    setTimeout(() => {
      setIsVerifying(false);
      setScenario('verification-failed');
      notify('Independent verification rerun completed. Drift detected outside tolerance.');
    }, 420);
  };

  // Dossier Export Handler
  const exportReport = () => {
    setIsExporting(true);
    const target = page === 'Run Detail'
      ? (activeRunDetails.id === 'EXP-0248' || activeRunDetails.id === 'EXP-0249' ? candidates.find(c => c.id === activeRunDetails.candidateId) : BASE_CANDIDATES.find(c => c.id === activeRunDetails.candidateId)) ?? currentCandidate
      : winner ?? currentCandidate;
    const body = `SLOKern Engineering Dossier\nGenerated: deterministic frontend demo\n\nWORKLOAD\nName: ${builder.workload}\nModel: ${builder.model}\n\nHARD SLOs\nP95 latency <= ${builder.p95} ms\nThroughput >= ${builder.minThroughput}k tok/s\nError rate <= ${builder.maxError}%\n\nCANDIDATE\nID: ${target.id}\nName: ${target.name}\nP50: ${target.p50} ms | P95: ${target.p95} ms | P99: ${target.p99} ms\nThroughput: ${target.throughput}k tok/s | Error: ${target.error}% | GPU: ${target.gpu}%\nFeasibility: ${target.feasible ? 'Feasible' : 'Infeasible'}\nRationale: ${target.reason}\n\nVERIFICATION\nState: ${verificationState}\nVerification run: ${scenario === 'verification-failed' ? 'verify_01HZX8F9' : 'Not completed in this demo scenario'}\n\nPROVENANCE\nDEMO DATA: deterministic fixture values. No live backend measurement is connected.\nPolicy: slo-prod-03 · Evaluator: v0.4.2\n`;
    const blob = new Blob([body], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'slokern-engineering-dossier.md'; a.click(); URL.revokeObjectURL(url);
    setTimeout(() => {
      setIsExporting(false);
      notify('Engineering dossier exported successfully.');
    }, 400);
  };

  const navButton = (item: typeof NAV[number]) => (
    <button
      key={item.label}
      aria-label={item.navLabel}
      aria-current={page === item.label ? 'page' : undefined}
      className={`nav-item ${page === item.label ? 'nav-active' : ''}`}
      onClick={() => navigate(item.label)}
      title={item.navLabel}
    >
      <Icon name={item.icon} size={17} />
      <span>{item.navLabel}</span>
    </button>
  );

  return (
    <div className={`app ${settings.showAmbient ? 'ambient-on' : 'ambient-off'} ${settings.reducedMotion ? 'reduce-motion' : ''} ${settings.compactTables ? 'compact-tables' : ''}`}>
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true"><span /><span /><span /><span /></div>
          <div className="brand-text"><div>SLO<span>KERN</span></div><small>INFERENCE CONTROL / 01</small></div>
          <button className="sidebar-collapse" aria-label="Collapse sidebar" onClick={() => notify('Navigation is in its full workstation layout.')}><Icon name="menu" size={16} /></button>
        </div>
        <div className="workspace-switcher">
          <div className="workspace-avatar">S</div>
          <div className="workspace-copy"><strong>Inference Lab</strong><small>Research workspace</small></div>
          <Icon name="chevron" size={14} />
        </div>
        <nav className="primary-nav" aria-label="Primary navigation">
          {['WORKFLOW', 'OBSERVABILITY', 'SYSTEM'].map(section => (
            <div className="nav-section" key={section}>
              <div className="nav-section-label">{section}</div>
              {NAV.filter(n => n.section === section).map(navButton)}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-card">
            <div className="connection-top"><span className="connection-indicator" /><span>DEMO ENVIRONMENT</span></div>
            <div className="connection-copy">Deterministic fixtures active</div>
            <div className="connection-foot"><span>API</span><strong>NOT CONNECTED</strong></div>
          </div>
          <button className="profile-row" onClick={() => notify('Local demo workspace · no external account connected.')}>
            <div className="profile-avatar">RC</div>
            <div><strong>Control Plane</strong><small>Local workspace</small></div>
            <span className="profile-more">···</span>
          </button>
        </div>
      </aside>

      <main className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <Icon name="chevron" size={13} />
            <strong>{page === 'Run Detail' ? 'Run Detail' : NAV.find(item => item.label === page)?.navLabel ?? page}</strong>
          </div>
          <div className="topbar-right">
            <div className="run-context">
              <span className="demo-pip" />
              <span>DEMO RUN</span>
              <strong>EXP-0248</strong>
              <span className="context-sep" />
              <span>llama-3-8b</span>
            </div>
            <div className="topbar-divider" />
            <button className="icon-button" aria-label="Search registry" onClick={() => { setPage('Experiments'); setSearch(''); }}>
              <Icon name="search" size={17} />
            </button>
            <button
              className="icon-button notification-button"
              aria-label="Notifications"
              onClick={() => {
                if (scenario === 'verification-failed') {
                  notify('Alert: Verification drift breach detected (+11 ms vs 5 ms limit).');
                } else if (scenario === 'no-feasible') {
                  notify('Alert: Zero feasible candidates under current SLO ceilings.');
                } else if (evidenceStale) {
                  notify('Alert: Measurement evidence is stale relative to current workload inputs.');
                } else {
                  notify('All caught up. There are no pending system alerts.');
                }
              }}
            >
              <Icon name="bell" size={17} />
              {(scenario === 'verification-failed' || scenario === 'no-feasible' || evidenceStale) && <i />}
            </button>
            <div className="topbar-avatar" title="Rajdeep (Technical Owner)">RC</div>
          </div>
        </header>

        <div className="page-content">
          <div className="demo-banner">
            <span className="demo-symbol"><Icon name="command" size={13} /></span>
            <strong>DEMO DATA</strong>
            <span>Deterministic demonstration data. No live backend measurement is connected.</span>
            <button onClick={() => navigate('Settings')}>Scenario controls <Icon name="arrow" size={12} /></button>
          </div>

          {page === 'Command Center' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">COMMAND CENTER <span className="heading-slash">/</span> EXP-0248</div>
                  <h1>Experiment overview<span className="title-period">.</span></h1>
                  <p>One clear decision, backed by evidence you can inspect.</p>
                </div>
                <div className="heading-actions">
                  <Button icon="file" onClick={() => navigate('Evidence & Reports')}>View report</Button>
                  <Button variant="primary" icon="plus" onClick={() => navigate('Workload & SLO Builder')}>New experiment</Button>
                </div>
              </div>

              <section className="decision-hero panel">
                <div className="hero-left">
                  <div className="hero-label">
                    <span className="hero-mark"><Icon name="activity" size={14} /></span>
                    CURRENT OPTIMIZATION DECISION
                    <span className="hero-live">● DEMO</span>
                  </div>
                  <div className="decision-status">
                    <div className={`decision-check ${evidenceStale ? 'check-stale' : winner ? 'check-good' : 'check-bad'}`}>
                      {winner ? <Icon name="check" size={23} /> : <Icon name="alert" size={22} />}
                    </div>
                    <div>
                      <h2>{evidenceStale ? 'Decision requires fresh evidence' : winner ? 'Feasible candidate identified' : 'No feasible candidate'}</h2>
                      <p>{evidenceStale ? 'Relevant inputs changed after measurement. Re-run the evaluation before acting on this result.' : winner ? `${winner.id} ${winner.name} satisfies every hard SLO constraint.` : 'No candidate satisfies every hard SLO constraint in this scenario.'}</p>
                    </div>
                  </div>
                  <div className="hero-badges">
                    <Status tone={evidenceStale ? 'warning' : winner ? 'success' : 'danger'}>{evidenceStale ? 'STALE EVIDENCE' : winner ? 'FEASIBLE' : 'INFEASIBLE'}</Status>
                    <Status tone={verificationState === 'Failed' || verificationState === 'Stale' ? 'danger' : 'warning'}>VERIFICATION {verificationState.toUpperCase()}</Status>
                  </div>
                  <div className="decision-reason">
                    <span className="reason-line" />
                    <div>
                      <strong>{evidenceStale ? 'Evidence freshness' : winner ? 'Decision rationale' : 'Decision blocked'}</strong>
                      <p>{evidenceStale ? 'Workload or SLO inputs changed since these measurements were captured. Restore current evidence before accepting the decision.' : winner ? `P95 latency has ${Math.max(0, builder.p95 - winner.p95)} ms headroom. Throughput clears the minimum target by ${(winner.throughput - builder.minThroughput).toFixed(1)}k tok/s, while error rate remains below the defined ceiling.` : 'The current configuration has no feasible candidate. Inspect constraint outcomes before proceeding.'}</p>
                    </div>
                  </div>
                  <div className="hero-actions">
                    <Button variant="primary" icon="activity" onClick={() => navigate('Tuning Lab')}>Inspect candidates</Button>
                    <Button icon="shield" onClick={() => navigate('Verification')}>Open verification <Icon name="arrow" size={13} /></Button>
                    {winner && (
                      <Button icon="copy" onClick={() => handleCopyCli(winner)}>Copy vLLM flags</Button>
                    )}
                  </div>
                </div>

                <div className="hero-right">
                  <div className="decision-orbit">
                    <div className="orbit-center">
                      <div className="orbit-center-top">
                        <span>TOP CANDIDATE</span>
                        <Status tone={winner ? 'success' : 'danger'}>{winner ? 'FEASIBLE' : 'NONE'}</Status>
                      </div>
                      <strong className="orbit-candidate-id">{winner?.id ?? '—'}</strong>
                      <small>{winner ? `${winner.name} · b${winner.batch}_c${winner.concurrency} (${winner.kvCache})` : 'No feasible winner'}</small>
                      {winner && (
                        <LatencyInstruments ttftP95={winner.ttftP95} itlP95={winner.itlP95} />
                      )}
                    </div>
                  </div>
                  <div className="hero-right-foot">
                    <div><span>RANKED CANDIDATES</span><strong>04</strong></div>
                    <div><span>POLICY VERSION</span><strong>v0.4.2</strong></div>
                  </div>
                </div>
              </section>

              <div className="metric-grid four">
                <MetricCard label="P95 LATENCY" value={displayCandidate ? String(displayCandidate.p95) : '—'} unit="ms" delta={evidenceStale ? 'Evidence stale' : winner ? '−21 ms vs baseline' : 'No feasible result'} tone={winner ? 'positive' : 'negative'} icon="clock" />
                <MetricCard label="THROUGHPUT" value={displayCandidate ? displayCandidate.throughput.toFixed(1) : '—'} unit="k tok/s" delta={evidenceStale ? 'Evidence stale' : winner ? '+41.1% vs baseline' : 'Constraint unmet'} tone={winner ? 'positive' : 'negative'} icon="chart" />
                <MetricCard label="ERROR RATE" value={displayCandidate ? displayCandidate.error.toFixed(2) : '—'} unit="%" delta={evidenceStale ? 'Evidence stale' : winner ? 'Within defined ceiling' : 'Inspect constraint violations'} tone={winner ? 'positive' : 'negative'} icon="shield" />
                <MetricCard label="GPU UTILIZATION" value={displayCandidate ? String(displayCandidate.gpu) : '—'} unit="%" delta="Illustrative fixture value" tone="neutral" icon="cpu" />
              </div>

              <div className="two-column-grid overview-grid">
                <section className="panel chart-panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">MEASUREMENT WINDOW</div>
                      <h3>Latency profile <span className="subtle-inline">/ P95</span></h3>
                    </div>
                    <div className="panel-header-right">
                      <Status tone="info">SIMULATED</Status>
                      <button className="small-select" onClick={() => setMonitorRange(monitorRange === '5 minutes' ? '15 minutes' : '5 minutes')}>
                        {monitorRange} ⌄
                      </button>
                    </div>
                  </div>
                  <div className="chart-legend">
                    <span><i className="legend-primary" /> P95 latency</span>
                    <span><i className="legend-dash" /> Hard SLO · {builder.p95} ms</span>
                  </div>
                  <LineChart variant="latency" />
                  <div className="chart-foot">
                    <span><i className="foot-dot" /> Sample stream simulated</span>
                    <span>Last sample <strong>14:42:18.204</strong></span>
                  </div>
                </section>

                <section className="panel candidate-summary">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">RANKING ENGINE</div>
                      <h3>Candidate outcomes</h3>
                    </div>
                    <button className="text-button" onClick={() => navigate('Tuning Lab')}>View all <Icon name="arrow" size={13} /></button>
                  </div>
                  <div className="rank-list">
                    {candidates.slice(0, 3).map((c, i) => (
                      <div
                        role="button"
                        tabIndex={0}
                        className={`rank-row ${c.id === selectedCandidate ? 'rank-selected' : ''}`}
                        key={c.id}
                        onClick={() => openCandidate(c.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            openCandidate(c.id);
                          }
                        }}
                      >
                        <span className={`rank-number ${i === 0 && c.feasible ? 'rank-winner' : ''}`}>{String(i + 1).padStart(2, '0')}</span>
                        <span className="rank-name">
                          <strong>{c.name}</strong>
                          <small>{c.id} · {c.batch} batch / {c.concurrency} concurrency</small>
                        </span>
                        <span className="rank-metric">
                          <strong>{c.p95} <small>ms</small></strong>
                          <small>P95</small>
                        </span>
                        <Status tone={candidateStatusTone(c)}>{c.feasible ? 'Feasible' : 'Infeasible'}</Status>
                        <Icon name="chevron" size={14} />
                      </div>
                    ))}
                  </div>
                  <div className="rank-foot">
                    <span>Ranked by deterministic evaluator</span>
                    <span className="mono">EVAL / 04.2</span>
                  </div>
                </section>
              </div>

              <div className="two-column-grid lower-grid">
                <section className="panel constraints-panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">HARD CONSTRAINTS</div>
                      <h3>Service-level objectives</h3>
                    </div>
                    <Status tone={evidenceStale ? 'warning' : winner ? 'success' : 'danger'}>
                      {evidenceStale ? 'EVIDENCE STALE' : winner ? '3 / 3 PASS' : 'CONSTRAINT FAIL'}
                    </Status>
                  </div>
                  <div className="constraint-list">
                    {constraintChecks.map(c => (
                      <div className="constraint-row" key={c.name}>
                        <span className={`constraint-icon ${evidenceStale ? 'constraint-stale' : c.pass ? 'constraint-pass' : 'constraint-fail'}`}>
                          <Icon name={evidenceStale ? 'clock' : c.pass ? 'check' : 'alert'} size={14} />
                        </span>
                        <div className="constraint-copy">
                          <strong>{c.name}</strong>
                          <small>{evidenceStale ? 'Refresh evidence to confirm this outcome' : c.sub}</small>
                        </div>
                        <div className="constraint-values">
                          <strong>{evidenceStale ? '—' : c.actual}</strong>
                          <small>{c.limit}</small>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="panel event-panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">AUDIT TRAIL</div>
                      <h3>Recent events</h3>
                    </div>
                    <button className="text-button" onClick={() => navigate('Evidence & Reports')}>Full evidence <Icon name="arrow" size={13} /></button>
                  </div>
                  <div className="event-list">
                    {EVENTS.slice(0, 3).map((e, i) => (
                      <div className="event-item" key={e.time}>
                        <div className={`event-icon event-${e.type}`}>
                          {e.type === 'success' ? <Icon name="check" size={13} /> : e.type === 'warning' ? <Icon name="alert" size={13} /> : <Icon name="activity" size={13} />}
                        </div>
                        <div className="event-body">
                          <strong>{e.title}</strong>
                          <small>{e.detail}</small>
                        </div>
                        <time>{i === 0 ? 'Now' : i === 1 ? '−00:00:01' : '−00:00:20'}</time>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            </>
          )}

          {page === 'Experiments' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">WORKFLOW / RUN REGISTRY</div>
                  <h1>Experiments<span className="title-period">.</span></h1>
                  <p>Find a run, inspect its state, and resume from the evidence.</p>
                </div>
                <div className="heading-actions">
                  <Button icon="download" loading={isExporting} onClick={exportReport}>Export selected</Button>
                  <Button variant="primary" icon="plus" onClick={() => navigate('Workload & SLO Builder')}>Create experiment</Button>
                </div>
              </div>

              <div className="registry-stats">
                <div><span>ALL EXPERIMENTS</span><strong>12</strong><small>Across 3 workloads</small></div>
                <div><span>COMPLETED</span><strong>08</strong><small className="green-text">Ready for review</small></div>
                <div><span>NEEDS ATTENTION</span><strong>02</strong><small className="amber-text">Evidence or SLO issue</small></div>
                <div><span>ACTIVE NOW</span><strong>01</strong><small>Simulated execution</small></div>
              </div>

              <section className="panel table-panel">
                <div className="table-toolbar">
                  <div className="search-field">
                    <Icon name="search" size={15} />
                    <input
                      aria-label="Search experiments"
                      placeholder="Search by run ID, workload, model…"
                      value={search}
                      onChange={e => setSearch(e.target.value)}
                    />
                    {search && <button aria-label="Clear search" onClick={() => setSearch('')}>×</button>}
                  </div>
                  <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} aria-label="Filter by status">
                    <option>All statuses</option>
                    <option>Completed</option>
                    <option>Running</option>
                    <option>Needs review</option>
                    <option>Failed</option>
                  </select>
                  <button className="filter-button" onClick={() => notify('Showing deterministic demo experiment records.')}>
                    <Icon name="sliders" size={14} /> Filters
                  </button>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>EXPERIMENT / RUN</th>
                        <th>WORKLOAD</th>
                        <th>STATE</th>
                        <th>FEASIBILITY</th>
                        <th>VERIFICATION</th>
                        <th>UPDATED</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {visibleExperiments.map(r => (
                        <tr
                          key={r.id}
                          className="clickable-row"
                          onClick={() => { setActiveRun(r.run); setActiveRunMeta(r); navigate('Run Detail'); }}
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              setActiveRun(r.run);
                              setActiveRunMeta(r);
                              navigate('Run Detail');
                            }
                          }}
                        >
                          <td>
                            <div className="experiment-cell">
                              <span className="experiment-glyph"><Icon name="layers" size={15} /></span>
                              <span><strong>{r.id}</strong><small>{r.run}</small></span>
                            </div>
                          </td>
                          <td><strong className="table-primary">{r.work}</strong><small className="table-secondary">{r.model}</small></td>
                          <td><Status tone={r.state === 'Completed' ? 'success' : r.state === 'Running' ? 'info' : r.state === 'Failed' ? 'danger' : 'warning'}>{r.state}</Status></td>
                          <td><Status tone={r.feasibility === 'Feasible' ? 'success' : r.feasibility === 'Infeasible' ? 'danger' : 'warning'}>{r.feasibility}</Status></td>
                          <td><Status tone={r.verification === 'Verified' ? 'success' : r.verification === 'Failed' || r.verification === 'Stale' ? 'danger' : 'warning'}>{r.verification}</Status></td>
                          <td className="updated-cell">{r.updated}</td>
                          <td><Icon name="chevron" size={15} /></td>
                        </tr>
                      ))}
                      {visibleExperiments.length === 0 && (
                        <tr>
                          <td colSpan={7}>
                            <div className="table-empty">
                              <Icon name="search" size={18} />
                              <strong>No matching experiments</strong>
                              <span>Try another run ID, workload, or status filter.</span>
                              <button onClick={() => { setSearch(''); setStatusFilter('All statuses'); }}>Clear filters</button>
                            </div>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                  {search && <div className="table-search-note">Filtering results for “{search}”</div>}
                </div>
                <div className="table-footer">
                  <span>Showing <strong>{visibleExperiments.length}</strong> of {experimentRecords.length} matching demo records</span>
                  <nav aria-label="Pagination">
                    <button disabled aria-label="Go to previous page">Previous</button>
                    <button className="pagination-active" aria-label="Page 1" aria-current="page">1</button>
                    <button aria-label="Go to page 2" onClick={() => notify('Only the first fixture page is included in this demo.')}>2</button>
                    <button aria-label="Go to next page" onClick={() => notify('Only the first fixture page is included in this demo.')}>Next <Icon name="chevron" size={12} /></button>
                  </nav>
                </div>
              </section>
            </>
          )}

          {page === 'Workload & SLO Builder' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">WORKFLOW / CONFIGURATION</div>
                  <h1>Workload & SLO Builder<span className="title-period">.</span></h1>
                  <p>Define the operating envelope before the evaluator gets a vote.</p>
                </div>
                <div className="heading-actions">
                  <Status tone="info">DRAFT CONFIGURATION</Status>
                </div>
              </div>

              {!showReview ? (
                <div className="builder-layout">
                  <div className="builder-main">
                    <section className="panel form-panel">
                      <div className="form-section-heading">
                        <span className="step-num">01</span>
                        <div>
                          <h3>Workload definition</h3>
                          <p>Identify the traffic shape the serving configuration must sustain.</p>
                        </div>
                        <MiniTag>REQUIRED</MiniTag>
                      </div>
                      <div className="form-grid">
                        <label className="field field-wide">
                          Workload profile <span className="field-note">Named workload under test</span>
                          <select value={builder.workload} onChange={e => setBuilder({ ...builder, workload: e.target.value })}>
                            <option value="chat-completions-prod">chat-completions-prod</option>
                            <option value="summarization-batch">summarization-batch</option>
                            <option value="code-assist-staging">code-assist-staging</option>
                          </select>
                        </label>
                        <label className="field">
                          Offered request rate <span className="unit-label">req/min</span>
                          <input type="number" min="1" value={builder.inputRate} onChange={e => setBuilder({ ...builder, inputRate: Number(e.target.value) })} />
                          <small>Expected request arrival rate</small>
                        </label>
                        <label className="field">
                          Mean input tokens <span className="unit-label">tokens</span>
                          <input type="number" min="1" value={builder.inputTokens} onChange={e => setBuilder({ ...builder, inputTokens: Number(e.target.value) })} />
                          <small>Prompt length estimate</small>
                        </label>
                        <label className="field">
                          Mean output tokens <span className="unit-label">tokens</span>
                          <input type="number" min="1" value={builder.outputTokens} onChange={e => setBuilder({ ...builder, outputTokens: Number(e.target.value) })} />
                          <small>Generated response estimate</small>
                        </label>
                      </div>
                    </section>

                    <section className="panel form-panel">
                      <div className="form-section-heading">
                        <span className="step-num">02</span>
                        <div>
                          <h3>Model & serving configuration</h3>
                          <p>Choose the runtime profile and candidate settings to measure.</p>
                        </div>
                      </div>
                      <div className="form-grid">
                        <label className="field field-wide">
                          Model <span className="field-note">Demo model registry</span>
                          <select value={builder.model} onChange={e => setBuilder({ ...builder, model: e.target.value })}>
                            <option>Llama-3-8B-Instruct</option>
                            <option>Qwen2.5-7B-Instruct</option>
                            <option>Mistral-7B-Instruct-v0.3</option>
                          </select>
                        </label>
                        <label className="field">
                          Max batch size
                          <input type="number" min="1" max="128" value={builder.batch} onChange={e => setBuilder({ ...builder, batch: Number(e.target.value) })} />
                          <small>Upper bound for batch formation</small>
                        </label>
                        <label className="field">
                          Max concurrency
                          <input type="number" min="1" max="256" value={builder.concurrency} onChange={e => setBuilder({ ...builder, concurrency: Number(e.target.value) })} />
                          <small>Concurrent in-flight requests</small>
                        </label>
                        <label className="field">
                          KV cache precision
                          <select value={builder.kvCache} onChange={e => setBuilder({ ...builder, kvCache: e.target.value })}>
                            <option>FP16</option>
                            <option>FP8</option>
                            <option>INT8</option>
                          </select>
                          <small>Runtime memory / precision trade-off</small>
                        </label>
                      </div>
                    </section>

                    <section className="panel form-panel">
                      <div className="form-section-heading">
                        <span className="step-num">03</span>
                        <div>
                          <h3>Hard service-level objectives</h3>
                          <p>These are constraints, not aspirational dashboard targets.</p>
                        </div>
                        <MiniTag tone="accent">HARD LIMITS</MiniTag>
                      </div>
                      <div className="form-grid">
                        <label className="field">
                          P95 latency ceiling <span className="unit-label">ms</span>
                          <input type="number" min="1" value={builder.p95} onChange={e => setBuilder({ ...builder, p95: Number(e.target.value) })} />
                          <small>Requests beyond this threshold fail</small>
                        </label>
                        <label className="field">
                          Minimum throughput <span className="unit-label">k tok/s</span>
                          <input type="number" min="1" value={builder.minThroughput} onChange={e => setBuilder({ ...builder, minThroughput: Number(e.target.value) })} />
                          <small>Minimum sustained token rate</small>
                        </label>
                        <label className="field">
                          Maximum error rate <span className="unit-label">%</span>
                          <input type="number" min="0" max="100" step="0.01" value={builder.maxError} onChange={e => setBuilder({ ...builder, maxError: Number(e.target.value) })} />
                          <small>Failed requests as a percentage</small>
                        </label>
                      </div>
                    </section>

                    <div className="builder-bottom-actions">
                      <Button
                        onClick={() => {
                          if (!confirmReset) {
                            setConfirmReset(true);
                            notify('Click "Confirm Reset" to restore default demo parameters.');
                            setTimeout(() => setConfirmReset(false), 4000);
                          } else {
                            setBuilder({ workload: 'chat-completions-prod', model: 'Llama-3-8B-Instruct', inputRate: 1200, inputTokens: 768, outputTokens: 256, p95: 50, minThroughput: 50, maxError: 0.5, batch: 16, concurrency: 32, kvCache: 'FP8' });
                            setConfirmReset(false);
                            notify('Builder fields reset to recommended demo defaults.');
                          }
                        }}
                        icon="refresh"
                      >
                        {confirmReset ? 'Confirm Reset' : 'Reset fields'}
                      </Button>
                      <Button
                        variant="primary"
                        icon="arrow"
                        onClick={() => {
                          if (builderValid) {
                            setShowReview(true);
                          } else {
                            notify('Fix the blocking builder errors before review.');
                          }
                        }}
                      >
                        Validate & review
                      </Button>
                    </div>
                  </div>

                  <aside className="builder-aside">
                    <section className="panel validation-panel">
                      <div className="panel-header">
                        <div>
                          <div className="eyebrow">VALIDATION SUMMARY</div>
                          <h3>Pre-flight check</h3>
                        </div>
                        <Status tone={builderValid ? 'success' : 'danger'}>{builderValid ? 'Ready to review' : 'Blocking errors'}</Status>
                      </div>
                      <div className="validation-list">
                        <div className="validation-item">
                          <span className="validation-check"><Icon name="check" size={13} /></span>
                          <span><strong>Required fields</strong><small>Workload and model selected</small></span>
                        </div>
                        <div className="validation-item">
                          <span className="validation-check"><Icon name="check" size={13} /></span>
                          <span><strong>Numeric constraints</strong><small>Hard SLOs are explicitly defined</small></span>
                        </div>
                        <div className="validation-item">
                          <span className={builder.batch > 0 && builder.concurrency > 0 ? 'validation-check' : 'validation-fail'}>
                            <Icon name={builder.batch > 0 && builder.concurrency > 0 ? 'check' : 'alert'} size={13} />
                          </span>
                          <span>
                            <strong>Serving settings</strong>
                            <small>{builder.batch > 0 && builder.concurrency > 0 ? 'Batch and concurrency bounds valid' : 'Must be greater than zero'}</small>
                          </span>
                        </div>
                      </div>
                      {!builderValid && (
                        <div className="blocking-summary" role="alert">
                          <strong>Blocking errors · {builderErrors.length}</strong>
                          <ul>
                            {builderErrors.map(error => <li key={error}>{error}</li>)}
                          </ul>
                        </div>
                      )}
                      <div className="validation-note">
                        <Icon name="alert" size={15} />
                        <p>Frontend validation is a convenience layer. An integrated backend must validate this configuration independently.</p>
                      </div>
                    </section>

                    <section className="panel config-summary">
                      <div className="eyebrow">EFFECTIVE CONFIGURATION</div>
                      <h3>Request envelope</h3>
                      <div className="config-line">
                        <span>Approx. input volume</span>
                        <strong>{(builder.inputRate * builder.inputTokens / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 })}k tok/min</strong>
                      </div>
                      <div className="config-line">
                        <span>Batch / concurrency</span>
                        <strong>{builder.batch} / {builder.concurrency}</strong>
                      </div>
                      <div className="config-line">
                        <span>KV cache</span>
                        <strong>{builder.kvCache}</strong>
                      </div>
                      <div className="config-line">
                        <span>Model precision</span>
                        <strong>Fixture profile</strong>
                      </div>
                    </section>

                    <div className="trust-note">
                      <Icon name="shield" size={16} />
                      <span><strong>Decision integrity</strong> A candidate only wins if it satisfies every hard constraint. No feasible candidate is not a successful outcome.</span>
                    </div>
                  </aside>
                </div>
              ) : (
                <section className="panel review-panel">
                  <div className="review-success-icon"><Icon name="check" size={24} /></div>
                  <div className="eyebrow">REVIEW & LAUNCH</div>
                  <h2>Configuration is ready for review.</h2>
                  <p>This frontend can run a deterministic demonstration only. Launching creates a demo run record, not a real inference job.</p>
                  <div className="review-summary-grid">
                    <div><span>WORKLOAD</span><strong>{builder.workload}</strong></div>
                    <div><span>MODEL</span><strong>{builder.model}</strong></div>
                    <div><span>HARD SLO / P95</span><strong>≤ {builder.p95} ms</strong></div>
                    <div><span>THROUGHPUT FLOOR</span><strong>≥ {builder.minThroughput}k tok/s</strong></div>
                    <div><span>MAX ERROR RATE</span><strong>≤ {builder.maxError}%</strong></div>
                    <div><span>SERVING PROFILE</span><strong>Batch {builder.batch} / Concurrency {builder.concurrency} / {builder.kvCache}</strong></div>
                  </div>
                  <div className="review-actions">
                    <Button onClick={() => setShowReview(false)}>Back to edit</Button>
                    <Button
                      variant="primary"
                      icon="play"
                      onClick={() => {
                        setActiveRun('demo_EXP0249');
                        setDemoRunCreated(true);
                        setScenario('standard');
                        setActiveRunMeta({
                          id: 'EXP-0249',
                          run: 'demo_EXP0249',
                          work: builder.workload,
                          model: builder.model,
                          state: 'Completed',
                          feasibility: 'Feasible',
                          verification: 'Pending',
                          updated: 'Just now',
                          candidateId: 'C-02',
                        });
                        setShowReview(false);
                        setPage('Experiments');
                        notify('Demo experiment record created. No backend job was submitted.');
                      }}
                    >
                      Launch demo run
                    </Button>
                  </div>
                </section>
              )}
            </>
          )}

          {page === 'Tuning Lab' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">WORKFLOW / SEARCH SPACE</div>
                  <h1>Tuning Lab<span className="title-period">.</span></h1>
                  <p>Compare candidates without hiding the constraints that decide the winner.</p>
                </div>
                <div className="heading-actions">
                  <Status tone="info">4 CANDIDATES</Status>
                  {evidenceStale && <Status tone="danger">EVIDENCE STALE</Status>}
                  <Button
                    variant="primary"
                    icon="refresh"
                    loading={isEvaluating}
                    onClick={handleReevaluate}
                  >
                    {isEvaluating ? 'Evaluating...' : 'Re-evaluate'}
                  </Button>
                </div>
              </div>

              <div className="tuning-toolbar">
                <div className="toolbar-context">
                  <span className="toolbar-icon"><Icon name="layers" size={16} /></span>
                  <span><strong>EXP-0248 · Candidate matrix</strong><small>Evaluator v0.4.2 · Policy slo-prod-03</small></span>
                </div>
                <div className="toolbar-chips">
                  <span><i className="dot-pass" /> Feasible</span>
                  <span><i className="dot-fail" /> Infeasible</span>
                  <span><i className="dot-muted" /> Baseline</span>
                </div>
              </div>

              <ParetoFrontier
                candidates={candidates}
                selectedId={selectedCandidate}
                onSelect={setSelectedCandidate}
                p95Ceiling={builder.p95}
                minThroughput={builder.minThroughput}
              />

              <div className="tuning-layout">
                <div className="candidate-matrix">
                  {candidates.map((c, i) => (
                    <div
                      key={c.id}
                      role="button"
                      tabIndex={0}
                      aria-pressed={selectedCandidate === c.id}
                      className={`candidate-card ${c.id === selectedCandidate ? 'candidate-selected' : ''} ${c.feasible ? 'candidate-feasible' : ''} ${isEvaluating ? 'candidate-evaluating' : ''}`}
                      onClick={() => setSelectedCandidate(c.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelectedCandidate(c.id);
                        }
                      }}
                    >
                      <div className="candidate-card-top">
                        <span className="candidate-id">{c.id} <span>/{String(i + 1).padStart(2, '0')}</span></span>
                        <span className={`candidate-chip ${c.feasible ? 'chip-feasible' : c.id === 'C-01' ? 'chip-baseline' : 'chip-infeasible'}`}>
                          {c.feasible ? 'FEASIBLE' : c.id === 'C-01' ? 'BASELINE' : 'INFEASIBLE'}
                        </span>
                      </div>
                      <div className="candidate-title-row">
                        <div>
                          <h3>{c.name}</h3>
                          <p>{c.subtitle}</p>
                        </div>
                        {c.feasible && (
                          <span className="winner-emblem" title="Top Feasible Candidate">
                            <Icon name="check" size={17} />
                          </span>
                        )}
                      </div>
                      <div className="candidate-primary-metric">
                        <div>
                          <span>P95 LATENCY</span>
                          <strong>{c.p95}<small>ms</small></strong>
                        </div>
                        <div className="metric-secondary">
                          <span>THROUGHPUT</span>
                          <strong>{c.throughput}<small>k tok/s</small></strong>
                        </div>
                      </div>
                      <div className="candidate-telemetry-split">
                        <LatencyInstruments ttftP95={c.ttftP95} itlP95={c.itlP95} compact />
                      </div>
                      <div className="candidate-mini-chart">
                        <div className="mini-chart-line" style={{ height: `${Math.max(23, 85 - c.p95)}%` }} />
                        <div className="mini-chart-line" style={{ height: `${Math.max(23, 90 - c.p95 + 12)}%` }} />
                        <div className="mini-chart-line" style={{ height: `${Math.max(23, 77 - c.p95 + 22)}%` }} />
                        <div className="mini-chart-line" style={{ height: `${Math.max(23, 95 - c.p95 + 5)}%` }} />
                        <div className="mini-chart-line" style={{ height: `${Math.max(23, 70 - c.p95 + 30)}%` }} />
                        <div className="mini-chart-line" style={{ height: `${Math.max(23, 88 - c.p95 + 14)}%` }} />
                        <div className="mini-chart-line" style={{ height: `${Math.max(23, 80 - c.p95 + 20)}%` }} />
                        <div className="mini-chart-line" style={{ height: `${Math.max(23, 92 - c.p95 + 8)}%` }} />
                      </div>
                      <div className="candidate-meta">
                        <span>Batch <strong>{c.batch}</strong></span>
                        <span>Concurrency <strong>{c.concurrency}</strong></span>
                        <span>KV <strong>{c.kvCache}</strong></span>
                      </div>
                      <div className="candidate-reason">
                        <span className={`reason-icon ${c.feasible ? 'reason-icon-pass' : 'reason-icon-fail'}`}>
                          <Icon name={c.feasible ? 'check' : 'alert'} size={13} />
                        </span>
                        {scenario === 'no-feasible' && c.id === 'C-02' ? 'P95 latency 55 ms breaches the hard limit.' : c.reason}
                      </div>
                    </div>
                  ))}
                </div>

                <aside className="panel candidate-inspector">
                  <div className="inspector-header">
                    <div>
                      <div className="eyebrow">CANDIDATE INSPECTOR</div>
                      <h3>{currentCandidate.name}</h3>
                      <p className="mono">{currentCandidate.id} · EXP-0248</p>
                    </div>
                    <button
                      className={`icon-button ${copiedId === currentCandidate.id ? 'button-copied' : ''}`}
                      aria-label={copiedId === currentCandidate.id ? 'Copied to clipboard' : 'Copy candidate ID'}
                      title={copiedId === currentCandidate.id ? 'Copied!' : 'Copy candidate ID'}
                      onClick={() => handleCopyId(currentCandidate.id)}
                    >
                      <Icon name={copiedId === currentCandidate.id ? 'check' : 'copy'} size={15} />
                      {copiedId === currentCandidate.id && <span className="micro-tooltip">Copied</span>}
                    </button>
                  </div>
                  <Status tone={currentCandidate.feasible ? 'success' : 'danger'}>
                    {currentCandidate.feasible ? 'Feasible' : 'Infeasible'}
                  </Status>
                  <p className={`inspector-reason ${currentCandidate.feasible ? 'is-feasible' : 'is-infeasible'}`}>
                    {currentCandidate.reason}
                  </p>
                  <div className="inspector-metrics">
                    <div><span>TTFT P95</span><strong className="inspector-value-pair">{currentCandidate.ttftP95}<small>ms</small></strong></div>
                    <div><span>ITL P95</span><strong className="inspector-value-pair">{currentCandidate.itlP95}<small>ms/token</small></strong></div>
                    <div><span>P50 LATENCY</span><strong>{currentCandidate.p50}<small>ms</small></strong></div>
                    <div><span>P95 LATENCY</span><strong>{currentCandidate.p95}<small>ms</small></strong></div>
                    <div><span>THROUGHPUT</span><strong>{currentCandidate.throughput}<small>k</small></strong></div>
                    <div><span>ERROR RATE</span><strong>{currentCandidate.error.toFixed(2)}<small>%</small></strong></div>
                  </div>
                  <div className="inspector-divider" />
                  <div className="eyebrow">EFFECTIVE SETTINGS</div>
                  <div className="config-line"><span>Max batch size</span><strong>{currentCandidate.batch}</strong></div>
                  <div className="config-line"><span>Concurrency</span><strong>{currentCandidate.concurrency}</strong></div>
                  <div className="config-line"><span>KV cache precision</span><strong>{currentCandidate.kvCache}</strong></div>
                  <div className="inspector-slo">
                    <div><span>Hard P95 ceiling</span><strong>{currentCandidate.p95 <= builder.p95 ? 'Within limit' : `+${currentCandidate.p95 - builder.p95} ms over`}</strong></div>
                    <ProgressBar value={Math.min(100, currentCandidate.p95 / builder.p95 * 100)} tone={currentCandidate.p95 <= builder.p95 ? 'green' : 'danger'} />
                  </div>
                  <Button variant="primary" icon="file" className="full-button" onClick={() => { setPage('Evidence & Reports'); setReportTab('Candidate rationale'); }}>
                    Inspect evidence <Icon name="arrow" size={13} />
                  </Button>
                  <Button
                    className="full-button"
                    icon="copy"
                    onClick={() => handleCopyCli(currentCandidate)}
                  >
                    Copy vLLM flags
                  </Button>
                  <Button
                    className="full-button"
                    icon="shield"
                    disabled={!currentCandidate.feasible || evidenceStale}
                    onClick={() => {
                      setSelectedCandidate(currentCandidate.id);
                      setPage('Verification');
                      notify(`Verification review opened for ${currentCandidate.id}.`);
                    }}
                  >
                    {evidenceStale ? 'Verification unavailable: evidence is stale' : currentCandidate.feasible ? 'Prepare independent verification' : 'Verification unavailable: candidate is infeasible'}
                  </Button>
                  <div className="inspector-footnote">Ranking is determined by the evaluator fixture, not card order or visual styling.</div>
                </aside>
              </div>
            </>
          )}

          {page === 'Live Monitor' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">OBSERVABILITY / TELEMETRY</div>
                  <h1>Live Monitor<span className="title-period">.</span></h1>
                  <p>Read the run state and the telemetry state as separate signals.</p>
                </div>
                <div className="heading-actions">
                  <Status tone="info">SIMULATED STREAM</Status>
                  <Button icon={monitorPaused ? 'play' : 'pause'} onClick={() => setMonitorPaused(!monitorPaused)}>
                    {monitorPaused ? 'Resume chart' : 'Pause chart'}
                  </Button>
                </div>
              </div>

              <section className="monitor-run-banner panel">
                <div className="monitor-run-icon"><Icon name="activity" size={20} /></div>
                <div className="monitor-run-detail">
                  <div className="eyebrow">CURRENT RUN / EXP-0248</div>
                  <h3>chat-completions-prod <MiniTag tone="info">DEMO RUN</MiniTag></h3>
                  <p>run_01HZX8F2 · Llama-3-8B-Instruct · 120s measurement window</p>
                </div>
                <div className="monitor-run-progress">
                  <div className="monitor-progress-label"><span>Simulated progress</span><strong>100%</strong></div>
                  <ProgressBar value={100} />
                  <small>Execution complete · telemetry playback {monitorPaused ? 'paused' : 'available'}</small>
                </div>
                <div className="run-state-stamp">
                  <span className="stamp-check"><Icon name="check" size={14} /></span>
                  <span><strong>COMPLETED</strong><small>Execution state</small></span>
                </div>
              </section>

              <div className="metric-grid four monitor-metrics">
                <MetricCard label="P95 LATENCY" value={winner ? String(winner.p95) : '55'} unit="ms" delta={`SLO ≤ ${builder.p95} ms`} tone={winner ? 'positive' : 'negative'} icon="clock" />
                <MetricCard label="THROUGHPUT" value={winner ? winner.throughput.toFixed(1) : '46.1'} unit="k tok/s" delta={`Target ≥ ${builder.minThroughput}k`} tone={winner ? 'positive' : 'negative'} icon="chart" />
                <MetricCard label="ERROR RATE" value={winner ? winner.error.toFixed(2) : '0.64'} unit="%" delta={`Limit ≤ ${builder.maxError}%`} tone={winner ? 'positive' : 'negative'} icon="alert" />
                <MetricCard label="GPU MEMORY" value="18.2" unit="GB" delta="Illustrative fixture value" tone="neutral" icon="cpu" />
              </div>

              <div className="monitor-grid">
                <section className="panel monitor-chart-panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">TIME SERIES / P95</div>
                      <h3>Request latency <span className="subtle-inline">ms</span></h3>
                    </div>
                    <div className="panel-header-right">
                      <Status tone={monitorPaused ? 'warning' : 'info'}>{monitorPaused ? 'PAUSED' : 'PLAYBACK'}</Status>
                      <select className="small-select" value={monitorRange} onChange={e => setMonitorRange(e.target.value)} aria-label="Select monitor range">
                        <option>5 minutes</option>
                        <option>15 minutes</option>
                        <option>1 hour</option>
                      </select>
                    </div>
                  </div>
                  <div className="big-chart-legend">
                    <span><i className="legend-primary" /> P95 latency</span>
                    <span><i className="legend-dash" /> Hard SLO ceiling</span>
                  </div>
                  <LineChart variant="latency" paused={monitorPaused} />
                  <div className="chart-foot">
                    <span>{monitorPaused ? 'Playback paused by user' : 'Simulated points are presented for UI demonstration'}</span>
                    <span>Window <strong>{monitorRange}</strong></span>
                  </div>
                </section>

                <section className="panel monitor-throughput">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">TIME SERIES / OUTPUT</div>
                      <h3>Throughput <span className="subtle-inline">k tok/s</span></h3>
                    </div>
                    <Status tone="info">DEMO</Status>
                  </div>
                  <LineChart variant="throughput" compact paused={monitorPaused} />
                  <div className="throughput-current">
                    <span>Current sustained</span>
                    <strong>{winner ? winner.throughput.toFixed(1) : '46.1'} <small>k tok/s</small></strong>
                  </div>
                  <ProgressBar value={winner ? 77 : 46} tone="green" />
                  <div className="throughput-scale">
                    <span>0</span>
                    <span>Target {builder.minThroughput}k</span>
                    <span>80k</span>
                  </div>
                </section>
              </div>

              <div className="two-column-grid lower-grid">
                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">EVENT STREAM</div>
                      <h3>Chronological events</h3>
                    </div>
                    <Status tone="info">FIXTURE FEED</Status>
                  </div>
                  <div className="event-list monitor-events">
                    {EVENTS.map(e => (
                      <div className="event-item" key={e.time}>
                        <time>{e.time}</time>
                        <div className={`event-icon event-${e.type}`}>
                          <Icon name={e.type === 'success' ? 'check' : e.type === 'warning' ? 'alert' : 'activity'} size={13} />
                        </div>
                        <div className="event-body">
                          <strong>{e.title}</strong>
                          <small>{e.detail}</small>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">STATE INTERPRETATION</div>
                      <h3>Signals are not interchangeable</h3>
                    </div>
                  </div>
                  <div className="signal-list">
                    <div>
                      <Status tone="success">COMPLETED</Status>
                      <span>Execution has reached a terminal state.</span>
                    </div>
                    <div>
                      <Status tone="info">TELEMETRY</Status>
                      <span>Available here as deterministic simulated data.</span>
                    </div>
                    <div>
                      <Status tone={evidenceStale ? 'danger' : 'success'}>{evidenceStale ? 'STALE' : 'EVIDENCE'}</Status>
                      <span>{evidenceStale ? 'Input changes invalidate previous measurements.' : 'Evidence freshness is scoped to the active scenario.'}</span>
                    </div>
                    <div>
                      <Status tone={winner ? 'success' : 'danger'}>SLO {winner ? 'PASS' : 'BREACH'}</Status>
                      <span>Constraint outcome is calculated separately from execution.</span>
                    </div>
                  </div>
                </section>
              </div>
            </>
          )}

          {page === 'Verification' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">OBSERVABILITY / INDEPENDENT RERUN</div>
                  <h1>Verification<span className="title-period">.</span></h1>
                  <p>Feasibility is a candidate property. Verification is a separate experiment.</p>
                </div>
                <div className="heading-actions">
                  <Status tone={verificationState === 'Failed' ? 'danger' : verificationState === 'Stale' ? 'danger' : 'warning'}>
                    {verificationState.toUpperCase()} VERIFICATION
                  </Status>
                  <Button
                    variant="primary"
                    icon="refresh"
                    disabled={!winner || evidenceStale}
                    loading={isVerifying}
                    onClick={handleRunVerification}
                  >
                    {isVerifying ? 'Running rerun...' : 'Run verification demo'}
                  </Button>
                </div>
              </div>

              <div className={`verification-hero panel ${verificationState === 'Failed' ? 'verification-failed' : verificationState === 'Stale' ? 'verification-stale' : ''}`}>
                <div className="verification-mark">
                  {verificationState === 'Failed' ? <Icon name="alert" size={26} /> : verificationState === 'Stale' ? <Icon name="clock" size={25} /> : <Icon name="shield" size={26} />}
                </div>
                <div className="verification-copy">
                  <div className="eyebrow">INDEPENDENT VERIFICATION VERDICT</div>
                  <h2>{verificationState === 'Failed' ? 'Verification failed' : verificationState === 'Stale' ? 'Evidence is stale' : 'Pending independent verification'}</h2>
                  <p>{verificationState === 'Failed' ? 'The verification rerun diverged beyond the configured metric tolerance. The candidate remains feasible from its original measurement, but the claim is not verified.' : verificationState === 'Stale' ? 'Relevant workload or SLO inputs changed after measurement. Existing evidence cannot establish the current decision.' : 'C-02 has passed the feasibility evaluator, but an independent rerun has not been completed in this scenario. No verified claim is made.'}</p>
                  <div className="verification-meta">
                    <span>Candidate <strong>{winner?.id ?? 'C-02'}</strong></span>
                    <span>Verification run <strong>{verificationState === 'Failed' ? 'verify_01HZX8F9' : 'NOT CREATED'}</strong></span>
                    <span>Policy <strong>verify-tolerance-v1</strong></span>
                  </div>
                </div>
                <div className="verification-status-block">
                  <Status tone={verificationState === 'Failed' || verificationState === 'Stale' ? 'danger' : 'warning'}>
                    {verificationState.toUpperCase()}
                  </Status>
                  <small>Independent evidence</small>
                </div>
              </div>

              <SectionTitle eyebrow="REPRODUCIBILITY CHECK" title="Optimization vs. verification" detail="Compare the selected optimization measurements with a distinct rerun. Fixture values are disclosed." right={<MiniTag tone="accent">DEMO DATA</MiniTag>} />

              <div className="comparison-cards">
                <section className="panel comparison-card">
                  <div className="comparison-head">
                    <div className="comparison-icon"><Icon name="activity" size={17} /></div>
                    <div>
                      <h3>Optimization result</h3>
                      <small>run_01HZX8F2</small>
                    </div>
                    <Status tone={winner ? 'success' : 'danger'}>{winner ? 'Feasible' : 'Infeasible'}</Status>
                  </div>
                  <div className="comparison-metrics">
                    <div><span>P95 LATENCY</span><strong>{winner?.p95 ?? 55}<small>ms</small></strong></div>
                    <div><span>THROUGHPUT</span><strong>{winner?.throughput.toFixed(1) ?? '46.1'}<small>k</small></strong></div>
                    <div><span>ERROR RATE</span><strong>{winner?.error.toFixed(2) ?? '0.64'}<small>%</small></strong></div>
                  </div>
                  <div className="comparison-foot">
                    <span>120s measurement window</span>
                    <Status tone="success">INITIAL RUN</Status>
                  </div>
                </section>

                <div className="comparison-arrow">
                  <Icon name="arrow" size={22} />
                  <span>INDEPENDENT RERUN</span>
                </div>

                <section className={`panel comparison-card ${verificationState === 'Failed' ? 'comparison-card-failed' : ''}`}>
                  <div className="comparison-head">
                    <div className="comparison-icon verify-icon"><Icon name="shield" size={17} /></div>
                    <div>
                      <h3>Verification result</h3>
                      <small>{verificationState === 'Failed' ? 'verify_01HZX8F9' : 'Run not available'}</small>
                    </div>
                    <Status tone={verificationState === 'Failed' || verificationState === 'Stale' ? 'danger' : 'warning'}>
                      {verificationState}
                    </Status>
                  </div>
                  <div className="comparison-metrics">
                    <div>
                      <span>P95 LATENCY</span>
                      <strong>{verificationState === 'Failed' ? '58' : '—'}<small>{verificationState === 'Failed' ? 'ms' : ''}</small></strong>
                      <em className={verificationState === 'Failed' ? 'drift-bad' : ''}>{verificationState === 'Failed' ? '+11 ms drift' : 'No measurement'}</em>
                    </div>
                    <div>
                      <span>THROUGHPUT</span>
                      <strong>{verificationState === 'Failed' ? '59.4' : '—'}<small>{verificationState === 'Failed' ? 'k' : ''}</small></strong>
                      <em className={verificationState === 'Failed' ? 'drift-bad' : ''}>{verificationState === 'Failed' ? '−3.9% drift' : 'No measurement'}</em>
                    </div>
                    <div>
                      <span>ERROR RATE</span>
                      <strong>{verificationState === 'Failed' ? '0.09' : '—'}<small>{verificationState === 'Failed' ? '%' : ''}</small></strong>
                      <em>{verificationState === 'Failed' ? 'Within tolerance' : 'No measurement'}</em>
                    </div>
                  </div>
                  <div className="comparison-foot">
                    <span>{verificationState === 'Failed' ? 'P95 drift exceeds tolerance' : 'Awaiting a distinct evidence run'}</span>
                    <MiniTag tone={verificationState === 'Failed' ? 'danger' : 'neutral'}>{verificationState === 'Failed' ? 'DRIFT DETECTED' : 'PENDING'}</MiniTag>
                  </div>
                </section>
              </div>

              <div className="two-column-grid verify-lower">
                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">TOLERANCE POLICY</div>
                      <h3>Verification criteria</h3>
                    </div>
                    <MiniTag>verify-tolerance-v1</MiniTag>
                  </div>
                  <div className="tolerance-list">
                    <div><span>P95 latency drift</span><strong>≤ 5 ms</strong><Status tone={verificationState === 'Failed' ? 'danger' : 'warning'}>{verificationState === 'Failed' ? 'Fail' : 'Not assessed'}</Status></div>
                    <div><span>Throughput drift</span><strong>≤ 5%</strong><Status tone={verificationState === 'Failed' ? 'success' : 'warning'}>{verificationState === 'Failed' ? 'Pass' : 'Not assessed'}</Status></div>
                    <div><span>Error rate regression</span><strong>≤ 0.1 pp</strong><Status tone={verificationState === 'Failed' ? 'success' : 'warning'}>{verificationState === 'Failed' ? 'Pass' : 'Not assessed'}</Status></div>
                  </div>
                </section>

                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">EVIDENCE DETAILS</div>
                      <h3>What this verdict means</h3>
                    </div>
                  </div>
                  <div className="explanation-block">
                    <Icon name="info" size={17} />
                    <p>{verificationState === 'Failed' ? 'The initial candidate met SLO constraints. The independent rerun failed the drift criterion, so the system withholds the verified label.' : verificationState === 'Stale' ? 'Measurements are attached to a prior input version. Re-measure the current configuration before making a new optimization claim.' : 'The initial candidate meets the deterministic constraints, but verification is still pending. A feasible result must not be described as verified until independent evidence passes.'}</p>
                  </div>
                  <Button className="full-button" icon="file" onClick={() => navigate('Evidence & Reports')}>
                    Open evidence dossier <Icon name="arrow" size={13} />
                  </Button>
                </section>
              </div>
            </>
          )}

          {page === 'Evidence & Reports' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">OBSERVABILITY / AUDIT DOSSIER</div>
                  <h1>Evidence & Reports<span className="title-period">.</span></h1>
                  <p>Every decision links back to the run, its configuration, and its provenance.</p>
                </div>
                <div className="heading-actions">
                  <Status tone="info">DEMO DOSSIER</Status>
                  <Button variant="primary" icon="download" loading={isExporting} onClick={exportReport}>Export dossier</Button>
                </div>
              </div>

              <div className="report-summary-grid">
                <div className="report-stat"><span>ACTIVE DOSSIER</span><strong>EXP-0248</strong><small>chat-completions-prod</small></div>
                <div className="report-stat"><span>POLICY VERSION</span><strong>slo-prod-03</strong><small>Hard constraints · v1.4</small></div>
                <div className="report-stat"><span>DECISION STATUS</span><strong className={evidenceStale ? 'amber-text' : winner ? 'green-text' : 'red-text'}>{evidenceStale ? 'Stale' : winner ? 'Feasible' : 'Infeasible'}</strong><small>{evidenceStale ? 'Refresh measurements' : winner ? 'Verification pending' : 'No valid winner'}</small></div>
                <div className="report-stat"><span>PROVENANCE</span><strong>Deterministic</strong><small>Fixture values only</small></div>
              </div>

              <div className="report-layout">
                <aside className="panel report-nav" role="tablist" aria-label="Dossier contents">
                  <div className="eyebrow">DOSSIER CONTENTS</div>
                  {['Overview', 'Workload & SLOs', 'Candidate rationale', 'Verification evidence', 'Raw event log', 'Provenance'].map((t, i) => (
                    <button
                      key={t}
                      role="tab"
                      aria-selected={reportTab === t}
                      className={`report-nav-item ${reportTab === t ? 'report-nav-active' : ''}`}
                      onClick={() => setReportTab(t)}
                    >
                      <span className="report-nav-num">{String(i + 1).padStart(2, '0')}</span>
                      <span>{t}</span>
                      <Icon name="chevron" size={13} />
                    </button>
                  ))}
                  <div className="report-nav-note">
                    <Icon name="shield" size={15} />
                    <p>All values in this dossier are traceable to the selected deterministic run fixture.</p>
                  </div>
                </aside>

                <section className="panel report-document">
                  <div className="document-topline">
                    <span>ENGINEERING DOSSIER / {reportTab.toUpperCase()}</span>
                    <span>SLK · EXP-0248</span>
                  </div>

                  {reportTab === 'Overview' && (
                    <>
                      <div className="document-heading">
                        <div className="document-symbol">
                          <div className="brand-mark"><span /><span /><span /><span /></div>
                        </div>
                        <div>
                          <div className="eyebrow">SLOKERN / ENGINEERING DOSSIER</div>
                          <h2>Inference optimization record</h2>
                          <p>Experiment EXP-0248 · Revision 01</p>
                        </div>
                      </div>
                      <div className="document-verdict">
                        <div>
                          <span>FEASIBILITY VERDICT</span>
                          <strong>{winner ? 'Feasible' : 'Infeasible'}</strong>
                          <small>{winner ? 'Candidate C-02 meets all declared constraints.' : 'No candidate meets every constraint in this scenario.'}</small>
                        </div>
                        <Status tone={winner ? 'success' : 'danger'}>{winner ? 'PASS' : 'BLOCKED'}</Status>
                      </div>
                      <div className="document-section">
                        <h3>01 / Decision summary</h3>
                        <p>{winner ? 'Candidate C-02 Balanced is the highest-ranked feasible fixture. It achieves 47 ms P95 latency, 61.8k tokens per second, and a 0.08% error rate.' : 'No candidate currently satisfies the complete constraint set. A successful optimization claim cannot be made from this evidence.'} Independent verification status is <strong>{verificationState.toLowerCase()}</strong>, which remains separate from feasibility.</p>
                      </div>
                      <div className="document-section">
                        <h3>02 / Key measurements</h3>
                        <div className="doc-metric-row">
                          <div><span>P95 LATENCY</span><strong>{winner?.p95 ?? '—'}<small>ms</small></strong></div>
                          <div><span>THROUGHPUT</span><strong>{winner?.throughput.toFixed(1) ?? '—'}<small>k tok/s</small></strong></div>
                          <div><span>ERROR RATE</span><strong>{winner?.error.toFixed(2) ?? '—'}<small>%</small></strong></div>
                        </div>
                      </div>
                      <div className="document-section">
                        <h3>03 / Evidence statement</h3>
                        <div className="evidence-callout">
                          <Icon name="info" size={16} />
                          <p>This dossier was generated from deterministic frontend fixtures. It is not a production benchmark, a live GPU measurement, or a signed backend audit record.</p>
                        </div>
                      </div>
                    </>
                  )}

                  {reportTab === 'Workload & SLOs' && (
                    <>
                      <h2>Workload & SLO specification</h2>
                      <p className="document-lead">Input assumptions and thresholds used to evaluate EXP-0248.</p>
                      <div className="document-section">
                        <h3>Workload definition</h3>
                        {[['Workload', builder.workload], ['Model', builder.model], ['Offered load', `${builder.inputRate} req/min`], ['Mean input tokens', String(builder.inputTokens)], ['Mean output tokens', String(builder.outputTokens)]].map(([a, b]) => (
                          <div className="doc-row" key={a}><span>{a}</span><strong>{b}</strong></div>
                        ))}
                      </div>
                      <div className="document-section">
                        <h3>Hard constraints</h3>
                        {[['P95 latency', `≤ ${builder.p95} ms`], ['Throughput', `≥ ${builder.minThroughput}k tok/s`], ['Error rate', `≤ ${builder.maxError}%`]].map(([a, b]) => (
                          <div className="doc-row" key={a}><span>{a}</span><strong>{b}</strong></div>
                        ))}
                      </div>
                    </>
                  )}

                  {reportTab === 'Candidate rationale' && (
                    <>
                      <h2>Candidate ranking rationale</h2>
                      <p className="document-lead">Deterministic evaluator results for the active configuration.</p>
                      {candidates.map(c => (
                        <div className="doc-candidate" key={c.id}>
                          <div>
                            <span className="mono">{c.id}</span>
                            <strong>{c.name}</strong>
                            <small>{c.p95} ms P95 · {c.throughput}k tok/s · {c.error}% errors</small>
                          </div>
                          <Status tone={c.feasible ? 'success' : 'danger'}>{c.feasible ? 'Feasible' : 'Infeasible'}</Status>
                          <p>{c.reason}</p>
                        </div>
                      ))}
                    </>
                  )}

                  {reportTab === 'Verification evidence' && (
                    <>
                      <h2>Independent verification</h2>
                      <p className="document-lead">The rerun remains independent from initial feasibility.</p>
                      <div className="document-verdict">
                        <div>
                          <span>VERIFICATION VERDICT</span>
                          <strong>{verificationState}</strong>
                          <small>{verificationState === 'Failed' ? 'P95 drift breached tolerance by 6 ms.' : 'No passing independent verification evidence is available in this scenario.'}</small>
                        </div>
                        <Status tone={verificationState === 'Failed' ? 'danger' : 'warning'}>{verificationState === 'Failed' ? 'FAIL' : 'PENDING'}</Status>
                      </div>
                    </>
                  )}

                  {reportTab === 'Raw event log' && (
                    <>
                      <h2>Event records</h2>
                      <p className="document-lead">Chronological fixture events with stable timestamps and reason codes.</p>
                      {EVENTS.map(e => (
                        <div className="raw-event" key={e.time}>
                          <time>{e.time}</time>
                          <div><strong>{e.title}</strong><small>{e.detail}</small></div>
                          <MiniTag tone={e.type === 'success' ? 'green' : e.type === 'warning' ? 'warning' : 'info'}>{e.type.toUpperCase()}</MiniTag>
                        </div>
                      ))}
                    </>
                  )}

                  {reportTab === 'Provenance' && (
                    <>
                      <h2>Provenance & policy metadata</h2>
                      <p className="document-lead">Source context for the displayed decision.</p>
                      {[['Data source', 'Deterministic frontend fixtures'], ['Backend connection', 'Not connected'], ['Evaluator version', 'v0.4.2'], ['Policy set', 'slo-prod-03'], ['Verification policy', 'verify-tolerance-v1'], ['Evidence validity', evidenceStale ? 'Stale' : 'Fixture valid for selected scenario'], ['Export status', 'Locally generated Markdown'], ['Run identifier', activeRun]].map(([a, b]) => (
                        <div className="doc-row" key={a}><span>{a}</span><strong>{b}</strong></div>
                      ))}
                      <div className="evidence-callout">
                        <Icon name="alert" size={16} />
                        <p>Exporting this report creates a local Markdown file. It does not create signed, tamper-proof provenance.</p>
                      </div>
                    </>
                  )}

                  <div className="document-footer">
                    <span>SLOKERN · SYSTEMS LAB</span>
                    <span>CONFIDENTIALITY: DEMO ONLY</span>
                    <span>PAGE 01 / 01</span>
                  </div>
                </section>
              </div>
            </>
          )}

          {page === 'Runtime Profile' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">SYSTEM / SERVING ENVIRONMENT</div>
                  <h1>Runtime Profile<span className="title-period">.</span></h1>
                  <p>Inspect the hardware and runtime context without confusing fixtures for detection.</p>
                </div>
                <div className="heading-actions">
                  <Status tone="warning">ILLUSTRATIVE PROFILE</Status>
                  <Button icon="refresh" onClick={() => notify('Runtime inventory is fixture data. No hardware probe was attempted.')}>Refresh fixture</Button>
                </div>
              </div>

              <section className="runtime-hero panel">
                <div className="runtime-hero-grid" />
                <div className="runtime-chip"><Icon name="cpu" size={21} /></div>
                <div className="runtime-hero-copy">
                  <div className="eyebrow">RUNTIME PROFILE / RP-01</div>
                  <h2>Inference serving node</h2>
                  <p>Illustrative configuration for the current model profile. This frontend has not queried a GPU or runtime endpoint.</p>
                  <div className="runtime-tags">
                    <MiniTag tone="accent">CUDA COMPATIBLE PROFILE</MiniTag>
                    <MiniTag tone="neutral">DEMO INVENTORY</MiniTag>
                  </div>
                </div>
                <div className="runtime-version">
                  <span>PROFILE REVISION</span>
                  <strong>RP-01.04</strong>
                  <small>Fixture metadata</small>
                </div>
              </section>

              <div className="runtime-grid">
                <section className="panel runtime-panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">HARDWARE INVENTORY</div>
                      <h3>Compute resources</h3>
                    </div>
                    <Status tone="warning">NOT DETECTED</Status>
                  </div>
                  <div className="resource-visual">
                    <div className="gpu-chip-visual">
                      <div className="chip-etched">GPU</div>
                      <div className="chip-center">
                        <Icon name="cpu" size={28} />
                        <strong>ACCELERATOR</strong>
                        <small>FIXTURE</small>
                      </div>
                      <div className="chip-corner">SLK / 01</div>
                    </div>
                    <div className="resource-summary">
                      <span>ILLUSTRATIVE GPU</span>
                      <strong>NVIDIA A100 80GB</strong>
                      <small>Example only · not hardware-detected</small>
                      <div className="resource-line"><span>Memory bandwidth</span><strong>2.0 TB/s</strong></div>
                      <div className="resource-line"><span>Memory capacity</span><strong>80 GB HBM2e</strong></div>
                      <div className="resource-line"><span>Compute class</span><strong>Datacenter</strong></div>
                    </div>
                  </div>
                  <div className="resource-disclaimer">
                    <Icon name="info" size={14} /> Values are fixture metadata, not measurements from this machine.
                  </div>
                </section>

                <section className="panel runtime-panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">SOFTWARE STACK</div>
                      <h3>Runtime environment</h3>
                    </div>
                    <MiniTag>EXAMPLE</MiniTag>
                  </div>
                  <div className="runtime-inventory">
                    {[['Inference engine', 'vLLM 0.6.x'], ['CUDA runtime', '12.4'], ['Driver profile', 'R550 series'], ['Model artifact', 'Llama-3-8B-Instruct'], ['Weight precision', 'FP16'], ['KV cache precision', 'FP8'], ['Parallelism', 'Tensor parallel = 1'], ['Serving interface', 'OpenAI-compatible API']].map(([a, b], i) => (
                      <div className="runtime-row" key={a}>
                        <span className="runtime-row-icon"><Icon name={i < 3 ? 'cpu' : i === 3 ? 'layers' : 'settings'} size={14} /></span>
                        <span>{a}</span>
                        <strong>{b}</strong>
                      </div>
                    ))}
                  </div>
                </section>
              </div>

              <div className="two-column-grid lower-grid">
                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">CAPACITY SNAPSHOT</div>
                      <h3>Fixture utilization</h3>
                    </div>
                    <Status tone="warning">STATIC VALUES</Status>
                  </div>
                  {[['GPU utilization', 78], ['GPU memory allocation', 67], ['CPU utilization', 34], ['Host memory allocation', 59]].map(([n, v]) => (
                    <div className="capacity-row" key={n as string}>
                      <div><span>{n}</span><strong>{v}%</strong></div>
                      <ProgressBar value={v as number} tone={Number(v) > 85 ? 'warning' : 'accent'} />
                    </div>
                  ))}
                </section>

                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <div className="eyebrow">COMPATIBILITY</div>
                      <h3>Configuration checks</h3>
                    </div>
                    <Status tone="warning">NOT EXECUTED</Status>
                  </div>
                  <div className="compat-list">
                    <div>
                      <span className="compat-icon"><Icon name="check" size={13} /></span>
                      <div><strong>Model / engine pair</strong><small>Known example profile</small></div>
                      <MiniTag tone="neutral">ASSUMED</MiniTag>
                    </div>
                    <div>
                      <span className="compat-icon"><Icon name="check" size={13} /></span>
                      <div><strong>KV cache precision</strong><small>Example FP8-compatible setting</small></div>
                      <MiniTag tone="neutral">ASSUMED</MiniTag>
                    </div>
                    <div>
                      <span className="compat-icon compat-warning"><Icon name="alert" size={13} /></span>
                      <div><strong>Actual device availability</strong><small>Requires a connected runtime probe</small></div>
                      <MiniTag tone="warning">UNKNOWN</MiniTag>
                    </div>
                  </div>
                </section>
              </div>
            </>
          )}

          {page === 'Settings' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">SYSTEM / PREFERENCES</div>
                  <h1>Settings<span className="title-period">.</span></h1>
                  <p>Control the demo experience without overriding the evaluator's hard rules.</p>
                </div>
                <div className="heading-actions">
                  <Button
                    onClick={() => {
                      setSettings({ reducedMotion: false, compactTables: false, showAmbient: true });
                      setScenario('standard');
                      notify('UI preferences and demo scenario reset to defaults.');
                    }}
                    icon="refresh"
                  >
                    Reset defaults
                  </Button>
                </div>
              </div>

              <div className="settings-layout">
                <div className="settings-main">
                  <section className="panel settings-panel">
                    <div className="settings-section-icon"><Icon name="activity" size={18} /></div>
                    <div className="settings-section-content">
                      <div className="eyebrow">PRESENTATION</div>
                      <h3>Appearance & display</h3>
                      <p>Adjust the workstation atmosphere and information density.</p>
                      <div className="setting-row">
                        <div>
                          <strong>Ambient green illumination</strong>
                          <small>Subtle background illumination behind major workspaces.</small>
                        </div>
                        <button
                          type="button"
                          role="switch"
                          aria-label="Ambient green illumination"
                          aria-checked={settings.showAmbient}
                          className={`toggle ${settings.showAmbient ? 'toggle-on' : ''}`}
                          onClick={() => setSettings({ ...settings, showAmbient: !settings.showAmbient })}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              setSettings({ ...settings, showAmbient: !settings.showAmbient });
                            }
                          }}
                        >
                          <span />
                        </button>
                      </div>
                      <div className="setting-row">
                        <div>
                          <strong>Reduce motion</strong>
                          <small>Disable optional transitions and decorative movement.</small>
                        </div>
                        <button
                          type="button"
                          role="switch"
                          aria-label="Reduce motion"
                          aria-checked={settings.reducedMotion}
                          className={`toggle ${settings.reducedMotion ? 'toggle-on' : ''}`}
                          onClick={() => setSettings({ ...settings, reducedMotion: !settings.reducedMotion })}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              setSettings({ ...settings, reducedMotion: !settings.reducedMotion });
                            }
                          }}
                        >
                          <span />
                        </button>
                      </div>
                      <div className="setting-row">
                        <div>
                          <strong>Compact tables</strong>
                          <small>Reduce table row height to fit more records.</small>
                        </div>
                        <button
                          type="button"
                          role="switch"
                          aria-label="Compact tables"
                          aria-checked={settings.compactTables}
                          className={`toggle ${settings.compactTables ? 'toggle-on' : ''}`}
                          onClick={() => setSettings({ ...settings, compactTables: !settings.compactTables })}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              setSettings({ ...settings, compactTables: !settings.compactTables });
                            }
                          }}
                        >
                          <span />
                        </button>
                      </div>
                    </div>
                  </section>

                  <section className="panel settings-panel">
                    <div className="settings-section-icon"><Icon name="layers" size={18} /></div>
                    <div className="settings-section-content">
                      <div className="eyebrow">DETERMINISTIC DEMO</div>
                      <h3>Scenario controls</h3>
                      <p>Switch reproducible fixtures to inspect edge cases. This does not change backend state.</p>
                      <div className="scenario-options">
                        {([
                          { id: 'standard', title: 'Feasible candidate · pending verification', desc: 'C-02 satisfies the hard SLOs. No independent verified claim.', tag: 'DEFAULT' },
                          { id: 'verification-failed', title: 'Verification failure', desc: 'C-02 remains feasible, but independent rerun drifts beyond tolerance.', tag: 'DRIFT' },
                          { id: 'no-feasible', title: 'No feasible candidate', desc: 'All candidates fail at least one hard constraint. No winner is declared.', tag: 'BLOCKED' },
                          { id: 'stale-evidence', title: 'Stale evidence', desc: 'Existing measurements no longer match the relevant input version.', tag: 'STALE' },
                        ] as const).map(s => (
                          <div
                            key={s.id}
                            role="button"
                            tabIndex={0}
                            aria-pressed={scenario === s.id}
                            className={`scenario-option ${scenario === s.id ? 'scenario-option-active' : ''}`}
                            onClick={() => { setScenario(s.id); notify(`Scenario changed to: ${s.title}.`); }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                setScenario(s.id);
                                notify(`Scenario changed to: ${s.title}.`);
                              }
                            }}
                          >
                            <span className="scenario-radio">{scenario === s.id && <i />}</span>
                            <span className="scenario-option-copy">
                              <strong>{s.title}</strong>
                              <small>{s.desc}</small>
                            </span>
                            <MiniTag tone={scenario === s.id ? 'accent' : 'neutral'}>{s.tag}</MiniTag>
                          </div>
                        ))}
                      </div>
                    </div>
                  </section>

                  <section className="panel settings-panel">
                    <div className="settings-section-icon"><Icon name="sliders" size={18} /></div>
                    <div className="settings-section-content">
                      <div className="eyebrow">EXPERIMENT DEFAULTS</div>
                      <h3>Default measurement policy</h3>
                      <p>These defaults inform the builder. They do not silently overwrite existing hard constraints.</p>
                      <div className="settings-readonly-grid">
                        <div><span>Default P95 ceiling</span><strong>50 ms</strong></div>
                        <div><span>Default throughput floor</span><strong>50k tok/s</strong></div>
                        <div><span>Default max error</span><strong>0.5%</strong></div>
                        <div><span>Evaluator fixture</span><strong>v0.4.2</strong></div>
                      </div>
                      <div className="settings-warning">
                        <Icon name="shield" size={15} />
                        <p>Hard SLO thresholds, ranking policy, and verification criteria are not editable here. Change them explicitly in the workload builder or policy integration.</p>
                      </div>
                    </div>
                  </section>
                </div>

                <aside className="settings-aside">
                  <section className="panel settings-aside-card">
                    <div className="aside-brand-mark">
                      <div className="brand-mark"><span /><span /><span /><span /></div>
                    </div>
                    <div className="eyebrow">SLOKERN / FRONTEND</div>
                    <h3>System status</h3>
                    <div className="config-line"><span>Version</span><strong>0.1.0-demo</strong></div>
                    <div className="config-line"><span>Integration</span><Status tone="warning">Not connected</Status></div>
                    <div className="config-line"><span>Data mode</span><Status tone="info">Fixtures only</Status></div>
                    <div className="config-line"><span>Persistence</span><strong>Local storage</strong></div>
                    <p className="settings-footnote">UI preferences and the selected demo scenario are stored locally when the browser permits it.</p>
                  </section>

                  <section className="panel settings-aside-card">
                    <div className="eyebrow">DESIGN SYSTEM</div>
                    <h3>Obsidian Black / NVIDIA Green</h3>
                    <p>Near-black foundations, restrained edge illumination, crisp telemetry, and purposeful semantic color.</p>
                    <div className="swatch-row">
                      {['#080A09', '#0E120F', '#151B15', '#76B900', '#95D500', '#E9B949', '#FF5555'].map(c => (
                        <span key={c} style={{ background: c }} title={c} />
                      ))}
                    </div>
                    <small className="mono">TOKENS / OBSIDIAN 1.0</small>
                  </section>
                </aside>
              </div>
            </>
          )}

          {page === 'Run Detail' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow heading-eyebrow">
                    <button className="inline-back" onClick={() => navigate('Experiments')}>EXPERIMENTS</button> / RUN DETAIL
                  </div>
                  <h1>Run detail<span className="title-period">.</span></h1>
                  <p>One lifecycle view connecting configuration, measurements, and independent verification.</p>
                </div>
                <div className="heading-actions">
                  <Button onClick={() => navigate('Experiments')}>Back to experiments</Button>
                  <Button variant="primary" icon="download" loading={isExporting} onClick={exportReport}>Export evidence</Button>
                </div>
              </div>

              <section className="run-detail-header panel">
                <div className="run-detail-icon"><Icon name="layers" size={21} /></div>
                <div className="run-detail-title">
                  <div className="eyebrow">RUN IDENTIFIER</div>
                  <h2>{activeRun}</h2>
                  <p>{activeExperimentId} · {activeWorkload} · {activeModel}</p>
                </div>
                <div className="run-detail-states">
                  <Status tone={activeRunDetails.state === 'Completed' ? 'success' : activeRunDetails.state === 'Failed' ? 'danger' : activeRunDetails.state === 'Running' ? 'info' : 'warning'}>
                    {`EXECUTION ${activeRunDetails.state.toUpperCase()}`}
                  </Status>
                  <Status tone={activeRunDetails.feasibility === 'Feasible' ? 'success' : activeRunDetails.feasibility === 'Infeasible' ? 'danger' : 'warning'}>
                    {activeRunDetails.feasibility.toUpperCase()}
                  </Status>
                  <Status tone={activeRunDetails.verification === 'Verified' ? 'success' : activeRunDetails.verification === 'Failed' || activeRunDetails.verification === 'Stale' ? 'danger' : 'warning'}>
                    {`VERIFICATION ${activeRunDetails.verification.toUpperCase()}`}
                  </Status>
                </div>
              </section>

              <div className="lifecycle-rail">
                {[
                  { n: '01', label: 'Specify', state: 'complete', desc: 'Workload defined' },
                  { n: '02', label: 'Validate', state: 'complete', desc: 'Settings accepted' },
                  { n: '03', label: 'Measure', state: 'complete', desc: 'Fixture recorded' },
                  { n: '04', label: 'Evaluate', state: activeRunDetails.feasibility === 'Feasible' ? 'complete' : 'blocked', desc: activeRunDetails.feasibility },
                  { n: '05', label: 'Optimize', state: activeRunDetails.feasibility === 'Feasible' ? 'complete' : 'blocked', desc: activeRunDetails.feasibility === 'Feasible' ? activeRunDetails.candidateId + ' ranked' : 'Blocked' },
                  { n: '06', label: 'Verify', state: activeRunDetails.verification === 'Failed' ? 'failed' : activeRunDetails.verification === 'Verified' ? 'complete' : 'pending', desc: activeRunDetails.verification },
                  { n: '07', label: 'Explain', state: 'pending', desc: 'Dossier available' },
                ].map(s => (
                  <div className={`lifecycle-step lifecycle-${s.state}`} key={s.n}>
                    <span>{s.state === 'complete' ? <Icon name="check" size={13} /> : s.n}</span>
                    <strong>{s.label}</strong>
                    <small>{s.desc}</small>
                  </div>
                ))}
              </div>

              <div className="run-detail-grid">
                <div className="run-detail-main">
                  <section className="panel">
                    <div className="panel-header">
                      <div>
                        <div className="eyebrow">REQUESTED CONFIGURATION</div>
                        <h3>Effective serving settings</h3>
                      </div>
                      <Button variant="ghost" icon="external" onClick={() => navigate('Workload & SLO Builder')}>Open builder</Button>
                    </div>
                    <div className="detail-settings-grid">
                      {[['Workload', activeWorkload], ['Model', activeModel], ['Batch size', String(builder.batch)], ['Max concurrency', String(builder.concurrency)], ['KV cache precision', builder.kvCache], ['Run policy', 'slo-prod-03']].map(([a, b]) => (
                        <div key={a}><span>{a}</span><strong>{b}</strong></div>
                      ))}
                    </div>
                  </section>

                  <section className="panel">
                    <div className="panel-header">
                      <div>
                        <div className="eyebrow">MEASUREMENT EVIDENCE</div>
                        <h3>Recorded metrics</h3>
                      </div>
                      <MiniTag tone="info">DETERMINISTIC</MiniTag>
                    </div>
                    <div className="detail-metrics-grid">
                      <div><span>P50 LATENCY</span><strong>{detailCandidate.p50}<small>ms</small></strong></div>
                      <div><span>P95 LATENCY</span><strong>{detailCandidate.p95}<small>ms</small></strong></div>
                      <div><span>P99 LATENCY</span><strong>{detailCandidate.p99}<small>ms</small></strong></div>
                      <div><span>THROUGHPUT</span><strong>{detailCandidate.throughput.toFixed(1)}<small>k tok/s</small></strong></div>
                    </div>
                    <div className="evidence-callout">
                      <Icon name="info" size={16} />
                      <p>Execution completion, evidence validity, SLO feasibility, and verification verdict remain four distinct state dimensions.</p>
                    </div>
                  </section>

                  <section className="panel">
                    <div className="panel-header">
                      <div>
                        <div className="eyebrow">STATE HISTORY</div>
                        <h3>Run events</h3>
                      </div>
                    </div>
                    <div className="event-list">
                      {EVENTS.map(e => (
                        <div className="event-item" key={e.time}>
                          <time>{e.time}</time>
                          <div className={`event-icon event-${e.type}`}>
                            <Icon name={e.type === 'success' ? 'check' : e.type === 'warning' ? 'alert' : 'activity'} size={13} />
                          </div>
                          <div className="event-body">
                            <strong>{e.title}</strong>
                            <small>{e.detail}</small>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                </div>

                <aside className="run-detail-aside">
                  <section className="panel">
                    <div className="eyebrow">EVIDENCE VALIDITY</div>
                    <h3>{evidenceStale ? 'Stale evidence' : 'Fixture evidence available'}</h3>
                    <p>{evidenceStale ? 'The selected scenario marks measurements stale because relevant inputs changed.' : 'Metrics are deterministic fixture values for the currently selected scenario.'}</p>
                    <Status tone={evidenceStale ? 'danger' : 'success'}>{evidenceStale ? 'STALE' : 'AVAILABLE'}</Status>
                    {evidenceStale && (
                      <Button className="full-button" variant="primary" icon="refresh" onClick={() => { setScenario('standard'); notify('Demo evidence restored to the baseline fixture scenario.'); }}>
                        Restore demo evidence
                      </Button>
                    )}
                  </section>

                  <section className="panel">
                    <div className="eyebrow">NEXT ACTION</div>
                    <h3>
                      {activeRunDetails.verification === 'Failed'
                        ? 'Investigate verification drift'
                        : activeRunDetails.verification === 'Verified'
                        ? 'Review verified evidence'
                        : activeRunDetails.feasibility === 'Feasible'
                        ? 'Run independent verification'
                        : 'Resolve hard constraints'}
                    </h3>
                    <p>
                      {activeRunDetails.verification === 'Failed'
                        ? 'Review the P95 drift reason code and compare the independent run before making a verified claim.'
                        : activeRunDetails.verification === 'Verified'
                        ? 'An independent verification result is recorded for this run. Inspect the supporting evidence rather than rerunning by default.'
                        : activeRunDetails.feasibility === 'Feasible'
                        ? 'This run meets its recorded hard constraints, but verification remains a separate gate.'
                        : 'No candidate can be declared a winner until all constraints are met.'}
                    </p>
                    <Button
                      variant="primary"
                      className="full-button"
                      icon={activeRunDetails.verification === 'Failed' || activeRunDetails.verification === 'Verified' ? 'file' : 'shield'}
                      onClick={() => navigate(activeRunDetails.verification === 'Failed' || activeRunDetails.verification === 'Verified' ? 'Evidence & Reports' : activeRunDetails.feasibility === 'Feasible' ? 'Verification' : 'Tuning Lab')}
                    >
                      {activeRunDetails.verification === 'Failed' || activeRunDetails.verification === 'Verified'
                        ? 'Inspect evidence'
                        : activeRunDetails.feasibility === 'Feasible'
                        ? 'Open verification'
                        : 'Inspect candidates'} <Icon name="arrow" size={13} />
                    </Button>
                  </section>

                  <section className="panel">
                    <div className="eyebrow">PROVENANCE</div>
                    <div className="config-line"><span>Data</span><strong>Fixture</strong></div>
                    <div className="config-line"><span>Evaluator</span><strong>v0.4.2</strong></div>
                    <div className="config-line"><span>Policy</span><strong>slo-prod-03</strong></div>
                    <div className="config-line"><span>Live API</span><Status tone="warning">Disconnected</Status></div>
                  </section>
                </aside>
              </div>
            </>
          )}

          <footer className="app-footer">
            <div>
              <span className="footer-brand"><span className="footer-spark">✳</span> SLOKERN</span>
              <span className="footer-divider" />
              <span>AI INFERENCE CONTROL PLANE</span>
            </div>
            <div>
              <span className="footer-demo-dot" /> DEMO MODE
              <span className="footer-divider" /> BUILD 0.1.0
              <span className="footer-divider" />
              <button onClick={() => navigate('Settings')}>PREFERENCES</button>
            </div>
          </footer>
        </div>
      </main>

      {toast && (
        <div className="toast" role="status" aria-live="polite">
          <span className="toast-icon"><Icon name="check" size={14} /></span>
          <span className="toast-message">{toast}</span>
          <button aria-label="Dismiss notification" className="toast-close" onClick={() => setToast('')}>×</button>
          <div className="toast-progress" />
        </div>
      )}
    </div>
  );
}
