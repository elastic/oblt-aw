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

"""Live E2E harness for obs:pr-actions-detective.

Drives the real failed Actions workflow_run → trigger → prelude → wrapper →
lock → agent path against elastic/oblt-aw (production consumer for this slice).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

# scripts/ siblings (e.g. get_enabled_workflows) when this file lives under scripts/obs/e2e/.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

WORKFLOW_ID = "obs:pr-actions-detective"
DEFAULT_CONFIG = Path("config/obs/e2e-pr-actions-detective.json")
MARKER_PATH = "testdata/agentic/pr-actions-detective/e2e-fixture-pr.md"
MARKER_BODY = (
    "# E2E fixture PR\n\n"
    "Kept open for live `workflow_run` → agent E2E of "
    "`obs:pr-actions-detective`. Do not merge.\n"
)
TRIGGER_PATH = "testdata/agentic/pr-actions-detective/e2e-fail-trigger.md"
FAIL_WORKFLOW_PATH = Path(".github/workflows/e2e-pr-actions-detective-fail.yml")
DEFAULT_FIXTURE_TITLE = "[e2e] PR Actions Detective fixture"
DEFAULT_FIXTURE_BODY = (
    "Long-lived fixture PR for `obs:pr-actions-detective`. Do not merge."
)
FIXTURE_BRANCH = "e2e/pr-actions-detective"
FIXTURE_LABEL = "e2e:pr-actions-detective"
DEFAULT_FAIL_LOG_MARKER = "OBLT_AW_E2E_PR_ACTIONS_INTENTIONAL_FAILURE"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_gh_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _running_in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def log_info(message: str) -> None:
    print(f"[pr-actions-detective-e2e] {message}", flush=True)


def log_error(message: str) -> None:
    print(
        f"::error::{message}" if _running_in_github_actions() else message, flush=True
    )


def normalize_e2e_pr_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return cfg with the canonical long-lived fixture PR fields filled in."""
    out = dict(cfg)
    e2e_pr = dict(out.get("e2e_pr") or {})
    label = str(e2e_pr.get("label") or FIXTURE_LABEL).strip()
    branch = str(e2e_pr.get("branch") or FIXTURE_BRANCH).strip()
    if label != FIXTURE_LABEL:
        raise RuntimeError(
            f"e2e_pr.label {label!r} must be the canonical fixture label "
            f"{FIXTURE_LABEL!r} (CI/agent skip guards require it)."
        )
    if branch != FIXTURE_BRANCH:
        raise RuntimeError(
            f"e2e_pr.branch {branch!r} must be the long-lived fixture "
            f"{FIXTURE_BRANCH!r}."
        )
    e2e_pr["label"] = label
    e2e_pr["branch"] = branch
    e2e_pr.setdefault("title", DEFAULT_FIXTURE_TITLE)
    e2e_pr.setdefault("body", DEFAULT_FIXTURE_BODY)
    out["e2e_pr"] = e2e_pr
    return out


def require_case_mode(case: dict[str, Any], mode: str, *, case_id: str) -> None:
    actual = str(case.get("mode") or "")
    if actual != mode:
        raise SystemExit(
            f"Case {case_id!r} mode is {actual!r}; harness requires {mode!r}."
        )


def gh_json(args: list[str], *, check: bool = True) -> Any:
    cmd = ["gh", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '').strip()}"
        )
    text = (proc.stdout or "").strip()
    if not text:
        return None
    return json.loads(text)


def gh_text(args: list[str], *, check: bool = True) -> str:
    cmd = ["gh", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '').strip()}"
        )
    return proc.stdout or ""


def commit_sha_from_contents_put(payload: Any) -> str:
    """Extract the new commit SHA from a GitHub Contents API PUT response."""
    if not isinstance(payload, dict):
        raise TypeError(
            f"Contents PUT response must be a mapping, got {type(payload).__name__}"
        )
    commit = payload.get("commit")
    if not isinstance(commit, dict):
        raise TypeError(
            "Contents PUT response missing commit object; cannot bind fail "
            "workflow wait to the fixture tip."
        )
    sha = str(commit.get("sha") or "").strip()
    if not sha:
        raise RuntimeError(
            "Contents PUT response missing commit.sha; cannot bind fail "
            "workflow wait to the fixture tip."
        )
    return sha


