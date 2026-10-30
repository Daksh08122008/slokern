/**
 * SLOKern Frontend Contract Definitions
 * Canonical TypeScript interfaces matching Pydantic models in src/slokern/contracts/
 * Authority: Aligned with schemas/*.json, AGENTS.md, and DEC-0014
 */

export type ExecutionStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export type EvidenceValidity = 'VALID' | 'INVALID' | 'CONTAMINATED';

export type FeasibilityVerdict = 'FEASIBLE' | 'INFEASIBLE' | 'INCONCLUSIVE';

export type VerificationState =
  | 'INDEPENDENT VERIFICATION PENDING'
  | 'NOT_RUN'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'VERIFICATION_FAILED'
  | 'VERIFICATION_INCONCLUSIVE';

export type ArrivalMode = 'poisson' | 'constant' | 'closed';

export type CostAccountingMode = 'mode_a_monetary' | 'mode_b_proxy';

export type RankingObjective =
  | 'monetary_cost_per_token'
  | 'monetary_cost_per_1k_requests'
  | 'gpu_seconds_per_request'
  | 'max_throughput_under_slo';

export type ParameterStatus = 'applied' | 'unsupported' | 'rejected' | 'default_fallback';

export type ReasonCode =
  | 'HARD_CONSTRAINTS_PASSED'
  | 'TTFT_P95_EXCEEDED'
  | 'TTFT_P50_EXCEEDED'
  | 'ITL_P95_EXCEEDED'
  | 'E2E_LATENCY_EXCEEDED'
  | 'ERROR_RATE_EXCEEDED'
  | 'THROUGHPUT_DEFICIT'
  | 'INSUFFICIENT_SAMPLES'
  | 'GENERATOR_SATURATED'
  | 'MISSING_REQUIRED_METRIC'
  | 'NON_NEGATIVE_VIOLATION'
  | 'DRIFT_TOLERANCE_EXCEEDED'
  | 'VERIFICATION_INCONCLUSIVE'
  | 'VERIFICATION_FAILED'
  | 'BUDGET_EXHAUSTED'
  | 'EXECUTION_ERROR'
  | 'UNSUPPORTED_PARAMETER';

export interface WorkloadSpec {
  schema_version: string;
  workload_name: string;
  fixture_id: string;
  arrival_mode: ArrivalMode;
  target_offered_rate: number;
  concurrency_limit: number;
  warmup_duration_s: number;
  measurement_duration_s: number;
  max_input_tokens: number;
  max_output_tokens: number;
}

export interface SLOConstraint {
  metric_name: string;
  statistic: 'p50' | 'p90' | 'p95' | 'p99' | 'mean' | 'max';
  threshold: number;
  unit: 'ms' | 's' | 'requests/s' | 'fraction';
  operator: '<=' | '<' | '>=' | '>';
}

export interface SLOSpec {
  slo_id: string;
  constraints: SLOConstraint[];
  min_sample_count: number;
}

export interface ExperimentBudget {
  max_candidates: number;
  max_wallclock_seconds: number;
  max_cost_limit?: number | null;
}

export interface ExperimentVerificationPolicy {
  repetitions: number;
  duration_multiplier: number;
}

export interface ExperimentSpec {
  experiment_id: string;
  workload: WorkloadSpec;
  slo: SLOSpec;
  search_space?: Record<string, any[]> | null;
  budget: ExperimentBudget;
  verification_policy?: ExperimentVerificationPolicy | null;
  metadata?: Record<string, any>;
}

export interface CandidateConfig {
  candidate_id: string;
  model_name: string;
  runtime_name: string;
  requested_settings: Record<string, any>;
  effective_settings: Record<string, any>;
  parameter_status: Record<string, ParameterStatus>;
  environment_fingerprint: Record<string, any>;
}

export interface RawRequestMeasurement {
  request_id: string;
  run_id: string;
  scheduled_at: number;
  sent_at: number;
  first_token_at?: number | null;
  completed_at: number;
  http_status: number;
  input_tokens: number;
  output_tokens: number;
  itl_observations_ms: number[];
  error_type?: string | null;
  is_valid: boolean;
  is_warmup: boolean;
}

export interface PercentileDistribution {
  p50?: number | null;
  p90?: number | null;
  p95?: number | null;
  p99?: number | null;
  mean?: number | null;
  min?: number | null;
  max?: number | null;
}

export interface MetricSet {
  metric_version?: string;
  run_id: string;
  sample_count: number;
  failed_request_count?: number;
  valid_count?: number;
  warmup_count?: number;
  error_count?: number;
  error_rate: number;
  offered_load_rps: number;
  achieved_load_rps: number;
  token_throughput_tps?: number;
  output_token_throughput_tps?: number;
  request_throughput_rps?: number;
  generator_saturated: boolean;
  ttft_ms: PercentileDistribution;
  itl_ms: PercentileDistribution;
  e2e_latency_ms: PercentileDistribution;
  monetary_cost_per_token?: number | null;
  monetary_cost_per_1k_requests?: number | null;
  gpu_seconds_per_request?: number | null;
  metadata?: Record<string, any>;
}

export interface ConstraintEvaluation {
  metric_name: string;
  statistic: string;
  threshold: number;
  operator: string;
  observed_value?: number | null;
  passed?: boolean | null;
  reason: ReasonCode;
  reason_code?: ReasonCode;
}

export interface FeasibilityResult {
  run_id: string;
  slo_id: string;
  evaluator_version: string;
  policy_version: string;
  overall_verdict: FeasibilityVerdict;
  validity_status: EvidenceValidity;
  constraint_evaluations: ConstraintEvaluation[];
  reasons: ReasonCode[];
  notes?: string;
  audit_notes?: string;
}

