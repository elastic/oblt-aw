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

"""Live E2E harness for obs:repo-scheduled.

Drives schedule/dispatch → prelude → obs-aw-repo-scheduled → agent → issue
against elastic/oblt-aw using the checked-in E2E bait instruction and
``e2e-repo-scheduled-mode=true`` (no default-branch Contents mutation).
"""

from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

estc = cast(Any, importlib.import_module("estc_pr_buildkite_detective_e2e_harness"))
oracle = cast(Any, importlib.import_module("oracle_repo_scheduled_e2e"))

WORKFLOW_ID = "obs:repo-scheduled"
DEFAULT_CONFIG = Path("config/obs/e2e-repo-scheduled.json")
DEFAULT_TITLE_PREFIX = "[oblt-aw][repo-scheduled]"
DEFAULT_BAIT_PATH = ".github/ai/scheduled/e2e-repo-scheduled-bait.md"
DEFAULT_BAIT_SOURCE = Path(DEFAULT_BAIT_PATH)
DEFAULT_AUTOMATION_ID = "e2e-repo-scheduled-bait"
E2E_REPO_SCHEDULED_BAIT_MARKER = "E2E_REPO_SCHEDULED_BAIT_MARKER"


def bait_content(source: Path = DEFAULT_BAIT_SOURCE) -> str:
    """Load checked-in bait instruction used as the intentional default-branch fixture."""
    text = source.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"Bait source is empty: {source}")
    if E2E_REPO_SCHEDULED_BAIT_MARKER not in text:
        raise RuntimeError(
            f"Bait source missing correlation marker "
            f"{E2E_REPO_SCHEDULED_BAIT_MARKER!r}: {source}"
        )
    return text


def bait_markers(bait_path: str) -> tuple[str, str]:
    """Path forms used to correlate issues to the checked-in bait instruction."""
    path = (bait_path or "").strip()
    if not path:
        raise ValueError("bait_path must be non-empty")
    if ".." in Path(path).parts:
        raise ValueError(f"invalid bait_path: {bait_path!r}")
    return path, Path(path).name


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)  # noqa: UP017


def load_e2e_config(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"E2E config must be a JSON object: {path}")
    return data


def default_branch(repo: str) -> str:
    raw = estc.gh_text(
        ["api", f"repos/{repo}", "--jq", ".default_branch"],
        check=True,
    )
    branch = str(raw or "").strip()
    if not branch:
        raise RuntimeError(f"Could not resolve default branch for {repo}")
    return branch


def _contents_get_error_is_absent(stderr: str, stdout: str) -> bool:
    err = f"{stderr}\n{stdout}".lower()
    return "404" in err or "not found" in err


def _remote_file_content_b64(repo: str, *, branch: str, path: str) -> str | None:
    """Return remote Contents API base64 payload, or None when absent (404)."""
    existing = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if existing.returncode != 0:
        if _contents_get_error_is_absent(existing.stderr or "", existing.stdout or ""):
            return None
        raise RuntimeError(
            f"Failed to read {path} on {branch}: "
            f"{(existing.stderr or existing.stdout or '').strip() or f'exit {existing.returncode}'}"
        )
    payload = json.loads(existing.stdout)
    return str(payload.get("content") or "").replace("\n", "")


def remote_bait_matches(repo: str, *, branch: str, path: str, content: str) -> bool:
    """True when the remote file exists and matches ``content`` exactly."""
    remote_b64 = _remote_file_content_b64(repo, branch=branch, path=path)
    if remote_b64 is None:
        return False
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    return remote_b64 == encoded


