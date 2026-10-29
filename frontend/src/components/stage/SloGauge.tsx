import React from 'react';
import { formatNumber } from '../../lib/format';

interface SloGaugeProps {
  label: string;
  measured: number;
  threshold: number;
  unit: string;
  isUpperBound?: boolean;
  statistic?: string;
}

export const SloGauge: React.FC<SloGaugeProps> = ({
  label,
  measured,
  threshold,
  unit,
  isUpperBound = true,
  statistic = 'p95',
}) => {
  const isPassing = isUpperBound ? measured <= threshold : measured >= threshold;
  const maxScale = Math.max(threshold * 1.5, measured * 1.2, 1);
  const thresholdPct = Math.min(100, Math.max(0, (threshold / maxScale) * 100));
  const measuredPct = Math.min(100, Math.max(0, (measured / maxScale) * 100));

  const headroom = isUpperBound ? threshold - measured : measured - threshold;
  const headroomStr = isPassing
    ? `+${formatNumber(headroom, 1)} ${unit} margin`
    : `-${formatNumber(Math.abs(headroom), 1)} ${unit} breach`;

  return (
    <div
      className="slo-gauge"
      style={{
        padding: '12px 14px',
        backgroundColor: 'var(--surface, #0E120F)',
        border: '1px solid var(--border, #263124)',
        borderRadius: '5px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              textTransform: 'uppercase',
              color: 'var(--text-secondary, #A0AAA0)',
            }}
          >
            {label}
          </span>
          <span
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-muted, #727D73)',
            }}
          >
            ({statistic})
          </span>
        </div>

        <span
          style={{
            fontSize: '11px',
            fontFamily: 'var(--font-mono, monospace)',
            fontWeight: 600,
            color: isPassing ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)',
          }}
        >
          {headroomStr}
        </span>
      </div>

      {/* Numerical read-out */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #F0F3EF)' }}>
          {formatNumber(measured, 1)} <span style={{ fontSize: '12px', fontWeight: 400, color: 'var(--text-secondary, #A0AAA0)' }}>{unit}</span>
        </div>
        <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
          Ceiling: {formatNumber(threshold, 1)} {unit}
        </div>
      </div>

      {/* Visual meter bar */}
      <div
        style={{
          position: 'relative',
          height: '6px',
          backgroundColor: 'var(--raised, #151B15)',
          borderRadius: '3px',
          overflow: 'hidden',
          marginTop: '2px',
        }}
      >
        {/* Measured fill */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: `${measuredPct}%`,
            backgroundColor: isPassing ? 'var(--primary, #76B900)' : 'var(--error, #FF5555)',
            borderRadius: '3px',
            transition: 'width 220ms ease',
          }}
        />

        {/* Ceiling marker */}
        <div
          style={{
            position: 'absolute',
            left: `${thresholdPct}%`,
            top: 0,
            bottom: 0,
            width: '2px',
            backgroundColor: 'var(--text-primary, #F0F3EF)',
            zIndex: 2,
          }}
          title={`Declared ceiling: ${threshold} ${unit}`}
        />
      </div>
    </div>
  );
};
