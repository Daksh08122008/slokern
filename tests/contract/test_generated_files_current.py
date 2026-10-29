"""
Purpose: Fails when generated schemas or types are out of date.
Owner: Rajdeep
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Type

import pytest
from pydantic import BaseModel

from slokern.contracts import (
    CandidateConfig,
    ExperimentSpec,
    FeasibilityResult,
    MetricSet,
    RawRequestMeasurement,
    ReportArtifact,
    RunRecord,
    SearchResult,
    SLOSpec,
    VerificationRecord,
    WorkloadSpec,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
GEN_SCRIPT = REPO_ROOT / "scripts" / "gen_contracts.py"

ROOT_MODELS: List[Type[BaseModel]] = [
    WorkloadSpec,
    SLOSpec,
    ExperimentSpec,
    CandidateConfig,
    RawRequestMeasurement,
    MetricSet,
    FeasibilityResult,
    RunRecord,
    SearchResult,
    VerificationRecord,
    ReportArtifact,
]


@pytest.mark.parametrize("model_cls", ROOT_MODELS, ids=lambda m: m.__name__)
def test_schema_file_exists_and_matches_model(model_cls: Type[BaseModel]):
    schema_path = SCHEMAS_DIR / f"{model_cls.__name__}.json"
    assert schema_path.exists(), (
        f"Missing schema file: {schema_path}. Run 'python scripts/gen_contracts.py' to generate."
    )

    expected_schema = model_cls.model_json_schema()
    expected_content = json.dumps(expected_schema, indent=2) + "\n"

    actual_content = schema_path.read_text(encoding="utf-8")
    actual_schema = json.loads(actual_content)

    assert actual_schema == expected_schema, (
        f"Schema for {model_cls.__name__} in {schema_path} does not match model_json_schema(). "
        "Run 'python scripts/gen_contracts.py' to update."
    )
    assert actual_content == expected_content, (
        f"Formatting or whitespace mismatch in {schema_path}. "
        "Run 'python scripts/gen_contracts.py' to normalize."
    )


def test_no_extra_unexpected_schema_files():
    expected_filenames = {f"{m.__name__}.json" for m in ROOT_MODELS}
    actual_files = {p.name for p in SCHEMAS_DIR.glob("*.json")}
    unexpected = actual_files - expected_filenames
    assert not unexpected, f"Found unexpected schema files in schemas/: {unexpected}"


def test_gen_contracts_script_check_mode():
    result = subprocess.run(
        [sys.executable, str(GEN_SCRIPT), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"scripts/gen_contracts.py --check failed with code {result.returncode}.\n"
        f"Stdout: {result.stdout}\nStderr: {result.stderr}"
    )


def test_gen_contracts_check_detects_outdated_schema(tmp_path: Path):
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.gen_contracts import generate_schemas

    # Populate tmp_path with valid schemas
    assert generate_schemas(tmp_path, check_only=False) is True

    # Tamper with one schema
    target = tmp_path / "WorkloadSpec.json"
    target.write_text('{"tampered": true}', encoding="utf-8")

    # Check mode must detect the change and return False
    assert generate_schemas(tmp_path, check_only=True) is False


def test_gen_contracts_check_detects_missing_schema(tmp_path: Path):
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.gen_contracts import generate_schemas

    # Populate tmp_path with valid schemas
    assert generate_schemas(tmp_path, check_only=False) is True

    # Delete one schema
    target = tmp_path / "SLOSpec.json"
    target.unlink()

    # Check mode must detect the missing file and return False
    assert generate_schemas(tmp_path, check_only=True) is False


def test_gen_contracts_check_detects_orphaned_schema(tmp_path: Path):
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.gen_contracts import generate_schemas

    # Populate tmp_path with valid schemas
    assert generate_schemas(tmp_path, check_only=False) is True

    # Add an unexpected orphaned schema file
    target = tmp_path / "UnexpectedObsoleteModel.json"
    target.write_text("{}", encoding="utf-8")

    # Check mode must detect the orphaned file and return False
    assert generate_schemas(tmp_path, check_only=True) is False

    # Generation mode must remove the orphaned file
    assert generate_schemas(tmp_path, check_only=False) is True
    assert not target.exists()
