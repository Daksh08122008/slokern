"""CLI validation tests for spec and budget failures."""

import json

from slokern.cli.commands.validate import validate_command
from slokern.contracts.enums import ArrivalMode
from slokern.contracts.spec import (
    ExperimentBudget,
    ExperimentSpec,
    ExperimentVerificationPolicy,
    SLOSpec,
    WorkloadSpec,
)


def make_spec(max_candidates=4):
    return ExperimentSpec(
        experiment_id="cli-validation-test",
        workload=WorkloadSpec(
            schema_version="1.0.0",
            workload_name="cli-validation",
            fixture_id="demo-fixture",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=1.0,
            concurrency_limit=1,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=8,
            max_output_tokens=8,
        ),
        slo=SLOSpec(slo_id="test-slo", constraints=[], min_sample_count=1),
        search_space={},
        budget=ExperimentBudget(
            max_candidates=max_candidates,
            max_wallclock_seconds=30,
        ),
        verification_policy=ExperimentVerificationPolicy(),
    )


def test_validate_command_accepts_valid_spec(tmp_path, capsys):
    spec_path = tmp_path / "valid-spec.json"
    spec_path.write_text(make_spec().model_dump_json())

    assert validate_command(str(spec_path)) == 0
    assert "Spec and budget valid." in capsys.readouterr().out


def test_validate_command_rejects_invalid_budget(tmp_path, capsys):
    spec_path = tmp_path / "invalid-budget.json"
    payload = make_spec(max_candidates=0).model_dump(mode="json")
    spec_path.write_text(json.dumps(payload))

    assert validate_command(str(spec_path)) == 1
    assert "budget.max_candidates" in capsys.readouterr().err
