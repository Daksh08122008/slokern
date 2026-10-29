"""
Purpose: Shared canonical enumerations: lifecycle state domains, verdicts, objectives, and reason codes.
Owner: Rajdeep (Architecture)
Authority: Aligned with docs/architecture.md, docs/decision-policy.md, and docs/adr/0001-mvp-scope-and-evidence.md
"""

from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution health of a benchmark or verification run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EvidenceValidity(str, Enum):
    """Integrity of the measurement evidence collected during a run."""
    VALID = "VALID"
    INVALID = "INVALID"
    CONTAMINATED = "CONTAMINATED"


class FeasibilityVerdict(str, Enum):
    """Deterministic assessment of a MetricSet against hard SLO constraints."""
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    INCONCLUSIVE = "INCONCLUSIVE"


class VerificationState(str, Enum):
    """Independent verification status of the selected winning candidate."""
    NOT_RUN = "NOT_RUN"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    VERIFICATION_INCONCLUSIVE = "VERIFICATION_INCONCLUSIVE"


class ArrivalMode(str, Enum):
    """Workload arrival scheduling distribution."""
    POISSON = "poisson"
    CONSTANT = "constant"
    CLOSED = "closed"


class CostAccountingMode(str, Enum):
    """Dual-mode cost accounting policy (ADR 0002)."""
    MODE_A_MONETARY = "mode_a_monetary"
    MODE_B_PROXY = "mode_b_proxy"


class RankingObjective(str, Enum):
    """Optimization objective for ranking feasible candidates."""
    MONETARY_COST_PER_TOKEN = "monetary_cost_per_token"
    MONETARY_COST_PER_1K_REQUESTS = "monetary_cost_per_1k_requests"
    GPU_SECONDS_PER_REQUEST = "gpu_seconds_per_request"
    MAX_THROUGHPUT_UNDER_SLO = "max_throughput_under_slo"


class ParameterStatus(str, Enum):
    """Status of requested serving configuration parameters after runtime read-back."""
    APPLIED = "applied"
    UNSUPPORTED = "unsupported"
    REJECTED = "rejected"
    DEFAULT_FALLBACK = "default_fallback"


class ReasonCode(str, Enum):
    """Machine-readable reason codes for feasibility and verification decisions."""
    HARD_CONSTRAINTS_PASSED = "HARD_CONSTRAINTS_PASSED"
    TTFT_P95_EXCEEDED = "TTFT_P95_EXCEEDED"
    TTFT_P50_EXCEEDED = "TTFT_P50_EXCEEDED"
    ITL_P95_EXCEEDED = "ITL_P95_EXCEEDED"
    E2E_LATENCY_EXCEEDED = "E2E_LATENCY_EXCEEDED"
    ERROR_RATE_EXCEEDED = "ERROR_RATE_EXCEEDED"
    THROUGHPUT_DEFICIT = "THROUGHPUT_DEFICIT"
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
    GENERATOR_SATURATED = "GENERATOR_SATURATED"
    CONTAMINATED_LOAD = "CONTAMINATED_LOAD"
    MISSING_REQUIRED_METRIC = "MISSING_REQUIRED_METRIC"
    UNSUPPORTED_OPERATOR = "UNSUPPORTED_OPERATOR"
    EXECUTION_CRASHED = "EXECUTION_CRASHED"
    VERIFICATION_DRIFT_EXCEEDED = "VERIFICATION_DRIFT_EXCEEDED"
