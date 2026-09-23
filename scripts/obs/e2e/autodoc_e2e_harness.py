#!/usr/bin/env python3
# Copyright 2026-2027 Elasticsearch B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Live E2E harness for obs:autodoc audit (docs-patrol).

Drives schedule/dispatch → prelude → obs-aw-autodoc audit → issue creation
against elastic/oblt-aw by seeding intentional undocumented public API bait.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

# Reuse shared gh / Contents / dashboard helpers from the ESTC harness.
# importlib keeps mypy from type-checking that module as a follow-import
# (its get_enabled_workflows ignore is unused when other scripts/ files are checked).
estc = cast(Any, importlib.import_module("estc_pr_buildkite_detective_e2e_harness"))

WORKFLOW_ID = "obs:autodoc"
DEFAULT_CONFIG = Path("config/obs/e2e-autodoc.json")
DEFAULT_TITLE_PREFIX = "[oblt-aw][autodoc]"
DEFAULT_BAIT_PATH = "scripts/e2e_autodoc_intentional_undocumented.py"
DEFAULT_BAIT_SOURCE = Path(
    "testdata/agentic/autodoc/bait/e2e_autodoc_intentional_undocumented.py"
)


def bait_content(source: Path = DEFAULT_BAIT_SOURCE) -> str:
    """Load checked-in bait source used for intentional default-branch drift."""
    text = source.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"Bait source is empty: {source}")
    return text


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_e2e_config(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"E2E config must be a JSON object: {path}")
    return data


def default_branch(repo: str) -> str:
    payload = estc.gh_json(["api", f"repos/{repo}", "--jq", ".default_branch"])
    branch = str(payload or "").strip()
    if not branch:
        raise RuntimeError(f"Could not resolve default branch for {repo}")
    return branch


def delete_branch_file(
    repo: str,
    *,
    branch: str,
    path: str,
    message: str,
) -> None:
    """Delete a file on ``branch`` when present (Contents API)."""
    existing = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if existing.returncode != 0:
        return
    payload = json.loads(existing.stdout)
    sha = str(payload.get("sha") or "").strip()
    if not sha:
        raise RuntimeError(f"Contents GET for {path} missing sha; cannot delete")
    estc.gh_json(
        [
            "api",
            "--method",
            "DELETE",
            f"repos/{repo}/contents/{path}",
            "-f",
            f"message={message}",
            "-f",
            f"sha={sha}",
            "-f",
            f"branch={branch}",
        ]
    )


def list_schedule_trigger_runs(
    repo: str, workflow_file: str, *, limit: int = 30
) -> list[dict[str, Any]]:
    payload = (
        estc.gh_json(
            [
                "run",
                "list",
                "--repo",
                repo,
                "--workflow",
                workflow_file,
                "--limit",
                str(limit),
                "--json",
                "databaseId,status,conclusion,createdAt,event,displayTitle,url,headSha",
            ]
        )
        or []
    )
    return cast(list[dict[str, Any]], payload)


def autodoc_audit_job_conclusion(run_detail: dict[str, Any] | None) -> str | None:
    """Return leave audit job conclusion when present (fail closed on name match).

    Prefer leaf agent / lock jobs under the autodoc audit path. Do not treat the
    overall schedule run conclusion as a substitute.
    """
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        conclusion = (job.get("conclusion") or "").lower()
        # Nested: autodoc / audit / agent (or safe_outputs after agent).
        if (
            "autodoc" in name
            and ("/ audit" in name or name.endswith("audit"))
            and ("/ agent" in name or name.endswith(" / agent") or name == "agent")
        ):
            return conclusion or None
        if "gh-aw-docs-patrol" in name and (
            "/ agent" in name or name.endswith(" / agent") or name == "agent"
        ):
            return conclusion or None
    # Fallback: any non-skipped agent job under autodoc when leaf naming differs.
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        if "autodoc" in name and (
            name.endswith(" / agent") or "/ agent" in name or name == "agent"
        ):
            return conclusion or None
    return None


def schedule_audit_job_executed(run_detail: dict[str, Any] | None) -> bool:
    return autodoc_audit_job_conclusion(run_detail) == "success"


def audit_agent_invoked(run_detail: dict[str, Any] | None) -> bool:
    return schedule_audit_job_executed(run_detail)


def wait_for_schedule_audit_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int] | None = None,
) -> dict[str, Any] | None:
    """Wait for a completed schedule-trigger run with a successful autodoc audit agent."""
    excluded = set(exclude_run_ids or ())
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for run in list_schedule_trigger_runs(repo, workflow_file):
            run_id = int(run["databaseId"])
            if run_id in excluded:
                continue
            created = estc._parse_gh_time(run["createdAt"])
            if created < since:
                continue
            event = (run.get("event") or "").lower()
            if event not in ("schedule", "workflow_dispatch"):
                continue
            while time.time() < deadline:
                detail = estc.gh_json(
                    [
                        "run",
                        "view",
                        str(run_id),
                        "--repo",
                        repo,
                        "--json",
                        "databaseId,status,conclusion,url,jobs,createdAt,headSha,event",
                    ]
                )
                if detail.get("status") != "completed":
                    time.sleep(interval_seconds)
                    continue
                if schedule_audit_job_executed(detail):
                    return cast(dict[str, Any], detail)
                # Completed without audit agent success — keep polling others.
                excluded.add(run_id)
                break
        time.sleep(interval_seconds)
    return None


