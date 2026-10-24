"""Bounded, deterministic 2×2 search orchestration."""

from dataclasses import dataclass
import itertools
import math
import threading
import time
from typing import List, Optional, Sequence

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ExecutionStatus, FeasibilityVerdict, RankingObjective
from slokern.contracts.search import CandidateSummary, SearchResult
from slokern.contracts.spec import ExperimentSpec
from slokern.core.search.budget import BudgetValidationError, validate_budget
from slokern.core.search.candidate_id import generate_candidate_id
from slokern.core.search.rank import EvaluatedCandidate, rank_candidates
from slokern.engine.runner.cancel import CancellationToken
from slokern.engine.runner.run_executor import SingleRunExecutor, SingleRunResult
from slokern.engine.serving.base import BaseServingAdapter


DEFAULT_SEARCH_SPACE = {
    "max_num_batched_tokens": (1024, 2048),
    "max_num_seqs": (16, 64),
}


class SearchConfigurationError(ValueError):
    """Raised when the experiment cannot be safely executed as declared."""


class SearchExecutionError(RuntimeError):
    """Raised when a search run fails or is cancelled before valid evidence."""

    def __init__(self, message: str, run_result: Optional[SingleRunResult] = None):
        super().__init__(message)
        self.run_result = run_result


@dataclass
class GridSearchOutcome:
    """Search decision plus the physical run results that support it."""

    search_result: SearchResult
    run_results: List[SingleRunResult]


class GridSearchController:
    """Run a baseline followed by at most four legal candidates.

    The current evidence-backed Mode B objective is output-token throughput
    under SLO. Monetary and GPU-seconds objectives are rejected until the
    experiment has verified pricing or GPU allocation evidence.
    """

    def __init__(
        self,
        executor: SingleRunExecutor,
        adapter: BaseServingAdapter,
        model_name: str,
    ) -> None:
        self.executor = executor
        self.adapter = adapter
        self.model_name = model_name

    def run(
        self,
        spec: ExperimentSpec,
        *,
        ranking_objective: RankingObjective,
        cancellation_token: Optional[CancellationToken] = None,
        seed: Optional[int] = 42,
        prompts: Optional[Sequence[str]] = None,
    ) -> GridSearchOutcome:
        """Validate, then execute baseline and bounded candidates in order."""
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

        candidate_settings = self._candidate_settings(spec)
        capabilities = self.adapter.get_capabilities()
        if not capabilities.is_model_supported(self.model_name):
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

        token = cancellation_token or CancellationToken()
        deadline = time.monotonic() + spec.budget.max_wallclock_seconds
        timeout = threading.Timer(spec.budget.max_wallclock_seconds, token.cancel)
        timeout.daemon = True
        timeout.start()
        run_results: List[SingleRunResult] = []
        evaluated: List[EvaluatedCandidate] = []
        candidate_summaries = {}
        tested_ids: List[str] = []
        candidate_limit = min(4, spec.budget.max_candidates)
        stopping_reason = "space_exhausted"

        try:
            configs = [self._make_config({})]
            configs.extend(
                self._make_config(settings)
                for settings in candidate_settings[:candidate_limit]
            )

            for index, config in enumerate(configs):
                if token.is_cancelled:
                    raise SearchExecutionError("Search was cancelled before the next run")
                if time.monotonic() >= deadline:
                    stopping_reason = "timeout"
                    break

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
                ranking_metric = self._ranking_metric(result) if verdict == FeasibilityVerdict.FEASIBLE else None
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
                    f"Selected {winner.candidate_id}: highest finite output-token "
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
            return GridSearchOutcome(search_result=search_result, run_results=run_results)
        finally:
            timeout.cancel()

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
        return CandidateConfig(
            candidate_id=generate_candidate_id(
                self.model_name, self.adapter.runtime_name, settings
            ),
            model_name=self.model_name,
            runtime_name=self.adapter.runtime_name,
            requested_settings=settings,
            effective_settings={},
            parameter_status={},
            environment_fingerprint={},
        )

    @staticmethod
    def _ranking_metric(result: SingleRunResult) -> Optional[float]:
        metrics = result.metric_set
        if metrics is None:
            return None
        value = metrics.token_throughput_tps
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        try:
            if not math.isfinite(value) or value < 0:
                return None
            return float(value)
        except OverflowError:
            return None
