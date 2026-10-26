"""
Purpose: `slokern optimize`: run a bounded optimization experiment with capability gating.
Owner: Rajdeep (Historical design: Rohan)
Authority: Aligned with AGENTS.md Section 1, 3, 5, 6 and DEC-0014
"""

from pathlib import Path
import sys
from typing import Optional

from slokern.contracts.enums import RankingObjective
from slokern.contracts.spec import ExperimentSpec
from slokern.core.search.budget import validate_budget
from slokern.core.search.grid import (
    GridSearchController,
    SearchConfigurationError,
    validate_search_capabilities,
)
from slokern.engine.serving.base import ConfigurationError
from slokern.engine.serving.factory import create_serving_adapter


def optimize_command(
    spec_file: str,
    adapter: Optional[str] = None,
    objective: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> int:
    """
    Executes an optimization experiment specified in spec_file.
    Enforces honest capability gating: halts immediately with SearchConfigurationError
    citing BLK-17 when target adapter does not dynamically support search knobs.
    """
    spec_path = Path(spec_file)
    if not spec_path.exists():
        print(f"[ERROR] Specification file not found: {spec_file}", file=sys.stderr)
        return 1

    try:
        content = spec_path.read_text(encoding="utf-8")
        spec = ExperimentSpec.model_validate_json(content)
        validate_budget(spec)
    except Exception as exc:
        print(f"[ERROR] Specification validation failed: {exc}", file=sys.stderr)
        return 1

    # Resolve ranking objective
    resolved_objective = RankingObjective.MAX_THROUGHPUT_UNDER_SLO
    if objective:
        try:
            resolved_objective = RankingObjective(objective)
        except ValueError:
            print(
                f"[ERROR] Invalid ranking objective '{objective}'. "
                f"Valid objectives: {[o.value for o in RankingObjective]}",
                file=sys.stderr,
            )
            return 1

    # Instantiate serving adapter
    try:
        serving_adapter = create_serving_adapter(backend=adapter)
    except ConfigurationError as exc:
        print(f"[ERROR] Serving adapter configuration failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[SLOKern Optimization Campaign]")
    print(f"  Experiment ID: {spec.experiment_id}")
    print(f"  Runtime:       {serving_adapter.runtime_name}")
    print(f"  Model:         {serving_adapter.model_name}")
    print(f"  Objective:     {resolved_objective.value}")
    print(f"  Budget Limit:  {spec.budget.max_candidates} candidates / {spec.budget.max_wallclock_seconds}s")

    # Capability Preflight Gating (BLK-17)
    search_params = list(spec.search_space.keys()) if spec.search_space else ["max_num_batched_tokens", "max_num_seqs"]
    try:
        validate_search_capabilities(serving_adapter, search_params)
    except SearchConfigurationError as exc:
        print(
            f"\n[HALT] Optimization campaign halted per BLK-17:\n"
            f"  {exc}\n"
            f"  To develop or test pipeline behavior locally, use: --adapter fake (DEMO DATA)\n"
            f"  To smoke-test or verify fixed defaults, use: slokern smoke-test or slokern verify",
            file=sys.stderr,
        )
        return 1

    # Execute Search Campaign
    try:
        controller = GridSearchController(
            adapter=serving_adapter,
            artifacts_root=output_dir or "artifacts",
            default_objective=resolved_objective,
            isolate_process=False,
        )
        outcome = controller.run(spec, ranking_objective=resolved_objective)
        search_res = outcome.search_result
        exp_dir = Path(output_dir or "artifacts") / "experiments" / spec.experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "search_result.json").write_text(search_res.model_dump_json(indent=2), encoding="utf-8")

        print("\n[OK] Optimization campaign completed successfully:")
        print(f"  Tested Candidates:    {len(search_res.tested_candidates)}")
        print(f"  Selected Winner ID:   {search_res.selected_candidate_id}")
        print(f"  Selection Rationale:  {search_res.selection_rationale}")
        print(f"  Stopping Reason:      {search_res.stopping_reason}")
        return 0

    except Exception as exc:
        print(f"[ERROR] Optimization campaign execution failed: {exc}", file=sys.stderr)
        return 1
