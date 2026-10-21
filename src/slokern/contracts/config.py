"""
Purpose: Requested vs applied configuration and candidate models with stable IDs.
Owner: Rajdeep
"""

from typing import Dict, Any
from pydantic import BaseModel, Field

from slokern.contracts.enums import ParameterStatus


class CandidateConfig(BaseModel):
    """Represents a concrete serving configuration. Distinguishes intent from verified runtime reality."""
    candidate_id: str = Field(..., description="Stable deterministic hash of canonical parameter values")
    model_name: str = Field(..., description="Formal model identifier")
    runtime_name: str = Field(..., description="Serving engine")
    requested_settings: Dict[str, Any] = Field(..., description="Key-value pairs requested by the search controller")
    effective_settings: Dict[str, Any] = Field(..., description="Key-value pairs confirmed by the adapter via runtime read-back")
    parameter_status: Dict[str, ParameterStatus] = Field(..., description="Map of parameters to status")
    environment_fingerprint: Dict[str, Any] = Field(..., description="Hash/dictionary of GPU hardware, driver, CUDA version, and runtime software commit")
