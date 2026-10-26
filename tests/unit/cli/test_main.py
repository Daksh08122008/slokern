"""
Purpose: Unit tests for CLI main routing and argument parsing.
Owner: Rajdeep
"""

from unittest.mock import patch
import pytest

from slokern.cli.main import main, build_parser


def test_build_parser():
    parser = build_parser()
    assert parser.prog == "slokern"


def test_main_no_arguments(capsys):
    ret = main([])
    assert ret == 1
    out = capsys.readouterr().out
    assert "usage: slokern" in out


def test_main_invalid_command():
    with pytest.raises(SystemExit) as exc_info:
        main(["unknown-cmd"])
    assert exc_info.value.code != 0


def test_main_routes_to_smoke_test():
    with patch("slokern.cli.main.smoke_test_command", return_value=0) as mock_cmd:
        ret = main(["smoke-test", "--adapter", "fake", "--prompt", "hello"])
        assert ret == 0
        mock_cmd.assert_called_once_with(
            adapter="fake",
            model=None,
            base_url=None,
            api_key=None,
            prompt="hello",
        )


def test_main_routes_to_optimize():
    with patch("slokern.cli.main.optimize_command", return_value=0) as mock_cmd:
        ret = main(["optimize", "spec.json", "--adapter", "fake", "--objective", "min_p95_ttft"])
        assert ret == 0
        mock_cmd.assert_called_once_with(
            spec_file="spec.json",
            adapter="fake",
            objective="min_p95_ttft",
            output_dir=None,
        )


def test_main_routes_to_optimize_with_verify():
    with patch("slokern.cli.main.optimize_command", return_value=0) as mock_cmd:
        ret = main(["optimize", "spec.json", "--adapter", "fake", "--verify"])
        assert ret == 0
        mock_cmd.assert_called_once_with(
            spec_file="spec.json",
            adapter="fake",
            objective=None,
            output_dir=None,
            auto_verify=True,
        )


def test_main_routes_to_verify():
    with patch("slokern.cli.main.verify_command", return_value=0) as mock_cmd:
        ret = main(["verify", "spec.json", "results.json", "--adapter", "fake"])
        assert ret == 0
        mock_cmd.assert_called_once_with(
            spec_file="spec.json",
            search_result_file="results.json",
            adapter="fake",
            output_dir=None,
        )


def test_main_routes_to_report():
    with patch("slokern.cli.main.report_command", return_value=0) as mock_cmd:
        ret = main(["report", "artifacts/exp-1", "--output-dir", "out/"])
        assert ret == 0
        mock_cmd.assert_called_once_with(
            experiment_dir="artifacts/exp-1",
            output_dir="out/",
        )


def test_main_routes_to_validate():
    with patch("slokern.cli.main.validate_command", return_value=0) as mock_cmd:
        ret = main(["validate", "spec.json"])
        assert ret == 0
        mock_cmd.assert_called_once_with(
            spec_file="spec.json",
        )
