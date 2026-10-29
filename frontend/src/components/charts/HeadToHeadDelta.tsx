import React from 'react';
import { formatNumber } from '../../lib/format';

interface HeadToHeadDeltaProps {
  label: string;
  baselineVal: number;
  candidateVal: number;
  unit: string;
  isLowerBetter?: boolean;
}

export const HeadToHeadDelta: React.FC<HeadToHeadDeltaProps> = ({
  label,
  baselineVal,
  candidateVal,
  unit,
  isLowerBetter = true,
}) => {
  const delta = candidateVal - baselineVal;
  const pctChange = baselineVal !== 0 ? (delta / baselineVal) * 100 : 0;
  const isImprovement = isLowerBetter ? delta < 0 : delta > 0;

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 10px',
        backgroundColor: 'var(--raised, #151B15)',
        borderRadius: '4px',
        fontSize: '12px',
        fontFamily: 'var(--font-mono, monospace)',
      }}
    >
      <span style={{ color: 'var(--text-secondary, #A0AAA0)' }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{ color: 'var(--text-muted, #727D73)' }}>
          {formatNumber(baselineVal, 1)} {unit}
        </span>
        <span style={{ color: 'var(--border-strong, #384635)' }}>→</span>
        <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>
          {formatNumber(candidateVal, 1)} {unit}
        </span>
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            color: isImprovement ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)',
          }}
        >
          ({delta > 0 ? `+${formatNumber(pctChange, 1)}%` : `${formatNumber(pctChange, 1)}%`})
        </span>
      </div>
    </div>
  );
};