def ensure_checked_in_bait(
    repo: str,
    *,
    branch: str,
    path: str,
    content: str,
) -> None:
    """Fail closed unless the checked-in bait is present and matches on ``branch``."""
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    remote_b64 = _remote_file_content_b64(repo, branch=branch, path=path)
    if remote_b64 is None:
        raise RuntimeError(
            f"Checked-in E2E bait missing on {branch} at {path!r}. "
            "Merge .github/ai/scheduled/e2e-repo-scheduled-bait.md before "
            "running live repo-scheduled E2E "
            "(see docs/testing/repo-scheduled-e2e.md)."
        )
    if remote_b64 != encoded:
        raise RuntimeError(
            f"Remote bait {path} on {branch} differs from the checked-in fixture; "
            "refusing to proceed. Align main with the in-repo bait file."
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


def _is_repo_scheduled_agent_leaf(
    name: str, *, automation_id: str = DEFAULT_AUTOMATION_ID
) -> bool:
    return bool(
        oracle.schedule_agent_job_name_matches(name, automation_id=automation_id)
    )


def schedule_agent_job_name(
    run_detail: dict[str, Any] | None,
    *,
    automation_id: str = DEFAULT_AUTOMATION_ID,
) -> str | None:
    """Return the matched agent leaf job name when present."""
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = str(job.get("name") or "")
        if not _is_repo_scheduled_agent_leaf(name, automation_id=automation_id):
            continue
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        return name
    return None


def repo_scheduled_agent_job_conclusion(
    run_detail: dict[str, Any] | None,
    *,
    automation_id: str = DEFAULT_AUTOMATION_ID,
) -> str | None:
    """Return leaf agent job conclusion when present (fail closed on name match)."""
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = job.get("name") or ""
        if not _is_repo_scheduled_agent_leaf(str(name), automation_id=automation_id):
            continue
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        return conclusion or None
    return None


def schedule_agent_job_executed(
    run_detail: dict[str, Any] | None,
    *,
    automation_id: str = DEFAULT_AUTOMATION_ID,
) -> bool:
    conclusion = repo_scheduled_agent_job_conclusion(
        run_detail, automation_id=automation_id
    )
    return conclusion is not None and conclusion not in ("", "skipped")


def agent_invoked(
    run_detail: dict[str, Any] | None,
    *,
    automation_id: str = DEFAULT_AUTOMATION_ID,
) -> bool:
    return schedule_agent_job_executed(run_detail, automation_id=automation_id)


def wait_for_schedule_agent_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int] | None = None,
    automation_id: str = DEFAULT_AUTOMATION_ID,
) -> dict[str, Any] | None:
    """Wait for a completed schedule-trigger run with an executed agent leaf."""
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
                if schedule_agent_job_executed(detail, automation_id=automation_id):
                    return cast(dict[str, Any], detail)
                excluded.add(run_id)
                break
        time.sleep(interval_seconds)
    return None


def dispatch_schedule_trigger(
    repo: str,
    workflow_file: str,
    *,
    e2e_repo_scheduled_mode: bool = False,
) -> None:
    args = ["workflow", "run", workflow_file, "--repo", repo]
    # Keep autodoc collateral off for this harness; enable repo-scheduled E2E mode.
    args.extend(["-f", "e2e-autodoc-mode=false"])
    if e2e_repo_scheduled_mode:
        args.extend(["-f", "e2e-repo-scheduled-mode=true"])
    estc.gh_text(args, check=True)


def _issue_body_matches_bait(body: str, bait_path: str) -> bool:
    text = body or ""
    if E2E_REPO_SCHEDULED_BAIT_MARKER not in text:
        return False
    full_path, basename = bait_markers(bait_path)
    return full_path in text or basename in text


