import React from 'react';

export type BadgeTone = 'verified' | 'feasible' | 'inconclusive' | 'infeasible' | 'error' | 'neutral' | 'demo' | 'warning';

interface BadgeProps {
  children: React.ReactNode;
  tone?: BadgeTone;
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  tone = 'neutral',
  size = 'md',
  icon,
  className = '',
}) => {
  const getStyles = (): { color: string; bg: string; border: string; glow?: string } => {
    switch (tone) {
      case 'verified':
        return {
          color: 'var(--primary-bright, #95D500)',
          bg: 'rgba(118, 185, 0, 0.12)',
          border: '1px solid var(--primary, #76B900)',
          glow: 'var(--glow-winner)',
        };
      case 'feasible':
        return {
          color: 'var(--text-secondary, #A0AAA0)',
          bg: 'rgba(160, 170, 160, 0.08)',
          border: '1px solid var(--border-strong, #384635)',
        };
      case 'inconclusive':
      case 'warning':
        return {
          color: 'var(--warning, #E9B949)',
          bg: 'rgba(233, 185, 73, 0.12)',
          border: '1px solid rgba(233, 185, 73, 0.35)',
        };
      case 'infeasible':
      case 'error':
        return {
          color: 'var(--error, #FF5555)',
          bg: 'rgba(255, 85, 85, 0.12)',
          border: '1px solid rgba(255, 85, 85, 0.35)',
        };
      case 'demo':
        return {
          color: 'var(--info, #8F9AA5)',
          bg: 'rgba(143, 154, 165, 0.08)',
          border: '1px solid var(--info-border, #394053)',
        };
      case 'neutral':
      default:
        return {
          color: 'var(--text-secondary, #A0AAA0)',
          bg: 'var(--raised, #151B15)',
          border: '1px solid var(--border, #263124)',
        };
    }
  };

  const s = getStyles();
  const isSm = size === 'sm';

  return (
    <span
      className={`slokern-badge ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: isSm ? '2px 6px' : '3px 8px',
        fontSize: '11px',
        fontWeight: 600,
        fontFamily: 'var(--font-mono, monospace)',
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        borderRadius: '3px',
        color: s.color,
        backgroundColor: s.bg,
        border: s.border,
        boxShadow: s.glow,
        whiteSpace: 'nowrap',
        lineHeight: 1.2,
      }}
    >
      {icon && <span style={{ display: 'inline-flex', alignItems: 'center' }}>{icon}</span>}
      {children}
    </span>
  );
};