def dispatch_schedule_trigger(repo: str, workflow_file: str) -> None:
    estc.gh_text(
        ["workflow", "run", workflow_file, "--repo", repo],
        check=True,
    )


def find_audit_issue(
    repo: str,
    *,
    title_prefix: str,
    since: datetime,
) -> dict[str, Any] | None:
    """Return the newest open issue whose title starts with ``title_prefix``."""
    issues = (
        estc.gh_json(
            [
                "issue",
                "list",
                "--repo",
                repo,
                "--state",
                "open",
                "--limit",
                "50",
                "--json",
                "number,title,url,createdAt,author",
            ]
        )
        or []
    )
    matches: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        title = str(issue.get("title") or "")
        if not title.startswith(title_prefix):
            continue
        created_raw = str(issue.get("createdAt") or "")
        if not created_raw:
            continue
        created = estc._parse_gh_time(created_raw)
        if created < since:
            continue
        matches.append(issue)
    if not matches:
        return None
    matches.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
    return matches[0]


def close_issue(repo: str, number: int, *, comment: str) -> None:
    estc.gh_text(
        [
            "issue",
            "close",
            str(number),
            "--repo",
            repo,
            "--comment",
            comment,
        ],
        check=True,
    )


def close_autodoc_fix_prs(repo: str, *, since: datetime) -> list[int]:
    """Close open autodoc fix PRs created after ``since`` (best-effort cleanup)."""
    prs = (
        estc.gh_json(
            [
                "pr",
                "list",
                "--repo",
                repo,
                "--state",
                "open",
                "--limit",
                "30",
                "--json",
                "number,title,createdAt,url",
            ]
        )
        or []
    )
    closed: list[int] = []
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        title = str(pr.get("title") or "")
        if (
            "Documentation analysis and improvement" not in title
            and not title.startswith("docs:")
        ):
            continue
        created_raw = str(pr.get("createdAt") or "")
        if not created_raw:
            continue
        if estc._parse_gh_time(created_raw) < since:
            continue
        number = int(pr["number"])
        estc.gh_text(
            [
                "pr",
                "close",
                str(number),
                "--repo",
                repo,
                "--comment",
                "Closed by obs:autodoc E2E harness cleanup.",
            ],
            check=False,
        )
        closed.append(number)
    return closed


