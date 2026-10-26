"""
Purpose: CLI entry point and command registration.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 11, DEC-0014
"""

import argparse
import sys
from typing import List, Optional

from slokern.cli.commands.optimize import optimize_command
from slokern.cli.commands.report import report_command
from slokern.cli.commands.smoke_test import smoke_test_command
from slokern.cli.commands.validate import validate_command
from slokern.cli.commands.verify import verify_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slokern",
        description="SLOKern: Optimize inference. Verify performance.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # smoke-test
    smoke_parser = subparsers.add_parser(
        "smoke-test",
        help="Run preflight probe checking endpoint health and request latency.",
    )
    smoke_parser.add_argument(
        "--adapter",
        choices=["local", "nebius", "fake"],
        help="Serving backend adapter (local, nebius, fake). Defaults to local (or SLOKERN_ADAPTER).",
    )
    smoke_parser.add_argument("--model", help="Target model identifier.")
    smoke_parser.add_argument("--base-url", help="Base URL of the serving endpoint.")
    smoke_parser.add_argument("--api-key", help="API key for authentication if required.")
    smoke_parser.add_argument(
        "--prompt",
        default="SLOKern preflight smoke test probe.",
        help="Prompt text for test probe request.",
    )

    # optimize
    opt_parser = subparsers.add_parser(
        "optimize",
        help="Run a bounded optimization experiment under capability gating.",
    )
    opt_parser.add_argument("spec_file", help="Path to ExperimentSpec JSON file.")
    opt_parser.add_argument(
        "--adapter",
        choices=["local", "nebius", "fake"],
        help="Serving backend adapter (local, nebius, fake). Defaults to local (or SLOKERN_ADAPTER).",
    )
    opt_parser.add_argument(
        "--objective",
        help="Ranking objective (e.g. min_p95_ttft, max_throughput_under_slo, min_cost_under_slo).",
    )
    opt_parser.add_argument(
        "--output-dir",
        help="Directory to persist experiment artifacts (default: artifacts).",
    )

    # verify
    verify_p = subparsers.add_parser(
        "verify",
        help="Independently rerun and audit the winning candidate under a fresh run ID.",
    )
    verify_p.add_argument("spec_file", help="Path to ExperimentSpec JSON file.")
    verify_p.add_argument("search_result", help="Path to SearchResult JSON file.")
    verify_p.add_argument(
        "--adapter",
        choices=["local", "nebius", "fake"],
        help="Serving backend adapter (local, nebius, fake). Defaults to local (or SLOKERN_ADAPTER).",
    )
    verify_p.add_argument(
        "--output-dir",
        help="Directory to persist verification artifacts (default: artifacts).",
    )

    # report
    report_p = subparsers.add_parser(
        "report",
        help="Export an evidence-backed report artifact and Markdown document.",
    )
    report_p.add_argument("experiment_dir", help="Directory containing experiment artifacts.")
    report_p.add_argument(
        "--output-dir",
        help="Directory to write report artifacts (defaults to experiment_dir).",
    )

    # validate
    validate_p = subparsers.add_parser(
        "validate",
        help="Validate an ExperimentSpec JSON file and budget limits.",
    )
    validate_p.add_argument("spec_file", help="Path to ExperimentSpec JSON file.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "smoke-test":
        return smoke_test_command(
            adapter=args.adapter,
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            prompt=args.prompt,
        )
    elif args.command == "optimize":
        return optimize_command(
            spec_file=args.spec_file,
            adapter=args.adapter,
            objective=args.objective,
            output_dir=args.output_dir,
        )
    elif args.command == "verify":
        return verify_command(
            spec_file=args.spec_file,
            search_result_file=args.search_result,
            adapter=args.adapter,
            output_dir=args.output_dir,
        )
    elif args.command == "report":
        return report_command(
            experiment_dir=args.experiment_dir,
            output_dir=args.output_dir,
        )
    elif args.command == "validate":
        return validate_command(
            spec_file=args.spec_file,
        )
    else:
        parser.print_help(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
