"""
Purpose: Candidate input and config validation logic.
Owner: Rajdeep
"""

from typing import Dict, Any, List
from slokern.contracts.config import CandidateConfig

def validate_candidate_settings(
    settings: Dict[str, Any],
    allowed_keys: List[str]
) -> bool:
    """
    Validates that a candidate only contains allowed settings.
    """
    for key in settings:
        if key not in allowed_keys:
            return False
    return True
