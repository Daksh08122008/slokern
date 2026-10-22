# Daksh

import uuid
from typing import Dict, Any, Callable
from evaluator.core import evaluate_run
from evaluator.schemas import Verdict, VerdictState


class IndependentVerificationRunner:
    """
    Executes a mandatory independent re-run of the winning candidate configuration
    to prove that benchmark performance is reproducible and not a statistical fluke.
    """

    def __init__(self, benchmark_executor_func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        :param benchmark_executor_func: A function provided by Saptak/Aman's 
               engine that actually executes a live benchmark run given a configuration.
        """
        self.benchmark_executor_func = benchmark_executor_func

    def verify_winner(
        self,
        winning_candidate_id: str,
        winning_config: Dict[str, Any],
        slo_spec: Dict[str, Any],
        original_metrics: Dict[str, Any],
        drift_tolerance_pct: float = 5.0
    ) -> Verdict:
        """
        Spins up a fresh, isolated run for the winning configuration, 
        evaluates it, and checks for performance drift against the search metrics.
        """
        # 1. Generate a brand-new independent run ID
        verification_run_id = f"verify_{uuid.uuid4().hex[:8]}"
        
        print(f"[*] Starting Independent Verification for candidate {winning_candidate_id}...")
        print(f"[*] Assigned Verification Run ID: {verification_run_id}")

        # 2. Execute a fresh benchmark run
        try:
            fresh_metrics = self.benchmark_executor_func(winning_config)
        except Exception as e:
            # If execution crashes during verification, it fails safely
            return Verdict(
                run_id=verification_run_id,
                candidate_id=winning_candidate_id,
                state=VerdictState.INFEASIBLE,
                notes=f"Independent verification run crashed during execution: {str(e)}"
            )

        # 3. Evaluate the fresh metrics using your core evaluator logic
        verification_verdict = evaluate_run(
            run_id=verification_run_id,
            candidate_id=winning_candidate_id,
            metrics=fresh_metrics,
            slo_spec=slo_spec
        )

        # 4. If the verification run itself failed or is inconclusive, return immediately
        if verification_verdict.state != VerdictState.FEASIBLE:
            verification_verdict.notes = (
                f"Verification FAILED: Candidate failed re-evaluation. "
                f"Original reason codes: {verification_verdict.reasons}"
            )
            return verification_verdict

        # 5. Check for severe performance drift compared to original search metrics
        original_ttft = original_metrics.get("ttft_p90", 0.0)
        fresh_ttft = fresh_metrics.get("ttft_p90", 0.0)
        
        if original_ttft > 0:
            drift_pct = ((fresh_ttft - original_ttft) / original_ttft) * 100.0
            if drift_pct > drift_tolerance_pct:
                verification_verdict.state = VerdictState.INFEASIBLE
                verification_verdict.notes = (
                    f"Verification FAILED due to performance drift: "
                    f"TTFT degraded by {drift_pct:.2f}% (tolerance: {drift_tolerance_pct}%)"
                )
                return verification_verdict

        # 6. Success! Certified verified winner
        verification_verdict.notes = "Independent verification PASSED. Performance is stable and reproducible."
        return verification_verdict

    