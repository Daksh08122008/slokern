"""
Purpose: Canonical serialization and stable candidate IDs.
Owner: Rajdeep (Historical design: Rohan)
"""

import hashlib
import json
from typing import Dict, Any

def _normalize_key(k: Any) -> str:
    """
    Normalizes dictionary keys into canonical strings:
    - preserves bools as 'True'/'False'
    - integer-valued floats (e.g. 1.0, -0.0) -> '1', '0'
    - enums / value objects -> str(val.value)
    - other types -> str(k)
    """
    if isinstance(k, bool):
        return str(k)
    if isinstance(k, (int, float)):
        if isinstance(k, float) and k.is_integer():
            return str(int(k))
        return str(k)
    if hasattr(k, "value") and not isinstance(k, (int, float, str, bool)):
        return str(k.value)
    return str(k)


def _normalize_value(val: Any) -> Any:
    """
    Recursively normalizes numeric values and data structures:
    - preserves bools as bools (distinct from int 1/0)
    - floats that represent integers (e.g. 1.0, 2.0, -0.0) -> int
    - enums / value objects -> recursively normalized value
    - sets and frozensets -> deterministically sorted lists
    - dicts and lists/tuples -> recursively normalized
    - pydantic models -> exported to dict and recursively normalized
    """
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val.is_integer():
            return int(val)
        return val
    if hasattr(val, "value") and not isinstance(val, (int, float, str, bool)):
        return _normalize_value(val.value)
    if isinstance(val, dict):
        return {_normalize_key(k): _normalize_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_normalize_value(v) for v in val]
    if isinstance(val, (set, frozenset)):
        normalized_elements = [_normalize_value(v) for v in val]
        return sorted(normalized_elements, key=lambda x: json.dumps(x, sort_keys=True))
    if hasattr(val, "model_dump"):
        return _normalize_value(val.model_dump(mode="json"))
    return val


def generate_candidate_id(model_name: str, runtime_name: str, requested_settings: Dict[str, Any]) -> str:
    """
    Generates a deterministic hash (candidate_id) based on the model, runtime,
    and the requested settings.
    """
    normalized_settings = _normalize_value(requested_settings)
    settings_str = json.dumps(normalized_settings, sort_keys=True)
    canonical_string = f"{model_name}|{runtime_name}|{settings_str}"
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()[:12]

