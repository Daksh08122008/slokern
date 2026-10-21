"""
Purpose: Raw request records and load statistics (offered, achieved, dispatch lag).
Owner: Rajdeep
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RawRequestMeasurement(BaseModel):
    """Granular, unaggregated event capture for every request. Must be preserved for reproducibility."""
    request_id: str = Field(..., description="Unique request identifier")
    run_id: str = Field(..., description="Associated run identifier")
    scheduled_at: float = Field(..., description="Intended dispatch timestamp (epoch seconds / ISO)")
    sent_at: float = Field(..., description="Socket write start timestamp")
    first_token_at: Optional[float] = Field(None, description="First token receipt timestamp (nullable for non-streaming or failed requests)")
    completed_at: float = Field(..., description="Response completion or abort timestamp")
    http_status: Optional[int] = Field(None, description="Response code")
    input_tokens: int = Field(..., description="Measured prompt token count")
    output_tokens: int = Field(..., description="Measured generated token count")
    itl_observations_ms: Optional[List[float]] = Field(None, description="Optional list of inter-token intervals in milliseconds")
    error_type: Optional[str] = Field(None, description="Error classification if failed")
    is_warmup: bool = Field(..., description="Boolean indicating if sample occurred during warm-up (excluded from metrics)")
    is_valid: bool = Field(..., description="Boolean indicating whether sample is free of client-side measurement anomalies")
