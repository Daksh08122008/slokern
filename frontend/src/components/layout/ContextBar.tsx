import React from 'react';
import { DemoDataChip } from '../common/DemoDataChip';

interface ContextBarProps {
  experimentId?: string;
  runtimeName?: string;
  onOpenRuntimeModal?: () => void;
  onRunSmokeProbe?: () => void;
  isProbing?: boolean;
}

export const ContextBar: React.FC<ContextBarProps> = ({
  experimentId = 'EXP-0248',
  runtimeName = 'vLLM v0.6.3 · Nebius H100 SXM5',
  onOpenRuntimeModal,
  onRunSmokeProbe,
  isProbing = false,
}) => {
  return (
    <header
      className="context-bar"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '48px',
        padding: '0 20px',
        backgroundColor: 'var(--surface, #0E120F)',
        borderBottom: '1px solid var(--border, #263124)',
        zIndex: 50,
      }}
      role="banner"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Brand Mark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '10px',
              height: '10px',
              backgroundColor: 'var(--primary, #76B900)',
              borderRadius: '2px',
            }}
            aria-hidden="true"
          />
          <span
            style={{
              fontWeight: 800,
              fontSize: '14px',
              letterSpacing: '0.08em',
              color: 'var(--text-primary, #F0F3EF)',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            SLOKERN
          </span>
          <span
            style={{
              fontSize: '11px',
              color: 'var(--text-muted, #727D73)',
              fontFamily: 'var(--font-mono, monospace)',
              borderLeft: '1px solid var(--border, #263124)',
              paddingLeft: '8px',
            }}
          >
            v1.0-prod
          </span>
        </div>

        {/* Experiment Breadcrumb */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '12px',
            fontFamily: 'var(--font-mono, monospace)',
            color: 'var(--text-secondary, #A0AAA0)',
          }}
        >
          <span style={{ color: 'var(--text-muted, #727D73)' }}>/</span>
          <span>active-exp:</span>
          <span
            style={{
              color: 'var(--text-primary, #F0F3EF)',
              fontWeight: 600,
              backgroundColor: 'var(--raised, #151B15)',
              padding: '2px 6px',
              borderRadius: '3px',
              border: '1px solid var(--border, #263124)',
            }}
          >
            {experimentId}
          </span>
        </div>
      </div>

      {/* Right Controls: Runtime Profile, Smoke Probe, Demo Chip */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          type="button"
          onClick={onOpenRuntimeModal}
          style={{
            background: 'none',
            border: '1px solid var(--border, #263124)',
            backgroundColor: 'var(--raised, #151B15)',
            color: 'var(--text-secondary, #A0AAA0)',
            fontSize: '11px',
            fontFamily: 'var(--font-mono, monospace)',
            padding: '4px 8px',
            borderRadius: '4px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
          title="Inspect active serving runtime environment & hardware fingerprint"
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: 'var(--primary, #76B900)',
            }}
          />
          <span>{runtimeName}</span>
        </button>

        {onRunSmokeProbe && (
          <button
            type="button"
            onClick={onRunSmokeProbe}
            disabled={isProbing}
            style={{
              background: 'none',
              border: '1px solid var(--border-strong, #384635)',
              backgroundColor: 'var(--elevated, #1D251E)',
              color: 'var(--text-primary, #F0F3EF)',
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: '4px',
              cursor: isProbing ? 'not-allowed' : 'pointer',
              opacity: isProbing ? 0.6 : 1,
            }}
            title="Execute preflight smoke test probe"
          >
            {isProbing ? 'Probing...' : 'Smoke Probe'}
          </button>
        )}

        <DemoDataChip />
      </div>
    </header>
  );
};