def put_branch_file(
    repo: str,
    *,
    branch: str,
    path: str,
    content: str,
    message: str,
) -> str | None:
    """Create or update a file on ``branch``.

    Returns the new commit SHA when a commit was made, or ``None`` when the
    remote file already matched ``content`` (no commit).
    """
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    existing_file = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    existing_sha: str | None = None
    if existing_file.returncode == 0:
        payload = json.loads(existing_file.stdout)
        existing_sha = payload.get("sha")
        remote_b64 = str(payload.get("content") or "").replace("\n", "")
        if remote_b64 == encoded:
            return None
    put_args = [
        "api",
        "--method",
        "PUT",
        f"repos/{repo}/contents/{path}",
        "-f",
        f"message={message}",
        "-f",
        f"content={encoded}",
        "-f",
        f"branch={branch}",
    ]
    if existing_sha:
        put_args.extend(["-f", f"sha={existing_sha}"])
    return commit_sha_from_contents_put(gh_json(put_args))


def load_e2e_config(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"E2E config must be a JSON object: {path}")
    return normalize_e2e_pr_config(data)


def dashboard_enables_workflow(repo: str, workflow_id: str) -> bool:
    from get_enabled_workflows import (  # type: ignore[import-not-found]
        parse_enabled_ids_from_body,
    )

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
    head_repo = pr.get("headRepository")
    if isinstance(head_repo, dict):
        name_with_owner = head_repo.get("nameWithOwner")
        if isinstance(name_with_owner, str) and name_with_owner:
            return name_with_owner
    return ""


def _same_repo_prs(prs: list[Any], repo: str) -> list[dict[str, Any]]:
    same: list[dict[str, Any]] = []
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        head = _pr_head_repo(pr)
        if head and head != repo:
            continue
        if not head:
            continue
        same.append(pr)
    return same


def _gh_pr_list_head_filter(branch: str) -> str:
    return branch


def _pr_number_from_gh_output(text: str) -> int | None:
    match = re.search(r"/pull/(\d+)\b", text)
    if not match:
        return None
    return int(match.group(1))


def _list_prs_by_head(
    repo: str, *, branch: str, state: str, limit: int = 5
) -> list[dict[str, Any]]:
    prs = gh_json(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            state,
            "--head",
            _gh_pr_list_head_filter(branch),
            "--json",
            "number,url,headRefName,headRefOid,title,headRepository,labels",
            "--limit",
            str(limit),
        ]
    )
    same_repo = _same_repo_prs(prs if isinstance(prs, list) else [], repo)
    return [pr for pr in same_repo if pr.get("headRefName") == branch]


