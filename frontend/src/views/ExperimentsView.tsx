import React, { useState } from 'react';
import { Badge } from '../components/common/Badge';
import { DemoDataChip } from '../components/common/DemoDataChip';
import { SegmentedControl } from '../components/common/SegmentedControl';
import { EmptyState } from '../components/common/EmptyState';
import { TelemetryScrubber } from '../components/charts/TelemetryScrubber';
import type { UIExperiment } from '../lib/adapters/viewModel';

interface ExperimentsViewProps {
  experiments: UIExperiment[];
  onSelectRun: (exp: UIExperiment) => void;
}

export const ExperimentsView: React.FC<ExperimentsViewProps> = ({
  experiments,
  onSelectRun,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'Completed' | 'Running' | 'Failed'>('all');
  const [selectedScrubberRun, setSelectedScrubberRun] = useState<string>('run_01HZX8F2');

  const filtered = experiments.filter((e) => {
    const matchesSearch =
      e.run.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.workload.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.model.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || e.state === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const getFeasibilityTone = (f: string) => {
    if (f === 'Feasible') return 'feasible';
    if (f === 'Infeasible') return 'infeasible';
    return 'inconclusive';
  };

  const getVerificationTone = (v: string) => {
    if (v === 'Verified') return 'verified';
    if (v === 'Failed') return 'infeasible';
    if (v === 'Pending') return 'warning';
    return 'neutral';
  };

  const getValidityTone = (v?: string) => {
    if (v === 'VALID') return 'neutral';
    if (v === 'STALE') return 'warning';
    return 'infeasible';
  };

  return (
    <div className="view-experiments workspace-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: 'var(--text-primary, #F0F3EF)', letterSpacing: '-0.025em', textWrap: 'balance' }}>
              Experiment Runs & Telemetry History
            </h1>
            <DemoDataChip size="sm" />
          </div>
          <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-secondary, #A0AAA0)', lineHeight: 1.45, textWrap: 'pretty', maxWidth: '75ch' }}>
            Search runs, execution states, offered-vs-achieved load audits, and unaggregated trace evidence
          </p>
        </div>
      </div>

      {/* Time-Series Empirical Request Scrubber Section */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', fontWeight: 650, color: 'var(--text-secondary, #A0AAA0)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Sample Stream Inspection · Active Run: {selectedScrubberRun}
          </span>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            Arrow keys scrub empirical samples (clamped HUD 16–84%)
          </span>
        </div>
        <TelemetryScrubber ttftCeilingMs={50.0} />
      </div>

      {/* Filter & Search Bar with SegmentedControl */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, maxWidth: '400px' }}>
          <input
            type="text"
            placeholder="Search run ID, workload, model, or candidate..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: 'var(--surface, #0E120F)',
              border: '1px solid var(--border, #263124)',
              borderRadius: '4px',
              padding: '6px 12px',
              fontSize: '12px',
              fontFamily: 'var(--font-mono, monospace)',
              color: 'var(--text-primary, #F0F3EF)',
              outline: 'none',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-muted, #727D73)' }}>
            State:
          </span>
          <SegmentedControl
            options={[
              { value: 'all', label: 'All Runs' },
              { value: 'Completed', label: 'Completed' },
              { value: 'Running', label: 'Running' },
              { value: 'Failed', label: 'Failed' },
            ]}
            value={statusFilter}
            onChange={setStatusFilter}
            size="sm"
          />
        </div>
      </div>

      {/* Table or EmptyState */}
      {filtered.length === 0 ? (
        <EmptyState
          title="No experiment runs match filter"
          description={`No recorded experiment runs matched query "${searchTerm}" under filter "${statusFilter}". Try searching by a different term or reset filters.`}
          actionLabel="Reset Filters"
          onAction={() => {
            setSearchTerm('');
            setStatusFilter('all');
          }}
        />
      ) : (
        <div
          style={{
            backgroundColor: 'var(--surface, #0E120F)',
            border: '1px solid var(--border, #263124)',
            borderRadius: '6px',
            overflow: 'hidden',
          }}
        >
          <div className="table-scroll" style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', fontFamily: 'var(--font-mono, monospace)', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--raised, #151B15)', borderBottom: '1px solid var(--border, #263124)', color: 'var(--text-secondary, #A0AAA0)' }}>
                  <th style={{ padding: '10px 16px' }}>RUN ID</th>
                  <th style={{ padding: '10px 16px' }}>WORKLOAD</th>
                  <th style={{ padding: '10px 16px' }}>MODEL</th>
                  <th style={{ padding: '10px 16px' }}>CANDIDATE</th>
                  <th style={{ padding: '10px 16px' }}>OFFERED / ACHIEVED</th>
                  <th style={{ padding: '10px 16px' }}>VALIDITY</th>
                  <th style={{ padding: '10px 16px' }}>SATURATION</th>
                  <th style={{ padding: '10px 16px' }}>STATE</th>
                  <th style={{ padding: '10px 16px' }}>FEASIBILITY</th>
                  <th style={{ padding: '10px 16px' }}>VERIFICATION</th>
                  <th style={{ padding: '10px 16px' }}>UPDATED</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((exp, idx) => {
                  const isScrubberActive = selectedScrubberRun === exp.run;
                  const reqRate = exp.requestedRateRps ?? 16.0;
                  const achRate = exp.achievedRateRps ?? (exp.state === 'Completed' ? 15.9 : 0.0);
                  const validity = exp.measurementValidity ?? 'VALID';
                  const isSaturated = exp.clientSaturation ?? false;

                  return (
                    <tr
                      key={exp.run}
                      onClick={() => {
                        setSelectedScrubberRun(exp.run);
                        onSelectRun(exp);
                      }}
                      style={{
                        borderBottom: idx === filtered.length - 1 ? 'none' : '1px solid var(--border, #263124)',
                        cursor: 'pointer',
                        backgroundColor: isScrubberActive
                          ? 'rgba(118, 185, 0, 0.08)'
                          : idx % 2 === 0
                          ? 'transparent'
                          : 'rgba(255,255,255,0.01)',
                        transition: 'background-color 140ms ease',
                      }}
                      onMouseEnter={(e) => {
                        if (!isScrubberActive) e.currentTarget.style.backgroundColor = 'var(--raised, #151B15)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isScrubberActive) {
                          e.currentTarget.style.backgroundColor = idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)';
                        }
                      }}
                      tabIndex={0}
                      role="button"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          setSelectedScrubberRun(exp.run);
                          onSelectRun(exp);
                        }
                      }}
                    >
                      <td style={{ padding: '10px 16px', color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>
                        {exp.run}
                      </td>
                      <td style={{ padding: '10px 16px', color: 'var(--text-primary, #F0F3EF)' }}>
                        {exp.workload}
                      </td>
                      <td style={{ padding: '10px 16px', color: 'var(--text-secondary, #A0AAA0)' }}>
                        {exp.model}
                      </td>
                      <td style={{ padding: '10px 16px', color: 'var(--text-primary, #F0F3EF)', fontWeight: 600 }}>
                        {exp.candidateId}
                      </td>
                      <td style={{ padding: '10px 16px', color: 'var(--text-primary, #F0F3EF)' }}>
                        <span>{reqRate.toFixed(1)}</span>
                        <span style={{ color: 'var(--text-muted, #727D73)', margin: '0 4px' }}>/</span>
                        <span style={{ color: achRate >= reqRate * 0.95 ? 'var(--primary-bright, #95D500)' : 'var(--warning, #E9B949)', fontWeight: 600 }}>
                          {achRate.toFixed(1)} rps
                        </span>
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        <Badge tone={getValidityTone(validity)} size="sm">
                          {validity}
                        </Badge>
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        <span style={{ color: isSaturated ? 'var(--error, #FF5555)' : 'var(--text-muted, #727D73)' }}>
                          {isSaturated ? 'SATURATED' : 'NOMINAL'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        <Badge tone={exp.state === 'Completed' ? 'neutral' : exp.state === 'Running' ? 'warning' : 'infeasible'} size="sm">
                          {exp.state}
                        </Badge>
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        <Badge tone={getFeasibilityTone(exp.feasibility)} size="sm">
                          {exp.feasibility}
                        </Badge>
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        <Badge tone={getVerificationTone(exp.verification)} size="sm">
                          {exp.verification}
                        </Badge>
                      </td>
                      <td style={{ padding: '10px 16px', color: 'var(--text-muted, #727D73)' }}>
                        {exp.updated}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
