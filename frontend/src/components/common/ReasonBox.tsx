import React from 'react';
import type { ReasonCode } from '../../types/contracts';

interface ReasonBoxProps {
  reasonCode?: ReasonCode | string;
  detailText?: string;
  isPassing?: boolean;
}

export const ReasonBox: React.FC<ReasonBoxProps> = ({
  reasonCode,
  detailText,
  isPassing = false,
}) => {
  return (
    <div
      className="reason-box"
      style={{
        padding: '10px 12px',
        backgroundColor: isPassing ? 'rgba(118, 185, 0, 0.08)' : 'rgba(255, 85, 85, 0.08)',
        border: '1px solid',
        borderColor: isPassing ? 'rgba(118, 185, 0, 0.3)' : 'rgba(255, 85, 85, 0.3)',
        borderRadius: '4px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
      }}
    >
      <div
        style={{
          fontSize: '11px',
          fontFamily: 'var(--font-mono, monospace)',
          fontWeight: 700,
          color: isPassing ? 'var(--primary-bright, #95D500)' : 'var(--error, #FF5555)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        {reasonCode ? `Reason Code: ${reasonCode}` : 'Evaluator reason code unavailable'}
      </div>
      {detailText && (
        <div style={{ fontSize: '12px', color: 'var(--text-primary, #F0F3EF)', lineHeight: 1.4 }}>
          {detailText}
        </div>
      )}
    </div>
  );
};