def find_open_e2e_pr(
    repo: str,
    label: str,
    *,
    branch: str,
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
        if prs:
            raise RuntimeError(
                f"Open PR(s) with label {label!r} exist, but none are same-repo "
                f"heads in {repo!r}. Refusing to target a fork fixture PR."
            )
        return None
    matched = [pr for pr in same_repo if pr.get("headRefName") == branch]
    if not matched:
        raise RuntimeError(
            f"Open PR(s) with label {label!r} exist, but none use branch "
            f"{branch!r} on {repo!r}. Refusing to target an unrelated "
            "fixture PR."
        )
    return matched[0]


def _ensure_label(repo: str, label: str) -> None:
    proc = subprocess.run(
        [
            "gh",
            "label",
            "create",
            label,
            "--repo",
            repo,
            "--description",
            "PR Actions Detective E2E fixture PR (long-lived)",
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


def _find_closed_fixture_pr(
    repo: str, *, branch: str, label: str
) -> dict[str, Any] | None:
    matched = _list_prs_by_head(repo, branch=branch, state="closed", limit=5)
    labeled = [pr for pr in matched if _pr_has_label(pr, label)]
    return labeled[0] if labeled else None


def ensure_e2e_pr(repo: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Find, reopen, or create the long-lived E2E fixture PR via the GitHub API."""
    cfg = normalize_e2e_pr_config(cfg)
    e2e_pr = cfg["e2e_pr"]
    label = str(e2e_pr["label"])
    branch = str(e2e_pr["branch"])
    if branch != FIXTURE_BRANCH:
        raise RuntimeError(
            f"Refusing fixture branch {branch!r}; expected {FIXTURE_BRANCH!r}."
        )
    existing = find_open_e2e_pr(repo, label, branch=branch)
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

    encoded = base64.b64encode(MARKER_BODY.encode("utf-8")).decode("ascii")
    existing_file = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{MARKER_PATH}?ref={branch}"],
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
        "message=chore(e2e): keep PR Actions Detective fixture PR marker",
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
    create_out = f"{create.stderr or ''}{create.stdout or ''}"
    if create.returncode == 0:
        created_number = _pr_number_from_gh_output(create.stdout or create_out)
        if created_number is not None:
            return _require_pr_label(repo, created_number, label)
    elif "already exists" not in create_out.lower():
        pass

    created = find_open_e2e_pr(repo, label, branch=branch)
    if created:
        return _require_pr_label(repo, int(created["number"]), label)

    closed = _find_closed_fixture_pr(repo, branch=branch, label=label)
    if closed:
        pr_number = int(closed["number"])
        reopen = subprocess.run(
            ["gh", "pr", "reopen", str(pr_number), "--repo", repo],
            capture_output=True,
            text=True,
            check=False,
        )
        if reopen.returncode != 0:
            raise RuntimeError(
                f"Fixture PR #{pr_number} on {repo} is closed and reopen failed: "
                f"{(reopen.stderr or reopen.stdout or '').strip() or f'exit {reopen.returncode}'}. "
                f"Create a new open same-repo PR labeled {label!r} on {branch!r}."
            )
        if not _pr_has_label(closed, label):
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
                    f"Failed to add label {label!r} to reopened PR #{pr_number} "
                    f"on {repo}: "
                    f"{(edit.stderr or edit.stdout or '').strip() or f'exit {edit.returncode}'}"
                )
        reopened = find_open_e2e_pr(repo, label, branch=branch)
        if reopened:
            return _require_pr_label(repo, int(reopened["number"]), label)
        return _require_pr_label(repo, pr_number, label)

    matched = _list_prs_by_head(repo, branch=branch, state="open", limit=5)
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
    if edit.returncode == 0:
        return _require_pr_label(repo, pr_number, label)
    raise RuntimeError(
        f"Failed to add label {label!r} to PR #{pr_number} on {repo}: "
        f"{(edit.stderr or edit.stdout or '').strip() or f'exit {edit.returncode}'}"
    )


def _list_issue_comments(repo: str, pr_number: int) -> list[dict[str, Any]]:
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
    deleted = 0
    for comment in _list_issue_comments(repo, pr_number):
        login = (comment.get("user") or {}).get("login")
        if not _is_bot_comment_author(login):
            continue
        body = comment.get("body") or ""
        if not all(marker in body for marker in markers):
            continue
        comment_id = comment.get("id")
        if comment_id is None:
            continue
        gh_json(
            [
                "api",
                "--method",
                "DELETE",
                f"repos/{repo}/issues/comments/{comment_id}",
            ]
        )
        deleted += 1
    if deleted:
        log_info(f"Cleared {deleted} prior detective comment(s) on PR #{pr_number}.")
    return deleted


def find_agent_comment(
    repo: str,
    pr_number: int,
    *,
    since: datetime,
    markers: list[str],
) -> dict[str, Any] | None:
    """Locate a post-``since`` bot comment using section markers as identity."""
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


def list_workflow_runs(
    repo: str, workflow_file: str, limit: int = 30
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


def sync_fail_workflow_to_fixture_branch(
    repo: str,
    *,
    branch: str,
    workflow_path: Path | None = None,
) -> str | None:
    """Ensure the fixture branch tip includes the fail-workflow YAML from this checkout."""
    path = workflow_path if workflow_path is not None else FAIL_WORKFLOW_PATH
    if not path.is_file():
        raise RuntimeError(
            f"Fail workflow YAML missing at {path}; cannot sync fixture branch."
        )
    content = path.read_text(encoding="utf-8")
    remote_path = str(FAIL_WORKFLOW_PATH).replace("\\", "/")
    synced_sha = put_branch_file(
        repo,
        branch=branch,
        path=remote_path,
        content=content,
        message="chore(e2e): sync PR Actions Detective fail workflow onto fixture branch",
    )
    if synced_sha:
        log_info(
            f"Synced {remote_path} onto {repo}@{branch} "
            f"(commit {synced_sha[:12]}) for intentional Actions failure."
        )
    else:
        log_info(f"{remote_path} already current on {repo}@{branch}.")
    return synced_sha


def bump_fail_trigger_on_fixture_branch(
    repo: str,
    *,
    branch: str,
    nonce: str | None = None,
) -> str:
    """Always commit a unique trigger file so pull_request synchronize fires."""
    run_nonce = nonce or uuid.uuid4().hex
    content = (
        "# E2E intentional Actions failure trigger\n\n"
        "Harness bumps this file each live run so `pull_request` synchronize "
        "fires `e2e-pr-actions-detective-fail.yml`.\n\n"
        f"run_nonce: {run_nonce}\n"
    )
    synced_sha = put_branch_file(
        repo,
        branch=branch,
        path=TRIGGER_PATH,
        content=content,
        message=f"chore(e2e): bump PR Actions Detective fail trigger ({run_nonce[:8]})",
    )
    if not synced_sha:
        # Content collided (extremely unlikely with uuid); force a distinct body.
        content = content + f"forced_at: {_utc_now().isoformat()}\n"
        synced_sha = put_branch_file(
            repo,
            branch=branch,
            path=TRIGGER_PATH,
            content=content,
            message=(
                f"chore(e2e): bump PR Actions Detective fail trigger "
                f"({run_nonce[:8]}-retry)"
            ),
        )
    if not synced_sha:
        raise RuntimeError(
            f"Failed to bump {TRIGGER_PATH} on {repo}@{branch}; "
            "cannot start intentional fail workflow_run."
        )
    log_info(
        f"Bumped {TRIGGER_PATH} on {repo}@{branch} "
        f"(commit {synced_sha[:12]}) to fire intentional failure."
    )
    return synced_sha


def wait_for_failed_actions_run(
    repo: str,
    workflow_file: str,
    *,
    head_sha: str,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    expected_event: str = "pull_request",
    expected_conclusion: str = "failure",
    exclude_run_ids: set[int] | None = None,
) -> dict[str, Any] | None:
    """Wait for a completed fail-workflow run on ``head_sha`` with the expected conclusion."""
    excluded = set(exclude_run_ids or ())
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for run in list_workflow_runs(repo, workflow_file):
            run_id = int(run["databaseId"])
            if run_id in excluded:
                continue
            created = _parse_gh_time(run["createdAt"])
            if created < since:
                continue
            if (run.get("headSha") or "") != head_sha:
                continue
            if (
                expected_event
                and (run.get("event") or "").lower() != expected_event.lower()
            ):
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
                if detail.get("status") != "completed":
                    time.sleep(interval_seconds)
                    continue
                conclusion = str(detail.get("conclusion") or "").lower()
                if conclusion == expected_conclusion.lower():
                    return cast(dict[str, Any], detail)
                excluded.add(run_id)
                break
        time.sleep(interval_seconds)
    return None


def verify_fail_log_marker(
    repo: str,
    run_id: int,
    *,
    marker: str,
) -> tuple[bool, str]:
    """Best-effort: confirm the intentional failure marker appears in job logs."""
    proc = subprocess.run(
        [
            "gh",
            "run",
            "view",
            str(run_id),
            "--repo",
            repo,
            "--log-failed",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    combined = f"{proc.stdout or ''}{proc.stderr or ''}"
    if marker in combined:
        return True, f"Found fail log marker {marker!r} in run {run_id}"
    if proc.returncode != 0 and not (proc.stdout or "").strip():
        return False, (
            f"Could not read failed logs for run {run_id} "
            f"(exit {proc.returncode}): {(proc.stderr or '').strip()[:400]}"
        )
    return False, f"Fail log marker {marker!r} not found in run {run_id} failed logs"


def wait_for_new_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int] | None = None,
    event: str | None = "workflow_run",
) -> dict[str, Any] | None:
    """Wait for a workflow_run-triggered caller run whose named job succeeded.

    Poll the **caller** ``trigger-obs-aw-workflow-run.yml`` run (not the
    ``workflow_call`` orchestrator). Skipped route jobs are ignored.
    """
    excluded = set(exclude_run_ids or ())
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for run in list_workflow_runs(repo, workflow_file):
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
                if detail.get("status") != "completed":
                    time.sleep(interval_seconds)
                    continue
                if workflow_run_job_executed(detail):
                    return cast(dict[str, Any], detail)
                excluded.add(run_id)
                break
        time.sleep(interval_seconds)
    return None


def workflow_run_job_conclusion(run_detail: dict[str, Any] | None) -> str | None:
    """Return the named workflow-run route job conclusion when present.

    Fail closed: do not treat overall run conclusion as a substitute.
    Prefer leaf suffixes that match ``run-obs-aw-workflow-run``.
    """
    if not run_detail:
        return None
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        if "run-obs-aw-workflow-run" in name or name.endswith("obs-aw-workflow-run"):
            conclusion = (job.get("conclusion") or "").lower()
            return conclusion or None
    return None


def workflow_run_job_executed(run_detail: dict[str, Any] | None) -> bool:
    return workflow_run_job_conclusion(run_detail) == "success"


def _job_names_indicate_agent(run_detail: dict[str, Any] | None) -> bool:
    if not run_detail:
        return False
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        if name == "agent" or name.endswith(" / agent") or "/ agent" in name:
            return True
        if "gh-aw-pr-actions-detective" in name:
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
    if _job_names_indicate_agent(run_detail):
        return True
    if not workflow_run_job_executed(run_detail):
        return False
    for run in list_workflow_runs(
        repo, "gh-aw-pr-actions-detective.lock.yml", limit=30
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
    cfg = normalize_e2e_pr_config(cfg)
    repo = str(cfg.get("consumer_repo") or "elastic/oblt-aw")
    workflow_id = str(case.get("workflow_id") or cfg.get("workflow_id") or WORKFLOW_ID)
    markers = list(
        expectations.get("agent_comment_markers")
        or cfg.get("agent_comment_markers")
        or ["### TL;DR", "## Remediation"]
    )
    fixture_meta = {
        "branch": cfg["e2e_pr"].get("branch"),
        "label": cfg["e2e_pr"].get("label"),
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
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "run_url": run_url,
        }
    if not trigger.get("create_failed_actions_run"):
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                "Live E2E is happy-path only: set "
                "trigger.create_failed_actions_run so an intentional GitHub "
                "Actions failure produces the workflow_run entry event."
            ),
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "run_url": run_url,
        }

    dashboard_ok = False
    sha: str | None = None
    target_pr_number: int | None = None
    fail_run_meta: dict[str, Any] = {}
    try:
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
                    "Enable the checkbox on the Control Plane Dashboard issue, "
                    "then re-run."
                ),
                "path_gates": {"dashboard_enabled": False},
                "expectations": expectations,
                "run_url": run_url,
            }

        pr_info = ensure_e2e_pr(repo, cfg)
        resolved_base = "main"
        sha = pr_info["headRefOid"]
        target_pr_number = int(pr_info["number"])
        e2e_branch = str(
            pr_info.get("headRefName") or cfg.get("e2e_pr", {}).get("branch") or ""
        )
        fixture_meta["pr_number"] = target_pr_number
        fixture_meta["pr_url"] = pr_info.get("url")

        if trigger.get("clear_prior_detective_comments"):
            clear_detective_comments(repo, target_pr_number, markers)

        since = _utc_now().replace(microsecond=0)
        trigger_workflow = str(
            cfg.get("workflow_run_trigger_workflow_file")
            or "trigger-obs-aw-workflow-run.yml"
        )
        fail_workflow = str(
            cfg.get("fail_workflow_file") or "e2e-pr-actions-detective-fail.yml"
        )
        known_trigger_ids = {
            int(run["databaseId"]) for run in list_workflow_runs(repo, trigger_workflow)
        }
        known_fail_ids = {
            int(run["databaseId"]) for run in list_workflow_runs(repo, fail_workflow)
        }

        if not e2e_branch:
            raise RuntimeError("Fixture PR is missing headRefName.")
        sync_fail_workflow_to_fixture_branch(repo, branch=e2e_branch)
        sha = bump_fail_trigger_on_fixture_branch(repo, branch=e2e_branch)

        timeout = int(cfg.get("poll_timeout_seconds") or 2400)
        interval = int(cfg.get("poll_interval_seconds") or 20)
        fail_timeout = int(
            cfg.get("fail_workflow_poll_timeout_seconds") or min(900, timeout)
        )
        expected_event = str(trigger.get("fail_workflow_event") or "pull_request")
        expected_conclusion = str(trigger.get("fail_workflow_conclusion") or "failure")

        fail_detail = wait_for_failed_actions_run(
            repo,
            fail_workflow,
            head_sha=sha,
            since=since,
            timeout_seconds=fail_timeout,
            interval_seconds=interval,
            expected_event=expected_event,
            expected_conclusion=expected_conclusion,
            exclude_run_ids=known_fail_ids,
        )
        if fail_detail is None:
            return {
                "workflow_id": workflow_id,
                "case_id": case.get("id", case_dir.name),
                "layer": "e2e",
                "mode": "live",
                "agent_invoked": False,
                "blocked": True,
                "block_reason": (
                    f"Timed out after {fail_timeout}s waiting for intentional "
                    f"fail workflow {fail_workflow!r} on commit {sha} "
                    f"(event={expected_event!r}, conclusion={expected_conclusion!r})."
                ),
                "path_gates": {"dashboard_enabled": dashboard_ok},
                "fixture": fixture_meta,
                "commit_sha": sha,
                "pr_number": target_pr_number,
                "trigger": trigger,
                "expectations": expectations,
                "run_url": run_url,
            }

        marker = str(cfg.get("fail_log_marker") or DEFAULT_FAIL_LOG_MARKER)
        marker_ok, marker_detail = verify_fail_log_marker(
            repo, int(fail_detail["databaseId"]), marker=marker
        )
        fail_run_meta = {
            "source": "created",
            "workflow_file": fail_workflow,
            "run_id": fail_detail.get("databaseId"),
            "url": fail_detail.get("url"),
            "conclusion": fail_detail.get("conclusion"),
            "event": fail_detail.get("event"),
            "head_sha": fail_detail.get("headSha"),
            "fail_log_marker_verified": marker_ok,
            "fail_log_marker_detail": marker_detail,
        }
        if not marker_ok:
            return {
                "workflow_id": workflow_id,
                "case_id": case.get("id", case_dir.name),
                "layer": "e2e",
                "mode": "live",
                "agent_invoked": False,
                "blocked": True,
                "block_reason": (
                    "Intentional fail workflow completed but log marker was not "
                    f"verified: {marker_detail}"
                ),
                "path_gates": {"dashboard_enabled": dashboard_ok},
                "fail_workflow": fail_run_meta,
                "fixture": fixture_meta,
                "commit_sha": sha,
                "pr_number": target_pr_number,
                "trigger": trigger,
                "expectations": expectations,
                "run_url": run_url,
            }

        run_detail = wait_for_new_run(
            repo,
            trigger_workflow,
            since=since,
            timeout_seconds=timeout,
            interval_seconds=interval,
            exclude_run_ids=known_trigger_ids,
            event="workflow_run",
        )
        if run_detail is None:
            raise TimeoutError(
                f"No successful workflow-run route for {trigger_workflow!r} "
                f"within {timeout}s after intentional Actions failure "
                f"(commit {sha}, fail run {fail_detail.get('url')})."
            )

        job_executed = workflow_run_job_executed(run_detail)
        job_conclusion = workflow_run_job_conclusion(run_detail)
        invoked = agent_job_invoked(repo, run_detail, since=since)
        comment = None
        if expectations.get("expect_agent_comment"):
            comment_deadline = time.time() + min(900, timeout)
            while time.time() < comment_deadline and comment is None:
                comment = find_agent_comment(
                    repo, target_pr_number, since=since, markers=markers
                )
                if comment:
                    break
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
            comment = find_agent_comment(
                repo, target_pr_number, since=since, markers=markers
            )
    except (RuntimeError, TimeoutError, TypeError, ValueError, OSError) as exc:
        blocked: dict[str, Any] = {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": str(exc),
            "path_gates": {"dashboard_enabled": dashboard_ok},
            "fixture": fixture_meta,
            "expectations": expectations,
            "trigger": trigger,
            "run_url": run_url,
        }
        if fail_run_meta:
            blocked["fail_workflow"] = fail_run_meta
        if sha is not None:
            blocked["commit_sha"] = sha
        if target_pr_number is not None:
            blocked["pr_number"] = target_pr_number
        return blocked

    path_gates = {
        "dashboard_enabled": dashboard_ok,
        "has_open_pr": True,
        "shared_proceed": dashboard_ok,
        "path_ready": bool(
            dashboard_ok and fail_run_meta.get("fail_log_marker_verified")
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
        "pr_number": target_pr_number,
        "pr_url": pr_info.get("url"),
        "pr_head_branch": e2e_branch,
        "pr_base_branch": resolved_base,
        "fixture": fixture_meta,
        "trigger": trigger,
        "fail_workflow": fail_run_meta,
        "workflow_run_trigger": {
            "run_seen": True,
            "job_executed": job_executed,
            "job_conclusion": job_conclusion,
            "run_id": run_detail.get("databaseId"),
            "conclusion": run_detail.get("conclusion"),
            "url": run_detail.get("url"),
        },
        "agent_comment": comment,
        "path_gates": path_gates,
        "expectations": expectations,
        "run_url": run_url,
        "harness_notes": [
            (
                "Happy path only: long-lived fixture PR → intentional GitHub "
                "Actions failure → workflow_run → trigger-obs-aw-workflow-run "
                "→ agent → PR comment."
            ),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run pr-actions-detective live E2E harness."
    )
    parser.add_argument(
        "--case-id",
        default="workflow-run-failure-open-pr-live",
        help="Case directory name under testdata/.../cases/",
    )
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/pr-actions-detective"),
        help="Root of PR Actions Detective live E2E cases",
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

    cfg = load_e2e_config(args.config_path)

    case_dir = args.testdata_root / "cases" / args.case_id
    if not case_dir.is_dir():
        raise SystemExit(f"Case directory not found: {case_dir}")

    outcome = run_live_case(
        case_dir,
        cfg,
        run_url=args.run_url or None,
    )

    args.outcome_path.parent.mkdir(parents=True, exist_ok=True)
    args.outcome_path.write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote harness outcome to {args.outcome_path}")
    summary = {
        "mode": outcome.get("mode"),
        "case_id": outcome.get("case_id"),
        "blocked": outcome.get("blocked"),
        "agent_invoked": outcome.get("agent_invoked"),
        "commit_sha": outcome.get("commit_sha"),
        "pr_number": outcome.get("pr_number"),
        "pr_url": outcome.get("pr_url"),
        "fixture": outcome.get("fixture"),
    }
    if outcome.get("blocked"):
        summary["block_reason"] = outcome.get("block_reason")
    fail_workflow = outcome.get("fail_workflow")
    if isinstance(fail_workflow, dict) and fail_workflow:
        summary["fail_workflow"] = {
            k: fail_workflow.get(k)
            for k in (
                "source",
                "url",
                "conclusion",
                "workflow_file",
                "fail_log_marker_verified",
            )
            if k in fail_workflow
        }
    print(json.dumps(summary, indent=2), flush=True)

    if outcome.get("blocked"):
        reason = str(outcome.get("block_reason") or "blocked")
        log_error(f"E2E harness blocked: {reason}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
