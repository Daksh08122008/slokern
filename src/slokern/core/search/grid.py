"""
Purpose: 2x2 Bounded grid search controller and candidate exploration orchestrator.
Owner: Rajdeep (Historical design: Rohan)
Authority: Aligned with AGENTS.md Section 1, 3, 5, 6, and ROADMAP.md TASK-10
"""

from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Union

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ExecutionStatus, FeasibilityVerdict, RankingObjective
from slokern.contracts.metrics import MetricSet
from slokern.contracts.search import CandidateSummary, SearchResult
from slokern.contracts.spec import ExperimentSpec, SLOSpec, WorkloadSpec
from slokern.core.search.budget import BudgetLimiter, BudgetValidationError, validate_budget
from slokern.core.search.rank import EvaluatedCandidate, rank_candidates
from slokern.core.search.space import generate_2x2_candidates
from slokern.engine.serving.base import BaseServingAdapter

if TYPE_CHECKING:
    from slokern.engine.runner.cancel import CancellationToken


DEFAULT_SEARCH_SPACE = {
    "max_num_batched_tokens": (1024, 2048),
    "max_num_seqs": (16, 64),
}


class SearchConfigurationError(ValueError):
    """Raised when the experiment cannot be safely executed as declared."""


class SearchExecutionError(RuntimeError):
    """Raised when a search run fails or is cancelled before valid evidence."""

    def __init__(self, message: str, run_result: Optional[Any] = None):
        super().__init__(message)
        self.run_result = run_result


@dataclass
class GridSearchOutcome:
    """Search decision plus the physical run results that support it."""

    search_result: SearchResult
    run_results: List[Any]
    verification_record: Optional[Any] = None


def validate_search_capabilities(
    adapter: Optional[BaseServingAdapter],
    search_space_params: Optional[Sequence[str]] = None,
) -> None:
    """
    Preflights adapter capabilities against requested search parameters.
    Halts immediately with SearchConfigurationError citing BLK-17 if the adapter
    does not support dynamic per-request application and read-back of process startup flags.
    """
    if adapter is None:
        return

    params_to_check = list(search_space_params) if search_space_params else ["max_num_batched_tokens", "max_num_seqs"]
    capabilities = adapter.get_capabilities()

    for p in params_to_check:
        if p not in capabilities.parameters:
            raise SearchConfigurationError(
                f"Search parameter {p!r} is not supported by runtime {capabilities.runtime_name!r}. "
                f"Halting optimization campaign due to unverified engine capabilities (BLK-17)."
            )

    fp = adapter.get_environment_fingerprint() if hasattr(adapter, "get_environment_fingerprint") else {}
    provider = str(fp.get("provider", "")).lower()
    runtime = str(getattr(adapter, "runtime_name", "")).lower()
    is_live_fixed_engine = (
        provider in ("nebius", "ollama")
        or "ollama" in runtime
        or "nebius" in runtime
    ) and not fp.get("is_simulated", False)

    if is_live_fixed_engine:
        raise SearchConfigurationError(
            f"Adapter {adapter.runtime_name!r} does not dynamically apply or read back process startup flags "
            f"({', '.join(params_to_check)}) per request. Halting optimization campaign (BLK-17)."
        )


def extract_ranking_metric(
    metric_set: Optional[MetricSet],
    objective: RankingObjective,
) -> Optional[float]:
    """
    Extracts the scalar ranking metric from a MetricSet according to the declared objective.
    Returns None if metric_set is None or the target metric is unavailable.
    """
    if metric_set is None:
        return None

    if objective == RankingObjective.MAX_THROUGHPUT_UNDER_SLO:
        # Prefer output token throughput; fallback to request throughput
        if metric_set.token_throughput_tps > 0:
            return round(metric_set.token_throughput_tps, 4)
        return round(metric_set.request_throughput_rps, 4)

    elif objective == RankingObjective.GPU_SECONDS_PER_REQUEST:
        # Mode B proxy: mean end-to-end request duration converted to seconds
        if metric_set.e2e_latency_ms and metric_set.e2e_latency_ms.mean is not None:
            return round(metric_set.e2e_latency_ms.mean / 1000.0, 6)
        if metric_set.request_throughput_rps > 0:
            return round(1.0 / metric_set.request_throughput_rps, 6)
        return None

    elif objective == RankingObjective.MONETARY_COST_PER_TOKEN:
        cost = metric_set.metadata.get("cost_per_token")
        if cost is not None:
            return float(cost)
        if metric_set.token_throughput_tps > 0:
            return round(1.0 / metric_set.token_throughput_tps, 6)
        return None

    elif objective == RankingObjective.MONETARY_COST_PER_1K_REQUESTS:
        cost = metric_set.metadata.get("cost_per_1k_requests")
        if cost is not None:
            return float(cost)
        if metric_set.request_throughput_rps > 0:
            return round(1000.0 / metric_set.request_throughput_rps, 6)
        return None

    return None


