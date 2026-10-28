"""
Purpose: API application assembly and multi-threaded HTTP server.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 3, 9, 12 and DEC-0014
"""

import json
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple, Union

from slokern.api.routes.health import get_health, run_smoke_probe
from slokern.api.routes.reports import get_report_data
from slokern.api.routes.runs import (
    dispatch_single_run,
    get_run_queue,
    get_run_status,
    list_recent_runs,
)
from slokern.api.routes.verification import dispatch_verification_run
from slokern.api.settings import (
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
)
from slokern.engine.store.redact import sanitize_secret_message


def handle_api_request(
    method: str,
    path: str,
    body: Union[Dict[str, Any], str, bytes, None] = None,
    artifacts_root: str = "artifacts",
) -> Tuple[int, Dict[str, str], bytes]:
    """
    In-process request dispatcher allowing deterministic unit testing without TCP sockets.
    Returns (status_code, headers_dict, response_bytes).
    """
    parsed = urllib.parse.urlsplit(path)
    clean_path = parsed.path.rstrip("/")
    query = urllib.parse.parse_qs(parsed.query)

    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

    parsed_body: Dict[str, Any] = {}
    if isinstance(body, (str, bytes)):
        try:
            val = json.loads(body)
            if isinstance(val, dict):
                parsed_body = val
        except Exception:
            pass
    elif isinstance(body, dict):
        parsed_body = body

    if method == "OPTIONS":
        return 200, headers, b""

    try:
        # GET /api/health
        if method == "GET" and clean_path == "/api/health":
            adapter = query.get("adapter", [None])[0]
            res = get_health(adapter_name=adapter)
            return 200, headers, json.dumps(res).encode("utf-8")

        # POST /api/smoke-test
        if method == "POST" and clean_path == "/api/smoke-test":
            payload = parsed_body
            adapter = payload.get("adapter")
            prompt = payload.get("prompt", "SLOKern preflight smoke test probe.")
            res = run_smoke_probe(adapter_name=adapter, prompt=prompt)
            status = 200 if res.get("status") == "success" else 503
            return status, headers, json.dumps(res).encode("utf-8")

        # POST /api/runs/single
        if method == "POST" and clean_path == "/api/runs/single":
            payload = parsed_body
            res = dispatch_single_run(payload, artifacts_root=artifacts_root)
            return 200, headers, json.dumps(res).encode("utf-8")

        # GET /api/runs
        if method == "GET" and clean_path == "/api/runs":
            runs_list = list_recent_runs(artifacts_root=artifacts_root)
            return 200, headers, json.dumps(runs_list).encode("utf-8")

        # GET /api/runs/<run_id>/trace
        match_trace = re.match(r"^/api/runs/(.+)/trace$", clean_path)
        if method == "GET" and match_trace:
            run_id = match_trace.group(1)
            # Security: Strict alphanumeric validation to prevent directory traversal
            if not re.match(r"^[a-zA-Z0-9_\-]+$", run_id):
                err = {"error": f"Invalid run_id format: {run_id}"}
                return 400, headers, json.dumps(err).encode("utf-8")

            resolved_path = None
            candidate_paths = [
                Path(artifacts_root) / "runs" / run_id / "raw_measurements.jsonl",
                Path(artifacts_root) / "runs" / run_id / "measurements.jsonl",
            ]
            for p in candidate_paths:
                if p.exists() and p.stat().st_size > 0:
                    resolved_path = p
                    break

            if resolved_path is None:
                for pat in (
                    f"experiments/*/runs/{run_id}/raw_measurements.jsonl",
                    f"experiments/*/runs/{run_id}/measurements.jsonl",
                ):
                    matches = list(Path(artifacts_root).glob(pat))
                    if matches and matches[0].exists() and matches[0].stat().st_size > 0:
                        resolved_path = matches[0]
                        break

            if resolved_path is None or not resolved_path.exists():
                err = {"error": f"Raw trace artifact not found for run {run_id}"}
                return 404, headers, json.dumps(err).encode("utf-8")

            trace_headers = dict(headers)
            trace_headers["Content-Type"] = "application/x-ndjson; charset=utf-8"
            trace_headers["Content-Disposition"] = f'attachment; filename="raw_measurements_{run_id}.jsonl"'
            return 200, trace_headers, resolved_path.read_bytes()

        # GET /api/runs/<run_id>
        match_run = re.match(r"^/api/runs/(.+)$", clean_path)
        if method == "GET" and match_run:
            run_id = match_run.group(1)
            if not re.match(r"^[a-zA-Z0-9_\-]+$", run_id):
                err = {"error": f"Invalid run_id format: {run_id}"}
                return 400, headers, json.dumps(err).encode("utf-8")
            res = get_run_status(run_id, artifacts_root=artifacts_root)
            status = 404 if res.get("error") == "Run not found" else 200
            return status, headers, json.dumps(res).encode("utf-8")

        # POST /api/runs/verify
        if method == "POST" and clean_path == "/api/runs/verify":
            payload = parsed_body
            res = dispatch_verification_run(payload, artifacts_root=artifacts_root)
            return 200, headers, json.dumps(res).encode("utf-8")

        # GET /api/reports/<experiment_id>
        match_rep = re.match(r"^/api/reports/(.+)$", clean_path)
        if method == "GET" and match_rep:
            exp_id = match_rep.group(1)
            if not re.match(r"^[a-zA-Z0-9_\-]+$", exp_id):
                err = {"error": f"Invalid experiment_id format: {exp_id}"}
                return 400, headers, json.dumps(err).encode("utf-8")
            res = get_report_data(exp_id, artifacts_root=artifacts_root)
            return 200, headers, json.dumps(res).encode("utf-8")

        # 404 Not Found
        err = {"error": f"Endpoint not found: {method} {clean_path}"}
        return 404, headers, json.dumps(err).encode("utf-8")

    except Exception as exc:
        sanitized = sanitize_secret_message(str(exc))
        err = {"error": sanitized, "status": "server_error"}
        return 500, headers, json.dumps(err).encode("utf-8")


class SlokernHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    Standard HTTP Request Handler implementing the SLOKern Control Plane REST & SSE API.
    """

    artifacts_root: str = "artifacts"

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        clean_path = parsed.path.rstrip("/")

        # Server-Sent Events stream: /api/runs/<run_id>/events
        match_sse = re.match(r"^/api/runs/(.+)/events$", clean_path)
        if match_sse:
            run_id = match_sse.group(1)
            if not re.match(r"^[a-zA-Z0-9_\-]+$", run_id):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid run_id format: {run_id}"}).encode("utf-8"))
                return

            queue = get_run_queue(run_id)
            if not queue:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Active run queue not found for {run_id}"}).encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self._send_cors_headers()
            self.end_headers()

            try:
                while True:
                    event = queue.get(timeout=1.0)
                    if event is None:
                        if queue.is_closed:
                            break
                        continue
                    self.wfile.write(event.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        # Standard REST GET dispatch
        status_code, headers, body_bytes = handle_api_request(
            method="GET",
            path=self.path,
            artifacts_root=self.artifacts_root,
        )
        self.send_response(status_code)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                body = json.loads(raw_body)
            except Exception:
                body = {}

        status_code, headers, body_bytes = handle_api_request(
            method="POST",
            path=self.path,
            body=body,
            artifacts_root=self.artifacts_root,
        )
        self.send_response(status_code)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body_bytes)

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy logging in tests/headless runs unless SLOKERN_LOG_HTTP=1
        import os
        if os.environ.get("SLOKERN_LOG_HTTP", "") == "1":
            super().log_message(format, *args)


def create_api_server(
    host: str = DEFAULT_API_HOST,
    port: int = DEFAULT_API_PORT,
    artifacts_root: str = "artifacts",
) -> ThreadingHTTPServer:
    """
    Instantiates multi-threaded HTTP server for SLOKern control plane.
    """
    handler = SlokernHTTPRequestHandler
    handler.artifacts_root = artifacts_root
    return ThreadingHTTPServer((host, port), handler)


def run_server(
    host: str = DEFAULT_API_HOST,
    port: int = DEFAULT_API_PORT,
    artifacts_root: str = "artifacts",
) -> None:
    server = create_api_server(host=host, port=port, artifacts_root=artifacts_root)
    print(f"[SLOKern API Control Plane] Listening on http://{host}:{port}")
    print(f"  Artifacts directory: {artifacts_root}")
    print("  Available endpoints: GET /api/health, POST /api/smoke-test, POST /api/runs/single, GET /api/runs, GET /api/runs/<id>/trace, GET /api/reports/<id>")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down SLOKern API server.")
        server.shutdown()


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_API_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_API_PORT
    run_server(host=host, port=port)
