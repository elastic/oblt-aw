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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

_E2E_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
for _path in (_E2E_DIR, _SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

estc = cast(Any, importlib.import_module("estc_pr_buildkite_detective_e2e_harness"))
e2e_gh = cast(Any, importlib.import_module("e2e_gh"))
oracle = cast(Any, importlib.import_module("oracle_repo_scheduled_e2e"))
discovery = cast(Any, importlib.import_module("repo_scheduled_instructions"))

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
                "databaseId,status,conclusion,createdAt,event,displayTitle,name,url,headSha",
            ]
        )
        or []
    )
    return cast(list[dict[str, Any]], payload)


def _run_matches_invocation(run: dict[str, Any], invocation_id: str) -> bool:
    """True when the schedule-trigger run title embeds the invocation id."""
    token = (invocation_id or "").strip()
    if not token:
        return True
    haystacks = (
        str(run.get("displayTitle") or ""),
        str(run.get("name") or ""),
    )
    return any(token in text for text in haystacks)


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


def discover_automations_job_name(
    run_detail: dict[str, Any] | None,
) -> str | None:
    """Return the matched discover-automations job name when present."""
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = str(job.get("name") or "")
        if oracle.schedule_discover_job_name_matches(name):
            return name
    return None


def discover_automations_job_conclusion(
    run_detail: dict[str, Any] | None,
) -> str | None:
    """Return discover-automations conclusion when the named job is present."""
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = str(job.get("name") or "")
        if not oracle.schedule_discover_job_name_matches(name):
            continue
        conclusion = str(job.get("conclusion") or "").strip().lower()
        return conclusion or None
    return None


def schedule_trigger_evidence(
    run_detail: dict[str, Any] | None,
    *,
    automation_id: str = DEFAULT_AUTOMATION_ID,
    include_run_conclusion: bool = False,
) -> dict[str, Any]:
    """Build schedule_trigger outcome fields from a completed (or partial) run."""
    payload: dict[str, Any] = {
        "run_seen": bool(run_detail),
        "job_executed": schedule_agent_job_executed(
            run_detail, automation_id=automation_id
        ),
        "job_conclusion": repo_scheduled_agent_job_conclusion(
            run_detail, automation_id=automation_id
        ),
        "job_name": schedule_agent_job_name(run_detail, automation_id=automation_id),
        "discover_job_name": discover_automations_job_name(run_detail),
        "discover_job_conclusion": discover_automations_job_conclusion(run_detail),
        "url": (run_detail or {}).get("url") if run_detail else None,
        "database_id": (run_detail or {}).get("databaseId") if run_detail else None,
    }
    if include_run_conclusion and run_detail is not None:
        payload["run_conclusion"] = run_detail.get("conclusion")
    return payload


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


