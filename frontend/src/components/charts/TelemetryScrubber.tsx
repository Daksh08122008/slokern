import React, { useState } from 'react';
import { formatLatency, formatNumber } from '../../lib/format';

interface TelemetryPoint {
  timeSec: number;
  ttftMs: number;
  itlMs: number;
  e2eMs: number;
  rps: number;
}

interface TelemetryScrubberProps {
  data?: TelemetryPoint[];
  ttftCeilingMs?: number;
}

// Generate realistic 60s sample series if not provided
function generateDefaultSeries(): TelemetryPoint[] {
  const points: TelemetryPoint[] = [];
  for (let s = 0; s <= 60; s += 2) {
    const jitter = Math.sin(s / 4) * 3;
    points.push({
      timeSec: s,
      ttftMs: 25.4 + jitter + (Math.random() * 2),
      itlMs: 9.3 + jitter * 0.3 + (Math.random() * 0.8),
      e2eMs: 46.2 + jitter * 1.2,
      rps: 16.0 + (Math.random() * 0.4 - 0.2),
    });
  }
  return points;
}

export const TelemetryScrubber: React.FC<TelemetryScrubberProps> = ({
  data = generateDefaultSeries(),
  ttftCeilingMs = 50.0,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(Math.floor(data.length / 2));

  const currentPoint = data[selectedIndex] || data[0];
  const headroomMs = ttftCeilingMs - currentPoint.ttftMs;
  const isPassing = headroomMs >= 0;

  // Clamp HUD position between 16% and 84% so it never clips chart edges
  const rawPct = (selectedIndex / Math.max(1, data.length - 1)) * 100;
  const clampedHudPct = Math.min(84, Math.max(16, rawPct));

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(data.length - 1, prev + 1));
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(0, prev - 1));
    } else if (e.key === 'Home') {
      e.preventDefault();
      setSelectedIndex(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      setSelectedIndex(data.length - 1);
    }
  };

  const chartWidth = 500;
  const chartHeight = 160;
  const padding = { top: 20, right: 20, bottom: 25, left: 40 };
  const pWidth = chartWidth - padding.left - padding.right;
  const pHeight = chartHeight - padding.top - padding.bottom;

  // TTFT range 15 to 60 ms
  const minVal = 15;
  const maxVal = 60;
  const scaleY = (v: number) => padding.top + pHeight - ((v - minVal) / (maxVal - minVal)) * pHeight;
  const scaleX = (idx: number) => padding.left + (idx / (data.length - 1)) * pWidth;

  const pointsString = data.map((d, idx) => `${scaleX(idx)},${scaleY(d.ttftMs)}`).join(' ');
  const ceilingY = scaleY(ttftCeilingMs);

  return (
    <div
      className="telemetry-scrubber"
      style={{
        position: 'relative',
        backgroundColor: 'var(--surface, #0E120F)',
        border: '1px solid var(--border, #263124)',
        borderRadius: '6px',
        padding: '16px',
        outline: 'none',
      }}
      tabIndex={0}
      role="region"
      aria-label="Time-Series Telemetry Scrubber"
      onKeyDown={handleKeyDown}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
            Real-Time Sample Stream Scrubber
          </h4>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            Use Left/Right arrow keys or click to inspect empirical sample ticks
          </span>
        </div>

        <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-secondary, #A0AAA0)' }}>
          t = {currentPoint.timeSec}s / 60s
        </div>
      </div>

      <svg
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const clickX = e.clientX - rect.left;
          const ratio = Math.max(0, Math.min(1, (clickX - padding.left) / pWidth));
          const idx = Math.round(ratio * (data.length - 1));
          setSelectedIndex(idx);
        }}
      >
        {/* SLO Ceiling Line */}
        <line
          x1={padding.left}
          y1={ceilingY}
          x2={padding.left + pWidth}
          y2={ceilingY}
          stroke="var(--error, #FF5555)"
          strokeWidth={1.5}
          strokeDasharray="4 3"
        />

        {/* Telemetry Line */}
        <polyline
          fill="none"
          stroke="var(--primary, #76B900)"
          strokeWidth={2}
          points={pointsString}
        />

        {/* Scrubber Vertical Line */}
        <line
          x1={scaleX(selectedIndex)}
          y1={padding.top}
          x2={scaleX(selectedIndex)}
          y2={padding.top + pHeight}
          stroke="var(--text-primary, #F0F3EF)"
          strokeWidth={1.5}
        />

        {/* Scrubber Active Dot */}
        <circle
          cx={scaleX(selectedIndex)}
          cy={scaleY(currentPoint.ttftMs)}
          r={5}
          fill="var(--primary-bright, #95D500)"
          stroke="var(--surface, #0E120F)"
          strokeWidth={2}
        />
      </svg>

      {/* Clamped HUD Pill (16-84%) */}
      <div
        style={{
          position: 'absolute',
          top: '46px',
          left: `${clampedHudPct}%`,
          transform: 'translateX(-50%)',
          backgroundColor: 'var(--glass-float, rgba(29, 37, 30, 0.92))',
          backdropFilter: 'blur(12px)',
          border: '1px solid var(--border-strong, #384635)',
          borderRadius: '4px',
          padding: '6px 10px',
          fontSize: '11px',
          fontFamily: 'var(--font-mono, monospace)',
          color: 'var(--text-primary, #F0F3EF)',
          pointerEvents: 'none',
          zIndex: 10,
          whiteSpace: 'nowrap',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ fontWeight: 700 }}>
          TTFT: {formatLatency(currentPoint.ttftMs)} · ITL: {formatLatency(currentPoint.itlMs)}
        </div>
        <div style={{ color: isPassing ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)' }}>
          {isPassing ? `+${formatNumber(headroomMs, 1)} ms headroom` : `-${formatNumber(Math.abs(headroomMs), 1)} ms breach`}
        </div>
      </div>

      {/* Aria Live Announcement Region */}
      <div className="sr-only" aria-live="polite" style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>
        Sample at second {currentPoint.timeSec}: TTFT {formatLatency(currentPoint.ttftMs)}, {headroomMs >= 0 ? `${headroomMs.toFixed(1)} milliseconds headroom` : `${Math.abs(headroomMs).toFixed(1)} milliseconds breach`}.
      </div>
    </div>
  );
};
