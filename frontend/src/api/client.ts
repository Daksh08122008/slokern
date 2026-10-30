/**
 * SLOKern Frontend API Client
 * Typed fetch client connecting the React UI to the Python control plane.
 * Authority: Aligned with AGENTS.md Section 3, 11, and DEC-0014
 */

import type {
  HealthResponse,
  SmokeTestResponse,
  SmokeTestArtifactResponse,
  RuntimeProfileResponse,
  ReportSummaryResponse,
  SingleRunDispatchResponse,
  RunStatusResponse,
  RunProgressEvent,
  VerificationRecord,
  ReportArtifact,
} from '../types/contracts';
import type { UICandidate, UIExperiment } from '../lib/adapters/viewModel';

const runtimeEnv = (import.meta as any).env;
const API_BASE = runtimeEnv?.VITE_API_URL ?? (runtimeEnv?.DEV ? 'http://127.0.0.1:8000' : '');

class ApiClientError extends Error {
  status: number;
  constructor(message: string, status: number = 500) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errMsg = `HTTP ${res.status} ${res.statusText}`;
      try {
        const errData = await res.json();
        if (errData.error) errMsg = errData.error;
      } catch {
        // ignore json parse error
      }
      throw new ApiClientError(errMsg, res.status);
    }
    return (await res.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiClientError) throw err;
    throw new ApiClientError(err.message || 'Network connection failed', 0);
  }
}

export async function checkHealth(adapter?: string): Promise<HealthResponse> {
  const query = adapter ? `?adapter=${encodeURIComponent(adapter)}` : '';
  return request<HealthResponse>(`/api/health${query}`, { method: 'GET' });
}

export async function getRuntimeProfile(): Promise<RuntimeProfileResponse> {
  return request<RuntimeProfileResponse>('/api/runtime', { method: 'GET' });
}

export async function getLatestSmokeTest(): Promise<SmokeTestArtifactResponse> {
  return request<SmokeTestArtifactResponse>('/api/smoke-test/latest', { method: 'GET' });
}

export async function listExperiments(): Promise<UIExperiment[]> {
  return request<UIExperiment[]>('/api/experiments', { method: 'GET' });
}

export async function getExperimentDetail(experimentId: string): Promise<any> {
  return request<any>(`/api/experiments/${encodeURIComponent(experimentId)}`, { method: 'GET' });
}

export async function getExperimentCandidates(experimentId: string): Promise<UICandidate[]> {
  return request<UICandidate[]>(`/api/experiments/${encodeURIComponent(experimentId)}/candidates`, {
    method: 'GET',
  });
}

export async function getExperimentVerification(experimentId: string): Promise<VerificationRecord> {
  return request<VerificationRecord>(
    `/api/experiments/${encodeURIComponent(experimentId)}/verification`,
    { method: 'GET' }
  );
}

export async function listReports(): Promise<ReportSummaryResponse[]> {
  return request<ReportSummaryResponse[]>('/api/reports', { method: 'GET' });
}

export async function runSmokeProbe(
  adapter?: string,
  prompt: string = 'SLOKern preflight smoke test probe.'
): Promise<SmokeTestResponse> {
  return request<SmokeTestResponse>('/api/smoke-test', {
    method: 'POST',
    body: JSON.stringify({ adapter, prompt }),
  });
}

export async function launchSingleRun(payload: Record<string, any>): Promise<SingleRunDispatchResponse> {
  return request<SingleRunDispatchResponse>('/api/runs/single', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getRunStatus(runId: string): Promise<RunStatusResponse> {
  return request<RunStatusResponse>(`/api/runs/${encodeURIComponent(runId)}`, {
    method: 'GET',
  });
}

export async function listRecentRuns(): Promise<RunStatusResponse[]> {
  return request<RunStatusResponse[]>('/api/runs', { method: 'GET' });
}

export async function runVerification(payload: Record<string, any>): Promise<VerificationRecord> {
  return request<VerificationRecord>('/api/runs/verify', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getReport(
  experimentId: string
): Promise<{ experiment_id: string; markdown: string; artifact: ReportArtifact | null }> {
  return request<{ experiment_id: string; markdown: string; artifact: ReportArtifact | null }>(
    `/api/reports/${encodeURIComponent(experimentId)}`,
    { method: 'GET' }
  );
}

export function getRunTraceUrl(runId: string): string {
  return `${API_BASE}/api/runs/${encodeURIComponent(runId)}/trace`;
}

export async function fetchRunTrace(runId: string): Promise<string> {
  const url = getRunTraceUrl(runId);
  const res = await fetch(url);
  if (!res.ok) {
    let errMsg = `Failed to fetch raw trace: HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson.error) errMsg = errJson.error;
    } catch {
      // ignore
    }
    throw new ApiClientError(errMsg, res.status);
  }
  return res.text();
}

/**
 * Subscribes to live SSE events from /api/runs/<run_id>/events.
 * Includes automatic polling fallback in case SSE is blocked or disconnects.
 */
export function subscribeRunProgress(
  runId: string,
  onProgress: (event: RunProgressEvent) => void,
  onComplete: (res: RunStatusResponse) => void,
  onError: (err: string) => void
): () => void {
  let isCancelled = false;
  let pollInterval: any = null;

  const startPolling = () => {
    if (pollInterval) return;
    pollInterval = setInterval(async () => {
      if (isCancelled) {
        clearInterval(pollInterval);
        return;
      }
      try {
        const status = await getRunStatus(runId);
        if (status.is_completed) {
          clearInterval(pollInterval);
          onComplete(status);
        } else if (status.execution_status === 'FAILED') {
          clearInterval(pollInterval);
          onError(status.error || 'Execution failed');
        } else {
          const totalReqs = status.workload
            ? Math.max(
                1,
                Math.round(
                  (status.workload.warmup_duration_s + status.workload.measurement_duration_s) *
                    status.workload.target_offered_rate
                )
              )
            : 10;
          onProgress({
            type: 'progress',
            run_id: runId,
            completed_requests: status.raw_measurements_count || 0,
            total_requests: totalReqs,
            current_ttft_ms: status.metric_set?.ttft_ms?.p50 ?? null,
          });
        }
      } catch (err: any) {
        // keep polling
      }
    }, 600);
  };

  try {
    const sseUrl = `${API_BASE}/api/runs/${encodeURIComponent(runId)}/events`;
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (e) => {
      if (isCancelled) return;
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'completed' && data.run_result) {
          eventSource.close();
          onComplete(data.run_result);
        } else if (data.type === 'failed') {
          eventSource.close();
          onError(data.error || 'Execution failed');
        } else {
          onProgress(data);
        }
      } catch (err) {
        // ignore parse error
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      if (!isCancelled) {
        startPolling();
      }
    };

    return () => {
      isCancelled = true;
      if (eventSource) eventSource.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  } catch (err) {
    startPolling();
    return () => {
      isCancelled = true;
      if (pollInterval) clearInterval(pollInterval);
    };
  }
}