def wait_for_correlated_schedule_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int] | None = None,
    automation_id: str = DEFAULT_AUTOMATION_ID,
    invocation_id: str = "",
    require_agent_leaf: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    """Wait for the correlated schedule-trigger run to complete.

    Returns ``(run_detail, None)`` on success.

    When ``require_agent_leaf`` is true, success also requires the bait agent
    leaf to have executed.

    When ``require_agent_leaf`` is false (empty-discovery / no-op), success
    requires the named ``discover-automations`` job to conclude ``success`` and
    the bait agent leaf to be absent — not merely any completed correlated run.

    Fail-closed: if the correlated run completes without the required evidence,
    return ``(run_detail, reason)`` immediately — do not exclude the run and
    keep polling until timeout (that hung promote E2E for ~2h).
    """
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
            if not _run_matches_invocation(run, invocation_id):
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
                        (
                            "databaseId,status,conclusion,url,jobs,createdAt,"
                            "headSha,event,displayTitle,name"
                        ),
                    ]
                )
                if detail.get("status") != "completed":
                    time.sleep(interval_seconds)
                    continue
                if not _run_matches_invocation(detail, invocation_id):
                    excluded.add(run_id)
                    break
                detail_cast = cast(dict[str, Any], detail)
                url = str(detail_cast.get("url") or "").strip() or f"run_id={run_id}"
                if require_agent_leaf:
                    if schedule_agent_job_executed(
                        detail_cast, automation_id=automation_id
                    ):
                        agent_conclusion = repo_scheduled_agent_job_conclusion(
                            detail_cast, automation_id=automation_id
                        )
                        if agent_conclusion == "success":
                            return detail_cast, None
                        reason = (
                            f"repo-scheduled agent leaf {automation_id!r} concluded "
                            f"{agent_conclusion!r} (url={url}). "
                            "Failing closed instead of waiting for an issue that "
                            "cannot appear after agent startup/run failure."
                        )
                        return detail_cast, reason
                    conclusion = (
                        str(detail_cast.get("conclusion") or "").strip() or "unknown"
                    )
                    reason = (
                        f"Schedule trigger run completed without repo-scheduled "
                        f"agent leaf {automation_id!r} "
                        f"(conclusion={conclusion!r}, url={url}). "
                        "Failing closed instead of polling until timeout."
                    )
                    return detail_cast, reason
                discover_name = discover_automations_job_name(detail_cast)
                discover_conclusion = discover_automations_job_conclusion(detail_cast)
                agent_ran = schedule_agent_job_executed(
                    detail_cast, automation_id=automation_id
                )
                if (
                    discover_name is not None
                    and discover_conclusion == "success"
                    and not agent_ran
                ):
                    return detail_cast, None
                reason = (
                    "Schedule trigger run completed without successful "
                    "discover-automations evidence for empty-discovery case "
                    f"(discover_job_name={discover_name!r}, "
                    f"discover_job_conclusion={discover_conclusion!r}, "
                    f"agent_executed={agent_ran}, url={url}). "
                    "Failing closed instead of treating any completed run as success."
                )
                return detail_cast, reason
        time.sleep(interval_seconds)
    return None, None


def wait_for_schedule_agent_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int] | None = None,
    automation_id: str = DEFAULT_AUTOMATION_ID,
    invocation_id: str = "",
) -> dict[str, Any] | None:
    """Wait for a completed schedule-trigger run with an executed agent leaf.

    Prefer ``wait_for_correlated_schedule_run`` for new call sites; this
    wrapper preserves the old return shape for unit tests.
    """
    detail, fail_reason = wait_for_correlated_schedule_run(
        repo,
        workflow_file,
        since=since,
        timeout_seconds=timeout_seconds,
        interval_seconds=interval_seconds,
        exclude_run_ids=exclude_run_ids,
        automation_id=automation_id,
        invocation_id=invocation_id,
        require_agent_leaf=True,
    )
    if fail_reason:
        return None
    return detail


def dispatch_schedule_trigger(
    repo: str,
    workflow_file: str,
    *,
    e2e_repo_scheduled_mode: bool = False,
    invocation_id: str = "",
) -> None:
    args = ["workflow", "run", workflow_file, "--repo", repo]
    # Keep autodoc collateral off for this harness; enable repo-scheduled E2E mode.
    args.extend(["-f", "e2e-autodoc-mode=false"])
    if e2e_repo_scheduled_mode:
        args.extend(["-f", "e2e-repo-scheduled-mode=true"])
    else:
        args.extend(["-f", "e2e-repo-scheduled-mode=false"])
    token = (invocation_id or "").strip()
    if token:
        args.extend(["-f", f"e2e-invocation-id={token}"])
    estc.gh_text(args, check=True)


