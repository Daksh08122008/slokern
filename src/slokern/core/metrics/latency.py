"""
Purpose: TTFT, ITL and end-to-end latency derivation from request records.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/metrics.md Section 2 and contracts/evidence.py
"""

from typing import List, Sequence, Union, Dict, Any
from slokern.contracts.evidence import RawRequestMeasurement


def _ensure_measurement(rec: Union[RawRequestMeasurement, Dict[str, Any]]) -> RawRequestMeasurement:
    if isinstance(rec, RawRequestMeasurement):
        return rec
    return RawRequestMeasurement.model_validate(rec)


def is_valid_completed_request(rec: Union[RawRequestMeasurement, Dict[str, Any]]) -> bool:
    """
    Returns True if the record represents an active, valid, non-error completed request.
    Warm-up requests and requests marked with anomalies or errors are excluded.
    """
    m = _ensure_measurement(rec)
    if m.is_warmup:
        return False
    if not m.is_valid:
        return False
    if m.error_type is not None:
        return False
    if m.http_status is not None and m.http_status != 200:
        return False
    return True


def extract_ttft_observations(records: Sequence[Union[RawRequestMeasurement, Dict[str, Any]]]) -> List[float]:
    """
    Extracts Time to First Token (TTFT) observations in milliseconds for valid completed requests.
    Excludes warm-up requests, invalid records, errors, non-streaming requests, and requests with 0 output tokens.
    TTFT = (first_token_at - sent_at) * 1000.0
    """
    ttft_observations: List[float] = []
    for rec in records:
        m = _ensure_measurement(rec)
        if not is_valid_completed_request(m):
            continue
        if m.first_token_at is not None and m.output_tokens >= 1:
            ttft_ms = (m.first_token_at - m.sent_at) * 1000.0
            ttft_observations.append(float(ttft_ms))
    return ttft_observations


def extract_itl_observations(records: Sequence[Union[RawRequestMeasurement, Dict[str, Any]]]) -> List[float]:
    """
    Extracts Inter-Token Latency (ITL) observations in milliseconds per token.
    Applies to valid completed streaming requests with output_tokens >= 2.
    Uses mean(itl_observations_ms) if recorded, otherwise falls back to:
        (completed_at - first_token_at) * 1000.0 / (output_tokens - 1)
    """
    itl_observations: List[float] = []
    for rec in records:
        m = _ensure_measurement(rec)
        if not is_valid_completed_request(m):
            continue
        if m.output_tokens < 2:
            continue
        if m.itl_observations_ms is not None and len(m.itl_observations_ms) > 0:
            avg_itl = sum(m.itl_observations_ms) / len(m.itl_observations_ms)
            itl_observations.append(float(avg_itl))
        elif m.first_token_at is not None:
            avg_itl = ((m.completed_at - m.first_token_at) * 1000.0) / (m.output_tokens - 1)
            itl_observations.append(float(avg_itl))
    return itl_observations


def extract_e2e_observations(records: Sequence[Union[RawRequestMeasurement, Dict[str, Any]]]) -> List[float]:
    """
    Extracts End-to-End (E2E) total request latency observations in milliseconds.
    Applies to all active, valid completed requests.
    E2E = (completed_at - sent_at) * 1000.0
    """
    e2e_observations: List[float] = []
    for rec in records:
        m = _ensure_measurement(rec)
        if not is_valid_completed_request(m):
            continue
        e2e_ms = (m.completed_at - m.sent_at) * 1000.0
        e2e_observations.append(float(e2e_ms))
    return e2e_observations
