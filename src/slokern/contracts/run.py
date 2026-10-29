"""
Purpose: Run, run lifecycle, environment and provenance models.
Owner: Rajdeep
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.enums import ExecutionStatus


class RunRecord(BaseModel):
    """Metadata tracking an individual benchmark execution."""
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., description="Unique identifier for this specific execution attempt")
    experiment_id: str = Field(..., description="Parent experiment identifier")
    candidate_id: str = Field(..., description="Evaluated candidate identifier")
    is_verification_run: bool = Field(..., description="Boolean distinguishing search runs from verification runs")
    execution_status: ExecutionStatus = Field(..., description="Run status")
    started_at: Optional[str] = Field(None, description="Microsecond UTC ISO timestamp")
    completed_at: Optional[str] = Field(None, description="Microsecond UTC ISO timestamp")
    raw_artifact_uri: Optional[str] = Field(None, description="Relative path to raw request recordings (.jsonl)")
    execution_error: Optional[Dict[str, Any]] = Field(None, description="Structured error details if execution failed before measurement completion")