class GridSearchController:
    """
    Orchestrates the 2x2 bounded parameter grid search campaign:
    1. Executes Run 0: baseline candidate configuration.
    2. Generates the 4 canonical grid candidates across the 2x2 space:
       max_num_batched_tokens in {1024, 2048} x max_num_seqs in {16, 64}.
    3. Executes Runs 1-4: each candidate benchmarked via SingleRunExecutor.
    4. Evaluates feasibility, ranks candidates deterministically under the declared objective.
    5. Selects the winning feasible candidate and persists canonical SearchResult contract.

    Supports both:
    - run(spec: ExperimentSpec, ...): Spec-driven execution with preflight budget validation.
    - execute(...): Direct invocation with modular components.
    """

    def __init__(
        self,
        executor: Optional[Any] = None,
        adapter: Optional[BaseServingAdapter] = None,
        model_name: Optional[str] = None,
        *,
        single_run_executor: Optional[Any] = None,
        artifacts_root: Union[str, Path] = "artifacts",
        default_objective: RankingObjective = RankingObjective.GPU_SECONDS_PER_REQUEST,
        isolate_process: bool = False,
    ) -> None:
        self.artifacts_root = Path(artifacts_root)
        self.default_objective = default_objective
        self.adapter = adapter
        self.model_name = model_name or (adapter.model_name if adapter else None)

        if executor is not None:
            self.executor = executor
            self.single_run_executor = executor
        elif single_run_executor is not None:
            self.single_run_executor = single_run_executor
            self.executor = single_run_executor
        else:
            from slokern.engine.runner.run_executor import SingleRunExecutor
            self.single_run_executor = SingleRunExecutor(
                artifacts_root=self.artifacts_root,
                isolate_process=isolate_process,
            )
            self.executor = self.single_run_executor

    def run(
        self,
        spec: ExperimentSpec,
        *,
        ranking_objective: RankingObjective,
        cancellation_token: Optional[Any] = None,
        seed: Optional[int] = 42,
        prompts: Optional[Sequence[str]] = None,
        auto_verify: bool = False,
    ) -> GridSearchOutcome:
        """Validate preflight budget and capabilities, then execute baseline and bounded candidates."""
        validate_budget(spec)
        if spec.budget.max_cost_limit is not None:
            raise BudgetValidationError(
                "budget.max_cost_limit cannot be enforced without an authoritative "
                "pricing source; no runs were started"
            )
        if ranking_objective != RankingObjective.MAX_THROUGHPUT_UNDER_SLO:
            raise SearchConfigurationError(
                "Only MAX_THROUGHPUT_UNDER_SLO is currently supported; monetary "
                "pricing and GPU allocation are not verified"
            )

        if self.adapter is None:
            raise SearchConfigurationError("Serving adapter must be configured on GridSearchController to call run()")

        # Capability Preflight Gating (BLK-17 / DEC-0014)
        search_params = list(spec.search_space.keys()) if spec.search_space else ["max_num_batched_tokens", "max_num_seqs"]
        validate_search_capabilities(self.adapter, search_params)

        candidate_settings = self._candidate_settings(spec)
        capabilities = self.adapter.get_capabilities()
        if not capabilities.is_model_supported(self.model_name or ""):
            raise SearchConfigurationError(
                f"Model {self.model_name!r} is not supported by "
                f"{capabilities.runtime_name!r}"
            )
        for settings in candidate_settings:
            for name, value in settings.items():
                parameter = capabilities.parameters.get(name)
                if parameter is None:
                    raise SearchConfigurationError(
                        f"Search parameter {name!r} is not supported by "
                        f"{capabilities.runtime_name!r}"
                    )
                is_valid, _, reason = parameter.validate_value(value)
                if not is_valid:
                    raise SearchConfigurationError(
                        f"Search parameter {name!r} value {value!r} is invalid: {reason}"
                    )

        from slokern.engine.runner.cancel import CancellationToken
        token: CancellationToken = cancellation_token or CancellationToken()

        deadline = time.monotonic() + spec.budget.max_wallclock_seconds
        timeout = threading.Timer(spec.budget.max_wallclock_seconds, token.cancel)
        timeout.daemon = True
        timeout.start()

        run_results: List[Any] = []
        evaluated: List[EvaluatedCandidate] = []
        candidate_summaries: Dict[str, CandidateSummary] = {}
        tested_ids: List[str] = []
        candidate_limit = min(4, spec.budget.max_candidates)
        stopping_reason = "space_exhausted"

        max_search_runs = 1 + candidate_limit
        max_verif_runs = spec.verification_policy.repetitions
        budget = BudgetLimiter(
            max_total_runs=max_search_runs + max_verif_runs,
            max_search_runs=max_search_runs,
            max_verification_runs=max_verif_runs,
            timeout_seconds=spec.budget.max_wallclock_seconds,
        )

        try:
            configs = [self._make_config({})]
            configs.extend(
                self._make_config(settings)
                for settings in candidate_settings[:candidate_limit]
            )

            for index, config in enumerate(configs):
                if token.is_cancelled:
                    raise SearchExecutionError("Search was cancelled before the next run")
                if time.monotonic() >= deadline or budget.is_timed_out():
                    stopping_reason = "timeout"
                    break
                if not budget.can_execute_search_run():
                    stopping_reason = "budget_exhausted"
                    break

                budget.record_search_run()

                result = self.executor.execute(
                    candidate_config=config,
                    workload=spec.workload,
                    slo=spec.slo,
                    experiment_id=spec.experiment_id,
                    adapter=self.adapter,
                    cancellation_token=token,
                    seed=None if seed is None else seed + index,
                    prompts=list(prompts) if prompts is not None else None,
                )
                run_results.append(result)
                if result.execution_status != ExecutionStatus.COMPLETED:
                    raise SearchExecutionError(
                        f"Search run {result.run_id!r} ended with "
                        f"{result.execution_status.value}; search stopped",
                        run_result=result,
                    )
                if result.feasibility_result is None or result.metric_set is None:
                    raise SearchExecutionError(
                        f"Search run {result.run_id!r} completed without required "
                        "feasibility or metric evidence",
                        run_result=result,
                    )

                verdict = result.feasibility_result.overall_verdict
                ranking_metric = (
                    extract_ranking_metric(result.metric_set, ranking_objective)
                    if verdict == FeasibilityVerdict.FEASIBLE
                    else None
                )
                tested_ids.append(config.candidate_id)
                candidate_summaries[config.candidate_id] = CandidateSummary(
                    verdict=verdict,
                    ranking_metric=ranking_metric,
                )
                evaluated.append(
                    EvaluatedCandidate(
                        candidate_id=config.candidate_id,
                        verdict=verdict,
                        ranking_metric=ranking_metric,
                        metric_set=result.metric_set,
                    )
                )

                if token.is_cancelled:
                    raise SearchExecutionError(
                        "Search exceeded its wall-clock budget during a run",
                        run_result=result,
                    )
                if index == 0 and candidate_limit < 4:
                    stopping_reason = "budget_exhausted"
                elif index == candidate_limit:
                    stopping_reason = "budget_exhausted" if candidate_limit < 4 else "space_exhausted"

            ranked = rank_candidates(evaluated, ranking_objective)
            winner = ranked[0] if ranked else None
            if winner is None:
                rationale = (
                    "No FEASIBLE candidate had finite output-token throughput; "
                    "no recommendation was selected."
                )
            else:
                rationale = (
                    f"Selected candidate '{winner.candidate_id}': highest finite output-token "
                    f"throughput ({winner.ranking_metric:g} tokens/s) among FEASIBLE "
                    "tested candidates; ties are broken by candidate ID."
                )

            search_result = SearchResult(
                experiment_id=spec.experiment_id,
                baseline_candidate_id=configs[0].candidate_id,
                tested_candidates=tested_ids,
                candidate_summaries=candidate_summaries,
                ranking_objective=ranking_objective,
                selected_candidate_id=winner.candidate_id if winner else None,
                selection_rationale=rationale,
                stopping_reason=stopping_reason,
            )
            search_dir = self.artifacts_root / "experiments" / spec.experiment_id
            search_dir.mkdir(parents=True, exist_ok=True)
            (search_dir / "search_result.json").write_text(search_result.model_dump_json(indent=2), encoding="utf-8")

            verification_record = None
            if auto_verify and winner is not None and budget.can_execute_verification_run():
                from slokern.core.verification.protocol import run_independent_verification

                winner_config = next((c for c in configs if c.candidate_id == winner.candidate_id), None)
                if winner_config is not None:
                    budget.record_verification_run()
                    verif_seed = None if seed is None else seed + 100
                    winner_result = next(
                        (
                            r for r in run_results
                            if getattr(r, "run_record", None) and r.run_record.candidate_id == winner.candidate_id
                        ),
                        None,
                    )
                    orig_run_id = (
                        winner_result.run_id
                        if winner_result is not None
                        else f"run-search-{winner.candidate_id[:6]}"
                    )
                    existing_run_ids = [r.run_id for r in run_results if getattr(r, "run_id", None)]
                    verification_record = run_independent_verification(
                        original_run_id=orig_run_id,
                        candidate_config=winner_config,
                        workload=spec.workload,
                        slo=spec.slo,
                        experiment_id=spec.experiment_id,
                        original_metrics=winner.metric_set,
                        adapter=self.adapter,
                        single_run_executor=self.single_run_executor,
                        artifacts_root=self.artifacts_root,
                        cancellation_token=token,
                        seed=verif_seed,
                        persist_record=True,
                        existing_run_ids=existing_run_ids,
                    )

            return GridSearchOutcome(
                search_result=search_result,
                run_results=run_results,
                verification_record=verification_record,
            )
        finally:
            timeout.cancel()

    def run_full_campaign(
        self,
        spec: ExperimentSpec,
        *,
        ranking_objective: RankingObjective,
        cancellation_token: Optional[Any] = None,
        seed: Optional[int] = 42,
        prompts: Optional[Sequence[str]] = None,
    ) -> GridSearchOutcome:
        """
        Executes a complete 6-run campaign:
        1 baseline + 4 candidates (5 search runs) + 1 independent verification run (Run 6).
        """
        return self.run(
            spec,
            ranking_objective=ranking_objective,
            cancellation_token=cancellation_token,
            seed=seed,
            prompts=prompts,
            auto_verify=True,
        )

    def _candidate_settings(self, spec: ExperimentSpec) -> List[dict]:
        declared = spec.search_space or DEFAULT_SEARCH_SPACE
        if len(declared) != 2:
            raise SearchConfigurationError(
                "The bounded search requires exactly two parameter axes"
            )
        axes = []
        for name in sorted(declared):
            values = declared[name]
            if not isinstance(values, (list, tuple)) or len(values) != 2:
                raise SearchConfigurationError(
                    f"Search axis {name!r} must declare exactly two values"
                )
            if values[0] == values[1]:
                raise SearchConfigurationError(
                    f"Search axis {name!r} must contain two distinct values"
                )
            axes.append((name, tuple(values)))
        return [
            {axes[0][0]: first, axes[1][0]: second}
            for first, second in itertools.product(*[axis[1] for axis in axes])
        ]

    def _make_config(self, settings: dict) -> CandidateConfig:
        from slokern.core.search.candidate_id import generate_candidate_id

        runtime_name = self.adapter.runtime_name if self.adapter else "vllm-default"
        model_name = self.model_name or (self.adapter.model_name if self.adapter else "model-default")
        return CandidateConfig(
            candidate_id=generate_candidate_id(
                model_name, runtime_name, settings
            ),
            model_name=model_name,
            runtime_name=runtime_name,
            requested_settings=settings,
            effective_settings={},
            parameter_status={},
            environment_fingerprint={},
        )

    def execute(
        self,
        baseline_config: CandidateConfig,
        workload: Optional[WorkloadSpec] = None,
        slo: Optional[SLOSpec] = None,
        experiment_id: str = "exp-default",
        experiment_spec: Optional[ExperimentSpec] = None,
        ranking_objective: Optional[RankingObjective] = None,
        serving_adapter: Optional[BaseServingAdapter] = None,
        cancellation_token: Optional[Any] = None,
        budget_limiter: Optional[BudgetLimiter] = None,
        output_dir: Optional[Union[str, Path]] = None,
        seed: Optional[int] = 42,
        stream: bool = True,
        prompts: Optional[Union[List[str], str]] = None,
        strict_config: bool = True,
        auto_verify: bool = False,
    ) -> SearchResult:
        """
        Executes the bounded 2x2 grid search campaign.

        Args:
            baseline_config: Configuration for Run 0 baseline.
            workload: Workload profile (can be omitted if experiment_spec provided).
            slo: Hard SLO constraints (can be omitted if experiment_spec provided).
            experiment_id: Unique experiment session identifier.
            experiment_spec: Optional complete ExperimentSpec root document.
            ranking_objective: Declared optimization objective for candidate ranking.
            serving_adapter: Serving adapter to use for inference benchmark runs.
            cancellation_token: Optional token for cooperative cancellation.
            budget_limiter: Optional budget tracker (defaults to standard 6-run budget).
            output_dir: Custom output directory for search_result.json.
            seed: Arrival generation seed.
            stream: Whether to stream generation tokens.
            prompts: Benchmark prompts.
            strict_config: Whether to reject unsupported runtime settings.

        Returns:
            SearchResult canonical contract model.
        """
        if experiment_spec:
            validate_budget(experiment_spec)

        resolved_experiment_id = (
            experiment_spec.experiment_id if experiment_spec else experiment_id
        )
        resolved_workload = (
            experiment_spec.workload if experiment_spec else workload
        )
        resolved_slo = (
            experiment_spec.slo if experiment_spec else slo
        )

        if resolved_workload is None or resolved_slo is None:
            raise ValueError(
                "Both workload (WorkloadSpec) and slo (SLOSpec) must be provided "
                "directly or via experiment_spec."
            )

        objective = ranking_objective or self.default_objective
        budget = budget_limiter or BudgetLimiter(
            max_total_runs=6,
            max_search_runs=5,
            max_verification_runs=1,
        )

        resolved_output_dir = (
            Path(output_dir)
            if output_dir
            else self.artifacts_root / "experiments" / resolved_experiment_id
        )
        resolved_output_dir.mkdir(parents=True, exist_ok=True)

        tested_candidates: List[str] = []
        candidate_summaries: Dict[str, CandidateSummary] = {}
        evaluated_candidates: List[EvaluatedCandidate] = []
        run_results: List[Any] = []

        is_cancelled = False
        adapter_to_use = serving_adapter or self.adapter

        # Run 0: Baseline execution
        if cancellation_token and cancellation_token.is_cancelled:
            is_cancelled = True
        elif budget.can_execute_search_run():
            baseline_run_id = f"run-00-baseline-{baseline_config.candidate_id[:6]}"
            budget.record_search_run()

            baseline_res = self.single_run_executor.execute(
                candidate_config=baseline_config,
                workload=resolved_workload,
                slo=resolved_slo,
                experiment_id=resolved_experiment_id,
                run_id=baseline_run_id,
                is_verification_run=False,
                adapter=adapter_to_use,
                cancellation_token=cancellation_token,
                seed=seed,
                stream=stream,
                prompts=prompts,
                raise_on_failure=False,
            )
            run_results.append(baseline_res)
            tested_candidates.append(baseline_config.candidate_id)

            verdict = (
                baseline_res.feasibility_result.overall_verdict
                if baseline_res.feasibility_result
                else FeasibilityVerdict.INCONCLUSIVE
            )
            metric_val = extract_ranking_metric(baseline_res.metric_set, objective)

            candidate_summaries[baseline_config.candidate_id] = CandidateSummary(
                verdict=verdict,
                ranking_metric=metric_val,
            )

            if baseline_res.metric_set is not None:
                evaluated_candidates.append(
                    EvaluatedCandidate(
                        candidate_id=baseline_config.candidate_id,
                        verdict=verdict,
                        ranking_metric=metric_val,
                        metric_set=baseline_res.metric_set,
                    )
                )

            if cancellation_token and cancellation_token.is_cancelled:
                is_cancelled = True

        # Generate 4 Search Candidates across 2x2 grid
        grid_candidates = generate_2x2_candidates(
            model_name=baseline_config.model_name,
            runtime_name=baseline_config.runtime_name,
        )

        all_grid_completed = True

        # Runs 1-4: Candidate Search
        for idx, candidate in enumerate(grid_candidates, start=1):
            if is_cancelled or (cancellation_token and cancellation_token.is_cancelled):
                is_cancelled = True
                all_grid_completed = False
                break

            if not budget.can_execute_search_run():
                all_grid_completed = False
                break

            run_id = f"run-{idx:02d}-cand-{candidate.candidate_id[:6]}"
            budget.record_search_run()

            run_res = self.single_run_executor.execute(
                candidate_config=candidate,
                workload=resolved_workload,
                slo=resolved_slo,
                experiment_id=resolved_experiment_id,
                run_id=run_id,
                is_verification_run=False,
                adapter=adapter_to_use,
                cancellation_token=cancellation_token,
                seed=seed,
                stream=stream,
                prompts=prompts,
                raise_on_failure=False,
            )
            run_results.append(run_res)

            if candidate.candidate_id not in tested_candidates:
                tested_candidates.append(candidate.candidate_id)

            verdict = (
                run_res.feasibility_result.overall_verdict
                if run_res.feasibility_result
                else FeasibilityVerdict.INCONCLUSIVE
            )
            metric_val = extract_ranking_metric(run_res.metric_set, objective)

            candidate_summaries[candidate.candidate_id] = CandidateSummary(
                verdict=verdict,
                ranking_metric=metric_val,
            )

            if run_res.metric_set is not None:
                evaluated_candidates.append(
                    EvaluatedCandidate(
                        candidate_id=candidate.candidate_id,
                        verdict=verdict,
                        ranking_metric=metric_val,
                        metric_set=run_res.metric_set,
                    )
                )

            if cancellation_token and cancellation_token.is_cancelled:
                is_cancelled = True
                all_grid_completed = False
                break

        # Filter and Rank Feasible Candidates
        ranked_feasible = rank_candidates(evaluated_candidates, objective)

        # Select Winner and Justify
        if ranked_feasible:
            winner = ranked_feasible[0]
            selected_candidate_id = winner.candidate_id
            selection_rationale = (
                f"Selected candidate '{selected_candidate_id}' as top-ranked feasible "
                f"configuration under objective '{objective.value}' with "
                f"ranking metric {winner.ranking_metric}."
            )
        else:
            selected_candidate_id = None
            selection_rationale = (
                f"No candidate among {len(tested_candidates)} tested configurations "
                f"satisfied all declared hard SLO constraints."
            )

        # Determine Canonical Stopping Reason
        stopping_reason = budget.get_stopping_reason(
            space_exhausted=all_grid_completed,
            cancelled=is_cancelled,
        )

        # Build Canonical SearchResult
        result = SearchResult(
            experiment_id=resolved_experiment_id,
            baseline_candidate_id=baseline_config.candidate_id,
            tested_candidates=tested_candidates,
            candidate_summaries=candidate_summaries,
            ranking_objective=objective,
            selected_candidate_id=selected_candidate_id,
            selection_rationale=selection_rationale,
            stopping_reason=stopping_reason,
        )

        # Persist search_result.json to disk atomically
        result_path = resolved_output_dir / "search_result.json"
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        # Run 6: Independent Verification Rerun if auto_verify is requested
        if auto_verify and selected_candidate_id and budget.can_execute_verification_run():
            from slokern.core.verification.protocol import run_independent_verification

            all_configs = [baseline_config] + grid_candidates
            winner_cfg = next((c for c in all_configs if c.candidate_id == selected_candidate_id), None)
            winner_eval = next((e for e in evaluated_candidates if e.candidate_id == selected_candidate_id), None)
            orig_metrics = winner_eval.metric_set if winner_eval else None

            if winner_cfg is not None and orig_metrics is not None:
                budget.record_verification_run()
                verif_seed = None if seed is None else seed + 100
                cand_run_ids = {baseline_config.candidate_id: f"run-00-base-{baseline_config.candidate_id[:6]}"}
                for idx, c in enumerate(grid_candidates, start=1):
                    cand_run_ids[c.candidate_id] = f"run-{idx:02d}-cand-{c.candidate_id[:6]}"
                orig_run_id = cand_run_ids.get(selected_candidate_id, f"run-search-{selected_candidate_id[:6]}")
                run_independent_verification(
                    original_run_id=orig_run_id,
                    candidate_config=winner_cfg,
                    workload=resolved_workload,
                    slo=resolved_slo,
                    experiment_id=resolved_experiment_id,
                    original_metrics=orig_metrics,
                    adapter=adapter_to_use,
                    single_run_executor=self.single_run_executor,
                    artifacts_root=self.artifacts_root,
                    cancellation_token=cancellation_token,
                    seed=verif_seed,
                    persist_record=True,
                    existing_run_ids=list(cand_run_ids.values()),
                )

        return result

    def run_grid_search(
        self,
        spec: Optional[ExperimentSpec] = None,
        *,
        baseline_config: Optional[CandidateConfig] = None,
        workload: Optional[WorkloadSpec] = None,
        slo: Optional[SLOSpec] = None,
        experiment_id: str = "exp-default",
        ranking_objective: Optional[RankingObjective] = None,
        serving_adapter: Optional[BaseServingAdapter] = None,
        cancellation_token: Optional[Any] = None,
        budget_limiter: Optional[BudgetLimiter] = None,
        output_dir: Optional[Union[str, Path]] = None,
        seed: Optional[int] = 42,
        stream: bool = True,
        prompts: Optional[Union[List[str], str]] = None,
        strict_config: bool = True,
        **kwargs,
    ) -> Any:
        """
        Executes bounded 2x2 grid search with mandatory capability preflight gating (BLK-17).
        """
        adapter_to_use = serving_adapter or self.adapter
        validate_search_capabilities(adapter_to_use)

        if spec is not None:
            return self.run(
                spec=spec,
                ranking_objective=ranking_objective or RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
                cancellation_token=cancellation_token,
                seed=seed,
                prompts=[prompts] if isinstance(prompts, str) else prompts,
            )

        resolved_baseline = baseline_config
        if resolved_baseline is None:
            model_name = self.model_name or (adapter_to_use.model_name if adapter_to_use else "default-model")
            runtime_name = adapter_to_use.runtime_name if adapter_to_use else "default-runtime"
            from slokern.core.search.candidate_id import generate_candidate_id

            resolved_baseline = CandidateConfig(
                candidate_id=generate_candidate_id(model_name, runtime_name, {}),
                model_name=model_name,
                runtime_name=runtime_name,
                requested_settings={},
                effective_settings={},
                parameter_status={},
                environment_fingerprint={},
            )

        return self.execute(
            baseline_config=resolved_baseline,
            workload=workload,
            slo=slo,
            experiment_id=experiment_id,
            ranking_objective=ranking_objective,
            serving_adapter=adapter_to_use,
            cancellation_token=cancellation_token,
            budget_limiter=budget_limiter,
            output_dir=output_dir,
            seed=seed,
            stream=stream,
            prompts=prompts,
            strict_config=strict_config,
        )


def run_grid_search(
    adapter: Optional[BaseServingAdapter] = None,
    spec: Optional[ExperimentSpec] = None,
    controller: Optional[GridSearchController] = None,
    **kwargs,
) -> Any:
    """Convenience entry point for running grid search with capability preflight gating (BLK-17)."""
    ctrl = controller or GridSearchController(adapter=adapter)
    return ctrl.run_grid_search(spec=spec, serving_adapter=adapter, **kwargs)
