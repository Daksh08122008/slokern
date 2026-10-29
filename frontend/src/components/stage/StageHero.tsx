import React from 'react';
import { Badge } from '../common/Badge';
import type { HeadroomResult } from '../../lib/format';
import type { VerificationDerivationResult } from '../../lib/status';

interface StageHeroProps {
  candidateName: string;
  candidateId: string;
  runtimeModel: string;
  bindingHeadroom: HeadroomResult | null;
  verificationStatus: VerificationDerivationResult;
  throughputDelta?: string;
  onOpenDetails?: () => void;
  onReplay?: () => void;
}

export const StageHero: React.FC<StageHeroProps> = ({
  candidateName,
  candidateId,
  runtimeModel,
  bindingHeadroom,
  verificationStatus,
  throughputDelta = '+41.1% throughput vs baseline',
  onOpenDetails,
  onReplay,
}) => {
  const isPassing = bindingHeadroom ? bindingHeadroom.isPassing : verificationStatus.isVerifiedWinner;
  const absHeadroom = bindingHeadroom ? Math.abs(bindingHeadroom.absoluteHeadroom).toFixed(1) : '3.0';
  const unit = bindingHeadroom?.unit || 'ms';
  const constraintLabel = bindingHeadroom
    ? `${bindingHeadroom.constraintName} (${bindingHeadroom.threshold} ${unit} CEILING)`
    : 'P95 TTFT (50 ms CEILING)';

  return (
    <section
      className="stage-hero"
      style={{
        padding: '32px 36px',
        backgroundColor: 'var(--surface, #0E120F)',
        border: '1px solid',
        borderColor: verificationStatus.isVerifiedWinner
          ? 'var(--border-strong, #384635)'
          : 'var(--border, #263124)',
        borderRadius: '8px',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: verificationStatus.isVerifiedWinner ? 'var(--glow-winner)' : 'none',
      }}
      aria-label="Optimization Outcome Summary"
    >
      {/* Top Meta Line: Badges + Candidate Info */}
      <div className="stage-meta-bar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Badge tone={verificationStatus.statusType} size="md">
            {verificationStatus.badgeLabel}
          </Badge>
          <span
            style={{
              fontSize: '13px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              color: 'var(--text-primary, #F0F3EF)',
            }}
          >
            {candidateId} · {candidateName}
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted, #727D73)' }}>|</span>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary, #A0AAA0)', fontFamily: 'var(--font-mono, monospace)' }}>
            {runtimeModel}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {onReplay && verificationStatus.isVerifiedWinner && (
            <button
              type="button"
              onClick={onReplay}
              title="Replay reveal sequence (Hotkey: R)"
              aria-label="Replay reveal animation"
              style={{
                background: 'none',
                border: '1px solid var(--border, #263124)',
                backgroundColor: 'transparent',
                color: 'var(--text-secondary, #A0AAA0)',
                fontSize: '11px',
                fontFamily: 'var(--font-mono, monospace)',
                padding: '4px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Replay ↻
            </button>
          )}

          {onOpenDetails && (
            <button
              type="button"
              onClick={onOpenDetails}
              style={{
                background: 'none',
                border: '1px solid var(--border-strong, #384635)',
                backgroundColor: 'var(--raised, #151B15)',
                color: 'var(--text-primary, #F0F3EF)',
                fontSize: '12px',
                fontFamily: 'var(--font-mono, monospace)',
                fontWeight: 600,
                padding: '4px 12px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Inspect Parameters & Artifacts →
            </button>
          )}
        </div>
      </div>

      {/* Hero Headroom Numeral (Apple-grade Stage Scale) */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', flexWrap: 'wrap' }}>
        <div
          className="stage-numeral tabular-nums"
          style={{
            fontSize: 'var(--text-stage, clamp(56px, 11vw, 136px))',
            fontWeight: 800,
            lineHeight: 0.95,
            letterSpacing: '-0.04em',
            fontFamily: 'var(--font-mono, monospace)',
            color: isPassing ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)',
            textShadow: isPassing ? '0 0 24px rgba(118, 185, 0, 0.25)' : 'none',
          }}
        >
          {isPassing ? `+${absHeadroom}` : `-${absHeadroom}`}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span
            style={{
              fontSize: 'clamp(20px, 3.5vw, 36px)',
              fontWeight: 700,
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-primary, #F0F3EF)',
            }}
          >
            {unit}
          </span>
          <span
            style={{
              fontSize: '12px',
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--text-muted, #727D73)',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            {isPassing ? 'HEADROOM ON' : 'BREACH ON'} {constraintLabel}
          </span>
        </div>
      </div>

      {/* Bottom Summary Callout */}
      <div
        style={{
          marginTop: '20px',
          paddingTop: '16px',
          borderTop: '1px solid var(--border, #263124)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: '13px',
            color: 'var(--text-secondary, #A0AAA0)',
            lineHeight: 1.4,
          }}
        >
          {verificationStatus.reasonText}
        </p>

        <span
          style={{
            fontSize: '12px',
            fontFamily: 'var(--font-mono, monospace)',
            color: isPassing ? 'var(--primary-bright, #95D500)' : 'var(--text-muted, #727D73)',
            fontWeight: 600,
          }}
        >
          {throughputDelta}
        </span>
      </div>
    </section>
  );
};