def find_e2e_issue(
    repo: str,
    *,
    title_prefix: str,
    since: datetime,
    bait_path: str,
) -> dict[str, Any] | None:
    """Return the newest open issue correlated to this E2E bait run."""
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
                "number,title,url,createdAt,author,body",
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
        body = str(issue.get("body") or "")
        if not _issue_body_matches_bait(body, bait_path):
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
        cfg.get("schedule_trigger_workflow_file") or "e2e-trigger-obs-aw-schedule.yml"
    )
    title_prefix = str(cfg.get("issue_title_prefix") or DEFAULT_TITLE_PREFIX)
    dash_id = str(cfg.get("dashboard_workflow_id") or WORKFLOW_ID)
    automation_id = str(cfg.get("automation_id") or DEFAULT_AUTOMATION_ID)
    timeout = int(cfg.get("poll_timeout_seconds") or 3600)
    interval = int(cfg.get("poll_interval_seconds") or 20)

    trigger_raw = case.get("trigger")
    trigger: dict[str, Any] = trigger_raw if isinstance(trigger_raw, dict) else {}
    expectations_raw = case.get("expectations")
    expectations: dict[str, Any] = (
        expectations_raw if isinstance(expectations_raw, dict) else {}
    )
    case_id = str(case.get("id") or "")

    bait_path = (
        str(cfg.get("bait_path") or DEFAULT_BAIT_PATH).strip() or DEFAULT_BAIT_PATH
    )
    bait_text = bait_content()
    since = _utc_now().replace(microsecond=0)
    case_deadline = time.time() + timeout
    issue: dict[str, Any] | None = None
    run_detail: dict[str, Any] | None = None
    cleaned = False
    branch = ""
    result: dict[str, Any] | None = None

    def _seconds_left() -> int:
        return max(0, int(case_deadline - time.time()))

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
                "job_name": None,
                "url": None,
            },
            "issue": None,
            "cleanup": {
                "completed": False,
                "bait_path": bait_path,
                "bait_removed": False,
                "bait_present": False,
            },
            "bait": {
                "path": bait_path,
                "commit_sha": None,
                "created_by_this_run": False,
            },
            **extra,
        }
        write_outcome(outcome_path, outcome)
        return outcome

    schema_err = oracle.case_expectations_schema_error("live", expectations)
    if schema_err:
        return _blocked(
            f"Checked-in case expectations failed schema validation: {schema_err}"
        )
    trigger_err = oracle.case_trigger_schema_error(trigger)
    if trigger_err:
        return _blocked(
            f"Checked-in case trigger failed schema validation: {trigger_err}"
        )

    dashboard_enabled = cast(bool, expectations["dashboard_enabled"])
    expect_issue = cast(bool, expectations["expect_issue"])
    dispatch_trigger_enabled = cast(bool, trigger["dispatch_schedule_trigger"])
    seed_instruction_bait = cast(bool, trigger["seed_instruction_bait"])
    cleanup_after = cast(bool, trigger["cleanup_after"])

    bait_removed = False
    bait_present = False

    def _cleanup_payload() -> dict[str, Any]:
        return {
            "completed": cleaned,
            "bait_path": bait_path,
            "bait_removed": bait_removed,
            "bait_present": bait_present,
        }

    def _perform_cleanup() -> None:
        """Close the E2E issue; leave the checked-in bait fixture in place."""
        nonlocal cleaned, bait_removed, bait_present
        if cleaned or not cleanup_after:
            return
        if issue is not None:
            close_issue(
                repo,
                int(issue["number"]),
                comment="Closed by obs:repo-scheduled E2E harness cleanup.",
            )
        if seed_instruction_bait and branch:
            bait_present = remote_bait_matches(
                repo, branch=branch, path=bait_path, content=bait_text
            )
            if not bait_present:
                raise RuntimeError(
                    f"Checked-in bait missing or content mismatch on {branch} "
                    f"at {bait_path!r} after cleanup"
                )
            bait_removed = False
        else:
            bait_present = True
            bait_removed = False
        cleaned = True
        cleaned_issue_number: int | None = (
            int(issue["number"]) if issue is not None else None
        )
        estc.log_info(
            f"Cleanup done (issue={cleaned_issue_number}, "
            f"bait_removed={bait_removed}, bait_present={bait_present})"
        )

    dashboard_ok = False
    try:
        if dashboard_enabled and not estc.dashboard_enables_workflow(repo, dash_id):
            result = _blocked(
                f"Dashboard does not enable {dash_id!r} for {repo}",
                path_gates={"dashboard_enabled": False},
            )
            return result

        dashboard_ok = True
        branch = default_branch(repo)
        if seed_instruction_bait:
            ensure_checked_in_bait(
                repo,
                branch=branch,
                path=bait_path,
                content=bait_text,
            )
            estc.log_info(f"Verified checked-in bait {bait_path} on {repo}@{branch}")

        known_run_ids = {
            int(run["databaseId"])
            for run in list_schedule_trigger_runs(repo, workflow_file)
        }
        if dispatch_trigger_enabled:
            dispatch_schedule_trigger(
                repo,
                workflow_file,
                e2e_repo_scheduled_mode=bool(seed_instruction_bait),
            )
            estc.log_info(f"Dispatched {workflow_file} on {repo}")

        run_detail = wait_for_schedule_agent_run(
            repo,
            workflow_file,
            since=since,
            timeout_seconds=_seconds_left(),
            interval_seconds=interval,
            exclude_run_ids=known_run_ids,
            automation_id=automation_id,
        )
        if run_detail is None:
            result = _blocked(
                f"Timed out waiting for {workflow_file} repo-scheduled agent leaf",
                path_gates={"dashboard_enabled": dashboard_ok},
            )
            return result

        completed_run: dict[str, Any] = run_detail
        job_conclusion = repo_scheduled_agent_job_conclusion(
            completed_run, automation_id=automation_id
        )
        agent_ok = agent_invoked(completed_run, automation_id=automation_id)
        run_created_raw = str(completed_run.get("createdAt") or "")
        issue_since = estc._parse_gh_time(run_created_raw) if run_created_raw else since
        issue_since = max(issue_since, since)

        if expect_issue:
            issue_deadline = min(case_deadline, time.time() + 900)
            while time.time() < issue_deadline:
                issue = find_e2e_issue(
                    repo,
                    title_prefix=title_prefix,
                    since=issue_since,
                    bait_path=bait_path,
                )
                if issue is not None:
                    break
                time.sleep(interval)
            if issue is None:
                result = _blocked(
                    f"Timed out waiting for open issue with title prefix "
                    f"{title_prefix!r} and bait markers for {bait_path!r}",
                    path_gates={"dashboard_enabled": dashboard_ok},
                    schedule_trigger={
                        "run_seen": True,
                        "job_executed": schedule_agent_job_executed(
                            completed_run, automation_id=automation_id
                        ),
                        "job_conclusion": job_conclusion,
                        "job_name": schedule_agent_job_name(
                            completed_run, automation_id=automation_id
                        ),
                        "url": completed_run.get("url"),
                    },
                    agent_invoked=agent_ok,
                )
                return result

        try:
            _perform_cleanup()
        except Exception as cleanup_exc:  # noqa: BLE001 — keep issue evidence
            result = _blocked(
                str(cleanup_exc),
                path_gates={"dashboard_enabled": dashboard_ok},
                schedule_trigger={
                    "run_seen": True,
                    "job_executed": schedule_agent_job_executed(
                        completed_run, automation_id=automation_id
                    ),
                    "job_conclusion": job_conclusion,
                    "job_name": schedule_agent_job_name(
                        completed_run, automation_id=automation_id
                    ),
                    "url": completed_run.get("url"),
                    "database_id": completed_run.get("databaseId"),
                },
                agent_invoked=agent_ok,
                issue=(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "url": issue.get("url"),
                    }
                    if issue is not None
                    else None
                ),
                cleanup=_cleanup_payload(),
            )
            return result

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
                "job_executed": schedule_agent_job_executed(
                    completed_run, automation_id=automation_id
                ),
                "job_conclusion": job_conclusion,
                "job_name": schedule_agent_job_name(
                    completed_run, automation_id=automation_id
                ),
                "url": completed_run.get("url"),
                "database_id": completed_run.get("databaseId"),
            },
            "issue": (
                {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "url": issue.get("url"),
                }
                if issue is not None
                else None
            ),
            "cleanup": _cleanup_payload(),
            "bait": {
                "path": bait_path,
                "commit_sha": None,
                "created_by_this_run": False,
            },
        }
        write_outcome(outcome_path, outcome)
        result = outcome
        return result
    except Exception as exc:  # noqa: BLE001 — harness must always write outcome
        estc.log_error(str(exc))
        result = _blocked(str(exc), path_gates={"dashboard_enabled": dashboard_ok})
        return result
    finally:
        if cleanup_after and not cleaned:
            try:
                _perform_cleanup()
                if result is not None:
                    result["cleanup"] = _cleanup_payload()
                    write_outcome(outcome_path, result)
            except Exception as cleanup_exc:  # noqa: BLE001
                estc.log_error(f"cleanup failed: {cleanup_exc}")
                if result is not None and not result.get("blocked"):
                    result["blocked"] = True
                    result["block_reason"] = f"cleanup failed: {cleanup_exc}"
                    result["cleanup"] = _cleanup_payload()
                    write_outcome(outcome_path, result)
                elif result is not None:
                    result["cleanup"] = _cleanup_payload()
                    write_outcome(outcome_path, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Live E2E harness for obs:repo-scheduled"
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--outcome-path", type=Path, required=True)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/repo-scheduled"),
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
