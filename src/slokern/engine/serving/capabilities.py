"""
Purpose: Declares which configuration parameters the runtime can truly apply.
Owner: Rajdeep (Historical design: Aman)
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from slokern.contracts.enums import ParameterStatus


class ParameterSpec(BaseModel):
    """Specification of a configurable serving parameter and its legal envelope."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Parameter name (e.g., 'max_num_seqs')")
    param_type: str = Field(..., description="Data type: 'int', 'float', 'str', 'bool'")
    default: Any = Field(..., description="Default value if not requested")
    min_value: Optional[float] = Field(None, description="Minimum numeric value if applicable")
    max_value: Optional[float] = Field(None, description="Maximum numeric value if applicable")
    allowed_values: Optional[List[Any]] = Field(None, description="Explicit discrete allowed values")
    description: str = Field("", description="Human-readable explanation of parameter")

    @field_validator("param_type")
    @classmethod
    def validate_param_type(cls, v: str) -> str:
        allowed = {"int", "float", "str", "bool"}
        if v not in allowed:
            raise ValueError(f"param_type must be one of {allowed}, got '{v}'")
        return v

    def validate_value(self, val: Any) -> Tuple[bool, ParameterStatus, str]:
        """Validates a candidate value against this parameter specification."""
        if self.param_type == "int":
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                return False, ParameterStatus.REJECTED, f"Expected int for {self.name}, got {type(val).__name__}"
            if isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    return False, ParameterStatus.REJECTED, f"Numeric parameter '{self.name}' cannot be NaN or Inf"
                if not val.is_integer():
                    return False, ParameterStatus.REJECTED, f"Expected integer float for {self.name}, got {val}"
            int_val = int(val)
            if self.min_value is not None and int_val < self.min_value:
                return False, ParameterStatus.REJECTED, f"Value {int_val} < min_value {self.min_value} for {self.name}"
            if self.max_value is not None and int_val > self.max_value:
                return False, ParameterStatus.REJECTED, f"Value {int_val} > max_value {self.max_value} for {self.name}"
            if self.allowed_values is not None and int_val not in self.allowed_values:
                return False, ParameterStatus.REJECTED, f"Value {int_val} not in allowed_values {self.allowed_values} for {self.name}"
            return True, ParameterStatus.APPLIED, ""

        elif self.param_type == "float":
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                return False, ParameterStatus.REJECTED, f"Expected float for {self.name}, got {type(val).__name__}"
            float_val = float(val)
            if math.isnan(float_val) or math.isinf(float_val):
                return False, ParameterStatus.REJECTED, f"Numeric parameter '{self.name}' cannot be NaN or Inf"
            if self.min_value is not None and float_val < self.min_value:
                return False, ParameterStatus.REJECTED, f"Value {float_val} < min_value {self.min_value} for {self.name}"
            if self.max_value is not None and float_val > self.max_value:
                return False, ParameterStatus.REJECTED, f"Value {float_val} > max_value {self.max_value} for {self.name}"
            if self.allowed_values is not None and float_val not in self.allowed_values:
                return False, ParameterStatus.REJECTED, f"Value {float_val} not in allowed_values {self.allowed_values} for {self.name}"
            return True, ParameterStatus.APPLIED, ""

        elif self.param_type == "str":
            if not isinstance(val, str):
                return False, ParameterStatus.REJECTED, f"Expected str for {self.name}, got {type(val).__name__}"
            if self.allowed_values is not None and val not in self.allowed_values:
                return False, ParameterStatus.REJECTED, f"Value '{val}' not in allowed_values {self.allowed_values} for {self.name}"
            return True, ParameterStatus.APPLIED, ""

        elif self.param_type == "bool":
            if not isinstance(val, bool):
                return False, ParameterStatus.REJECTED, f"Expected bool for {self.name}, got {type(val).__name__}"
            return True, ParameterStatus.APPLIED, ""

        return True, ParameterStatus.APPLIED, ""


class RuntimeCapabilities(BaseModel):
    """Declared capabilities and parameter envelope of a serving adapter."""
    model_config = ConfigDict(extra="forbid")

    runtime_name: str = Field(..., description="Engine name")
    supported_models: List[str] = Field(..., description="List of supported model identifiers (or ['*'])")
    parameters: Dict[str, ParameterSpec] = Field(default_factory=dict, description="Supported parameters map")
    supports_streaming: bool = Field(True, description="Whether runtime supports token streaming")
    supports_dynamic_batching: bool = Field(True, description="Whether runtime supports dynamic batching")
    max_concurrency: int = Field(256, description="Maximum concurrent request limit")

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __contains__(self, item: Any) -> bool:
        return hasattr(self, str(item))

    def to_dict(self) -> Dict[str, Any]:
        """Exports capabilities to dictionary representation."""
        return self.model_dump()

    def is_model_supported(self, model_name: str) -> bool:
        """Checks if model identifier is supported."""
        if "*" in self.supported_models:
            return True
        return model_name in self.supported_models

    def evaluate_settings(
        self,
        requested_settings: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, ParameterStatus], List[str]]:
        """
        Evaluates requested settings against declared capabilities.
        Returns:
            - effective_settings: dict of successfully applied settings (including defaults for unrequested supported settings)
            - parameter_status: dict mapping parameter names to ParameterStatus
            - notes: list of human-readable notes/warnings
        """
        effective_settings: Dict[str, Any] = {}
        parameter_status: Dict[str, ParameterStatus] = {}
        notes: List[str] = []

        # Evaluate all requested settings
        for param_name, val in requested_settings.items():
            if param_name not in self.parameters:
                parameter_status[param_name] = ParameterStatus.UNSUPPORTED
                notes.append(f"Parameter '{param_name}' is unsupported by runtime '{self.runtime_name}'")
            else:
                spec = self.parameters[param_name]
                is_valid, status, reason = spec.validate_value(val)
                parameter_status[param_name] = status
                if is_valid:
                    if spec.param_type == "int":
                        applied_val = int(val)
                    elif spec.param_type == "float":
                        applied_val = float(val)
                    else:
                        applied_val = val
                    effective_settings[param_name] = applied_val
                else:
                    notes.append(f"Parameter '{param_name}' rejected: {reason}")

        # Fill in defaults for unrequested supported parameters
        for param_name, spec in self.parameters.items():
            if param_name not in requested_settings:
                effective_settings[param_name] = spec.default
                parameter_status[param_name] = ParameterStatus.DEFAULT_FALLBACK

        return effective_settings, parameter_status, notes
