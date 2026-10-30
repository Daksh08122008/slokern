import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
SPEC_FILE = ROOT_DIR / "fixtures" / "campaigns" / "audit_offline_campaign.json"


class DemoArtifactError(Exception):
    """Raised when a successful campaign did not produce readable summary artifacts."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DemoArtifactError(f"Could not read campaign artifact {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DemoArtifactError(f"Expected a JSON object in campaign artifact: {path}")
    return payload


def _display(value: Any, suffix: str = "") -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.3f}{suffix}"
    return f"{value}{suffix}"


def _metric(metrics: dict[str, Any], distribution: str, statistic: str) -> Any:
    values = metrics.get(distribution)
    if not isinstance(values, dict):
        return None
    return values.get(statistic)


def _print_metrics(label: str, metrics: dict[str, Any]) -> None:
    print(f"\n{label}")
    print(f"  Samples:             {metrics.get('sample_count', 'unavailable')}")
    print(f"  Offered load:        {_display(metrics.get('offered_load_rps'), ' requests/s')}")
    print(f"  Achieved throughput: {_display(metrics.get('request_throughput_rps'), ' requests/s')}")
    print(f"  Output throughput:   {_display(metrics.get('token_throughput_tps'), ' tokens/s')}")
    print(f"  TTFT p95:            {_display(_metric(metrics, 'ttft_ms', 'p95'), ' ms')}")
    print(f"  ITL p50:             {_display(_metric(metrics, 'itl_ms', 'p50'), ' ms')}")
    print(f"  Error rate:          {_display(metrics.get('error_rate'))}")


def _print_summary(output_dir: Path, experiment_id: str) -> None:
    experiment_dir = output_dir / "experiments" / experiment_id
    search_path = experiment_dir / "search_result.json"
    verification_path = experiment_dir / "verification_record.json"
    search = _read_json(search_path)
    verification = _read_json(verification_path)
    spec = _read_json(SPEC_FILE)
    if spec.get("experiment_id") != experiment_id:
        raise DemoArtifactError(f"Experiment ID in {SPEC_FILE} does not match the campaign")
    workload = spec.get("workload", {})
    slo = spec.get("slo", {})

    if not isinstance(workload, dict) or not isinstance(slo, dict):
        raise DemoArtifactError(f"Workload or SLO in {SPEC_FILE} is not a JSON object")

    print("\n" + "=" * 68)
    print("SLOKern OFFLINE CAMPAIGN SUMMARY - SYNTHETIC DEMO DATA")
    print("Fake adapter output; these are not measurements from a live model or GPU.")
    print("=" * 68)
    print(f"Experiment: {experiment_id}")
    print(
        "Workload:   "
        f"{workload.get('workload_name', 'unavailable')} "
        f"({workload.get('arrival_mode', 'unavailable')} arrivals, "
        f"{_display(workload.get('target_offered_rate'), ' requests/s')})"
    )
    print(
        "Duration:   "
        f"{workload.get('warmup_duration_s', 'unavailable')}s warm-up + "
        f"{workload.get('measurement_duration_s', 'unavailable')}s measurement"
    )

    constraints = slo.get("constraints", [])
    print("SLO limits:")
    if isinstance(constraints, list):
        for constraint in constraints:
            if isinstance(constraint, dict):
                print(
                    f"  - {constraint.get('metric_name', 'metric')}."
                    f"{constraint.get('statistic', 'statistic')} "
                    f"{constraint.get('operator', '?')} "
                    f"{constraint.get('threshold', 'unavailable')} "
                    f"{constraint.get('unit', '')}"
                )

    candidates = search.get("candidate_summaries", {})
    tested_candidates = search.get("tested_candidates", [])
    if not isinstance(candidates, dict) or not isinstance(tested_candidates, list):
        raise DemoArtifactError(f"Search result has invalid candidate data: {search_path}")
    objective = search.get("ranking_objective", "unavailable")
    ranking_unit = "tokens/s" if objective == "max_throughput_under_slo" else "objective units"
    print(f"\nSearch: {len(tested_candidates)} candidates tested; objective={objective}")
    for candidate_id in tested_candidates:
        summary = candidates.get(candidate_id, {})
        if not isinstance(summary, dict):
            summary = {}
        print(
            f"  - {candidate_id}: {summary.get('verdict', 'unavailable')}, "
            f"ranking metric={_display(summary.get('ranking_metric'), f' {ranking_unit}')}"
        )

    winner_id = search.get("selected_candidate_id")
    print(f"\nSelected candidate: {winner_id or 'none'}")
    print(f"Selection rationale: {search.get('selection_rationale', 'unavailable')}")

    winner_run: dict[str, Any] | None = None
    winner_run_dir: Path | None = None
    if winner_id is not None:
        for record_path in (experiment_dir / "runs").glob("*/run_record.json"):
            record = _read_json(record_path)
            if record.get("candidate_id") == winner_id and not record.get("is_verification_run"):
                winner_run = record
                winner_run_dir = record_path.parent
                break
        if winner_run is None or winner_run_dir is None:
            raise DemoArtifactError(f"No search run record found for selected candidate {winner_id}")
        _print_metrics(
            "Selected search run metrics:",
            _read_json(winner_run_dir / "metrics.json"),
        )
        applied_config = _read_json(winner_run_dir / "applied_config.json")
        requested_settings = applied_config.get("requested_settings", {})
        selected_kind = "baseline/default candidate" if not requested_settings else "tuned candidate"
        print(f"  Candidate type:      {selected_kind}")
        print(f"  Requested settings:  {requested_settings}")
        print(
            "  Simulated effective settings: "
            f"{applied_config.get('effective_settings', 'unavailable')}"
        )
        print(f"  Parameter status:    {applied_config.get('parameter_status', 'unavailable')}")
        print(f"  Search run ID:       {winner_run.get('run_id', 'unavailable')}")

    print("\nIndependent verification:")
    print(f"  Verdict:          {verification.get('verification_verdict', 'unavailable')}")
    print(f"  Verification ID:  {verification.get('verification_id', 'unavailable')}")
    print(f"  Fresh run ID:     {verification.get('verification_run_id', 'unavailable')}")
    verification_metrics = verification.get("metric_set")
    if isinstance(verification_metrics, dict):
        _print_metrics("Verification run metrics:", verification_metrics)
    else:
        print("  Verification metrics: unavailable in the artifact")

    print("\nInspect the generated evidence:")
    print(f"  Search result:      {search_path}")
    print(f"  Verification record: {verification_path}")
    if winner_run_dir is not None:
        print(f"  Winner raw trace:   {winner_run_dir / 'raw_measurements.jsonl'}")
    verification_run_id = verification.get("verification_run_id")
    if isinstance(verification_run_id, str):
        verification_trace = (
            experiment_dir / "runs" / verification_run_id / "raw_measurements.jsonl"
        )
        print(f"  Verification trace: {verification_trace}")
    print("=" * 68)


def main() -> int:
    if not SPEC_FILE.is_file():
        print(f"[ERROR] Demo specification not found: {SPEC_FILE}", file=sys.stderr)
        return 1

    output_dir = ROOT_DIR / "artifacts" / f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    env = os.environ.copy()
    source_dir = str(ROOT_DIR / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        path for path in (source_dir, existing_pythonpath) if path
    )
    command = [
        sys.executable,
        "-m",
        "slokern.cli",
        "optimize",
        str(SPEC_FILE),
        "--adapter",
        "fake",
        "--output-dir",
        str(output_dir),
        "--verify",
    ]

    print("[DEMO DATA] Running the bounded offline campaign with the fake adapter.")
    result = subprocess.run(command, cwd=ROOT_DIR, env=env, check=False)
    if result.returncode == 0:
        try:
            _print_summary(output_dir, _read_json(SPEC_FILE).get("experiment_id", ""))
        except DemoArtifactError as exc:
            print(f"[ERROR] Campaign completed but its summary could not be loaded: {exc}", file=sys.stderr)
            return 1
        print(f"\n[DEMO DATA] All campaign artifacts: {output_dir}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
