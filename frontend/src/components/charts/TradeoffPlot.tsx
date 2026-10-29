import React, { useState } from 'react';
import type { UICandidate } from '../../lib/adapters/viewModel';
import { formatLatency, formatThroughput } from '../../lib/format';

interface TradeoffPlotProps {
  candidates: UICandidate[];
  selectedCandidateId: string;
  onSelectCandidate: (candidate: UICandidate) => void;
  latencyCeilingMs?: number;
  throughputFloorTps?: number;
}

export const TradeoffPlot: React.FC<TradeoffPlotProps> = ({
  candidates,
  selectedCandidateId,
  onSelectCandidate,
  latencyCeilingMs = 50,
  throughputFloorTps = 50,
}) => {
  const [hoveredCandidate, setHoveredCandidate] = useState<UICandidate | null>(null);

  // Chart dimensions & margins
  const width = 560;
  const height = 340;
  const margin = { top: 30, right: 30, bottom: 45, left: 55 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  // Domain scales
  // X: Latency 15ms -> 80ms
  const xMin = 15;
  const xMax = 80;
  // Y: Throughput 35k -> 85k tok/s
  const yMin = 35;
  const yMax = 85;

  const scaleX = (val: number) => {
    const clamped = Math.max(xMin, Math.min(xMax, val));
    return margin.left + ((clamped - xMin) / (xMax - xMin)) * plotWidth;
  };

  const scaleY = (val: number) => {
    const clamped = Math.max(yMin, Math.min(yMax, val));
    return margin.top + plotHeight - ((clamped - yMin) / (yMax - yMin)) * plotHeight;
  };

  const ceilingX = scaleX(latencyCeilingMs);
  const floorY = scaleY(throughputFloorTps);

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
            Empirical measured points only · Zero interpolated curves
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
        {/* Feasible Zone Shading (Top-Left: latency <= ceiling, throughput >= floor) */}
        <rect
          x={margin.left}
          y={margin.top}
          width={Math.max(0, ceilingX - margin.left)}
          height={Math.max(0, floorY - margin.top)}
          fill="rgba(118, 185, 0, 0.04)"
          stroke="rgba(118, 185, 0, 0.12)"
          strokeDasharray="3 3"
        />
        <text
          x={margin.left + 8}
          y={margin.top + 16}
          fill="rgba(118, 185, 0, 0.5)"
          fontSize="11px"
          fontFamily="var(--font-mono, monospace)"
          fontWeight={600}
        >
          FEASIBLE REGION
        </text>

        {/* Grid lines */}
        {[20, 30, 40, 50, 60, 70].map((xVal) => (
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

        {[40, 50, 60, 70, 80].map((yVal) => (
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

        {/* SLO Latency Ceiling line */}
        <line
          x1={ceilingX}
          y1={margin.top}
          x2={ceilingX}
          y2={margin.top + plotHeight}
          stroke="var(--error, #FF5555)"
          strokeWidth={1.5}
          strokeDasharray="4 3"
        />
        <text
          x={ceilingX + 4}
          y={margin.top + 28}
          fill="var(--error, #FF5555)"
          fontSize="11px"
          fontFamily="var(--font-mono, monospace)"
          fontWeight={600}
        >
          P95 CEILING ({latencyCeilingMs} ms)
        </text>

        {/* SLO Throughput Floor line */}
        <line
          x1={margin.left}
          y1={floorY}
          x2={margin.left + plotWidth}
          y2={floorY}
          stroke="var(--warning, #E9B949)"
          strokeWidth={1.5}
          strokeDasharray="4 3"
        />
        <text
          x={margin.left + plotWidth - 140}
          y={floorY - 6}
          fill="var(--warning, #E9B949)"
          fontSize="11px"
          fontFamily="var(--font-mono, monospace)"
          fontWeight={600}
        >
          FLOOR ({throughputFloorTps}k tok/s)
        </text>

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
        {[20, 30, 40, 50, 60, 70, 80].map((xVal) => (
          <text
            key={`lbl-x-${xVal}`}
            x={scaleX(xVal)}
            y={margin.top + plotHeight + 16}
            fill="var(--text-muted, #727D73)"
            fontSize="11px"
            fontFamily="var(--font-mono, monospace)"
            textAnchor="middle"
          >
            {xVal}
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
          End-to-End Latency P95 (ms) →
        </text>

        {/* Y Axis Labels */}
        {[40, 50, 60, 70, 80].map((yVal) => (
          <text
            key={`lbl-y-${yVal}`}
            x={margin.left - 8}
            y={scaleY(yVal) + 4}
            fill="var(--text-muted, #727D73)"
            fontSize="11px"
            fontFamily="var(--font-mono, monospace)"
            textAnchor="end"
          >
            {yVal}k
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
          const cx = scaleX(c.p95);
          const cy = scaleY(c.throughput);
          const isSelected = c.id === selectedCandidateId;
          const isWinner = c.tag === 'WINNER';
          const isBaseline = c.id === 'C-01';

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
          <div>P95 Latency: {formatLatency(hoveredCandidate.p95)}</div>
          <div>TTFT P95: {formatLatency(hoveredCandidate.ttftP95)}</div>
          <div>ITL P95: {formatLatency(hoveredCandidate.itlP95)}</div>
          <div>Throughput: {formatThroughput(hoveredCandidate.throughput * 1000)}</div>
          <div>KV Cache: {hoveredCandidate.kvCache} · Batch: {hoveredCandidate.batch}</div>
        </div>
      )}
    </div>
  );
};
