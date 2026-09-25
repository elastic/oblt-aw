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
against elastic/oblt-aw using the checked-in intentional undocumented bait and
E2E additional-instructions (no default-branch Contents mutation).
"""

from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
import re
import secrets
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
# Fix-path selection must match the oracle (key presence, not truthiness).
oracle = cast(Any, importlib.import_module("oracle_autodoc_e2e"))

WORKFLOW_ID = "obs:autodoc"
DEFAULT_CONFIG = Path("config/obs/e2e-autodoc.json")
DEFAULT_TITLE_PREFIX = "[oblt-aw][autodoc]"
DEFAULT_FIX_PR_TITLE = "docs: Documentation analysis and improvement"
DEFAULT_BAIT_PATH = "scripts/e2e_autodoc_intentional_undocumented.py"
DEFAULT_BAIT_SOURCE = Path("scripts/e2e_autodoc_intentional_undocumented.py")
# Must appear in bait source and in correlated audit issue bodies.
E2E_AUTODOC_BAIT_MARKER = "E2E_AUTODOC_BAIT_MARKER"
E2E_AUTODOC_RUN_TOKEN_PREFIX = "E2E_AUTODOC_RUN_TOKEN="
# After the audit issue is found, wait this long for a linked fix PR before cleanup.
FIX_PR_POLL_SECONDS = 600


def new_run_token() -> str:
    """Return a per-harness-run token used in E2E instructions and issue correlation."""
    return secrets.token_hex(8)


def bait_path_for_run(run_token: str, *, base_path: str = DEFAULT_BAIT_PATH) -> str:
    """Legacy helper: unique default-branch path (no longer used by live E2E).

    Kept for unit coverage of path validation. Live runs use the fixed
    ``DEFAULT_BAIT_PATH`` plus a run token in additional-instructions.
    """
    token = (run_token or "").strip()
    if not token or any(ch in token for ch in ("/", "\\", "..")):
        raise ValueError(f"invalid run_token for bait path: {run_token!r}")
    base = Path(base_path)
    if ".." in base.parts or base.is_absolute():
        raise ValueError(f"invalid bait base_path: {base_path!r}")
    stem = base.stem or "e2e_autodoc_intentional_undocumented"
    suffix = base.suffix or ".py"
    parent = base.parent.as_posix().strip(".")
    name = f"{stem}_{token}{suffix}"
    return f"{parent}/{name}" if parent and parent != "." else name


def run_token_marker(run_token: str) -> str:
    """Exact string that must appear in E2E instructions and correlated issue bodies."""
    token = (run_token or "").strip()
    if not token:
        raise ValueError("run_token must be non-empty")
    return f"{E2E_AUTODOC_RUN_TOKEN_PREFIX}{token}"


def bait_content(source: Path = DEFAULT_BAIT_SOURCE) -> str:
    """Load checked-in bait source used as the intentional default-branch fixture."""
    text = source.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"Bait source is empty: {source}")
    if E2E_AUTODOC_BAIT_MARKER not in text:
        raise RuntimeError(
            f"Bait source missing correlation marker {E2E_AUTODOC_BAIT_MARKER!r}: {source}"
        )
    return text


def e2e_additional_instructions(*, bait_path: str, run_token: str) -> str:
    """Platform instructions that force docs-patrol to evaluate the checked-in bait."""
    path = (bait_path or "").strip()
    if not path or ".." in Path(path).parts:
        raise ValueError(f"invalid bait_path: {bait_path!r}")
    marker = run_token_marker(run_token)
    return (
        "E2E autodoc bait (mandatory): Evaluate "
        f"`{path}` as an undocumented public API even if the lookback window "
        "has no commits and even if you would otherwise skip it. Do not treat "
        "it as test-only. File an issue that cites that path and includes both "
        f"`{E2E_AUTODOC_BAIT_MARKER}` and `{marker}` in the issue body."
    )


def bait_markers(bait_path: str, *, run_token: str) -> tuple[str, ...]:
    """Path forms plus run-token marker used to correlate audit issues.

    Live E2E uses a fixed bait path; isolation comes from ``run_token`` in
    additional-instructions and the issue body.
    """
    token = (run_token or "").strip()
    if not token:
        raise ValueError("run_token must be non-empty")
    path = (bait_path or "").strip()
    if not path:
        raise ValueError("bait_path must be non-empty")
    basename = Path(path).name
    return (path, basename, run_token_marker(token))


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


def remote_bait_present(repo: str, *, branch: str, path: str) -> bool:
    """True when Contents GET finds ``path`` on ``branch``."""
    return _remote_file_content_b64(repo, branch=branch, path=path) is not None


def ensure_checked_in_bait(
    repo: str,
    *,
    branch: str,
    path: str,
    content: str,
) -> None:
    """Fail closed unless the checked-in bait is present and matches on ``branch``.

    Live E2E never creates or deletes default-branch files (org Require-a-PR).
    """
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    remote_b64 = _remote_file_content_b64(repo, branch=branch, path=path)
    if remote_b64 is None:
        raise RuntimeError(
            f"Checked-in E2E bait missing on {branch} at {path!r}. "
            "Merge scripts/e2e_autodoc_intentional_undocumented.py before "
            "running live autodoc E2E (see docs/testing/autodoc-e2e-bait.md)."
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


def _is_audit_agent_leaf(name: str) -> bool:
    """True only for the canonical nested audit leaf (caller prefixes allowed)."""
    lowered = name.lower()
    leaf = "autodoc / audit / agent"
    return lowered == leaf or lowered.endswith(f" / {leaf}")


def schedule_audit_job_name(run_detail: dict[str, Any] | None) -> str | None:
    """Return the matched audit leaf job name when present."""
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = str(job.get("name") or "")
        if not _is_audit_agent_leaf(name):
            continue
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        return name
    return None


def autodoc_audit_job_conclusion(run_detail: dict[str, Any] | None) -> str | None:
    """Return leaf audit job conclusion when present (fail closed on name match).

    Prefer leaf agent jobs under the autodoc audit path. Do not treat the
    overall schedule run conclusion or sibling autodoc agent jobs as substitutes.
    Skipped/empty conclusions are ignored so a later non-skipped leaf can win.
    """
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = job.get("name") or ""
        if not _is_audit_agent_leaf(str(name)):
            continue
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        return conclusion or None
    return None


def schedule_audit_job_executed(run_detail: dict[str, Any] | None) -> bool:
    """True when the audit agent leaf ran (any non-skipped conclusion).

    Success is a separate signal via ``job_conclusion`` / oracle
    ``schedule_job_success``. A failed audit must not look like "never ran".
    """
    conclusion = autodoc_audit_job_conclusion(run_detail)
    return conclusion is not None and conclusion not in ("", "skipped")


def audit_agent_invoked(run_detail: dict[str, Any] | None) -> bool:
    return schedule_audit_job_executed(run_detail)


def audit_agent_succeeded(run_detail: dict[str, Any] | None) -> bool:
    return autodoc_audit_job_conclusion(run_detail) == "success"


def _is_fix_agent_leaf(name: str) -> bool:
    """True only for the canonical nested fix leaf (caller prefixes allowed)."""
    lowered = name.lower()
    leaf = "autodoc / fix / agent"
    return lowered == leaf or lowered.endswith(f" / {leaf}")


def autodoc_fix_job_conclusion(run_detail: dict[str, Any] | None) -> str | None:
    """Return leaf fix/create-PR agent conclusion when present (fail closed)."""
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = job.get("name") or ""
        if not _is_fix_agent_leaf(str(name)):
            continue
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        return conclusion or None
    return None


def schedule_fix_job_executed(run_detail: dict[str, Any] | None) -> bool:
    """True when the fix/create-PR agent leaf ran (any non-skipped conclusion).

    Success is a separate signal via ``job_conclusion`` / oracle
    ``fix_job_success``. A failed fix must not satisfy negative
    ``fix_agent_invoked: false`` expectations.
    """
    conclusion = autodoc_fix_job_conclusion(run_detail)
    return conclusion is not None and conclusion not in ("", "skipped")


def fix_agent_invoked(run_detail: dict[str, Any] | None) -> bool:
    return schedule_fix_job_executed(run_detail)


def fix_agent_succeeded(run_detail: dict[str, Any] | None) -> bool:
    return autodoc_fix_job_conclusion(run_detail) == "success"


def wait_for_schedule_audit_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int] | None = None,
) -> dict[str, Any] | None:
    """Wait for a completed schedule-trigger run with an executed audit leaf."""
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
                # Completed without an executed audit leaf — keep polling others.
                excluded.add(run_id)
                break
        time.sleep(interval_seconds)
    return None


def dispatch_schedule_trigger(
    repo: str,
    workflow_file: str,
    *,
    e2e_additional_instructions: str = "",
) -> None:
    args = ["workflow", "run", workflow_file, "--repo", repo]
    instructions = (e2e_additional_instructions or "").strip()
    if instructions:
        args.extend(["-f", f"e2e-additional-instructions={instructions}"])
    estc.gh_text(args, check=True)


def _issue_body_matches_bait(body: str, bait_path: str, *, run_token: str) -> bool:
    """Require bait path (or basename) and the per-run token marker in the issue body."""
    text = body or ""
    full_path, basename, token_marker = bait_markers(bait_path, run_token=run_token)
    if token_marker not in text:
        return False
    return full_path in text or basename in text


def find_audit_issue(
    repo: str,
    *,
    title_prefix: str,
    since: datetime,
    bait_path: str,
    run_token: str,
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
        if not _issue_body_matches_bait(body, bait_path, run_token=run_token):
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


def _pr_references_issue(body: str, issue_number: int, *, repo: str) -> bool:
    """True when PR body explicitly references the audit issue in ``repo``.

    Bare ``#N`` must not match cross-repo shorthand such as ``other/repo#N``.
    """
    text = body or ""
    owner, sep, name = repo.partition("/")
    if not sep or not owner or not name or "/" in name:
        raise ValueError(f"repo must be 'owner/name', got {repo!r}")
    owner_re = re.escape(owner)
    name_re = re.escape(name)
    patterns = (
        rf"(?i)\b(?:closes|fixes|resolves)\s+#\s*{issue_number}\b",
        rf"(?i)\b(?:closes|fixes|resolves)\s+https?://github\.com/{owner_re}/{name_re}/issues/{issue_number}\b",
        rf"(?i)\b{owner_re}/{name_re}#{issue_number}\b",
        # Bare #N: disallow when preceded by owner/name path characters.
        rf"(?<![\w.-])#\s*{issue_number}\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def list_fix_prs_for_issue(repo: str, *, issue_number: int) -> list[dict[str, Any]]:
    """Open PRs whose body references the audit issue (not title/time heuristics)."""
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
                "number,title,createdAt,url,body",
            ]
        )
        or []
    )
    linked: list[dict[str, Any]] = []
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        if _pr_references_issue(str(pr.get("body") or ""), issue_number, repo=repo):
            linked.append(pr)
    return linked


def close_prs_for_issue(repo: str, *, issue_number: int) -> list[int]:
    """Close open PRs that reference ``issue_number``.

    Propagates ``gh pr close`` failures so cleanup cannot report success while a
    linked fix PR remains open.
    """
    closed: list[int] = []
    for pr in list_fix_prs_for_issue(repo, issue_number=issue_number):
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
            check=True,
        )
        closed.append(number)
    return closed


def wait_for_fix_pr_for_issue(
    repo: str,
    *,
    issue_number: int,
    timeout_seconds: int,
    interval_seconds: int,
    required_title: str | None = None,
) -> list[dict[str, Any]]:
    """Poll for fix PRs linked to the audit issue; return matches at deadline.

    When ``required_title`` is set, only PRs with that exact title count — any
    other linked PR is ignored (fail closed).
    """
    deadline = time.time() + max(0, timeout_seconds)

    def _matches(linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if required_title is None:
            return linked
        return [pr for pr in linked if str(pr.get("title") or "") == required_title]

    while time.time() < deadline:
        matched = _matches(list_fix_prs_for_issue(repo, issue_number=issue_number))
        if matched:
            return matched
        time.sleep(interval_seconds)
    return _matches(list_fix_prs_for_issue(repo, issue_number=issue_number))


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
    fix_pr_title = str(cfg.get("fix_pr_title") or DEFAULT_FIX_PR_TITLE)
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

    # Fixed checked-in bait path; per-run isolation via instructions + issue marker.
    run_token = new_run_token()
    bait_path = (
        str(cfg.get("bait_path") or DEFAULT_BAIT_PATH).strip() or DEFAULT_BAIT_PATH
    )
    bait_text = bait_content()
    e2e_instructions = e2e_additional_instructions(
        bait_path=bait_path, run_token=run_token
    )
    # Coarse clock (drop microseconds) to avoid missing runs whose GitHub
    # createdAt truncates fractional seconds earlier than the runner clock.
    since = _utc_now().replace(microsecond=0)
    case_deadline = time.time() + timeout
    issue: dict[str, Any] | None = None
    fix_pr: dict[str, Any] | None = None
    run_detail: dict[str, Any] | None = None
    cleaned = False
    closed_prs: list[int] = []
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
            "fix_agent_invoked": False,
            "schedule_trigger": {
                "run_seen": False,
                "job_executed": False,
                "job_conclusion": None,
                "job_name": None,
                "url": None,
            },
            "fix_trigger": {
                "job_executed": False,
                "job_conclusion": None,
            },
            "audit_issue": None,
            "fix_pr": None,
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
                "run_token": run_token,
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

    # Key presence (not truthiness): negative fix cases still select fix mode.
    want_fix = bool(oracle.live_case_selects_fix(expectations))
    dashboard_enabled = cast(bool, expectations["dashboard_enabled"])
    expect_audit_issue = cast(bool, expectations["expect_audit_issue"])
    dispatch_trigger_enabled = cast(bool, trigger["dispatch_schedule_trigger"])
    seed_doc_drift_bait = cast(bool, trigger["seed_doc_drift_bait"])
    cleanup_after = cast(bool, trigger["cleanup_after"])
    expect_fix_invoked = (
        cast(bool, expectations["fix_agent_invoked"]) if want_fix else False
    )
    expect_fix_pr = cast(bool, expectations["expect_fix_pr"]) if want_fix else False

    bait_removed = False
    bait_present = False

    def _cleanup_payload(*, closed_prs: list[int]) -> dict[str, Any]:
        return {
            "completed": cleaned,
            "bait_path": bait_path,
            "bait_removed": bait_removed,
            "bait_present": bait_present,
            "closed_prs": closed_prs,
        }

    def _perform_cleanup(*, wait_for_fix_before_close: bool) -> list[int]:
        """Close linked PRs/issue; leave the checked-in bait fixture in place.

        Completion requires the fixed bait path still present when
        ``seed_doc_drift_bait`` is true (no Contents delete on the default branch).
        """
        nonlocal cleaned, bait_removed, bait_present
        if cleaned or not cleanup_after:
            return []
        closed: list[int] = []
        if issue is not None:
            issue_number = int(issue["number"])
            # Audit-only success: give the caller fix job a short window to open
            # a PR before cleanup closes the issue.
            if wait_for_fix_before_close and not want_fix:
                wait_for_fix_pr_for_issue(
                    repo,
                    issue_number=issue_number,
                    timeout_seconds=min(FIX_PR_POLL_SECONDS, _seconds_left()),
                    interval_seconds=interval,
                )
            closed = close_prs_for_issue(repo, issue_number=issue_number)
            close_issue(
                repo,
                issue_number,
                comment="Closed by obs:autodoc E2E harness cleanup.",
            )
        if seed_doc_drift_bait and branch:
            bait_present = remote_bait_present(repo, branch=branch, path=bait_path)
            if not bait_present:
                raise RuntimeError(
                    f"Checked-in bait missing on {branch} at {bait_path!r} after cleanup"
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
            f"Cleanup done (issue={cleaned_issue_number}, prs={closed}, "
            f"bait_removed={bait_removed}, bait_present={bait_present})"
        )
        return closed

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
        if seed_doc_drift_bait:
            ensure_checked_in_bait(
                repo,
                branch=branch,
                path=bait_path,
                content=bait_text,
            )
            estc.log_info(f"Verified checked-in bait {bait_path} on {repo}@{branch}")

        # Snapshot existing runs before dispatch so a concurrent schedule cannot
        # be attributed as this E2E's run.
        known_run_ids = {
            int(run["databaseId"])
            for run in list_schedule_trigger_runs(repo, workflow_file)
        }
        if dispatch_trigger_enabled:
            dispatch_schedule_trigger(
                repo,
                workflow_file,
                e2e_additional_instructions=(
                    e2e_instructions if seed_doc_drift_bait else ""
                ),
            )
            estc.log_info(f"Dispatched {workflow_file} on {repo}")

        run_detail = wait_for_schedule_audit_run(
            repo,
            workflow_file,
            since=since,
            timeout_seconds=_seconds_left(),
            interval_seconds=interval,
            exclude_run_ids=known_run_ids,
        )
        if run_detail is None:
            result = _blocked(
                f"Timed out waiting for {workflow_file} autodoc audit leaf execution",
                path_gates={"dashboard_enabled": dashboard_ok},
            )
            return result

        completed_run: dict[str, Any] = run_detail
        job_conclusion = autodoc_audit_job_conclusion(completed_run)
        agent_ok = audit_agent_invoked(completed_run)
        fix_job_conclusion = autodoc_fix_job_conclusion(completed_run)
        fix_ran = schedule_fix_job_executed(completed_run)
        fix_succeeded = fix_agent_succeeded(completed_run)
        # Prefer the accepted run's createdAt so older concurrent issues cannot match.
        run_created_raw = str(completed_run.get("createdAt") or "")
        issue_since = estc._parse_gh_time(run_created_raw) if run_created_raw else since
        issue_since = max(issue_since, since)

        if expect_audit_issue:
            issue_deadline = min(case_deadline, time.time() + 900)
            while time.time() < issue_deadline:
                issue = find_audit_issue(
                    repo,
                    title_prefix=title_prefix,
                    since=issue_since,
                    bait_path=bait_path,
                    run_token=run_token,
                )
                if issue is not None:
                    break
                time.sleep(interval)
            if issue is None:
                result = _blocked(
                    f"Timed out waiting for open issue with title prefix "
                    f"{title_prefix!r} and per-run bait markers for {bait_path!r}",
                    path_gates={"dashboard_enabled": dashboard_ok},
                    schedule_trigger={
                        "run_seen": True,
                        "job_executed": schedule_audit_job_executed(completed_run),
                        "job_conclusion": job_conclusion,
                        "job_name": schedule_audit_job_name(completed_run),
                        "url": completed_run.get("url"),
                    },
                    agent_invoked=agent_ok,
                    fix_agent_invoked=fix_ran,
                    fix_trigger={
                        "job_executed": fix_ran,
                        "job_conclusion": fix_job_conclusion,
                    },
                )
                return result

        if want_fix:
            # Positive invocation/PR paths require fix success. Negative paths
            # must still snapshot unexpected PRs without that gate.
            if (expect_fix_invoked or expect_fix_pr) and not fix_succeeded:
                result = _blocked(
                    f"Autodoc fix agent did not succeed "
                    f"(conclusion={fix_job_conclusion!r})",
                    path_gates={"dashboard_enabled": dashboard_ok},
                    schedule_trigger={
                        "run_seen": True,
                        "job_executed": schedule_audit_job_executed(completed_run),
                        "job_conclusion": job_conclusion,
                        "job_name": schedule_audit_job_name(completed_run),
                        "url": completed_run.get("url"),
                    },
                    agent_invoked=agent_ok,
                    # Preserve execution evidence: a failed leaf ran.
                    fix_agent_invoked=fix_ran,
                    fix_trigger={
                        "job_executed": fix_ran,
                        "job_conclusion": fix_job_conclusion,
                    },
                    audit_issue=(
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
            if expect_fix_pr and issue is None:
                result = _blocked(
                    "Fix-path case requires an audit issue before waiting for a PR",
                    path_gates={"dashboard_enabled": dashboard_ok},
                    schedule_trigger={
                        "run_seen": True,
                        "job_executed": schedule_audit_job_executed(completed_run),
                        "job_conclusion": job_conclusion,
                        "job_name": schedule_audit_job_name(completed_run),
                        "url": completed_run.get("url"),
                    },
                    agent_invoked=agent_ok,
                    fix_agent_invoked=fix_ran,
                    fix_trigger={
                        "job_executed": fix_ran,
                        "job_conclusion": fix_job_conclusion,
                    },
                )
                return result
            # Title-filter linked PRs so expect_fix_pr:false is fail-closed
            # (oracle sees any unexpected match). Presence waits; absence
            # snapshots once — including when fix was not expected to run.
            if expect_fix_pr:
                # Narrowed above: expect_fix_pr requires a non-None issue.
                assert issue is not None
                titled = wait_for_fix_pr_for_issue(
                    repo,
                    issue_number=int(issue["number"]),
                    timeout_seconds=min(3600, _seconds_left()),
                    interval_seconds=interval,
                    required_title=fix_pr_title,
                )
                if not titled:
                    result = _blocked(
                        f"Timed out waiting for open PR linked to issue "
                        f"#{issue['number']} with title {fix_pr_title!r}",
                        path_gates={"dashboard_enabled": dashboard_ok},
                        schedule_trigger={
                            "run_seen": True,
                            "job_executed": schedule_audit_job_executed(completed_run),
                            "job_conclusion": job_conclusion,
                            "job_name": schedule_audit_job_name(completed_run),
                            "url": completed_run.get("url"),
                        },
                        agent_invoked=agent_ok,
                        fix_agent_invoked=fix_ran,
                        fix_trigger={
                            "job_executed": fix_ran,
                            "job_conclusion": fix_job_conclusion,
                        },
                        audit_issue={
                            "number": issue.get("number"),
                            "title": issue.get("title"),
                            "url": issue.get("url"),
                        },
                    )
                    return result
                fix_pr = titled[0]
            elif issue is not None:
                titled = [
                    pr
                    for pr in list_fix_prs_for_issue(
                        repo, issue_number=int(issue["number"])
                    )
                    if str(pr.get("title") or "") == fix_pr_title
                ]
                if titled:
                    fix_pr = titled[0]

        try:
            closed_prs = _perform_cleanup(wait_for_fix_before_close=True)
        except Exception as cleanup_exc:  # noqa: BLE001 — keep audit/PR evidence
            result = _blocked(
                str(cleanup_exc),
                path_gates={"dashboard_enabled": dashboard_ok},
                schedule_trigger={
                    "run_seen": True,
                    "job_executed": schedule_audit_job_executed(completed_run),
                    "job_conclusion": job_conclusion,
                    "job_name": schedule_audit_job_name(completed_run),
                    "url": completed_run.get("url"),
                    "database_id": completed_run.get("databaseId"),
                },
                agent_invoked=agent_ok,
                fix_agent_invoked=fix_agent_invoked(completed_run),
                fix_trigger={
                    "job_executed": schedule_fix_job_executed(completed_run),
                    "job_conclusion": autodoc_fix_job_conclusion(completed_run),
                },
                audit_issue=(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "url": issue.get("url"),
                    }
                    if issue is not None
                    else None
                ),
                fix_pr=(
                    {
                        "number": fix_pr.get("number"),
                        "title": fix_pr.get("title"),
                        "url": fix_pr.get("url"),
                    }
                    if fix_pr is not None
                    else None
                ),
                cleanup=_cleanup_payload(closed_prs=[]),
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
            "fix_agent_invoked": fix_agent_invoked(completed_run),
            "schedule_trigger": {
                "run_seen": True,
                "job_executed": schedule_audit_job_executed(completed_run),
                "job_conclusion": job_conclusion,
                "job_name": schedule_audit_job_name(completed_run),
                "url": completed_run.get("url"),
                "database_id": completed_run.get("databaseId"),
            },
            "fix_trigger": {
                "job_executed": schedule_fix_job_executed(completed_run),
                "job_conclusion": autodoc_fix_job_conclusion(completed_run),
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
            "fix_pr": (
                {
                    "number": fix_pr.get("number"),
                    "title": fix_pr.get("title"),
                    "url": fix_pr.get("url"),
                }
                if fix_pr is not None
                else None
            ),
            "cleanup": _cleanup_payload(closed_prs=closed_prs),
            "bait": {
                "path": bait_path,
                "commit_sha": None,
                "created_by_this_run": False,
                "run_token": run_token,
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
        # Every post-seed exit (blocked, exception, or missed success cleanup)
        # must remove bait / close issue+PRs when cleanup_after is set.
        if cleanup_after and not cleaned:
            try:
                closed = _perform_cleanup(wait_for_fix_before_close=False)
                if result is not None:
                    result["cleanup"] = _cleanup_payload(closed_prs=closed)
                    write_outcome(outcome_path, result)
            except Exception as cleanup_exc:  # noqa: BLE001
                estc.log_error(f"cleanup failed: {cleanup_exc}")
                if result is not None and not result.get("blocked"):
                    result["blocked"] = True
                    result["block_reason"] = f"cleanup failed: {cleanup_exc}"
                    result["cleanup"] = _cleanup_payload(closed_prs=[])
                    write_outcome(outcome_path, result)
                elif result is not None:
                    result["cleanup"] = _cleanup_payload(closed_prs=[])
                    write_outcome(outcome_path, result)


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
