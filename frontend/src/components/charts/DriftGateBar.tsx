import React from 'react';
import { formatNumber } from '../../lib/format';

interface DriftGateBarProps {
  metricName: string;
  measuredDrift: number;
  toleranceThreshold?: number | null;
  unit: string;
  isAbsolute?: boolean;
}

export const DriftGateBar: React.FC<DriftGateBarProps> = ({
  metricName,
  measuredDrift,
  toleranceThreshold,
  unit,
}) => {
  const isToleranceDeclared = toleranceThreshold !== undefined && toleranceThreshold !== null && !Number.isNaN(toleranceThreshold);
  const absDrift = Math.abs(measuredDrift);
  const isPassing = isToleranceDeclared ? absDrift <= toleranceThreshold : false;

  const maxScale = isToleranceDeclared ? Math.max(toleranceThreshold * 1.6, absDrift * 1.2, 1) : Math.max(absDrift * 1.5, 1);
  const driftPct = Math.min(100, Math.max(0, (absDrift / maxScale) * 100));
  const tolPct = isToleranceDeclared ? Math.min(100, Math.max(0, (toleranceThreshold / maxScale) * 100)) : 0;

  return (
    <div
      className="drift-gate-bar"
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
        <span
          style={{
            fontSize: '11px',
            fontFamily: 'var(--font-mono, monospace)',
            fontWeight: 600,
            textTransform: 'uppercase',
            color: 'var(--text-secondary, #A0AAA0)',
          }}
        >
          {metricName} Drift
        </span>

        {isToleranceDeclared ? (
          <span
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              color: isPassing ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)',
            }}
          >
            {isPassing ? 'WITHIN TOLERANCE' : 'DRIFT BREACH'} ({measuredDrift > 0 ? `+${formatNumber(measuredDrift, 1)}` : formatNumber(measuredDrift, 1)} {unit})
          </span>
        ) : (
          <span
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              color: 'var(--warning, #E9B949)',
            }}
          >
            TOLERANCE UNDECLARED
          </span>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>
        <div style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>
          Drift: {formatNumber(absDrift, 2)} {unit}
        </div>
        <div style={{ color: 'var(--text-muted, #727D73)' }}>
          Declared Gate: {isToleranceDeclared ? `±${formatNumber(toleranceThreshold, 1)} ${unit}` : 'None'}
        </div>
      </div>

      {/* Meter Bar */}
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
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: `${driftPct}%`,
            backgroundColor: !isToleranceDeclared
              ? 'var(--warning, #E9B949)'
              : isPassing
              ? 'var(--primary, #76B900)'
              : 'var(--error, #FF5555)',
            borderRadius: '3px',
            transition: 'width 220ms ease',
          }}
        />

        {isToleranceDeclared && (
          <div
            style={{
              position: 'absolute',
              left: `${tolPct}%`,
              top: 0,
              bottom: 0,
              width: '2px',
              backgroundColor: 'var(--text-primary, #F0F3EF)',
              zIndex: 2,
            }}
            title={`Declared tolerance threshold: ${toleranceThreshold} ${unit}`}
          />
        )}
      </div>
    </div>
  );
};
