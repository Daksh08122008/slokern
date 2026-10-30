"""
Purpose: CLI entry point and command registration.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 11, DEC-0014
"""

import argparse
import sys
from typing import List, Optional

from slokern.cli.commands.credentials import (
    credentials_setup_command,
    credentials_status_command,
    credentials_validate_command,
)
from slokern.cli.commands.optimize import optimize_command
from slokern.cli.commands.report import report_command
from slokern.cli.commands.smoke_test import smoke_test_command
from slokern.cli.commands.validate import validate_command
from slokern.cli.commands.verify import verify_command
from slokern.config.secrets import load_runtime_secrets



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
    smoke_parser.add_argument(
        "--prompt",
        default="SLOKern preflight smoke test probe.",
        help="Prompt text for test probe request.",
    )
    smoke_parser.add_argument(
        "--artifact-path",
        help="Path to persist smoke test result JSON (default: artifacts/smoke_test_result.json).",
    )
    smoke_parser.add_argument(
        "--stream",
        action="store_true",
        help="Execute probe in streaming mode to verify TokenChunk streaming and measure TTFT.",
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
    opt_parser.add_argument(
        "--verify",
        action="store_true",
        help="Execute independent verification rerun (Run 6) immediately after candidate search.",
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

    # serve
    serve_p = subparsers.add_parser(
        "serve",
        help="Run the SLOKern control plane HTTP API server.",
    )
    serve_p.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    serve_p.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    serve_p.add_argument("--artifacts-dir", default="artifacts", help="Artifacts root directory")

    # credentials
    cred_parser = subparsers.add_parser(
        "credentials",
        help="Inspect, set up, and validate runtime credentials.",
    )
    cred_subparsers = cred_parser.add_subparsers(dest="cred_action", help="Credential actions")

    status_p = cred_subparsers.add_parser("status", help="Check credential status without exposing values.")
    status_p.add_argument("--secrets-file", help="Explicit path to secrets file.")
    status_p.add_argument("--json", action="store_true", help="Output status as JSON.")

    setup_p = cred_subparsers.add_parser("setup", help="Display instructions for secure credential configuration.")
    setup_p.add_argument("--source", help="Filter setup guidance by source (env, file).")

    val_p = cred_subparsers.add_parser("validate", help="Validate credentials format and remote authentication.")
    val_p.add_argument("--offline", action="store_true", help="Perform offline syntax check without contacting endpoint.")
    val_p.add_argument("--secrets-file", help="Explicit path to secrets file.")
    val_p.add_argument("--timeout", type=float, default=15.0, help="Network timeout in seconds (default: 15).")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    # Bootstrap discovered runtime secrets into environment early
    load_runtime_secrets()

    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "smoke-test":
        smoke_kwargs = {
            "adapter": args.adapter,
            "model": args.model,
            "base_url": args.base_url,
            "prompt": args.prompt,
        }
        if getattr(args, "artifact_path", None):
            smoke_kwargs["artifact_path"] = args.artifact_path
        if getattr(args, "stream", False):
            smoke_kwargs["stream"] = args.stream
        return smoke_test_command(**smoke_kwargs)
    elif args.command == "optimize":
        kwargs = {}
        if getattr(args, "verify", False):
            kwargs["auto_verify"] = True
        return optimize_command(
            spec_file=args.spec_file,
            adapter=args.adapter,
            objective=args.objective,
            output_dir=args.output_dir,
            **kwargs,
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
    elif args.command == "serve":
        from slokern.api.app import run_server
        run_server(host=args.host, port=args.port, artifacts_root=args.artifacts_dir)
        return 0
    elif args.command == "credentials":
        if args.cred_action == "status":
            return credentials_status_command(secrets_file=args.secrets_file, json_output=args.json)
        elif args.cred_action == "setup":
            return credentials_setup_command(source=args.source)
        elif args.cred_action == "validate":
            return credentials_validate_command(
                offline=args.offline,
                secrets_file=args.secrets_file,
                timeout_s=args.timeout,
            )
        else:
            print("Usage: slokern credentials {status,setup,validate} ...", file=sys.stderr)
            return 1
    else:
        parser.print_help(file=sys.stderr)
        return 1



if __name__ == "__main__":
    sys.exit(main())
