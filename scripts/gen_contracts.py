"""
Purpose: Generates canonical JSON Schemas from the contract models.
Owner: Rajdeep
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Type
from pydantic import BaseModel

from slokern.contracts import (
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
)

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


def generate_schemas(output_dir: Path, check_only: bool = False) -> bool:
    """
    Exports or validates JSON schemas for all root contract models.
    Returns True if successful (or up to date in check_only mode), False otherwise.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_current = True
    expected_filenames = {f"{model_cls.__name__}.json" for model_cls in ROOT_MODELS}

    for model_cls in ROOT_MODELS:
        schema_path = output_dir / f"{model_cls.__name__}.json"
        schema_dict = model_cls.model_json_schema()
        expected_content = json.dumps(schema_dict, indent=2) + "\n"

        if check_only:
            if not schema_path.is_file():
                print(f"[OUT OF DATE] Missing schema file: {schema_path}", file=sys.stderr)
                all_current = False
                continue

            current_content = schema_path.read_text(encoding="utf-8")
            if current_content != expected_content:
                print(f"[OUT OF DATE] Schema out of date: {schema_path}", file=sys.stderr)
                all_current = False
        else:
            with open(schema_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(expected_content)
            print(f"[GENERATED] {schema_path}")

    # Check or clean orphaned .json files in output directory
    actual_files = {p.name for p in output_dir.glob("*.json")}
    orphaned_files = sorted(actual_files - expected_filenames)
    if orphaned_files:
        if check_only:
            for orphan in orphaned_files:
                print(f"[OUT OF DATE] Unexpected orphaned schema file: {output_dir / orphan}", file=sys.stderr)
            all_current = False
        else:
            for orphan in orphaned_files:
                (output_dir / orphan).unlink()
                print(f"[REMOVED ORPHAN] {output_dir / orphan}")

    if check_only and all_current:
        print(f"[OK] All {len(ROOT_MODELS)} schemas are up to date.")

    return all_current


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate canonical JSON schemas for SLOKern contracts.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether generated schema files are current without overwriting.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "schemas",
        help="Directory to write JSON schema files (default: repo root / schemas).",
    )
    args = parser.parse_args()

    success = generate_schemas(args.output_dir, check_only=args.check)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
