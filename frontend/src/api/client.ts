/**
 * SLOKern Frontend API Client
 * Typed fetch client connecting the React UI to the Python FastAPI control plane.
 * Authority: Aligned with AGENTS.md Section 3, 11, and DEC-0014
 */

import type {
  HealthResponse,
  SmokeTestResponse,
  SingleRunDispatchResponse,
  RunStatusResponse,
  RunProgressEvent,
  VerificationRecord,
  ReportArtifact,
} from '../types/contracts';

const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';

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

  // Polling fallback function
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
          onProgress({
            type: 'progress',
            run_id: runId,
            completed_requests: status.raw_measurements_count || 0,
            total_requests: 10,
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

