import React from 'react';

interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  tone?: 'neutral' | 'success' | 'warning' | 'danger';
  subtext?: string;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  delta,
  tone = 'neutral',
  subtext,
  className = '',
}) => {
  const getDeltaColor = () => {
    switch (tone) {
      case 'success':
        return 'var(--primary-bright, #95D500)';
      case 'warning':
        return 'var(--warning, #E9B949)';
      case 'danger':
        return 'var(--error, #FF5555)';
      case 'neutral':
      default:
        return 'var(--text-secondary, #A0AAA0)';
    }
  };

  return (
    <div
      className={`slokern-metric-card ${className}`}
      style={{
        padding: '14px 16px',
        backgroundColor: 'var(--surface, #0E120F)',
        border: '1px solid var(--border, #263124)',
        borderRadius: '5px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
      }}
    >
      <div
        style={{
          fontSize: '11px',
          fontFamily: 'var(--font-mono, monospace)',
          fontWeight: 600,
          color: 'var(--text-secondary, #A0AAA0)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        {label}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
        <span
          className="tabular-nums"
          style={{
            fontSize: '22px',
            fontWeight: 700,
            fontFamily: 'var(--font-mono, monospace)',
            color: 'var(--text-primary, #F0F3EF)',
          }}
        >
          {value}
        </span>
        {unit && (
          <span style={{ fontSize: '12px', color: 'var(--text-secondary, #A0AAA0)' }}>
            {unit}
          </span>
        )}
      </div>

      {(delta || subtext) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', marginTop: '2px' }}>
          {delta && <span style={{ color: getDeltaColor(), fontWeight: 600 }}>{delta}</span>}
          {subtext && <span style={{ color: 'var(--text-muted, #727D73)' }}>{subtext}</span>}
        </div>
      )}
    </div>
  );
};
