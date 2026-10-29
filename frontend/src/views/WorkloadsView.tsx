import React, { useState } from 'react';
import { DemoDataChip } from '../components/common/DemoDataChip';
import type { WorkloadSpec, ArrivalMode } from '../types/contracts';

interface WorkloadsViewProps {
  onSaveWorkload?: (spec: WorkloadSpec) => void;
  onLaunchBenchmark?: (spec: WorkloadSpec) => void;
  isLaunching?: boolean;
}

export const WorkloadsView: React.FC<WorkloadsViewProps> = ({
  onLaunchBenchmark,
  isLaunching = false,
}) => {
  const [workloadName, setWorkloadName] = useState('chat-completions-prod');
  const [arrivalMode, setArrivalMode] = useState<ArrivalMode>('poisson');
  const [targetRate, setTargetRate] = useState(16);
  const [concurrency, setConcurrency] = useState(32);
  const [warmupSec, setWarmupSec] = useState(15);
  const [measureSec, setMeasureSec] = useState(60);
  const [maxInputTok, setMaxInputTok] = useState(1024);
  const [maxOutputTok, setMaxOutputTok] = useState(256);

  // SLO Ceilings
  const [ttftCeiling, setTtftCeiling] = useState(50);
  const [itlCeiling, setItlCeiling] = useState(15);
  const [throughputFloor, setThroughputFloor] = useState(50);
  const [errorRateCeiling, setErrorRateCeiling] = useState(1.0);

  // Hardened Validation (guards against NaN, Infinity, negative values, and empty strings)
  const errors: string[] = [];
  if (!workloadName || workloadName.trim().length === 0) {
    errors.push('Workload identifier cannot be empty');
  }
  if (Number.isNaN(targetRate) || !Number.isFinite(targetRate) || targetRate <= 0) {
    errors.push('Target rate must be a valid number > 0 rps');
  }
  if (Number.isNaN(concurrency) || !Number.isFinite(concurrency) || concurrency <= 0) {
    errors.push('Concurrency limit must be a valid integer > 0');
  }
  if (Number.isNaN(warmupSec) || !Number.isFinite(warmupSec) || warmupSec < 5) {
    errors.push('Warm-up duration must be at least 5s to ensure GPU cache thermalization');
  }
  if (Number.isNaN(measureSec) || !Number.isFinite(measureSec) || measureSec < 15) {
    errors.push('Measurement duration must be at least 15s for statistically valid sample sizes');
  }
  if (Number.isNaN(maxInputTok) || !Number.isFinite(maxInputTok) || maxInputTok <= 0) {
    errors.push('Max input tokens must be > 0');
  }
  if (Number.isNaN(maxOutputTok) || !Number.isFinite(maxOutputTok) || maxOutputTok <= 0) {
    errors.push('Max output tokens must be > 0');
  }
  if (Number.isNaN(ttftCeiling) || !Number.isFinite(ttftCeiling) || ttftCeiling <= 0) {
    errors.push('TTFT ceiling must be > 0 ms');
  }
  if (Number.isNaN(itlCeiling) || !Number.isFinite(itlCeiling) || itlCeiling <= 0) {
    errors.push('ITL ceiling must be > 0 ms');
  }
  if (Number.isNaN(throughputFloor) || !Number.isFinite(throughputFloor) || throughputFloor <= 0) {
    errors.push('Throughput floor must be > 0 tok/s');
  }
  if (Number.isNaN(errorRateCeiling) || !Number.isFinite(errorRateCeiling) || errorRateCeiling < 0) {
    errors.push('Error rate ceiling must be >= 0%');
  }

  const isValid = errors.length === 0;

  const currentSpec: WorkloadSpec = {
    schema_version: '1.0.0',
    workload_name: workloadName,
    fixture_id: 'sharegpt-v3-eval',
    arrival_mode: arrivalMode,
    target_offered_rate: targetRate,
    concurrency_limit: concurrency,
    warmup_duration_s: warmupSec,
    measurement_duration_s: measureSec,
    max_input_tokens: maxInputTok,
    max_output_tokens: maxOutputTok,
  };

  return (
    <div className="view-workloads workspace-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', letterSpacing: '-0.025em', textWrap: 'balance' }}>
              Workload & Service-Level Objectives
            </h1>
            <DemoDataChip size="sm" />
          </div>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', lineHeight: 1.45, textWrap: 'pretty', maxWidth: '75ch' }}>
            Define arrival patterns, token distributions, and hard constraint thresholds before measuring
          </p>
        </div>

        {onLaunchBenchmark && (
          <button
            type="button"
            onClick={() => onLaunchBenchmark(currentSpec)}
            disabled={!isValid || isLaunching}
            style={{
              backgroundColor: isValid && !isLaunching ? 'var(--primary, #76B900)' : 'var(--raised, #151B15)',
              border: '1px solid',
              borderColor: isValid && !isLaunching ? 'var(--primary-bright, #95D500)' : 'var(--border, #263124)',
              color: isValid && !isLaunching ? '#080A09' : 'var(--text-muted, #727D73)',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 700,
              padding: '8px 18px',
              borderRadius: '4px',
              cursor: isValid && !isLaunching ? 'pointer' : 'not-allowed',
            }}
          >
            {isLaunching ? 'Running Preflight Probe...' : 'Validate & Preflight Check →'}
          </button>
        )}
      </div>

      {/* Validation Errors Notice */}
      {errors.length > 0 && (
        <div style={{ padding: '12px 16px', backgroundColor: 'rgba(255, 85, 85, 0.1)', border: '1px solid rgba(255, 85, 85, 0.35)', borderRadius: '4px' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--error, #FF5555)', marginBottom: '4px' }}>
            Specification Validation Blockers:
          </div>
          <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: 'var(--text-primary, #F0F3EF)' }}>
            {errors.map((err) => (
              <li key={err}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Two Column Grid: Workload Parameters + Hard SLO Constraints */}
      <div className="workloads-form-grid">
        {/* Left: Workload Parameters */}
        <div
          style={{
            backgroundColor: 'var(--surface, #0E120F)',
            border: '1px solid var(--border, #263124)',
            borderRadius: '6px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
            Workload Traffic Profile
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12px', fontFamily: 'var(--font-mono, monospace)' }}>
            <div>
              <label style={{ display: 'block', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                Workload Identifier
              </label>
              <input
                type="text"
                value={workloadName}
                onChange={(e) => setWorkloadName(e.target.value)}
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '8px 10px',
                  backgroundColor: 'var(--raised, #151B15)',
                  border: '1px solid var(--border, #263124)',
                  color: 'var(--text-primary, #F0F3EF)',
                  borderRadius: '4px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                Arrival Pattern
              </label>
              <select
                value={arrivalMode}
                onChange={(e) => setArrivalMode(e.target.value as ArrivalMode)}
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '8px 10px',
                  backgroundColor: 'var(--raised, #151B15)',
                  border: '1px solid var(--border, #263124)',
                  color: 'var(--text-primary, #F0F3EF)',
                  borderRadius: '4px',
                }}
              >
                <option value="poisson">Poisson Process (Stochastic Memoryless Inter-Arrivals)</option>
                <option value="constant">Constant Interval (Deterministic Cadence)</option>
                <option value="closed">Closed Loop (Concurrency Bound Driven)</option>
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                  Target Offered Rate (rps)
                </label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={Number.isNaN(targetRate) ? '' : targetRate}
                  onChange={(e) => setTargetRate(e.target.value === '' ? NaN : Number(e.target.value))}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '8px 10px',
                    backgroundColor: 'var(--raised, #151B15)',
                    border: '1px solid var(--border, #263124)',
                    color: 'var(--text-primary, #F0F3EF)',
                    borderRadius: '4px',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                  Concurrency Limit
                </label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={Number.isNaN(concurrency) ? '' : concurrency}
                  onChange={(e) => setConcurrency(e.target.value === '' ? NaN : Number(e.target.value))}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '8px 10px',
                    backgroundColor: 'var(--raised, #151B15)',
                    border: '1px solid var(--border, #263124)',
                    color: 'var(--text-primary, #F0F3EF)',
                    borderRadius: '4px',
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                  Warm-up Duration (s)
                </label>
                <input
                  type="number"
                  min="5"
                  step="1"
                  value={Number.isNaN(warmupSec) ? '' : warmupSec}
                  onChange={(e) => setWarmupSec(e.target.value === '' ? NaN : Number(e.target.value))}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '8px 10px',
                    backgroundColor: 'var(--raised, #151B15)',
                    border: '1px solid var(--border, #263124)',
                    color: 'var(--text-primary, #F0F3EF)',
                    borderRadius: '4px',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                  Measure Duration (s)
                </label>
                <input
                  type="number"
                  min="15"
                  step="1"
                  value={Number.isNaN(measureSec) ? '' : measureSec}
                  onChange={(e) => setMeasureSec(e.target.value === '' ? NaN : Number(e.target.value))}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '8px 10px',
                    backgroundColor: 'var(--raised, #151B15)',
                    border: '1px solid var(--border, #263124)',
                    color: 'var(--text-primary, #F0F3EF)',
                    borderRadius: '4px',
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                  Max Input Tokens
                </label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={Number.isNaN(maxInputTok) ? '' : maxInputTok}
                  onChange={(e) => setMaxInputTok(e.target.value === '' ? NaN : Number(e.target.value))}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '8px 10px',
                    backgroundColor: 'var(--raised, #151B15)',
                    border: '1px solid var(--border, #263124)',
                    color: 'var(--text-primary, #F0F3EF)',
                    borderRadius: '4px',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                  Max Output Tokens
                </label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={Number.isNaN(maxOutputTok) ? '' : maxOutputTok}
                  onChange={(e) => setMaxOutputTok(e.target.value === '' ? NaN : Number(e.target.value))}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '8px 10px',
                    backgroundColor: 'var(--raised, #151B15)',
                    border: '1px solid var(--border, #263124)',
                    color: 'var(--text-primary, #F0F3EF)',
                    borderRadius: '4px',
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right: Hard SLO Constraints */}
        <div
          style={{
            backgroundColor: 'var(--surface, #0E120F)',
            border: '1px solid var(--border, #263124)',
            borderRadius: '6px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 650, color: 'var(--text-primary, #F0F3EF)' }}>
              Deterministic Hard Constraints
            </h2>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--primary-bright, #95D500)' }}>
              policy: slo-prod-03
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '12px', fontFamily: 'var(--font-mono, monospace)' }}>
            <div>
              <label style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                <span>TTFT Ceiling (P95 Latency)</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>{ttftCeiling} ms</span>
              </label>
              <input
                type="range"
                min="20"
                max="150"
                value={ttftCeiling}
                onChange={(e) => setTtftCeiling(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary, #76B900)' }}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-muted, #727D73)' }}>
                Maximum allowable time to first token for prefill burst.
              </span>
            </div>

            <div>
              <label style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                <span>ITL Ceiling (P95 Inter-Token Latency)</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>{itlCeiling} ms</span>
              </label>
              <input
                type="range"
                min="5"
                max="50"
                value={itlCeiling}
                onChange={(e) => setItlCeiling(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary, #76B900)' }}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-muted, #727D73)' }}>
                Maximum token generation cadence during decode phase.
              </span>
            </div>

            <div>
              <label style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                <span>Throughput Floor</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>{throughputFloor}k tok/s</span>
              </label>
              <input
                type="range"
                min="20"
                max="120"
                value={throughputFloor}
                onChange={(e) => setThroughputFloor(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary, #76B900)' }}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-muted, #727D73)' }}>
                Minimum aggregate token throughput required to pass.
              </span>
            </div>

            <div>
              <label style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary, #A0AAA0)', marginBottom: '4px' }}>
                <span>Error Rate Ceiling</span>
                <span style={{ color: 'var(--text-primary, #F0F3EF)' }}>{errorRateCeiling}%</span>
              </label>
              <input
                type="range"
                min="0.1"
                max="5.0"
                step="0.1"
                value={errorRateCeiling}
                onChange={(e) => setErrorRateCeiling(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary, #76B900)' }}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-muted, #727D73)' }}>
                Strict rejection threshold for non-200 HTTP responses.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