def _issue_body_matches_bait(body: str, bait_path: str) -> bool:
    text = e2e_gh.normalize_issue_body_for_markers(body)
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
    invocation_id: str = "",
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
    token = (invocation_id or "").strip()
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
        body = e2e_gh.normalize_issue_body_for_markers(str(issue.get("body") or ""))
        if not _issue_body_matches_bait(body, bait_path):
            continue
        if token and f"E2E_INVOCATION_ID={token}" not in body and token not in body:
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
                "discover_job_name": None,
                "discover_job_conclusion": None,
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
    e2e_repo_scheduled_mode = cast(bool, trigger["e2e_repo_scheduled_mode"])
    cleanup_after = cast(bool, trigger["cleanup_after"])
    invocation_id = uuid.uuid4().hex[:12]

    bait_removed = False
    bait_present = False

    def _cleanup_payload() -> dict[str, Any]:
        return {
            "completed": cleaned,
            "bait_path": bait_path,
            "bait_removed": bait_removed,
            "bait_present": bait_present,
        }

    def _rediscover_issue(*, since_time: datetime) -> None:
        """Find a bait-correlated issue when the waiter timed out mid-flight."""
        nonlocal issue
        if issue is not None:
            return
        issue = find_e2e_issue(
            repo,
            title_prefix=title_prefix,
            since=since_time,
            bait_path=bait_path,
            invocation_id=invocation_id if e2e_repo_scheduled_mode else "",
        )

    def _perform_cleanup(*, since_time: datetime | None = None) -> None:
        """Close the E2E issue; leave the checked-in bait fixture in place."""
        nonlocal cleaned, bait_removed, bait_present
        if cleaned or not cleanup_after:
            return
        if issue is None and e2e_repo_scheduled_mode:
            _rediscover_issue(since_time=since_time or since)
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

        expect_agent_leaf = cast(bool, expectations["schedule_job_executed"])
        # Preflight: E2E mode must be able to resolve the checked-in bait without
        # a permanent root apm.yml (injection path). Fail before dispatch/wait.
        if e2e_repo_scheduled_mode:
            try:
                discovery.resolve_e2e_bait_only(
                    Path("."),
                    [],
                    schedule_profile="daily",
                    bait_id=automation_id,
                    bait_path=bait_path,
                )
            except (TypeError, ValueError, OSError) as exc:
                result = _blocked(
                    f"E2E bait preflight failed before schedule dispatch: {exc}",
                    path_gates={"dashboard_enabled": dashboard_ok},
                    invocation_id=invocation_id,
                )
                return result
            estc.log_info(
                f"E2E bait preflight ok for {bait_path!r} "
                f"(automation_id={automation_id!r})"
            )

        known_run_ids = {
            int(run["databaseId"])
            for run in list_schedule_trigger_runs(repo, workflow_file)
        }
        if dispatch_trigger_enabled:
            dispatch_schedule_trigger(
                repo,
                workflow_file,
                e2e_repo_scheduled_mode=e2e_repo_scheduled_mode,
                invocation_id=invocation_id,
            )
            estc.log_info(
                f"Dispatched {workflow_file} on {repo} "
                f"(e2e_mode={e2e_repo_scheduled_mode}, invocation_id={invocation_id})"
            )

        run_detail, wait_fail_reason = wait_for_correlated_schedule_run(
            repo,
            workflow_file,
            since=since,
            timeout_seconds=_seconds_left(),
            interval_seconds=interval,
            exclude_run_ids=known_run_ids,
            automation_id=automation_id,
            invocation_id=invocation_id,
            require_agent_leaf=expect_agent_leaf,
        )
        if wait_fail_reason is not None:
            completed_failed = run_detail or {}
            _rediscover_issue(since_time=since)
            result = _blocked(
                wait_fail_reason,
                path_gates={"dashboard_enabled": dashboard_ok},
                invocation_id=invocation_id,
                schedule_trigger=schedule_trigger_evidence(
                    completed_failed,
                    automation_id=automation_id,
                    include_run_conclusion=True,
                ),
                agent_invoked=False,
                issue=(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "url": issue.get("url"),
                    }
                    if issue is not None
                    else None
                ),
            )
            return result
        if run_detail is None:
            _rediscover_issue(since_time=since)
            timeout_msg = (
                f"Timed out waiting for {workflow_file} repo-scheduled agent leaf "
                f"(invocation_id={invocation_id})"
                if expect_agent_leaf
                else (
                    f"Timed out waiting for {workflow_file} schedule trigger "
                    f"completion (invocation_id={invocation_id})"
                )
            )
            result = _blocked(
                timeout_msg,
                path_gates={"dashboard_enabled": dashboard_ok},
                invocation_id=invocation_id,
                issue=(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "url": issue.get("url"),
                    }
                    if issue is not None
                    else None
                ),
            )
            return result

        completed_run: dict[str, Any] = run_detail
        agent_ok = agent_invoked(completed_run, automation_id=automation_id)
        run_created_raw = str(completed_run.get("createdAt") or "")
        issue_since = estc._parse_gh_time(run_created_raw) if run_created_raw else since
        issue_since = max(issue_since, since)

        if expect_issue:
            # Schedule run (including safe_outputs) already completed. Issue
            # creation is synchronous with that run — only allow a short API
            # lag window, then fail closed (do not burn ~900s after a noop).
            issue_grace_deadline = min(
                case_deadline, time.time() + max(30, interval * 3)
            )
            while time.time() < issue_grace_deadline:
                issue = find_e2e_issue(
                    repo,
                    title_prefix=title_prefix,
                    since=issue_since,
                    bait_path=bait_path,
                    invocation_id=invocation_id,
                )
                if issue is not None:
                    break
                time.sleep(interval)
            if issue is None:
                run_url = str(completed_run.get("url") or "").strip() or "(no url)"
                result = _blocked(
                    f"Schedule trigger completed with agent leaf success but no "
                    f"open issue with title prefix {title_prefix!r}, bait markers "
                    f"for {bait_path!r}, and invocation_id={invocation_id} "
                    f"(run={run_url}). Failing closed — the agent likely noop'd "
                    "or safe-outputs did not create the bait issue.",
                    path_gates={"dashboard_enabled": dashboard_ok},
                    invocation_id=invocation_id,
                    schedule_trigger=schedule_trigger_evidence(
                        completed_run, automation_id=automation_id
                    ),
                    agent_invoked=agent_ok,
                )
                return result
        else:
            # Normal wake: any new bait-marker issue is a regression (flag was false).
            stray = find_e2e_issue(
                repo,
                title_prefix=title_prefix,
                since=issue_since,
                bait_path=bait_path,
                invocation_id="",
            )
            if stray is not None:
                issue = stray
                result = _blocked(
                    "Unexpected bait-correlated issue on normal-wake "
                    f"(e2e_repo_scheduled_mode=false): {stray.get('url')}",
                    path_gates={"dashboard_enabled": dashboard_ok},
                    invocation_id=invocation_id,
                    schedule_trigger=schedule_trigger_evidence(
                        completed_run, automation_id=automation_id
                    ),
                    agent_invoked=agent_ok,
                    issue={
                        "number": stray.get("number"),
                        "title": stray.get("title"),
                        "url": stray.get("url"),
                    },
                )
                return result

        try:
            _perform_cleanup(since_time=issue_since)
        except Exception as cleanup_exc:  # noqa: BLE001 — keep issue evidence
            result = _blocked(
                str(cleanup_exc),
                path_gates={"dashboard_enabled": dashboard_ok},
                invocation_id=invocation_id,
                schedule_trigger=schedule_trigger_evidence(
                    completed_run, automation_id=automation_id
                ),
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
            "invocation_id": invocation_id,
            "path_gates": {"dashboard_enabled": dashboard_ok},
            "agent_invoked": agent_ok,
            "schedule_trigger": schedule_trigger_evidence(
                completed_run, automation_id=automation_id
            ),
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
        result = _blocked(
            str(exc),
            path_gates={"dashboard_enabled": dashboard_ok},
            invocation_id=invocation_id,
        )
        return result
    finally:
        if cleanup_after and not cleaned:
            try:
                _perform_cleanup(since_time=since)
                if result is not None:
                    result["cleanup"] = _cleanup_payload()
                    if "invocation_id" not in result:
                        result["invocation_id"] = invocation_id
                    write_outcome(outcome_path, result)
            except Exception as cleanup_exc:  # noqa: BLE001
                estc.log_error(f"cleanup failed: {cleanup_exc}")
                if result is not None and not result.get("blocked"):
                    result["blocked"] = True
                    result["block_reason"] = f"cleanup failed: {cleanup_exc}"
                    result["cleanup"] = _cleanup_payload()
                    result["invocation_id"] = invocation_id
                    write_outcome(outcome_path, result)
                elif result is not None:
                    result["cleanup"] = _cleanup_payload()
                    result["invocation_id"] = invocation_id
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
