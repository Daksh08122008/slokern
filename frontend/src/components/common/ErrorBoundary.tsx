import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public override state: ErrorBoundaryState = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    // Keep telemetry safe: do not leak credentials
    console.error('[SLOKern ErrorBoundary] Uncaught render exception:', error.message);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          className="error-boundary-container"
          style={{
            margin: '24px 0',
            padding: '24px 28px',
            backgroundColor: 'var(--surface, #0E120F)',
            border: '1px solid var(--error, #FF5555)',
            borderRadius: '6px',
            boxShadow: '0 4px 20px rgba(255, 85, 85, 0.15)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
          role="alert"
          aria-live="assertive"
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  padding: '3px 8px',
                  borderRadius: '3px',
                  color: 'var(--error, #FF5555)',
                  backgroundColor: 'rgba(255, 85, 85, 0.12)',
                  border: '1px solid rgba(255, 85, 85, 0.35)',
                }}
              >
                EXECUTION_RENDER_ERROR
              </span>
              <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)' }}>
                {this.props.fallbackTitle || 'Component Render Failure Safely Intercepted'}
              </h2>
            </div>

            <button
              type="button"
              onClick={this.handleReset}
              style={{
                backgroundColor: 'var(--raised, #151B15)',
                border: '1px solid var(--border-strong, #384635)',
                color: 'var(--text-primary, #F0F3EF)',
                fontSize: '12px',
                fontFamily: 'var(--font-mono, monospace)',
                fontWeight: 600,
                padding: '6px 14px',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Recover & Reload View ↺
            </button>
          </div>

          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', lineHeight: 1.45 }}>
            A rendering exception was isolated by the SLOKern Workstation Error Boundary. The remainder of the application, control plane connections, and telemetry stores remain uncorrupted.
          </p>

          <div
            style={{
              padding: '10px 14px',
              backgroundColor: 'var(--canvas, #080A09)',
              border: '1px solid var(--border, #263124)',
              borderRadius: '4px',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--error, #FF5555)',
              overflowX: 'auto',
            }}
          >
            {this.state.error?.message || 'Unknown render exception'}
          </div>

          {this.state.errorInfo?.componentStack && (
            <details style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
              <summary style={{ cursor: 'pointer', padding: '4px 0', userSelect: 'none' }}>
                Component Stack Trace
              </summary>
              <pre style={{ margin: '8px 0 0', padding: '8px', backgroundColor: 'var(--raised, #151B15)', borderRadius: '4px', overflowX: 'auto', color: 'var(--text-secondary, #A0AAA0)' }}>
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