export interface RunRecord {
  run_id: string;
  experiment_id: string;
  candidate_id: string;
  execution_status: ExecutionStatus;
  started_at: string;
  completed_at?: string | null;
  wallclock_duration_seconds?: number | null;
  raw_artifact_uri?: string | null;
  error_message?: string | null;
}

export interface CandidateSummary {
  candidate_id: string;
  rank: number;
  verdict: FeasibilityVerdict;
  is_feasible: boolean;
  primary_metric_value: number;
  objective_name: string;
}

export interface SearchResult {
  experiment_id: string;
  total_candidates_tested: number;
  selected_candidate_id?: string | null;
  selection_rationale: string;
  stopping_reason: string;
  ranked_candidates: CandidateSummary[];
}

export interface MetricDriftComparison {
  metric_name: string;
  reference_value: number;
  verification_value: number;
  absolute_drift: number;
  relative_drift?: number | null;
  tolerance: number;
  comparison_method: string;
  unit: string;
  passed: boolean;
  failure_reason?: string | null;
  statistic?: string;
  search_value?: number;
  percentage_drift?: number;
  tolerance_threshold?: number;
  drift_acceptable?: boolean;
}

export interface DriftAnalysis {
  metric_deltas?: Record<string, number>;
  slo_drift_detected: boolean;
  metric_comparisons?: Record<string, MetricDriftComparison> | null;
  drift_exceeded?: boolean;
  comparisons?: MetricDriftComparison[];
  notes?: string;
}

export interface VerificationRecord {
  verification_id: string;
  experiment_id: string;
  candidate_id: string;
  original_run_id?: string | null;
  verification_run_id?: string | null;
  verification_verdict: VerificationState;
  final_decision_notes?: string | null;
  drift_analysis?: DriftAnalysis | null;
  metric_set?: MetricSet | null;
  feasibility_result?: FeasibilityResult | null;
  reason_codes?: ReasonCode[] | null;
}

export interface ReportArtifact {
  experiment_id: string;
  title: string;
  summary: string;
  baseline?: Record<string, any> | null;
  search?: SearchResult | null;
  verification?: VerificationRecord | null;
  markdown_content?: string;
}

/** API Payload & Response Models */
export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  runtime: string;
  model: string;
  endpoint: string;
  is_healthy: boolean;
  fingerprint: Record<string, any>;
  message?: string;
  error?: string;
}

export interface SmokeTestResponse {
  status: 'success' | 'failed';
  runtime: string;
  model: string;
  status_code: number;
  first_token_latency_ms: number | null;
  total_latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  output_preview: string;
  metadata: Record<string, any>;
  error?: string | null;
}

export interface SingleRunDispatchResponse {
  run_id: string;
  experiment_id: string;
  candidate_id?: string;
  status: ExecutionStatus;
  message: string;
}

export interface RunStatusResponse {
  run_id: string;
  experiment_id: string;
  candidate_id: string;
  execution_status: ExecutionStatus;
  is_completed: boolean;
  is_feasible: boolean;
  metric_set?: MetricSet | null;
  feasibility_result?: FeasibilityResult | null;
  applied_config?: {
    effective_settings?: {
      max_num_batched_tokens?: number;
      max_num_seqs?: number;
      kv_cache_dtype?: string;
      gpu_memory_utilization?: number;
    };
  } | null;
  raw_measurements_count: number;
  artifact_paths?: Record<string, string>;
  workload?: WorkloadSpec;
  slo?: SLOSpec;
  error?: string | null;
}

export interface RunProgressEvent {
  type: 'progress' | 'completed' | 'failed';
  run_id: string;
  completed_requests: number;
  total_requests: number;
  current_ttft_ms?: number | null;
  run_result?: RunStatusResponse;
  error?: string | null;
}



export interface SmokeTestArtifactResponse {
  timestamp: string;
  status: 'PASSED' | 'FAILED' | 'NONE';
  adapter: string;
  model: string;
  endpoint_host: string;
  provider: string;
  is_simulated: boolean;
  evidence_classification: 'LIVE' | 'DEMO DATA' | 'UNVERIFIED';
  health_check: boolean;
  model_confirmed: boolean;
  probe_request: {
    status_code: number;
    ttft_ms: number;
    total_latency_ms: number;
    input_tokens: number;
    output_tokens: number;
    output_preview?: string;
    error?: string | null;
  };
  streaming_probe?: {
    chunk_count: number;
    first_chunk_ttft_ms: number;
    stream_success: boolean;
  };
  error?: string | null;
}

export interface RuntimeProfileResponse {
  status: string;
  adapter: string;
  provider: string;
  model: string;
  endpoint_host: string;
  endpoint_url: string;
  is_healthy: boolean;
  is_simulated: boolean;
  evidence_classification: 'LIVE' | 'DEMO DATA' | 'UNVERIFIED';
  capability_preflight: {
    status: string;
    limitation_note: string;
    token_factory_constraint: boolean;
    supported_serving_controls: string[];
    unsupported_serving_controls: string[];
  };
  latest_smoke_test: SmokeTestArtifactResponse;
}

export interface ReportSummaryResponse {
  experiment_id: string;
  report_id: string;
  created_at: string;
  model: string;
  evidence_classification: 'LIVE' | 'DEMO DATA' | 'UNVERIFIED';
  selected_candidate_id: string;
  has_markdown: boolean;
  path: string;
}
