"""
Purpose: Compiles immutable ReportArtifact and renders human-readable Markdown reports.
Owner: Rajdeep (Architecture & Implementation)
Authority: Aligned with AGENTS.md Section 1, 3, 5, 7, 8 and DEC-0014
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import FeasibilityVerdict, VerificationState
from slokern.contracts.report import BaselineSummary, ReportArtifact, SearchSummary
from slokern.contracts.search import SearchResult
from slokern.contracts.spec import ExperimentSpec
from slokern.contracts.verification import VerificationRecord
from slokern.common.security import sanitize_report_artifact, sanitize_credentials, assert_no_unredacted_credentials


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_report_artifact(
    experiment_spec: ExperimentSpec,
    baseline_summary: BaselineSummary,
    search_summary: SearchSummary,
    environment_fingerprint: Dict[str, Any],
    limitations_disclosed: Dict[str, Any],
    cost_accounting_basis: str,
    artifact_paths: Dict[str, str],
    selected_candidate: Optional[CandidateConfig] = None,
    verification_record: Optional[VerificationRecord] = None,
    report_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> ReportArtifact:
    """
    Compiles immutable ReportArtifact adhering strictly to the contract schema.
    """
    resolved_id = report_id or f"rep-{uuid.uuid4().hex[:8]}"
    resolved_created_at = created_at or _now_iso()

    return ReportArtifact(
        report_id=resolved_id,
        created_at=resolved_created_at,
        experiment_spec=experiment_spec,
        environment_fingerprint=environment_fingerprint,
        baseline_summary=baseline_summary,
        search_summary=search_summary,
        selected_candidate=selected_candidate,
        verification_record=verification_record,
        limitations_disclosed=limitations_disclosed,
        cost_accounting_basis=cost_accounting_basis,
        artifact_paths=artifact_paths,
    )


def render_markdown_report(report: ReportArtifact) -> str:
    """
    Renders an auditable, evidence-backed Markdown report from a ReportArtifact.
    Discloses verification status, baseline comparison, hardware environment,
    limitations, and pricing basis.
    """
    lines: List[str] = []

    lines.append(f"# SLOKern Optimization & Verification Report")
    lines.append("")
    lines.append(f"> **Report ID:** `{report.report_id}`  ")
    lines.append(f"> **Generated At:** `{report.created_at}`  ")
    lines.append(f"> **Experiment ID:** `{report.experiment_spec.experiment_id}`  ")
    lines.append("")

    # Status Callout
    verif = report.verification_record
    if verif:
        if verif.verification_verdict == VerificationState.VERIFIED:
            lines.append("> [!NOTE]")
            lines.append("> **INDEPENDENT VERIFICATION PASSED**: The selected configuration was rerun independently and confirmed to satisfy all declared hard SLO constraints.")
        elif verif.verification_verdict == VerificationState.VERIFICATION_FAILED:
            lines.append("> [!WARNING]")
            lines.append("> **VERIFICATION FAILED**: The selected configuration violated declared hard SLO constraints or drifted across thresholds during independent rerun.")
        else:
            lines.append("> [!CAUTION]")
            lines.append(f"> **VERIFICATION INCONCLUSIVE**: The verification rerun ended with status `{verif.verification_verdict.value}`.")
    else:
        lines.append("> [!IMPORTANT]")
        lines.append("> **SEARCH COMPLETE (UNVERIFIED)**: Optimization completed without an independent verification rerun.")
    lines.append("")

    # Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    if report.selected_candidate:
        lines.append(f"- **Selected Candidate:** `{report.selected_candidate.candidate_id}`")
        lines.append(f"- **Model:** `{report.selected_candidate.model_name}`")
        lines.append(f"- **Runtime Engine:** `{report.selected_candidate.runtime_name}`")
        applied_str = json.dumps(report.selected_candidate.effective_settings)
        lines.append(f"- **Applied Settings:** `{applied_str}`")
    else:
        lines.append("- **Selected Candidate:** None (No tested candidate satisfied all hard SLO constraints).")
    lines.append("")

    # Baseline Summary
    lines.append("## 2. Baseline Configuration")
    lines.append("")
    base = report.baseline_summary
    lines.append(f"- **Baseline ID:** `{base.baseline_candidate_id}`")
    lines.append(f"- **Verdict:** `{base.verdict.value}`")
    if base.metrics:
        lines.append("- **Key Metrics:**")
        for k, v in base.metrics.items():
            lines.append(f"  - `{k}`: {v}")
    lines.append("")

    # Search Exploration Summary
    lines.append("## 3. Search Space & Candidate Rankings")
    lines.append("")
    lines.append(f"- **Total Tested Candidates:** {len(report.search_summary.tested_candidates)}")
    if report.search_summary.rankings:
        lines.append("- **Rankings (Top to Bottom):**")
        for idx, r in enumerate(report.search_summary.rankings, start=1):
            lines.append(f"  {idx}. `{r}`")
    if report.search_summary.rejected_options:
        lines.append("- **Rejected / Infeasible Options:**")
        for rej in report.search_summary.rejected_options:
            lines.append(f"  - `{rej}`")
    lines.append("")

    # Independent Verification Audit
    if verif:
        lines.append("## 4. Independent Verification Audit")
        lines.append("")
        lines.append(f"- **Verification Session ID:** `{verif.verification_id}`")
        lines.append(f"- **Original Run ID:** `{verif.original_run_id}`")
        lines.append(f"- **Fresh Verification Run ID:** `{verif.verification_run_id}`")
        lines.append(f"- **Final Verdict:** `{verif.verification_verdict.value}`")
        if verif.final_decision_notes:
            lines.append(f"- **Decision Notes:** {verif.final_decision_notes}")
        if verif.drift_analysis:
            lines.append(f"- **SLO Threshold Drift Detected:** `{verif.drift_analysis.slo_drift_detected}`")
            lines.append("- **Metric Deltas (% difference):**")
            for m_key, delta_val in verif.drift_analysis.metric_deltas.items():
                lines.append(f"  - `{m_key}`: `{delta_val:+g}%`")
        lines.append("")

    # Limitations Disclosed
    lines.append("## 5. Disclosed Limitations & Environment Fingerprint")
    lines.append("")
    lines.append("### Environment Metadata")
    lines.append("```json")
    lines.append(json.dumps(report.environment_fingerprint, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("### Limitations & Search Space Bounds")
    lines.append("```json")
    lines.append(json.dumps(report.limitations_disclosed, indent=2))
    lines.append("```")
    lines.append("")

    # Cost Accounting Basis
    lines.append("## 6. Cost Accounting Basis")
    lines.append("")
    lines.append(f"{report.cost_accounting_basis}")
    lines.append("")

    # Physical Artifact References
    lines.append("## 7. Artifact References")
    lines.append("")
    for name, path in report.artifact_paths.items():
        lines.append(f"- **{name}:** `{path}`")
    lines.append("")

    return "\n".join(lines)


def write_report_artifacts(
    report: ReportArtifact,
    output_dir: Union[str, Path],
) -> Tuple[Path, Path]:
    """
    Persists report.json and report.md atomically into the target directory.
    Returns (json_path, md_path).
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    json_path = out_path / "report.json"
    md_path = out_path / "report.md"

    # Write report.json atomically
    temp_json = out_path / f"report.json.tmp.{uuid.uuid4().hex[:6]}"
    sanitized_report = sanitize_report_artifact(report)
    temp_json.write_text(sanitized_report.model_dump_json(indent=2), encoding="utf-8")
    assert_no_unredacted_credentials(temp_json.read_text(encoding="utf-8"))
    temp_json.replace(json_path)

    # Write report.md atomically
    sanitized_report = sanitize_report_artifact(report)
    md_content = render_markdown_report(sanitized_report)
    md_content = sanitize_credentials(md_content)
    assert_no_unredacted_credentials(md_content)
    temp_md = out_path / f"report.md.tmp.{uuid.uuid4().hex[:6]}"
    temp_md.write_text(md_content, encoding="utf-8")
    temp_md.replace(md_path)

    return json_path, md_path
