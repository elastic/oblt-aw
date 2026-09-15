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

"""Live E2E harness for obs:estc-pr-buildkite-detective.

Drives the real status → trigger → prelude → wrapper → lock → agent path
against elastic/oblt-aw (production consumer for this slice).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

WORKFLOW_ID = "obs:estc-pr-buildkite-detective"
DEFAULT_CONFIG = Path("config/obs/e2e-estc-pr-buildkite-detective.json")
FAIL_STATES = ("failed", "timed_out")
MARKER_PATH = "testdata/agentic/estc-pr-buildkite-detective/e2e-fixture-pr.md"
MARKER_BODY = (
    "# E2E fixture PR\n\n"
    "Kept open for live status→agent E2E of "
    "`obs:estc-pr-buildkite-detective`. Do not merge.\n"
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_gh_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def gh_json(args: list[str], *, check: bool = True) -> Any:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    if not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)


def flatten_slurped_pages(payload: Any) -> list[Any]:
    """Flatten ``gh api --paginate --slurp`` output into a single list.

    ``--slurp`` wraps each page (itself a JSON array) in an outer array.
    """
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise TypeError(
            f"expected list from paginated gh api, got {type(payload).__name__}"
        )
    if not payload:
        return []
    if all(isinstance(page, list) for page in payload):
        flat: list[Any] = []
        for page in payload:
            flat.extend(page)
        return flat
    # Single-page response may already be a flat list of objects.
    return payload


def require_case_mode(case: dict[str, Any], mode: str, *, case_id: str) -> None:
    """Fail closed when the checked-in case mode does not match the harness mode."""
    declared = str(case.get("mode") or "").strip()
    if not declared:
        raise RuntimeError(
            f"Case {case_id!r} is missing required field case.json.mode "
            f"(expected {mode!r})"
        )
    if declared != mode:
        raise RuntimeError(
            f"Case {case_id!r} declares mode={declared!r} but harness was "
            f"invoked with mode={mode!r}"
        )


def infer_status_publisher(payload: dict[str, Any] | None, *, fallback: str) -> str:
    """Classify status publisher from GitHub status ``creator.login`` when present."""
    if not isinstance(payload, dict):
        return fallback
    creator = payload.get("creator")
    if isinstance(creator, dict):
        login = str(creator.get("login") or "").lower()
        if "buildkite" in login:
            return "buildkite"
        if login:
            return "harness" if fallback == "harness" else "other"
    return fallback


def publisher_for_created_build_status(payload: dict[str, Any] | None) -> str:
    """Created-build path: missing ``creator.login`` must not default to Buildkite."""
    return infer_status_publisher(payload, fallback="other")


def gh_text(args: list[str], *, check: bool = True) -> str:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout


def load_e2e_config(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"E2E config must be a JSON object: {path}")
    return data


def dashboard_enables_workflow(repo: str, workflow_id: str) -> bool:
    from get_enabled_workflows import parse_enabled_ids_from_body

    issues = gh_json(
        [
            "api",
            f"repos/{repo}/issues?labels=oblt-aw%2Fdashboard&state=open",
            "--jq",
            ".",
        ]
    )
    if not issues:
        return False
    body = issues[0].get("body") or ""
    enabled = json.loads(parse_enabled_ids_from_body(body))
    return workflow_id in enabled


def _pr_head_repo(pr: dict[str, Any]) -> str:
    """Return owner/name for the PR head repository, if present."""
    head_repo = pr.get("headRepository")
    if isinstance(head_repo, dict):
        name_with_owner = head_repo.get("nameWithOwner")
        if isinstance(name_with_owner, str) and name_with_owner:
            return name_with_owner
    return ""


def _same_repo_prs(prs: list[Any], repo: str) -> list[dict[str, Any]]:
    """Keep only PRs whose head lives in ``repo`` (exclude forks)."""
    same: list[dict[str, Any]] = []
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        head = _pr_head_repo(pr)
        if head and head != repo:
            continue
        if not head:
            # Defensive: require explicit head repo metadata.
            continue
        same.append(pr)
    return same


def find_open_e2e_pr(
    repo: str,
    label: str,
    *,
    branch: str | None = None,
    strict_branch: bool = True,
) -> dict[str, Any] | None:
    prs = gh_json(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--label",
            label,
            "--json",
            "number,url,headRefName,headRefOid,title,headRepository,labels",
            "--limit",
            "20",
        ]
    )
    if not prs:
        return None
    same_repo = _same_repo_prs(prs if isinstance(prs, list) else [], repo)
    if not same_repo:
        if branch and strict_branch and prs:
            raise RuntimeError(
                f"Open PR(s) with label {label!r} exist, but none are same-repo "
                f"heads in {repo!r}. Refusing to target a fork fixture PR."
            )
        return None
    if branch:
        matched = [pr for pr in same_repo if pr.get("headRefName") == branch]
        if not matched:
            if strict_branch:
                raise RuntimeError(
                    f"Open PR(s) with label {label!r} exist, but none use branch "
                    f"{branch!r} on {repo!r}. Refusing to target an unrelated "
                    "fixture PR."
                )
            return None
        return matched[0]
    return same_repo[0]


def _ensure_label(repo: str, label: str) -> None:
    """Create the label if missing; fail closed on unexpected errors."""
    proc = subprocess.run(
        [
            "gh",
            "label",
            "create",
            label,
            "--repo",
            repo,
            "--description",
            "Long-lived PR for ESTC detective E2E",
            "--color",
            "0E8A16",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return
    combined = f"{proc.stderr or ''}{proc.stdout or ''}".lower()
    if "already exists" in combined:
        return
    raise RuntimeError(
        f"Failed to ensure label {label!r} on {repo}: "
        f"{(proc.stderr or proc.stdout or '').strip() or f'exit {proc.returncode}'}"
    )


def _pr_has_label(pr: dict[str, Any], label: str) -> bool:
    labels = pr.get("labels") or []
    if not isinstance(labels, list):
        return False
    for item in labels:
        if isinstance(item, dict) and item.get("name") == label:
            return True
        if isinstance(item, str) and item == label:
            return True
    return False


def _require_pr_label(repo: str, pr_number: int, label: str) -> dict[str, Any]:
    """Re-fetch the PR and fail if the required label is missing."""
    pr = gh_json(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "number,url,headRefName,headRefOid,title,headRepository,labels",
        ]
    )
    if not isinstance(pr, dict):
        raise TypeError(f"Failed to view PR #{pr_number} on {repo}: expected object")
    if not _pr_has_label(pr, label):
        raise RuntimeError(
            f"PR #{pr_number} on {repo} is missing required label {label!r}. "
            "Refusing to use an unlabeled E2E fixture PR."
        )
    head = _pr_head_repo(pr)
    if head != repo:
        raise RuntimeError(
            f"PR #{pr_number} head repository is {head!r}, expected {repo!r}."
        )
    return pr


def ensure_e2e_pr(repo: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Find or create the long-lived E2E fixture PR via the GitHub API only."""
    e2e_pr = cfg["e2e_pr"]
    label = str(e2e_pr["label"])
    existing = find_open_e2e_pr(repo, label, branch=str(e2e_pr.get("branch") or ""))
    if existing:
        return _require_pr_label(repo, int(existing["number"]), label)

    _ensure_label(repo, label)
    default_branch = gh_text(
        [
            "repo",
            "view",
            repo,
            "--json",
            "defaultBranchRef",
            "-q",
            ".defaultBranchRef.name",
        ]
    ).strip()
    base_sha = gh_text(
        ["api", f"repos/{repo}/git/ref/heads/{default_branch}", "--jq", ".object.sha"]
    ).strip()
    branch = e2e_pr["branch"]

    ref_proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/git/ref/heads/{branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if ref_proc.returncode != 0:
        gh_json(
            [
                "api",
                "--method",
                "POST",
                f"repos/{repo}/git/refs",
                "-f",
                f"ref=refs/heads/{branch}",
                "-f",
                f"sha={base_sha}",
            ]
        )

    # Create or update marker file on the E2E branch.
    encoded = base64.b64encode(MARKER_BODY.encode("utf-8")).decode("ascii")
    existing_file = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/contents/{MARKER_PATH}?ref={branch}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    put_args = [
        "api",
        "--method",
        "PUT",
        f"repos/{repo}/contents/{MARKER_PATH}",
        "-f",
        "message=chore(e2e): keep ESTC detective fixture PR marker",
        "-f",
        f"content={encoded}",
        "-f",
        f"branch={branch}",
    ]
    if existing_file.returncode == 0:
        sha = json.loads(existing_file.stdout).get("sha")
        if sha:
            put_args.extend(["-f", f"sha={sha}"])
    gh_json(put_args)

    create = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--base",
            default_branch,
            "--head",
            branch,
            "--title",
            e2e_pr["title"],
            "--body",
            e2e_pr["body"],
            "--label",
            label,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if create.returncode != 0 and "already exists" not in (
        create.stderr + create.stdout
    ):
        # PR may already exist without label; recovery path below adds it.
        pass

    created = find_open_e2e_pr(repo, label, branch=branch, strict_branch=False)
    if created:
        return _require_pr_label(repo, int(created["number"]), label)

    prs = gh_json(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--head",
            f"{repo.split('/')[0]}:{branch}",
            "--json",
            "number,url,headRefName,headRefOid,title,headRepository,labels",
            "--limit",
            "5",
        ]
    )
    same_repo = _same_repo_prs(prs if isinstance(prs, list) else [], repo)
    matched = [pr for pr in same_repo if pr.get("headRefName") == branch]
    if not matched:
        raise RuntimeError(
            f"Failed to ensure E2E PR on {repo} branch {branch}. "
            f"Create an open same-repo PR labeled {label!r}."
        )
    pr_number = int(matched[0]["number"])
    edit = subprocess.run(
        [
            "gh",
            "pr",
            "edit",
            str(pr_number),
            "--repo",
            repo,
            "--add-label",
            label,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if edit.returncode != 0:
        raise RuntimeError(
            f"Failed to add label {label!r} to PR #{pr_number} on {repo}: "
            f"{(edit.stderr or edit.stdout or '').strip() or f'exit {edit.returncode}'}"
        )
    return _require_pr_label(repo, pr_number, label)


def _list_issue_comments(repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Paginate issue comments newest-first (GitHub default is oldest-first)."""
    comments: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = (
            gh_json(
                [
                    "api",
                    f"repos/{repo}/issues/{pr_number}/comments?per_page=100&page={page}",
                    "--jq",
                    ".",
                ]
            )
            or []
        )
        if not batch:
            break
        comments.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        if page > 50:
            break
    # Newest first for find/clear of recent agent output.
    comments.sort(
        key=lambda c: c.get("created_at") or c.get("createdAt") or "",
        reverse=True,
    )
    return comments


def _is_bot_comment_author(login: str | None) -> bool:
    if not login:
        return False
    lower = login.lower()
    return lower.endswith("[bot]") or lower in {
        "github-actions",
        "copilot",
        "copilot-swe-agent",
    }


def clear_detective_comments(repo: str, pr_number: int, markers: list[str]) -> int:
    comments = _list_issue_comments(repo, pr_number)
    deleted = 0
    for comment in comments:
        body = comment.get("body") or ""
        if not all(marker in body for marker in markers):
            continue
        login = (comment.get("user") or {}).get("login")
        if not _is_bot_comment_author(login):
            continue
        cid = comment.get("id")
        if not cid:
            continue
        proc = subprocess.run(
            ["gh", "api", "-X", "DELETE", f"repos/{repo}/issues/comments/{cid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            deleted += 1
    return deleted


def list_commit_statuses(repo: str, sha: str) -> list[dict[str, Any]]:
    """Return commit statuses across all pages (newest first per GitHub)."""
    raw = gh_json(
        [
            "api",
            f"repos/{repo}/commits/{sha}/statuses",
            "--paginate",
            "--slurp",
        ]
    )
    return cast(list[dict[str, Any]], flatten_slurped_pages(raw))


def match_commit_status(
    statuses: list[dict[str, Any]],
    *,
    context: str,
    state: str,
    target_url: str | None = None,
    since: datetime | None = None,
) -> dict[str, Any] | None:
    """Find a status matching context/state and optional target_url / since."""
    for status in statuses:
        if str(status.get("context") or "") != context:
            continue
        if str(status.get("state") or "") != state:
            continue
        if target_url and str(status.get("target_url") or "") != target_url:
            continue
        if since is not None:
            created_raw = status.get("created_at") or status.get("updated_at") or ""
            if not created_raw:
                continue
            if _parse_gh_time(str(created_raw)) < since:
                continue
        return status
    return None


def wait_for_commit_status(
    repo: str,
    sha: str,
    *,
    context: str,
    state: str,
    target_url: str | None,
    since: datetime | None,
    timeout_seconds: int,
    interval_seconds: int,
) -> dict[str, Any] | None:
    """Poll GitHub commit statuses until the expected Buildkite status appears."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        matched = match_commit_status(
            list_commit_statuses(repo, sha),
            context=context,
            state=state,
            target_url=target_url,
            since=since,
        )
        if matched:
            return matched
        time.sleep(interval_seconds)
    return None


def list_status_trigger_runs(
    repo: str, workflow_file: str, limit: int = 20
) -> list[dict[str, Any]]:
    return (
        gh_json(
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


def wait_for_new_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int] | None = None,
    event: str | None = "status",
) -> dict[str, Any] | None:
    """Wait for a workflow run created after ``since`` that has completed.

    Correlates by excluding known run IDs and optional ``event`` (default
    ``status``). Does **not** filter on ``headSha``: status-triggered runs use
    the default-branch tip as ``GITHUB_SHA`` / run ``headSha``, while the status
    commit is ``github.event.sha``.

    Returns ``None`` if no matching completed run appears before the deadline
    (in-progress matches are not treated as seen).
    """
    excluded = set(exclude_run_ids or ())
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for run in list_status_trigger_runs(repo, workflow_file):
            run_id = int(run["databaseId"])
            if run_id in excluded:
                continue
            created = _parse_gh_time(run["createdAt"])
            if created < since:
                continue
            if event and (run.get("event") or "").lower() != event.lower():
                continue
            while time.time() < deadline:
                detail = gh_json(
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
                if detail.get("status") == "completed":
                    return cast(dict[str, Any], detail)
                time.sleep(interval_seconds)
            # Matched a run but it never completed — fail closed (unseen).
            return None
        time.sleep(interval_seconds)
    return None


def status_job_conclusion(run_detail: dict[str, Any] | None) -> str | None:
    """Return the obs-aw-status job conclusion when that named job is present.

    Fail closed: do not treat the overall run conclusion as a substitute when the
    status job is absent (rename, empty jobs list, or unrelated successful jobs).
    """
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        if "run-obs-aw-status" in name or name.endswith("obs-aw-status"):
            conclusion = (job.get("conclusion") or "").lower()
            return conclusion or None
    return None


def status_job_executed(run_detail: dict[str, Any] | None) -> bool:
    """True only when the status route job completed with success."""
    return status_job_conclusion(run_detail) == "success"


def _job_names_indicate_agent(run_detail: dict[str, Any] | None) -> bool:
    """True when a non-skipped GH-AW agent (or lock) job ran.

    Ignores orchestrator/wrapper job names such as ``estc-pr-buildkite-detective``
    — those reusable calls can succeed while the agent job is skipped (no open PR).
    """
    if not run_detail:
        return False
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        # Lock file job id from gh-aw-estc-pr-buildkite-detective.lock.yml
        if name == "agent" or name.endswith(" / agent") or "/ agent" in name:
            return True
        if "gh-aw-estc-pr-buildkite-detective" in name:
            return True
    return False


def _view_run_jobs(repo: str, run_id: int) -> dict[str, Any] | None:
    detail = gh_json(
        [
            "run",
            "view",
            str(run_id),
            "--repo",
            repo,
            "--json",
            "databaseId,status,conclusion,url,jobs,createdAt,headSha",
        ]
    )
    return cast(dict[str, Any], detail) if detail else None


def agent_job_invoked(
    repo: str,
    run_detail: dict[str, Any] | None,
    *,
    since: datetime,
) -> bool:
    """Detect agent invocation via explicit non-skipped lock/agent jobs only.

    Nested ``workflow_call`` jobs are not listed on the status-trigger run, so we
    also inspect recent lock workflow runs — but only when the status route job
    actually succeeded (gate/skip cases must not scan unrelated lock history).
    A completed lock with a skipped ``agent`` job is never treated as invoked.
    """
    if _job_names_indicate_agent(run_detail):
        return True
    if not status_job_executed(run_detail):
        return False
    for run in list_status_trigger_runs(
        repo, "gh-aw-estc-pr-buildkite-detective.lock.yml", limit=30
    ):
        created = _parse_gh_time(run["createdAt"])
        if created < since:
            continue
        status = (run.get("status") or "").lower()
        if status != "completed":
            continue
        conclusion = (run.get("conclusion") or "").lower()
        if conclusion == "skipped":
            continue
        detail = _view_run_jobs(repo, int(run["databaseId"]))
        if _job_names_indicate_agent(detail):
            return True
    return False


def _buildkite_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return dict(cfg.get("buildkite_failure") or {})


def resolve_buildkite_org_pipeline(cfg: dict[str, Any]) -> tuple[str, str]:
    bk = _buildkite_cfg(cfg)
    org = os.environ.get(
        str(bk.get("org_env") or "E2E_BUILDKITE_ORG"), ""
    ).strip() or str(bk.get("org_default") or "elastic")
    pipeline = os.environ.get(
        str(bk.get("pipeline_env") or "E2E_BUILDKITE_PIPELINE"), ""
    ).strip() or str(bk.get("pipeline_default") or "oblt-aw-e2e-estc-fail")
    return org, pipeline


def buildkite_api_token(cfg: dict[str, Any]) -> str | None:
    bk = _buildkite_cfg(cfg)
    token_env = str(bk.get("token_env") or "BUILDKITE_TOKEN")
    token = os.environ.get(token_env, "").strip()
    return token or None


def bk_api_json(
    token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    url = f"https://api.buildkite.com/v2/{path.lstrip('/')}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body.strip() else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Buildkite API {method} {path} failed ({exc.code}): {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Buildkite API {method} {path} network error: {exc}"
        ) from exc


def create_buildkite_build(
    token: str,
    *,
    org: str,
    pipeline: str,
    commit: str,
    branch: str,
    message: str,
    pull_request_id: int | None = None,
    pull_request_base_branch: str | None = None,
    pull_request_repository: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "commit": commit,
        "branch": branch,
        "message": message,
        "ignore_pipeline_branch_filters": True,
        "meta_data": {"oblt_aw_e2e": "estc-pr-buildkite-detective"},
    }
    if pull_request_id:
        payload["pull_request_id"] = pull_request_id
        if pull_request_base_branch:
            payload["pull_request_base_branch"] = pull_request_base_branch
        if pull_request_repository:
            payload["pull_request_repository"] = pull_request_repository
    created = bk_api_json(
        token,
        "POST",
        f"organizations/{org}/pipelines/{pipeline}/builds",
        payload,
    )
    if not isinstance(created, dict) or not created.get("web_url"):
        raise RuntimeError(
            f"Buildkite create build returned unexpected payload: {created}"
        )
    return created


def wait_for_buildkite_build(
    token: str,
    *,
    org: str,
    pipeline: str,
    number: int,
    timeout_seconds: int,
    interval_seconds: int,
) -> dict[str, Any]:
    terminal = {"passed", "failed", "canceled", "blocked", "skipped", "not_run"}
    deadline = time.time() + timeout_seconds
    last: dict[str, Any] | None = None
    while time.time() < deadline:
        last = bk_api_json(
            token,
            "GET",
            f"organizations/{org}/pipelines/{pipeline}/builds/{number}",
        )
        state = str((last or {}).get("state") or "")
        if state in terminal:
            return last or {}
        time.sleep(interval_seconds)
    raise TimeoutError(
        f"Timed out waiting for Buildkite build {org}/{pipeline}#{number} "
        f"(last state={(last or {}).get('state')})"
    )


def verify_buildkite_fail_log_marker(
    token: str,
    *,
    org: str,
    pipeline: str,
    number: int,
    marker: str,
) -> tuple[bool, str]:
    """Fetch failed job logs and require the intentional-failure marker."""
    build = bk_api_json(
        token,
        "GET",
        f"organizations/{org}/pipelines/{pipeline}/builds/{number}",
    )
    if not isinstance(build, dict):
        return False, "build payload missing"
    checked = 0
    for job in build.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        if job.get("type") != "script":
            continue
        if str(job.get("state") or "") not in FAIL_STATES:
            continue
        job_id = job.get("id")
        if not job_id:
            continue
        checked += 1
        try:
            log_payload = bk_api_json(
                token,
                "GET",
                f"organizations/{org}/pipelines/{pipeline}/builds/{number}/jobs/{job_id}/log",
            )
        except RuntimeError as exc:
            return False, f"log fetch failed for job {job_id}: {exc}"
        content = ""
        if isinstance(log_payload, dict):
            content = str(log_payload.get("content") or "")
        elif isinstance(log_payload, str):
            content = log_payload
        if marker in content:
            return True, f"found in job {job.get('name') or job_id}"
    if checked == 0:
        return False, "no failed script jobs to inspect"
    return False, f"marker absent in {checked} failed script job log(s)"


def ensure_failed_buildkite_target_url(
    cfg: dict[str, Any],
    *,
    commit: str,
    branch: str,
    pr_number: int | None,
    case_id: str,
) -> tuple[str, dict[str, Any]]:
    """Create a failed Buildkite build and return (web_url, build_meta)."""
    token = buildkite_api_token(cfg)
    if not token:
        bk = _buildkite_cfg(cfg)
        token_env = str(bk.get("token_env") or "BUILDKITE_TOKEN")
        raise RuntimeError(f"Missing {token_env} (write_builds + read).")

    org, pipeline = resolve_buildkite_org_pipeline(cfg)
    bk = _buildkite_cfg(cfg)
    repo = str(cfg.get("consumer_repo") or "elastic/oblt-aw")
    pr_repo = f"https://github.com/{repo}.git"
    created = create_buildkite_build(
        token,
        org=org,
        pipeline=pipeline,
        commit=commit,
        branch=branch,
        message=f"oblt-aw e2e intentional failure ({case_id})",
        pull_request_id=pr_number or None,
        pull_request_base_branch="main" if pr_number else None,
        pull_request_repository=pr_repo if pr_number else None,
    )
    number = int(created["number"])
    finished = wait_for_buildkite_build(
        token,
        org=org,
        pipeline=pipeline,
        number=number,
        timeout_seconds=int(bk.get("poll_timeout_seconds") or 900),
        interval_seconds=int(bk.get("poll_interval_seconds") or 10),
    )
    state = str(finished.get("state") or "")
    web_url = str(finished.get("web_url") or created.get("web_url") or "")
    if state != "failed":
        raise RuntimeError(
            f"Expected Buildkite build to fail for E2E; got state={state} url={web_url}"
        )
    if not web_url:
        raise RuntimeError("Buildkite build finished without web_url")
    marker = str(bk.get("fail_log_marker") or "").strip()
    marker_ok = False
    marker_detail = "no fail_log_marker configured"
    if marker:
        marker_ok, marker_detail = verify_buildkite_fail_log_marker(
            token, org=org, pipeline=pipeline, number=number, marker=marker
        )
        if not marker_ok:
            raise RuntimeError(
                f"Buildkite build {web_url} failed but log marker {marker!r} "
                f"was not found ({marker_detail})"
            )
    return web_url, {
        "source": "created",
        "org": org,
        "pipeline": pipeline,
        "number": number,
        "state": state,
        "web_url": web_url,
        "pull_request_id": pr_number,
        "fail_log_marker": marker or None,
        "fail_log_marker_verified": marker_ok if marker else None,
        "fail_log_marker_detail": marker_detail,
    }


def needs_real_failed_buildkite(
    trigger: dict[str, Any], _expectations: dict[str, Any]
) -> bool:
    """True when the live case must create a failed Buildkite build."""
    return bool(trigger.get("create_failed_buildkite_build"))


def find_agent_comment(
    repo: str,
    pr_number: int,
    *,
    since: datetime,
    markers: list[str],
) -> dict[str, Any] | None:
    """Locate a post-``since`` bot comment using section markers as identity.

    Markers identify detective comments for find/clear. The live oracle only
    asserts presence/absence of a located comment; marker-shape checks are
    deferred to a follow-up.
    """
    for comment in _list_issue_comments(repo, pr_number):
        created_raw = comment.get("created_at") or comment.get("createdAt") or ""
        if not created_raw:
            continue
        created = _parse_gh_time(created_raw)
        if created < since:
            continue
        login = (comment.get("user") or {}).get("login")
        if not _is_bot_comment_author(login):
            continue
        body = comment.get("body") or ""
        markers_present = {marker: marker in body for marker in markers}
        if all(markers_present.values()):
            return {
                "id": comment.get("id"),
                "url": comment.get("html_url"),
                "user": login,
                "created_at": comment.get("created_at"),
                "markers_present": markers_present,
                "body_has_markers": True,
            }
    return None


def run_live_case(
    case_dir: Path,
    cfg: dict[str, Any],
    *,
    run_url: str | None = None,
) -> dict[str, Any]:
    case = _load_json(case_dir / "case.json")
    require_case_mode(case, "live", case_id=str(case.get("id", case_dir.name)))
    trigger = case.get("trigger") or {}
    expectations = case.get("expectations") or {}
    repo = str(cfg.get("consumer_repo") or "elastic/oblt-aw")
    workflow_id = str(case.get("workflow_id") or cfg.get("workflow_id") or WORKFLOW_ID)
    markers = list(
        expectations.get("agent_comment_markers")
        or cfg.get("agent_comment_markers")
        or ["### TL;DR", "## Remediation"]
    )

    dashboard_ok = dashboard_enables_workflow(
        repo, str(cfg.get("dashboard_workflow_id") or workflow_id)
    )
    if expectations.get("dashboard_enabled") and not dashboard_ok:
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                f"Dashboard does not enable {workflow_id} on {repo}. "
                "Enable the checkbox on the Control Plane Dashboard issue, then re-run."
            ),
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "run_url": run_url,
        }

    # Fail closed on missing Buildkite create credentials before mutating GitHub.
    if needs_real_failed_buildkite(trigger, expectations) and not buildkite_api_token(
        cfg
    ):
        bk = _buildkite_cfg(cfg)
        token_env = str(bk.get("token_env") or "BUILDKITE_TOKEN")
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": f"Missing {token_env} (write_builds + read).",
            "path_gates": {"dashboard_enabled": dashboard_ok},
            "expectations": expectations,
            "run_url": run_url,
        }

    if not trigger.get("require_open_pr", True):
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                "Live E2E is happy-path only and requires an open fixture PR "
                "(trigger.require_open_pr must be true)."
            ),
            "path_gates": {"dashboard_enabled": dashboard_ok},
            "expectations": expectations,
            "run_url": run_url,
        }
    if not trigger.get("create_failed_buildkite_build"):
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                "Live E2E is happy-path only: set "
                "trigger.create_failed_buildkite_build so Buildkite publishes "
                "the commit status (no harness-posted synthetic statuses)."
            ),
            "path_gates": {"dashboard_enabled": dashboard_ok},
            "expectations": expectations,
            "run_url": run_url,
        }

    pr_info = ensure_e2e_pr(repo, cfg)
    # Refresh OID after possible marker commit.
    refreshed = (
        find_open_e2e_pr(
            repo,
            cfg["e2e_pr"]["label"],
            branch=str(cfg["e2e_pr"].get("branch") or ""),
        )
        or pr_info
    )
    pr_info = refreshed
    sha = pr_info["headRefOid"]
    pr_number = int(pr_info["number"])
    e2e_branch = str(
        pr_info.get("headRefName") or cfg.get("e2e_pr", {}).get("branch") or ""
    )

    if trigger.get("clear_prior_detective_comments"):
        clear_detective_comments(repo, pr_number, markers)

    # Capture before Buildkite create so we observe the status-triggered Actions run.
    since = _utc_now().replace(microsecond=0)
    workflow_file_early = str(
        cfg.get("status_trigger_workflow_file") or "trigger-obs-aw-status.yml"
    )
    known_run_ids = {
        int(run["databaseId"])
        for run in list_status_trigger_runs(repo, workflow_file_early)
    }

    try:
        target_url, buildkite_meta = ensure_failed_buildkite_target_url(
            cfg,
            commit=sha,
            branch=e2e_branch or str(cfg.get("e2e_pr", {}).get("branch") or "main"),
            pr_number=pr_number,
            case_id=str(case.get("id", case_dir.name)),
        )
    except (RuntimeError, TimeoutError, ValueError) as exc:
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": str(exc),
            "path_gates": {"dashboard_enabled": dashboard_ok},
            "expectations": expectations,
            "run_url": run_url,
        }

    state = str(trigger.get("status_state") or "failure")
    timeout = int(cfg.get("poll_timeout_seconds") or 2400)
    interval = int(cfg.get("poll_interval_seconds") or 20)
    org, pipeline = resolve_buildkite_org_pipeline(cfg)
    context = f"buildkite/{org}/{pipeline}"
    status_timeout = int(cfg.get("status_observe_timeout_seconds") or min(300, timeout))
    observed = wait_for_commit_status(
        repo,
        sha,
        context=context,
        state=state,
        target_url=target_url,
        since=since,
        timeout_seconds=status_timeout,
        interval_seconds=interval,
    )
    if not observed:
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                f"Timed out waiting for GitHub commit status "
                f"context={context!r} state={state!r} "
                f"target_url={target_url!r} on {sha[:12]}."
            ),
            "path_gates": {"dashboard_enabled": dashboard_ok},
            "buildkite": buildkite_meta,
            "trigger": trigger,
            "expectations": expectations,
            "run_url": run_url,
        }

    description = observed.get("description")
    target_url = observed.get("target_url") or target_url
    state = str(observed.get("state") or state)
    context = str(observed.get("context") or context)
    # Missing creator.login must not default to Buildkite; URL matching
    # correlates the status, but publisher identity fails closed.
    status_publisher = publisher_for_created_build_status(observed)

    run_detail = wait_for_new_run(
        repo,
        workflow_file_early,
        since=since,
        timeout_seconds=timeout,
        interval_seconds=interval,
        exclude_run_ids=known_run_ids,
    )

    job_executed = status_job_executed(run_detail)
    job_conclusion = status_job_conclusion(run_detail)
    invoked = agent_job_invoked(repo, run_detail, since=since)
    comment = None
    if expectations.get("expect_agent_comment"):
        comment_deadline = time.time() + min(900, timeout)
        while time.time() < comment_deadline and comment is None:
            comment = find_agent_comment(repo, pr_number, since=since, markers=markers)
            if comment:
                break
            # Nested agent jobs may finish after the parent lists them.
            if run_detail and run_detail.get("databaseId"):
                run_detail = gh_json(
                    [
                        "run",
                        "view",
                        str(run_detail["databaseId"]),
                        "--repo",
                        repo,
                        "--json",
                        "databaseId,status,conclusion,url,jobs,createdAt,headSha,event",
                    ]
                )
            invoked = agent_job_invoked(repo, run_detail, since=since)
            time.sleep(interval)
    else:
        comment = find_agent_comment(repo, pr_number, since=since, markers=markers)

    path_gates = {
        "dashboard_enabled": dashboard_ok,
        "state_failure": state == "failure",
        "context_contains_buildkite": "buildkite" in context.lower(),
        "has_open_pr": True,
        "shared_proceed": dashboard_ok,
        "path_ready": bool(
            state == "failure" and "buildkite" in context.lower() and dashboard_ok
        ),
    }

    return {
        "workflow_id": workflow_id,
        "case_id": case.get("id", case_dir.name),
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": invoked,
        "blocked": False,
        "consumer_repo": repo,
        "commit_sha": sha,
        "pr_number": pr_number,
        "pr_url": pr_info.get("url"),
        "trigger": trigger,
        "status": {
            "state": state,
            "context": context,
            "target_url": target_url,
            "description": description,
            "publisher": status_publisher,
            "api_url": observed.get("url"),
        },
        "buildkite": buildkite_meta,
        "status_trigger": {
            "run_seen": run_detail is not None,
            "job_executed": job_executed,
            "job_conclusion": job_conclusion,
            "run_id": (run_detail or {}).get("databaseId"),
            "conclusion": (run_detail or {}).get("conclusion"),
            "url": (run_detail or {}).get("url"),
        },
        "agent_comment": comment,
        "path_gates": path_gates,
        "expectations": expectations,
        "run_url": run_url,
        "harness_notes": [
            (
                "Happy path only: harness creates an intentional Buildkite failure; "
                "Buildkite publishes the GitHub commit status; "
                "trigger-obs-aw-status → agent → PR comment."
            ),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run estc-pr-buildkite-detective live E2E harness."
    )
    parser.add_argument(
        "--case-id",
        default="status-failure-open-pr-live",
        help="Case directory name under testdata/.../cases/",
    )
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/estc-pr-buildkite-detective"),
        help="Root of ESTC detective live E2E cases",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Live E2E config JSON",
    )
    parser.add_argument(
        "--outcome-path",
        type=Path,
        required=True,
        help="Where to write the machine-readable harness outcome JSON",
    )
    parser.add_argument(
        "--run-url",
        default="",
        help="Optional GitHub Actions run URL to embed in the outcome",
    )
    args = parser.parse_args(argv)

    case_dir = args.testdata_root / "cases" / args.case_id
    if not case_dir.is_dir():
        raise SystemExit(f"Case directory not found: {case_dir}")

    cfg = load_e2e_config(args.config_path)
    outcome = run_live_case(case_dir, cfg, run_url=args.run_url or None)

    args.outcome_path.parent.mkdir(parents=True, exist_ok=True)
    args.outcome_path.write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote harness outcome to {args.outcome_path}")
    print(
        json.dumps(
            {
                "mode": outcome.get("mode"),
                "case_id": outcome.get("case_id"),
                "blocked": outcome.get("blocked"),
                "agent_invoked": outcome.get("agent_invoked"),
            },
            indent=2,
        )
    )

    if outcome.get("blocked"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
