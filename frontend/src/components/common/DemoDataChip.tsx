import React from 'react';

interface DemoDataChipProps {
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const DemoDataChip: React.FC<DemoDataChipProps> = ({
  label = 'DEMO DATA',
  size = 'md',
  className = '',
}) => {
  const isSm = size === 'sm';
  return (
    <span
      className={`demo-data-chip ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: isSm ? '2px 6px' : '3px 8px',
        fontSize: isSm ? '11px' : '11px',
        fontWeight: 600,
        fontFamily: 'var(--font-mono, monospace)',
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: 'var(--info, #8F9AA5)',
        backgroundColor: 'rgba(143, 154, 165, 0.08)',
        border: '1px solid var(--info-border, #394053)',
        borderRadius: '3px',
        userSelect: 'none',
        lineHeight: 1.2,
      }}
      title="Deterministic demo fixture. Not an active GPU hardware telemetry stream."
      role="status"
      aria-label="Demo data fixture"
    >
      <span
        style={{
          width: '5px',
          height: '5px',
          borderRadius: '50%',
          backgroundColor: 'var(--info, #8F9AA5)',
          display: 'inline-block',
          opacity: 0.85,
        }}
        aria-hidden="true"
      />
      {label}
    </span>
  );
};
