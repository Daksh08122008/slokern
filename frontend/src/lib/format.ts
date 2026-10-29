/**
 * Formatting and mathematical calculation helpers for SLOKern telemetry
 * Strictly enforces tabular numbers, unit clarity, and binding constraint headroom math.
 */

import type { SLOConstraint } from '../types/contracts';

export function formatNumber(val: number | null | undefined, decimals = 1): string {
  if (val === null || val === undefined || Number.isNaN(val) || !Number.isFinite(val)) return '—';
  return val.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatLatency(ms: number | null | undefined, decimals = 1): string {
  if (ms === null || ms === undefined || Number.isNaN(ms) || !Number.isFinite(ms)) return '—';
  const abs = Math.abs(ms);
  const sign = ms < 0 ? '-' : '';
  if (abs > 0 && abs < 1) return `${sign}${(abs * 1000).toFixed(0)} µs`;
  if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(2)} s`;
  return `${sign}${abs.toFixed(decimals)} ms`;
}

export function formatThroughput(tps: number | null | undefined, decimals = 1): string {
  if (tps === null || tps === undefined || Number.isNaN(tps) || !Number.isFinite(tps)) return '—';
  const abs = Math.abs(tps);
  const sign = tps < 0 ? '-' : '';
  if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(decimals)}k tok/s`;
  return `${sign}${abs.toFixed(decimals)} tok/s`;
}

export function formatPercent(fraction: number | null | undefined, decimals = 2): string {
  if (fraction === null || fraction === undefined || Number.isNaN(fraction) || !Number.isFinite(fraction)) return '—';
  return `${(fraction * 100).toFixed(decimals)}%`;
}

export interface HeadroomResult {
  constraintName: string;
  metricName: string;
  statistic: string;
  threshold: number;
  measured: number;
  unit: string;
  operator: '<=' | '<' | '>=' | '>';
  isPassing: boolean;
  relativeHeadroomFraction: number; // e.g. 0.06 for 6% headroom, negative if breach
  absoluteHeadroom: number;         // e.g. 3.0 for 3ms headroom, negative if breach
  formattedHeadroom: string;        // "3.0 ms headroom" or "18.0 ms over ceiling"
  headroomPercentage: number;       // e.g. 6.0 (%)
}

/**
 * Computes the binding constraint (the constraint with the least margin / most critical headroom)
 * from a list of SLO constraints and observed metrics.
 */
export function computeBindingConstraintHeadroom(
  constraints: SLOConstraint[],
  measuredValues: Record<string, number | null | undefined>
): HeadroomResult | null {
  if (!constraints || constraints.length === 0) return null;

  let mostBinding: HeadroomResult | null = null;

  for (const c of constraints) {
    // Generate potential metric lookup keys: e.g. "ttft_ms.p95", "p95", "latency_p95", "ttft_p95", etc.
    const keyCandidates = [
      `${c.metric_name}.${c.statistic}`,
      `${c.metric_name}_${c.statistic}`,
      c.statistic,
      c.metric_name,
    ];

    let measured: number | undefined;
    for (const key of keyCandidates) {
      if (typeof measuredValues[key] === 'number') {
        measured = measuredValues[key] as number;
        break;
      }
    }

    if (measured === undefined || Number.isNaN(measured) || !Number.isFinite(measured)) continue;

    const isUpperBound = c.operator === '<=' || c.operator === '<';
    let isPassing = false;
    let absoluteHeadroom = 0;
    let relativeHeadroomFraction = 0;

    if (isUpperBound) {
      isPassing = c.operator === '<=' ? measured <= c.threshold : measured < c.threshold;
      absoluteHeadroom = Number((c.threshold - measured).toFixed(4));
      relativeHeadroomFraction = c.threshold !== 0 ? absoluteHeadroom / c.threshold : 0;
    } else {
      isPassing = c.operator === '>=' ? measured >= c.threshold : measured > c.threshold;
      absoluteHeadroom = Number((measured - c.threshold).toFixed(4));
      relativeHeadroomFraction = c.threshold !== 0 ? absoluteHeadroom / c.threshold : 0;
    }

    const absVal = Math.abs(absoluteHeadroom);
    const unitStr = c.unit || '';
    const formattedHeadroom = isPassing
      ? `${formatNumber(absVal, 1)} ${unitStr} headroom`
      : isUpperBound
      ? `${formatNumber(absVal, 1)} ${unitStr} over ceiling`
      : `${formatNumber(absVal, 1)} ${unitStr} below floor`;

    const result: HeadroomResult = {
      constraintName: `${c.metric_name.toUpperCase()} ${c.statistic.toUpperCase()}`,
      metricName: c.metric_name,
      statistic: c.statistic,
      threshold: c.threshold,
      measured,
      unit: c.unit,
      operator: c.operator,
      isPassing,
      relativeHeadroomFraction,
      absoluteHeadroom,
      formattedHeadroom,
      headroomPercentage: relativeHeadroomFraction * 100,
    };

    // Binding constraint is the one with smallest relativeHeadroomFraction
    // (most negative if breaching, or smallest positive if passing)
    if (!mostBinding || result.relativeHeadroomFraction < mostBinding.relativeHeadroomFraction) {
      mostBinding = result;
    }
  }

  return mostBinding;
}
