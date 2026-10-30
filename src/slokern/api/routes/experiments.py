"""
Purpose: Experiment discovery, candidate hierarchy, search space retrieval, and verification status.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 3, 4, 5, 7, 14 and DEC-0014
"""

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from slokern.api.routes.runs import get_run_status
from slokern.contracts.enums import FeasibilityVerdict


def _find_experiment_dir(experiment_id: str, artifacts_root: str = "artifacts") -> Optional[Path]:
    """
    Safely locates an experiment directory under artifacts_root.
    Prevents path traversal attacks using strict regex validation.
    Prioritizes audit-offline-validation for campaign artifacts.
    """
    if not re.match(r"^[a-zA-Z0-9_\-]+$", experiment_id):
        return None

    root = Path(artifacts_root)
    # 1. Audit offline validation path (authoritative for demo campaign)
    p_audit = root / "audit-offline-validation" / "experiments" / experiment_id
    if p_audit.is_dir():
        return p_audit

    # 2. Direct artifacts/experiments/<id>
    p_direct = root / "experiments" / experiment_id
    if p_direct.is_dir():
        return p_direct

    # 3. Bootstrap / Codex validation path
    p_codex = root / "codex-validation-nebius-bootstrap-20261030" / "experiments" / experiment_id
    if p_codex.is_dir():
        return p_codex

    # 4. Glob fallback under artifacts root
    matches = list(root.glob(f"**/experiments/{experiment_id}"))
    if matches and matches[0].is_dir():
        return matches[0]

    return None


