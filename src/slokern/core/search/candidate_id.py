"""
Purpose: Canonical serialization and stable candidate IDs.
Owner: Rohan
"""

import hashlib
import json
from typing import Dict, Any

def generate_candidate_id(model_name: str, runtime_name: str, requested_settings: Dict[str, Any]) -> str:
    """
    Generates a deterministic hash (candidate_id) based on the model, runtime,
    and the requested settings.
    """
    settings_str = json.dumps(requested_settings, sort_keys=True)
    canonical_string = f"{model_name}|{runtime_name}|{settings_str}"
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()[:12]
