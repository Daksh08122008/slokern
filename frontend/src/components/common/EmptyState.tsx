import React from 'react';

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  icon,
}) => {
  return (
    <div
      className="empty-state"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
        backgroundColor: 'var(--surface, #0E120F)',
        border: '1px solid var(--border, #263124)',
        borderRadius: '6px',
        gap: '12px',
      }}
    >
      {icon && (
        <div style={{ color: 'var(--text-muted, #727D73)', marginBottom: '4px' }}>
          {icon}
        </div>
      )}
      <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
        {title}
      </h3>
      <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', maxWidth: '420px', lineHeight: 1.5 }}>
        {description}
      </p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          style={{
            marginTop: '8px',
            backgroundColor: 'var(--elevated, #1D251E)',
            border: '1px solid var(--border-strong, #384635)',
            color: 'var(--text-primary, #F0F3EF)',
            padding: '6px 14px',
            borderRadius: '4px',
            fontSize: '12px',
            fontFamily: 'var(--font-mono, monospace)',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
