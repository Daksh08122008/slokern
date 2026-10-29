from slokern.contracts.enums import (
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
    VerificationState,
)
from slokern.contracts.run import RunRecord
from slokern.contracts.verdict import FeasibilityResult
from slokern.contracts.verification import VerificationRecord


def test_enum_values_and_state_transitions():
    assert ExecutionStatus.PENDING == "PENDING"
    assert ExecutionStatus.RUNNING == "RUNNING"
    assert ExecutionStatus.COMPLETED == "COMPLETED"
    assert ExecutionStatus.FAILED == "FAILED"
    assert ExecutionStatus.CANCELLED == "CANCELLED"

    assert EvidenceValidity.VALID == "VALID"
    assert EvidenceValidity.INVALID == "INVALID"
    assert EvidenceValidity.CONTAMINATED == "CONTAMINATED"

    assert FeasibilityVerdict.FEASIBLE == "FEASIBLE"
    assert FeasibilityVerdict.INFEASIBLE == "INFEASIBLE"
    assert FeasibilityVerdict.INCONCLUSIVE == "INCONCLUSIVE"

    assert VerificationState.NOT_RUN == "NOT_RUN"
    assert VerificationState.VERIFYING == "VERIFYING"
    assert VerificationState.VERIFIED == "VERIFIED"
    assert VerificationState.VERIFICATION_FAILED == "VERIFICATION_FAILED"
    assert VerificationState.VERIFICATION_INCONCLUSIVE == "VERIFICATION_INCONCLUSIVE"

def test_verification_states_independent():
    # Execution failed != SLO infeasible
    run_rec = RunRecord(
        run_id="run-1",
        experiment_id="exp-1",
        candidate_id="cand-1",
        is_verification_run=False,
        execution_status=ExecutionStatus.FAILED
    )
    assert run_rec.execution_status == ExecutionStatus.FAILED

    # Feasibility does not establish that a candidate has passed independent verification.
    feas_res = FeasibilityResult(
        policy_version="1.0.0",
        run_id="run-1",
        overall_verdict=FeasibilityVerdict.FEASIBLE,
        constraint_evaluations=[],
        validity_status=EvidenceValidity.VALID
    )
    assert feas_res.overall_verdict == FeasibilityVerdict.FEASIBLE

    verif_rec = VerificationRecord(
        verification_id="v-1",
        experiment_id="exp-1",
        candidate_id="cand-1",
        original_run_id="run-1",
        verification_run_id="run-2",
        verification_verdict=VerificationState.NOT_RUN
    )
    assert verif_rec.verification_verdict == VerificationState.NOT_RUN

    # These three are separate objects, showing state independence.
    assert run_rec.execution_status != ExecutionStatus.COMPLETED
    assert feas_res.overall_verdict == FeasibilityVerdict.FEASIBLE
    assert verif_rec.verification_verdict == VerificationState.NOT_RUN
