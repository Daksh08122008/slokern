import React from 'react';

export type WorkspaceDestination =
  | 'Overview'
  | 'Workloads'
  | 'Experiments'
  | 'Tuning Lab'
  | 'Verification'
  | 'Reports';

interface SidebarProps {
  currentWorkspace: WorkspaceDestination;
  onSelectWorkspace: (dest: WorkspaceDestination) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

interface NavItemDef {
  key: WorkspaceDestination;
  label: string;
  hotkey: string;
  icon: (size: number) => React.ReactNode;
}

const NAV_ITEMS: NavItemDef[] = [
  {
    key: 'Overview',
    label: 'Overview',
    hotkey: '1',
    icon: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    key: 'Workloads',
    label: 'Workloads',
    hotkey: '2',
    icon: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M4 6h16M4 12h16M4 18h16" />
        <circle cx="9" cy="6" r="2" fill="currentColor" />
        <circle cx="15" cy="12" r="2" fill="currentColor" />
        <circle cx="8" cy="18" r="2" fill="currentColor" />
      </svg>
    ),
  },
  {
    key: 'Experiments',
    label: 'Experiments',
    hotkey: '3',
    icon: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="m12 3 9 5-9 5-9-5 9-5Z" />
        <path d="m3 12 9 5 9-5M3 16l9 5 9-5" />
      </svg>
    ),
  },
  {
    key: 'Tuning Lab',
    label: 'Tuning Lab',
    hotkey: '4',
    icon: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M3 12h4l2.4-7 4.2 14 2.4-7H21" />
      </svg>
    ),
  },
  {
    key: 'Verification',
    label: 'Verification',
    hotkey: '5',
    icon: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 3 20 6v5c0 5-3.4 8-8 10-4.6-2-8-5-8-10V6l8-3Z" />
        <path d="m8.5 12 2.2 2.2 4.8-5" />
      </svg>
    ),
  },
  {
    key: 'Reports',
    label: 'Reports',
    hotkey: '6',
    icon: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M6 3.5h8l4 4v13H6z" />
        <path d="M14 3.5v4h4M9 12h6M9 16h6" />
      </svg>
    ),
  },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentWorkspace,
  onSelectWorkspace,
  collapsed = false,
  onToggleCollapse,
}) => {
  return (
    <aside
      className={`slokern-sidebar ${collapsed ? 'collapsed' : ''}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: collapsed ? '66px' : '244px',
        backgroundColor: 'var(--glass-chrome, rgba(14, 18, 15, 0.72))',
        backdropFilter: 'blur(16px)',
        borderRight: '1px solid var(--border, #263124)',
        userSelect: 'none',
        flexShrink: 0,
        height: '100%',
        boxSizing: 'border-box',
        transition: 'width 180ms cubic-bezier(0.16, 1, 0.3, 1)',
      }}
      role="navigation"
      aria-label="Main Navigation"
    >
      <div style={{ padding: collapsed ? '16px 8px 8px' : '16px 16px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {!collapsed && (
          <div
            style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              letterSpacing: '0.08em',
              color: 'var(--text-muted, #727D73)',
              textTransform: 'uppercase',
              paddingLeft: '8px',
            }}
          >
            Workspaces
          </div>
        )}
        {onToggleCollapse && (
          <button
            type="button"
            onClick={onToggleCollapse}
            title={collapsed ? 'Expand Sidebar (Ctrl+B)' : 'Collapse Sidebar (Ctrl+B)'}
            aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted, #727D73)',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: collapsed ? '0 auto 8px' : '0 0 8px',
            }}
          >
            <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              {collapsed ? (
                <path d="m9 18 6-6-6-6" />
              ) : (
                <path d="m15 18-6-6 6-6" />
              )}
            </svg>
          </button>
        )}
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '3px', padding: '0 8px', flex: 1 }}>
        {NAV_ITEMS.map((item) => {
          const isActive = currentWorkspace === item.key;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onSelectWorkspace(item.key)}
              aria-current={isActive ? 'page' : undefined}
              title={`${item.label} (Press ${item.hotkey})`}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'space-between',
                gap: '10px',
                width: '100%',
                padding: collapsed ? '10px 0' : '8px 12px',
                borderRadius: '5px',
                border: '1px solid',
                borderColor: isActive ? 'var(--border-strong, #384635)' : 'transparent',
                backgroundColor: isActive ? 'var(--raised, #151B15)' : 'transparent',
                color: isActive ? 'var(--text-primary, #F0F3EF)' : 'var(--text-secondary, #A0AAA0)',
                cursor: 'pointer',
                textAlign: 'left',
                position: 'relative',
                transition: 'background-color 140ms ease, color 140ms ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', color: isActive ? 'var(--primary, #76B900)' : 'inherit' }}>
                  {item.icon(17)}
                </span>
                {!collapsed && (
                  <span
                    style={{
                      fontSize: '13px',
                      fontWeight: isActive ? 600 : 450,
                      letterSpacing: '-0.01em',
                    }}
                  >
                    {item.label}
                  </span>
                )}
              </div>

              {!collapsed && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {isActive && (
                    <span
                      style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        backgroundColor: 'var(--primary, #76B900)',
                      }}
                      aria-hidden="true"
                    />
                  )}
                  <kbd
                    style={{
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono, monospace)',
                      color: 'var(--text-muted, #727D73)',
                      backgroundColor: 'rgba(255, 255, 255, 0.04)',
                      padding: '1px 5px',
                      borderRadius: '3px',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                    }}
                  >
                    {item.hotkey}
                  </kbd>
                </div>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer System Status */}
      <div
        style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border, #263124)',
          fontSize: '11px',
          fontFamily: 'var(--font-mono, monospace)',
          color: 'var(--text-muted, #727D73)',
          display: collapsed ? 'none' : 'block',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Budget Runs</span>
          <span style={{ color: 'var(--text-secondary, #A0AAA0)', fontWeight: 600 }}>6 / 6 max</span>
        </div>
      </div>
    </aside>
  );
};
