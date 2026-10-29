import React, { useEffect } from 'react';

interface SlideOverDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  eyebrow?: string; // backwards compatibility
  children: React.ReactNode;
  width?: string;
}

export const SlideOverDrawer: React.FC<SlideOverDrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  eyebrow,
  children,
  width = '480px',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="slide-over-backdrop"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 100,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
    >
      <div
        className="slide-over-panel"
        style={{
          width: '100%',
          maxWidth: width,
          height: '100%',
          backgroundColor: 'var(--elevated, #1D251E)', // Solid elevated, NOT glass
          borderLeft: '1px solid var(--border-strong, #384635)',
          boxShadow: 'var(--shadow-lg, 0 8px 24px rgba(0, 0, 0, 0.75))',
          display: 'flex',
          flexDirection: 'column',
          boxSizing: 'border-box',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            borderBottom: '1px solid var(--border, #263124)',
            backgroundColor: 'var(--surface, #0E120F)',
          }}
        >
          <div>
            <h2
              id="drawer-title"
              style={{
                margin: 0,
                fontSize: '16px',
                fontWeight: 650,
                color: 'var(--text-primary, #F0F3EF)',
                letterSpacing: '-0.015em',
                textWrap: 'balance',
              }}
            >
              {title}
            </h2>
            {(subtitle || eyebrow) && (
              <div
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono, monospace)',
                  color: 'var(--text-secondary, #A0AAA0)',
                  marginTop: '3px',
                }}
              >
                {subtitle || eyebrow}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none',
              border: '1px solid var(--border, #263124)',
              backgroundColor: 'var(--raised, #151B15)',
              color: 'var(--text-secondary, #A0AAA0)',
              borderRadius: '4px',
              padding: '6px 8px',
              cursor: 'pointer',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Close inspector (Esc)"
            aria-label="Close"
          >
            <span style={{ fontSize: '14px', lineHeight: 1 }}>✕</span>
            <kbd style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', opacity: 0.7 }}>Esc</kbd>
          </button>
        </div>

        {/* Drawer Content */}
        <div
          style={{
            padding: '20px',
            overflowY: 'auto',
            flex: 1,
            color: 'var(--text-primary, #F0F3EF)',
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
};
