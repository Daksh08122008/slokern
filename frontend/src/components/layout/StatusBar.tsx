import React from 'react';
import { DemoDataChip } from '../common/DemoDataChip';

export type ScenarioType = 'standard' | 'verification-failed' | 'no-feasible' | 'stale-evidence';

interface StatusBarProps {
  scenario: ScenarioType;
  onScenarioChange: (s: ScenarioType) => void;
  healthStatus?: 'ok' | 'degraded' | 'error';
  healthPingMs?: number;
  activeRunId?: string;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  scenario,
  onScenarioChange,
  healthStatus = 'ok',
  healthPingMs = 14,
  activeRunId = 'run_01HZX8F2',
}) => {
  const getHealthColor = () => {
    switch (healthStatus) {
      case 'ok':
        return 'var(--primary, #76B900)';
      case 'degraded':
        return 'var(--warning, #E9B949)';
      case 'error':
      default:
        return 'var(--error, #FF5555)';
    }
  };

  return (
    <footer
      className="status-bar"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '32px',
        padding: '0 16px',
        backgroundColor: 'var(--surface, #0E120F)',
        borderTop: '1px solid var(--border, #263124)',
        fontSize: '11px',
        fontFamily: 'var(--font-mono, monospace)',
        color: 'var(--text-secondary, #A0AAA0)',
        zIndex: 40,
        userSelect: 'none',
      }}
      role="contentinfo"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <DemoDataChip size="sm" />

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-muted, #727D73)' }}>scenario:</span>
          <select
            value={scenario}
            onChange={(e) => onScenarioChange(e.target.value as ScenarioType)}
            style={{
              backgroundColor: 'var(--raised, #151B15)',
              border: '1px solid var(--border, #263124)',
              color: 'var(--text-primary, #F0F3EF)',
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              padding: '2px 6px',
              borderRadius: '3px',
              cursor: 'pointer',
              outline: 'none',
            }}
            title="Switch deterministic demo scenario"
            aria-label="Demo Scenario Selector"
          >
            <option value="standard">standard (C-02 Verified Winner)</option>
            <option value="verification-failed">verification-failed (Drift Breach)</option>
            <option value="no-feasible">no-feasible (All Breaching)</option>
            <option value="stale-evidence">stale-evidence (Clock Expired)</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ color: 'var(--text-muted, #727D73)' }}>active_run:</span>
          <span style={{ color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>{activeRunId}</span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: getHealthColor(),
              display: 'inline-block',
            }}
            aria-hidden="true"
          />
          <span style={{ textTransform: 'uppercase' }}>control-plane: {healthStatus}</span>
          <span style={{ color: 'var(--text-muted, #727D73)' }}>({healthPingMs}ms)</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted, #727D73)' }}>
          <span>Switch:</span>
          <kbd style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', padding: '1px 4px', borderRadius: '2px', border: '1px solid rgba(255,255,255,0.08)' }}>1-6</kbd>
        </div>
      </div>
    </footer>
  );
};