def _find_campaign_spec(experiment_id: str, fixtures_root: str = "fixtures/campaigns") -> Optional[Dict[str, Any]]:
    """Return the persisted campaign spec matching an experiment ID, if present."""
    root = Path(fixtures_root)
    if not root.is_dir():
        return None
    for spec_file in sorted(root.glob("*.json")):
        try:
            spec = json.loads(spec_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if spec.get("experiment_id") == experiment_id:
            return spec
    return None


def list_experiments(artifacts_root: str = "artifacts") -> List[Dict[str, Any]]:
    """
    Discovers all persisted experiments across the filesystem hierarchy.
    Extracts metadata, run counts, models, and explicit evidence classification.
    """
    root = Path(artifacts_root)
    exp_dirs: List[Path] = []
    seen_ids = set()

    # Prioritize audit-offline-validation first so it claims exp-audit-offline-campaign
    search_roots = [
        root / "audit-offline-validation" / "experiments",
        root / "experiments",
        root / "codex-validation-nebius-bootstrap-20261030" / "experiments",
    ]

    for s_root in search_roots:
        if s_root.is_dir():
            for p in s_root.iterdir():
                if p.is_dir() and p.name not in seen_ids and not p.name.startswith("."):
                    seen_ids.add(p.name)
                    exp_dirs.append(p)

    # Glob fallback for any remaining experiments
    for p in root.glob("**/experiments/*"):
        if p.is_dir() and p.name not in seen_ids and not p.name.startswith("."):
            seen_ids.add(p.name)
            exp_dirs.append(p)

    results: List[Dict[str, Any]] = []

    for d in exp_dirs:
        exp_id = d.name
        campaign_spec = _find_campaign_spec(exp_id)

        # Read search_result.json
        search_res = None
        sr_file = d / "search_result.json"
        if sr_file.exists():
            try:
                search_res = json.loads(sr_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Discover runs
        runs_dir = d / "runs"
        run_subdirs = [r for r in runs_dir.iterdir() if r.is_dir()] if runs_dir.is_dir() else []
        runs_count = len(run_subdirs)

        selected_candidate = search_res.get("selected_candidate_id") if search_res else None
        sample_run_id = ""
        if selected_candidate:
            for run_dir in run_subdirs:
                try:
                    run_record = json.loads((run_dir / "run_record.json").read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if run_record.get("candidate_id") == selected_candidate:
                    sample_run_id = run_dir.name
                    break
        if not sample_run_id and run_subdirs:
            sample_run_id = run_subdirs[0].name
        model_name = "Unavailable"
        runtime_name = "Unavailable"
        evidence_class = "UNVERIFIED"
        achieved_load = None
        error_rate = None
        measurement_validity = None
        client_saturation = None
        exclusions_count = None

        if sample_run_id:
            status = get_run_status(sample_run_id, artifacts_root=artifacts_root)
            if status.get("applied_config"):
                ac = status["applied_config"]
                model_name = ac.get("model_name", model_name)
                runtime_name = ac.get("runtime_name", runtime_name)
                fp = ac.get("environment_fingerprint", {})
                is_simulated = fp.get("is_simulated")
                if fp.get("mode") == "DEMO DATA" or is_simulated:
                    evidence_class = "DEMO DATA"
                elif fp.get("provider") == "nebius":
                    evidence_class = "LIVE"
                else:
                    evidence_class = "UNVERIFIED"

            ms = status.get("metric_set") or {}
            achieved_load = ms.get("achieved_load_rps")
            error_rate = ms.get("error_rate")
            client_saturation = ms.get("generator_saturated")
            feas = status.get("feasibility_result") or {}
            measurement_validity = feas.get("validity_status")
            raw_count = status.get("raw_measurements_count")
            sample_count = ms.get("sample_count")
            if isinstance(raw_count, int) and isinstance(sample_count, int):
                exclusions_count = raw_count - sample_count

        # Verification status
        verif_file = d / "verification_record.json"
        verif_status = "Pending"
        if verif_file.exists():
            try:
                vdata = json.loads(verif_file.read_text(encoding="utf-8"))
                verdict = vdata.get("verification_verdict", "")
                if verdict in ("VERIFIED", "VerificationVerdict.VERIFIED"):
                    verif_status = "Verified"
                elif "FAIL" in verdict:
                    verif_status = "Failed"
                else:
                    verif_status = "Inconclusive"
            except Exception:
                verif_status = "Pending"

        selected_candidate_data = next(
            (candidate for candidate in get_experiment_candidates(exp_id, artifacts_root)
             if candidate.get("id") == selected_candidate),
            None,
        ) if selected_candidate else None
        selected_verdict = (
            selected_candidate_data.get("feasibilityVerdict")
            if selected_candidate_data else "INCONCLUSIVE"
        )
        feasibility_status = {
            "FEASIBLE": "Feasible",
            "INFEASIBLE": "Infeasible",
            "INCONCLUSIVE": "Inconclusive",
        }.get(selected_verdict, "Inconclusive")
        tested_candidates = (search_res or {}).get("tested_candidates", [])
        space = (campaign_spec or {}).get("search_space", {})
        search_space_count = math.prod(len(values) for values in space.values()) if space else None

        mtime = d.stat().st_mtime
        updated_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        results.append({
            "id": exp_id,
            "run": sample_run_id or "run-none",
            "workload": (campaign_spec or {}).get("workload", {}).get("workload_name", "Metadata unavailable"),
            "arrivalMode": (campaign_spec or {}).get("workload", {}).get("arrival_mode"),
            "targetOfferedRateRps": (campaign_spec or {}).get("workload", {}).get("target_offered_rate"),
            "sloConstraints": (campaign_spec or {}).get("slo", {}).get("constraints", []),
            "model": model_name,
            "state": "Completed" if runs_count > 0 else "Pending",
            "feasibility": feasibility_status,
            "verification": verif_status,
            "updated": updated_str,
            "candidateId": selected_candidate or "",
            "baselineCandidateId": (search_res or {}).get("baseline_candidate_id"),
            "runsCount": runs_count,
            "evidenceClassification": evidence_class,
            "durationSeconds": (campaign_spec or {}).get("workload", {}).get("measurement_duration_s"),
            "verificationDurationMultiplier": (campaign_spec or {}).get("verification_policy", {}).get("duration_multiplier"),
            "requestedRateRps": (campaign_spec or {}).get("workload", {}).get("target_offered_rate"),
            "achievedRateRps": achieved_load,
            "measurementValidity": measurement_validity,
            "clientSaturation": client_saturation,
            "errorRatePct": error_rate * 100 if error_rate is not None else None,
            "exclusionsCount": exclusions_count,
            "selected_candidate_id": selected_candidate,
            "candidateEvaluationsCount": len(tested_candidates),
            "candidateBudget": (campaign_spec or {}).get("budget", {}).get("max_candidates"),
            "searchSpaceCandidateCount": search_space_count,
            "rankingObjective": search_res.get("ranking_objective") if search_res else None,
            "ranking_objective": search_res.get("ranking_objective") if search_res else None,
            "stopping_reason": search_res.get("stopping_reason") if search_res else None,
            "selection_rationale": search_res.get("selection_rationale") if search_res else None,
        })

    return results


def get_experiment_detail(experiment_id: str, artifacts_root: str = "artifacts") -> Dict[str, Any]:
    """
    Returns complete detail for a single experiment including search result and child runs.
    """
    exp_dir = _find_experiment_dir(experiment_id, artifacts_root=artifacts_root)
    if not exp_dir:
        return {"error": f"Experiment '{experiment_id}' not found"}

    search_res = None
    sr_file = exp_dir / "search_result.json"
    if sr_file.exists():
        try:
            search_res = json.loads(sr_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    verif_record = None
    verif_file = exp_dir / "verification_record.json"
    if verif_file.exists():
        try:
            verif_record = json.loads(verif_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    runs = []
    runs_dir = exp_dir / "runs"
    if runs_dir.is_dir():
        for r_dir in sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime):
            if r_dir.is_dir():
                r_status = get_run_status(r_dir.name, artifacts_root=artifacts_root)
                if r_status.get("error") != "Run not found":
                    runs.append(r_status)

    return {
        "experiment_id": experiment_id,
        "search_result": search_res,
        "verification_record": verif_record,
        "runs": runs,
        "runs_count": len(runs),
        "evidence_classification": "DEMO DATA" if "fake" in str(runs) or "offline" in experiment_id else "LIVE",
    }


def get_experiment_candidates(experiment_id: str, artifacts_root: str = "artifacts") -> List[Dict[str, Any]]:
    """
    Constructs UICandidate view models for all candidate configurations evaluated in the experiment.
    Binds empirical metrics (TTFT, ITL, throughput) and evaluator feasibility verdicts.
    Groups multiple runs per candidate to present distinct candidate profiles.
    """
    exp_dir = _find_experiment_dir(experiment_id, artifacts_root=artifacts_root)
    if not exp_dir:
        return []

    search_res = None
    sr_file = exp_dir / "search_result.json"
    if sr_file.exists():
        try:
            search_res = json.loads(sr_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    winner_id = search_res.get("selected_candidate_id") if search_res else None

    runs_dir = exp_dir / "runs"
    if not runs_dir.is_dir():
        return []

    candidates_map: Dict[str, Dict[str, Any]] = {}

    for r_dir in sorted(runs_dir.iterdir(), key=lambda p: p.name):
        if not r_dir.is_dir():
            continue

        run_id = r_dir.name
        # Skip verification runs in the candidate search list
        if "verify" in run_id:
            continue

        run_data = get_run_status(run_id, artifacts_root=artifacts_root)
        if run_data.get("error") == "Run not found":
            continue

        cid = run_data.get("candidate_id") or run_id
        applied = run_data.get("applied_config") or {}
        eff = applied.get("effective_settings", {})
        m = run_data.get("metric_set") or {}
        feas = run_data.get("feasibility_result") or {}

        ttft_p50 = m.get("ttft_ms", {}).get("p50")
        ttft_p95 = m.get("ttft_ms", {}).get("p95")
        ttft_p99 = m.get("ttft_ms", {}).get("p99")
        itl_p95 = m.get("itl_ms", {}).get("p95")
        e2e_p95 = m.get("e2e_latency_ms", {}).get("p95")
        throughput = m.get("token_throughput_tps")
        err_pct = m.get("error_rate")
        err_pct = err_pct * 100 if err_pct is not None else None

        verdict = feas.get("overall_verdict", "INCONCLUSIVE")
        is_feasible = verdict == FeasibilityVerdict.FEASIBLE.value
        is_winner = (cid == winner_id)
        tag = "WINNER" if is_winner and is_feasible else verdict
        evaluations = feas.get("constraint_evaluations", [])
        failed_reason_codes = [
            item.get("reason_code", item.get("reason"))
            for item in evaluations
            if item.get("passed") is False and item.get("reason_code", item.get("reason"))
        ]
        reason_codes = failed_reason_codes or [
            item.get("reason_code", item.get("reason"))
            for item in evaluations
            if item.get("reason_code", item.get("reason"))
        ]

        config_summary = []
        if eff.get("max_num_seqs") is not None:
            config_summary.append(f"max_seqs={eff['max_num_seqs']}")
        if eff.get("max_num_batched_tokens") is not None:
            config_summary.append(f"max_batched_tokens={eff['max_num_batched_tokens']}")
        candidate_obj = {
            "id": cid,
            "name": f"Candidate {cid[:8]}",
            "subtitle": f"Run {run_id}" + (f" · {', '.join(config_summary)}" if config_summary else ""),
            "batch": eff["max_num_batched_tokens"] // 512 if eff.get("max_num_batched_tokens") is not None else None,
            "concurrency": eff.get("max_num_seqs"),
            "kvCache": eff["kv_cache_dtype"].upper() if eff.get("kv_cache_dtype") is not None else None,
            "p50": round(ttft_p50, 1) if ttft_p50 is not None else None,
            "p95": round(ttft_p95, 1) if ttft_p95 is not None else None,
            "p99": round(ttft_p99, 1) if ttft_p99 is not None else None,
            "throughput": round(throughput, 1) if throughput is not None else None,
            "error": round(err_pct, 2) if err_pct is not None else None,
            "gpu": int(eff["gpu_memory_utilization"] * 100) if eff.get("gpu_memory_utilization") is not None else None,
            "feasible": is_feasible,
            "feasibilityVerdict": verdict,
            "evidenceValidity": feas.get("validity_status"),
            "reason": feas.get("audit_notes", "Evaluator result unavailable."),
            "reasonCodes": reason_codes,
            "tag": tag,
            "ttftP95": round(ttft_p95, 1) if ttft_p95 is not None else None,
            "itlP95": round(itl_p95, 1) if itl_p95 is not None else None,
            "e2eP95": round(e2e_p95, 1) if e2e_p95 is not None else None,
            "run_id": run_id,
            "rawConfig": applied,
            "metricSet": m,
            "feasibilityResult": feas,
        }

        # Keep primary candidate evaluation
        if cid not in candidates_map or is_winner:
            candidates_map[cid] = candidate_obj

    candidates = list(candidates_map.values())
    candidates.sort(key=lambda c: (c["tag"] != "WINNER", c["id"]))
    return candidates


def get_experiment_verification(experiment_id: str, artifacts_root: str = "artifacts") -> Dict[str, Any]:
    """
    Returns independent verification status.
    If no verification record exists, returns honest PENDING status per AGENTS.md Section 7.
    """
    exp_dir = _find_experiment_dir(experiment_id, artifacts_root=artifacts_root)
    if not exp_dir:
        return {
            "status": "pending",
            "verification_verdict": "INDEPENDENT VERIFICATION PENDING",
            "is_verified": False,
            "final_decision_notes": f"Experiment '{experiment_id}' not found.",
        }

    verif_file = exp_dir / "verification_record.json"
    if verif_file.exists():
        try:
            data = json.loads(verif_file.read_text(encoding="utf-8"))
            data["is_verified"] = data.get("verification_verdict") in ("VERIFIED", "VerificationVerdict.VERIFIED")
            data["status"] = "completed"
            return data
        except Exception as e:
            return {
                "status": "error",
                "verification_verdict": "ERROR",
                "is_verified": False,
                "error": str(e),
            }

    search_res = None
    sr_file = exp_dir / "search_result.json"
    if sr_file.exists():
        try:
            search_res = json.loads(sr_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    selected_cand = search_res.get("selected_candidate_id") if search_res else None
    original_run_id = None
    runs_dir = exp_dir / "runs"
    if selected_cand and runs_dir.is_dir():
        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            try:
                run_record = json.loads((run_dir / "run_record.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if run_record.get("candidate_id") == selected_cand and not run_record.get("is_verification_run"):
                original_run_id = run_record.get("run_id", run_dir.name)
                break

    return {
        "status": "pending",
        "verification_verdict": "INDEPENDENT VERIFICATION PENDING",
        "is_verified": False,
        "verification_id": "verif-pending",
        "experiment_id": experiment_id,
        "candidate_id": selected_cand,
        "original_run_id": original_run_id,
        "verification_run_id": None,
        "final_decision_notes": (
            "Independent verification rerun has not yet been executed for this campaign. "
            "Verification must be executed independently with a fresh run ID per AGENTS.md § 7."
        ),
        "drift_analysis": None,
    }


def list_all_reports(artifacts_root: str = "artifacts") -> List[Dict[str, Any]]:
    """
    Discovers all compiled reports across artifacts_root.
    """
    root = Path(artifacts_root)
    reports = []
    seen = set()

    for r_json in root.glob("**/report.json"):
        exp_id = r_json.parent.name
        if exp_id in seen:
            continue
        seen.add(exp_id)

        try:
            data = json.loads(r_json.read_text(encoding="utf-8"))
            mtime = r_json.stat().st_mtime
            updated_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

            reports.append({
                "experiment_id": exp_id,
                "report_id": data.get("report_id", f"rep-{exp_id}"),
                "created_at": data.get("generated_at", updated_str),
                "model": data.get("workload_spec", {}).get("model_name", "meta-llama/Meta-Llama-3-8B-Instruct"),
                "evidence_classification": "DEMO DATA" if "offline" in str(r_json) or data.get("is_simulated", True) else "LIVE",
                "selected_candidate_id": data.get("selected_candidate_id", ""),
                "has_markdown": (r_json.parent / "report.md").exists(),
                "path": str(r_json),
            })
        except Exception:
            pass

    reports.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return reports