def write_outcome(path: Path, outcome: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_live_case(
    *,
    case: dict[str, Any],
    cfg: dict[str, Any],
    outcome_path: Path,
    run_url: str,
) -> dict[str, Any]:
    repo = str(cfg.get("consumer_repo") or "elastic/oblt-aw")
    workflow_file = str(
        cfg.get("schedule_trigger_workflow_file") or "trigger-obs-aw-schedule.yml"
    )
    title_prefix = str(cfg.get("issue_title_prefix") or DEFAULT_TITLE_PREFIX)
    bait_path = str(cfg.get("bait_path") or DEFAULT_BAIT_PATH)
    dash_id = str(cfg.get("dashboard_workflow_id") or WORKFLOW_ID)
    timeout = int(cfg.get("poll_timeout_seconds") or 3600)
    interval = int(cfg.get("poll_interval_seconds") or 20)

    trigger_raw = case.get("trigger")
    trigger: dict[str, Any] = trigger_raw if isinstance(trigger_raw, dict) else {}
    expectations_raw = case.get("expectations")
    expectations: dict[str, Any] = (
        expectations_raw if isinstance(expectations_raw, dict) else {}
    )
    case_id = str(case.get("id") or "")

    since = _utc_now()
    bait_sha: str | None = None
    issue: dict[str, Any] | None = None
    run_detail: dict[str, Any] | None = None
    cleaned = False
    branch = ""

    def _blocked(reason: str, **extra: Any) -> dict[str, Any]:
        outcome = {
            "workflow_id": WORKFLOW_ID,
            "case_id": case_id,
            "layer": "e2e",
            "mode": "live",
            "blocked": True,
            "block_reason": reason,
            "run_url": run_url,
            "path_gates": {"dashboard_enabled": False},
            "agent_invoked": False,
            "schedule_trigger": {
                "run_seen": False,
                "job_executed": False,
                "job_conclusion": None,
                "url": None,
            },
            "audit_issue": None,
            **extra,
        }
        write_outcome(outcome_path, outcome)
        return outcome

    try:
        if expectations.get(
            "dashboard_enabled"
        ) and not estc.dashboard_enables_workflow(repo, dash_id):
            return _blocked(
                f"Dashboard does not enable {dash_id!r} for {repo}",
                path_gates={"dashboard_enabled": False},
            )

        dashboard_ok = True
        branch = default_branch(repo)
        if trigger.get("seed_doc_drift_bait"):
            bait_sha = estc.put_branch_file(
                repo,
                branch=branch,
                path=bait_path,
                content=bait_content(),
                message="chore(e2e): seed autodoc intentional undocumented bait",
            )
            estc.log_info(
                f"Seeded bait {bait_path} on {repo}@{branch}"
                + (f" (commit {bait_sha[:12]})" if bait_sha else " (already present)")
            )
        if trigger.get("dispatch_schedule_trigger"):
            dispatch_schedule_trigger(repo, workflow_file)
            estc.log_info(f"Dispatched {workflow_file} on {repo}")

        run_detail = wait_for_schedule_audit_run(
            repo,
            workflow_file,
            since=since,
            timeout_seconds=timeout,
            interval_seconds=interval,
        )
        if run_detail is None:
            return _blocked(
                f"Timed out waiting for {workflow_file} autodoc audit agent success",
                path_gates={"dashboard_enabled": dashboard_ok},
            )

        completed_run: dict[str, Any] = run_detail
        job_conclusion = autodoc_audit_job_conclusion(completed_run)
        agent_ok = audit_agent_invoked(completed_run)

        if expectations.get("expect_audit_issue"):
            deadline = time.time() + min(timeout, 900)
            while time.time() < deadline:
                issue = find_audit_issue(repo, title_prefix=title_prefix, since=since)
                if issue is not None:
                    break
                time.sleep(interval)
            if issue is None:
                return _blocked(
                    f"Timed out waiting for open issue with title prefix {title_prefix!r}",
                    path_gates={"dashboard_enabled": dashboard_ok},
                    schedule_trigger={
                        "run_seen": True,
                        "job_executed": schedule_audit_job_executed(completed_run),
                        "job_conclusion": job_conclusion,
                        "url": completed_run.get("url"),
                    },
                    agent_invoked=agent_ok,
                )

        if trigger.get("cleanup_after"):
            if issue is not None:
                close_issue(
                    repo,
                    int(issue["number"]),
                    comment="Closed by obs:autodoc E2E harness cleanup.",
                )
            closed_prs = close_autodoc_fix_prs(repo, since=since)
            delete_branch_file(
                repo,
                branch=branch,
                path=bait_path,
                message="chore(e2e): remove autodoc intentional undocumented bait",
            )
            cleaned = True
            issue_number = issue.get("number") if issue is not None else None
            estc.log_info(
                f"Cleanup done (issue={issue_number}, prs={closed_prs}, bait removed)"
            )

        outcome = {
            "workflow_id": WORKFLOW_ID,
            "case_id": case_id,
            "layer": "e2e",
            "mode": "live",
            "blocked": False,
            "run_url": run_url,
            "path_gates": {"dashboard_enabled": dashboard_ok},
            "agent_invoked": agent_ok,
            "schedule_trigger": {
                "run_seen": True,
                "job_executed": schedule_audit_job_executed(completed_run),
                "job_conclusion": job_conclusion,
                "url": completed_run.get("url"),
            },
            "audit_issue": (
                {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "url": issue.get("url"),
                }
                if issue is not None
                else None
            ),
            "cleanup": {"completed": cleaned, "bait_path": bait_path},
            "bait": {"path": bait_path, "commit_sha": bait_sha},
        }
        write_outcome(outcome_path, outcome)
        return outcome
    except Exception as exc:  # noqa: BLE001 — harness must always write outcome
        estc.log_error(str(exc))
        # Best-effort bait cleanup on failure.
        try:
            if trigger.get("seed_doc_drift_bait") and not cleaned:
                delete_branch_file(
                    repo,
                    branch=branch,
                    path=bait_path,
                    message="chore(e2e): remove autodoc bait after harness error",
                )
        except Exception as cleanup_exc:  # noqa: BLE001
            estc.log_error(f"bait cleanup failed: {cleanup_exc}")
        return _blocked(str(exc), path_gates={"dashboard_enabled": False})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live E2E harness for obs:autodoc")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--outcome-path", type=Path, required=True)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/autodoc"),
    )
    args = parser.parse_args(argv)

    cfg = load_e2e_config(args.config)
    case_path = args.testdata_root / "cases" / args.case_id / "case.json"
    if not case_path.is_file():
        raise SystemExit(f"Missing case file: {case_path}")
    case = _load_json(case_path)
    if not isinstance(case, dict):
        raise SystemExit(f"Case must be a JSON object: {case_path}")
    estc.require_case_mode(case, "live", case_id=args.case_id)

    outcome = run_live_case(
        case=case,
        cfg=cfg,
        outcome_path=args.outcome_path,
        run_url=args.run_url or os.environ.get("RUN_URL", ""),
    )
    if outcome.get("blocked"):
        estc.log_error(str(outcome.get("block_reason") or "blocked"))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
