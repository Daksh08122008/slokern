import React, { useState } from 'react';
import type { UICandidate } from '../../lib/adapters/viewModel';
import { formatLatency, formatNumber } from '../../lib/format';

interface TradeoffPlotProps {
  candidates: UICandidate[];
  selectedCandidateId: string;
  onSelectCandidate: (candidate: UICandidate) => void;
  baselineCandidateId?: string;
}

export const TradeoffPlot: React.FC<TradeoffPlotProps> = ({
  candidates,
  selectedCandidateId,
  onSelectCandidate,
  baselineCandidateId,
}) => {
  const [hoveredCandidate, setHoveredCandidate] = useState<UICandidate | null>(null);

  // Chart dimensions & margins
  const width = 560;
  const height = 340;
  const margin = { top: 30, right: 30, bottom: 45, left: 55 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const plottedCandidates = candidates.filter((candidate) => candidate.p95 != null && candidate.throughput != null);
  const latencyValues = plottedCandidates.map((candidate) => candidate.p95 as number);
  const throughputValues = plottedCandidates.map((candidate) => candidate.throughput as number);
  const latencyMin = latencyValues.length ? Math.min(...latencyValues) : 0;
  const latencyMax = latencyValues.length ? Math.max(...latencyValues) : 1;
  const throughputMin = throughputValues.length ? Math.min(...throughputValues) : 0;
  const throughputMax = throughputValues.length ? Math.max(...throughputValues) : 1;
  const xPadding = Math.max((latencyMax - latencyMin) * 0.15, Math.abs(latencyMin) * 0.05, 0.5);
  const yPadding = Math.max((throughputMax - throughputMin) * 0.15, Math.abs(throughputMin) * 0.05, 1);
  const xMin = latencyMin - xPadding;
  const xMax = latencyMax + xPadding;
  const yMin = Math.max(0, throughputMin - yPadding);
  const yMax = throughputMax + yPadding;
  const xTicks = Array.from({ length: 5 }, (_, index) => xMin + ((xMax - xMin) * index) / 4);
  const yTicks = Array.from({ length: 5 }, (_, index) => yMin + ((yMax - yMin) * index) / 4);

  const scaleX = (val: number) => {
    const clamped = Math.max(xMin, Math.min(xMax, val));
    return margin.left + ((clamped - xMin) / (xMax - xMin)) * plotWidth;
  };

  const scaleY = (val: number) => {
    const clamped = Math.max(yMin, Math.min(yMax, val));
    return margin.top + plotHeight - ((clamped - yMin) / (yMax - yMin)) * plotHeight;
  };


  return (
    <div
      className="tradeoff-plot-container"
      style={{
        position: 'relative',
        backgroundColor: 'var(--surface, #0E120F)',
        border: '1px solid var(--border, #263124)',
        borderRadius: '6px',
        padding: '16px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '13px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
            2D Latency vs. Throughput Trade-off
          </h3>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            Persisted metrics only · axes fit the available candidate measurements
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--primary-bright, #95D500)', boxShadow: '0 0 6px rgba(118,185,0,0.5)' }} />
            <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>Winner</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', border: '1.5px solid var(--text-secondary, #A0AAA0)', backgroundColor: 'transparent' }} />
            <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Feasible</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '7px', height: '7px', transform: 'rotate(45deg)', backgroundColor: 'var(--error, #FF5555)' }} />
            <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>Breach</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '7px', height: '7px', border: '1px dashed var(--text-muted, #727D73)', backgroundColor: 'transparent' }} />
            <span style={{ color: 'var(--text-muted, #727D73)' }}>Baseline</span>
          </div>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
        role="img"
        aria-label="2D Latency vs Throughput Tradeoff Chart"
      >
        {/* Grid lines */}
        {xTicks.map((xVal) => (
          <line
            key={`grid-x-${xVal}`}
            x1={scaleX(xVal)}
            y1={margin.top}
            x2={scaleX(xVal)}
            y2={margin.top + plotHeight}
            stroke="var(--border, #263124)"
            strokeWidth={1}
            strokeDasharray="2 2"
            opacity={0.4}
          />
        ))}

        {yTicks.map((yVal) => (
          <line
            key={`grid-y-${yVal}`}
            x1={margin.left}
            y1={scaleY(yVal)}
            x2={margin.left + plotWidth}
            y2={scaleY(yVal)}
            stroke="var(--border, #263124)"
            strokeWidth={1}
            strokeDasharray="2 2"
            opacity={0.4}
          />
        ))}

        {/* Axes lines */}
        <line
          x1={margin.left}
          y1={margin.top + plotHeight}
          x2={margin.left + plotWidth}
          y2={margin.top + plotHeight}
          stroke="var(--border-strong, #384635)"
          strokeWidth={1.5}
        />
        <line
          x1={margin.left}
          y1={margin.top}
          x2={margin.left}
          y2={margin.top + plotHeight}
          stroke="var(--border-strong, #384635)"
          strokeWidth={1.5}
        />

        {/* X Axis Labels */}
        {xTicks.map((xVal) => (
          <text
            key={`lbl-x-${xVal}`}
            x={scaleX(xVal)}
            y={margin.top + plotHeight + 16}
            fill="var(--text-muted, #727D73)"
            fontSize="11px"
            fontFamily="var(--font-mono, monospace)"
            textAnchor="middle"
          >
            {formatNumber(xVal, 1)}
          </text>
        ))}
        <text
          x={margin.left + plotWidth / 2}
          y={margin.top + plotHeight + 34}
          fill="var(--text-secondary, #A0AAA0)"
          fontSize="11px"
          fontFamily="var(--font-mono, monospace)"
          textAnchor="middle"
          fontWeight={600}
        >
          TTFT P95 (ms) →
        </text>

        {/* Y Axis Labels */}
        {yTicks.map((yVal) => (
          <text
            key={`lbl-y-${yVal}`}
            x={margin.left - 8}
            y={scaleY(yVal) + 4}
            fill="var(--text-muted, #727D73)"
            fontSize="11px"
            fontFamily="var(--font-mono, monospace)"
            textAnchor="end"
          >
            {formatNumber(yVal, 1)}
          </text>
        ))}
        <text
          transform={`rotate(-90) translate(-${margin.top + plotHeight / 2}, 14)`}
          fill="var(--text-secondary, #A0AAA0)"
          fontSize="11px"
          fontFamily="var(--font-mono, monospace)"
          textAnchor="middle"
          fontWeight={600}
        >
          Throughput (tok/s) →
        </text>

        {/* Candidate Points (Measured points only with shape-encoded semantics) */}
        {candidates.map((c) => {
          if (c.p95 == null || c.throughput == null) return null;
          const cx = scaleX(c.p95);
          const cy = scaleY(c.throughput);
          const isSelected = c.id === selectedCandidateId;
          const isWinner = c.tag === 'WINNER' && c.feasible;
          const isBaseline = c.id === baselineCandidateId;

          return (
            <g
              key={c.id}
              onClick={() => onSelectCandidate(c)}
              onMouseEnter={() => setHoveredCandidate(c)}
              onMouseLeave={() => setHoveredCandidate(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* Outer Selection Ring */}
              {isSelected && (
                <circle
                  cx={cx}
                  cy={cy}
                  r={14}
                  fill="none"
                  stroke={isWinner ? 'var(--primary, #76B900)' : 'var(--text-primary, #F0F3EF)'}
                  strokeWidth={2}
                  strokeDasharray={isWinner ? undefined : '2 2'}
                />
              )}

              {/* Point Glyphs: Distinct Lightness, Chroma & Shape */}
              {isWinner ? (
                <g>
                  <circle cx={cx} cy={cy} r={9} fill="rgba(118, 185, 0, 0.22)" />
                  <circle cx={cx} cy={cy} r={6} fill="var(--primary-bright, #95D500)" stroke="var(--canvas, #080A09)" strokeWidth={1.5} />
                </g>
              ) : isBaseline ? (
                <rect
                  x={cx - 5}
                  y={cy - 5}
                  width={10}
                  height={10}
                  fill="var(--raised, #151B15)"
                  stroke="var(--text-secondary, #A0AAA0)"
                  strokeWidth={1.5}
                  strokeDasharray="2 1"
                />
              ) : c.feasible ? (
                <circle
                  cx={cx}
                  cy={cy}
                  r={6}
                  fill="var(--raised, #151B15)"
                  stroke="var(--text-secondary, #A0AAA0)"
                  strokeWidth={2}
                />
              ) : (
                <rect
                  x={cx - 5}
                  y={cy - 5}
                  width={10}
                  height={10}
                  transform={`rotate(45 ${cx} ${cy})`}
                  fill="var(--error, #FF5555)"
                  stroke="var(--canvas, #080A09)"
                  strokeWidth={1.5}
                />
              )}

              {/* Point ID Label */}
              <text
                x={cx}
                y={cy - 12}
                fill={isSelected ? 'var(--text-primary, #F0F3EF)' : 'var(--text-secondary, #A0AAA0)'}
                fontSize="11px"
                fontFamily="var(--font-mono, monospace)"
                fontWeight={isSelected ? 700 : 500}
                textAnchor="middle"
              >
                {c.id}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Hover Tooltip (Glass Float) */}
      {hoveredCandidate && (
        <div
          style={{
            position: 'absolute',
            bottom: '24px',
            right: '24px',
            backgroundColor: 'var(--glass-float, rgba(29, 37, 30, 0.88))',
            backdropFilter: 'blur(12px)',
            border: '1px solid var(--border-strong, #384635)',
            borderRadius: '4px',
            padding: '10px 14px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono, monospace)',
            color: 'var(--text-primary, #F0F3EF)',
            pointerEvents: 'none',
            zIndex: 10,
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: '4px', color: hoveredCandidate.feasible ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)' }}>
            {hoveredCandidate.id} · {hoveredCandidate.name} ({hoveredCandidate.feasible ? 'FEASIBLE' : 'INFEASIBLE'})
          </div>
          <div>TTFT P95: {formatLatency(hoveredCandidate.ttftP95)}</div>
          <div>ITL P95: {formatLatency(hoveredCandidate.itlP95)}</div>
          <div>End-to-end P95: {formatLatency(hoveredCandidate.e2eP95)}</div>
          <div>Throughput: {formatNumber(hoveredCandidate.throughput, 1)} tok/s</div>
          <div>KV Cache: {hoveredCandidate.kvCache ?? '—'} · Batch: {hoveredCandidate.batch ?? '—'}</div>
        </div>
      )}
    </div>
  );
};
