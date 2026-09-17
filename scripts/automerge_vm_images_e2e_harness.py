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

"""Live E2E harness for obs:automerge:vm-images.

Creates an ephemeral same-repo PR that mimics playground updatecli VM-image
bumps (github-actions[bot] + .buildkite/** IMAGE pins), then waits for
dependency-review → merge-ready → automerge approve/merge.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

# Reuse shared gh / Contents helpers from the ESTC harness.
import estc_pr_buildkite_detective_e2e_harness as estc

WORKFLOW_ID = "obs:automerge"
DEFAULT_CONFIG = Path("config/obs/e2e-automerge-vm-images.json")
DEFAULT_FIXTURE_PIPELINE = Path(".buildkite/pipeline.e2e-automerge-vm-images.yml")
FIXTURE_LABEL = "e2e:automerge-vm-images"
FIXTURE_BRANCH_PREFIX = "e2e/automerge-vm-images/"
IMAGE_PIN_RE = re.compile(
    r'(IMAGE_[A-Z0-9_]+):\s*"platform-ingest-elastic-agent-([^-"]+)-(\d+)"'
)
ALLOWED_AUTHOR = "github-actions[bot]"


def author_login_from_rest_pull(payload: dict[str, Any]) -> str:
    """Extract PR author login from a REST ``GET /repos/.../pulls/{n}`` payload.

    Use REST ``user.login`` (same form as ``github.event.pull_request.user.login``
    and ``allowed_pr_authors.json``). Do **not** use ``gh pr view --json author``:
    since gh >= 2.50 GraphQL returns ``app/github-actions`` for the Actions bot
    while REST still returns ``github-actions[bot]``.
    """
    user = payload.get("user")
    if not isinstance(user, dict):
        raise TypeError("REST pull payload missing object user")
    login = str(user.get("login") or "").strip()
    if not login:
        raise RuntimeError("REST pull payload missing user.login")
    return login


def rest_pr_author_login(repo: str, pr_number: int) -> str:
    """Return fixture PR author login via the REST Pulls API."""
    payload = estc.gh_json(["api", f"repos/{repo}/pulls/{pr_number}"])
    if not isinstance(payload, dict):
        raise TypeError(
            f"Unexpected REST pulls/{pr_number} payload type: {type(payload).__name__}"
        )
    return author_login_from_rest_pull(payload)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_e2e_config(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"E2E config must be a JSON object: {path}")
    return data


def bump_image_pins(content: str, version: str) -> str:
    """Replace IMAGE_* platform-ingest pins with ``version`` (playground shape)."""

    def _replace(match: re.Match[str]) -> str:
        return f'{match.group(1)}: "platform-ingest-elastic-agent-{match.group(2)}-{version}"'

    updated, count = IMAGE_PIN_RE.subn(_replace, content)
    if count < 1:
        raise RuntimeError(
            "fixture pipeline has no IMAGE_* platform-ingest pins to bump "
            f"(pattern {IMAGE_PIN_RE.pattern!r})"
        )
    return updated


def required_dashboard_ids(cfg: dict[str, Any]) -> list[str]:
    raw = cfg.get("required_dashboard_ids") or [
        "obs:dependency-review",
        "obs:automerge",
        "obs:automerge:vm-images",
    ]
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("required_dashboard_ids must be a non-empty list")
    ids = [str(item).strip() for item in raw if str(item).strip()]
    if not ids:
        raise RuntimeError("required_dashboard_ids resolved empty")
    return ids


def dashboard_enables_all(repo: str, workflow_ids: list[str]) -> tuple[bool, list[str]]:
    """Return (all_enabled, missing_ids)."""
    missing = [
        workflow_id
        for workflow_id in workflow_ids
        if not estc.dashboard_enables_workflow(repo, workflow_id)
    ]
    return (not missing, missing)


def ensure_label(repo: str, label: str) -> None:
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
            "E2E fixture for obs:automerge:vm-images",
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


def seed_fixture_pipeline_on_default_branch(
    repo: str,
    *,
    default_branch: str,
    pipeline_path: Path,
) -> str | None:
    """Create the fixture pipeline on the default branch only when missing.

    Refuses to overwrite an existing remote file whose content differs (default
    branch is not a silent write target for live E2E). No-ops when content
    already matches.
    """
    if not pipeline_path.is_file():
        raise RuntimeError(f"Fixture pipeline missing at {pipeline_path}")
    content = pipeline_path.read_text(encoding="utf-8")
    remote_path = str(pipeline_path).replace("\\", "/")
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    existing = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{remote_path}?ref={default_branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if existing.returncode == 0:
        payload = json.loads(existing.stdout)
        remote_b64 = str(payload.get("content") or "").replace("\n", "")
        if remote_b64 == encoded:
            return None
        raise RuntimeError(
            f"Fixture pipeline {remote_path} already exists on {default_branch} "
            "with different content; refusing to overwrite. Update via a normal "
            "PR or align the checked-in fixture before re-running live E2E."
        )
    err = (existing.stderr or existing.stdout or "").lower()
    if existing.returncode != 0 and "404" not in err and "not found" not in err:
        raise RuntimeError(
            f"Failed to read {remote_path} on {default_branch}: "
            f"{(existing.stderr or existing.stdout or '').strip() or f'exit {existing.returncode}'}"
        )
    return estc.put_branch_file(
        repo,
        branch=default_branch,
        path=remote_path,
        content=content,
        message="chore(e2e): seed automerge vm-images fixture pipeline",
    )


def create_bump_pr(
    repo: str,
    cfg: dict[str, Any],
    *,
    version: str,
    run_id: str,
) -> dict[str, Any]:
    """Create a same-repo PR with a forced VM-image bump (playground shape)."""
    e2e = cfg.get("e2e_pr") or {}
    label = str(e2e.get("label") or FIXTURE_LABEL).strip() or FIXTURE_LABEL
    if label != FIXTURE_LABEL:
        raise RuntimeError(
            f"e2e_pr.label {label!r} must be {FIXTURE_LABEL!r} "
            "(CI skip guards require the canonical fixture label)."
        )
    branch_prefix = (
        str(e2e.get("branch_prefix") or FIXTURE_BRANCH_PREFIX).strip()
        or FIXTURE_BRANCH_PREFIX
    )
    if not branch_prefix.startswith(FIXTURE_BRANCH_PREFIX.rstrip("/")):
        raise RuntimeError(
            f"e2e_pr.branch_prefix {branch_prefix!r} must start with "
            f"{FIXTURE_BRANCH_PREFIX!r}"
        )
    if not branch_prefix.endswith("/"):
        branch_prefix = f"{branch_prefix}/"
    branch = f"{branch_prefix}{run_id}-{version}"
    pipeline_rel = str(
        cfg.get("fixture_pipeline_path") or DEFAULT_FIXTURE_PIPELINE
    ).replace("\\", "/")
    local_pipeline = Path(pipeline_rel)
    if not local_pipeline.is_file():
        raise RuntimeError(f"Fixture pipeline missing at {local_pipeline}")

    ensure_label(repo, label)
    default_branch = estc.gh_text(
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
    seed_fixture_pipeline_on_default_branch(
        repo, default_branch=default_branch, pipeline_path=local_pipeline
    )
    base_sha = estc.gh_text(
        ["api", f"repos/{repo}/git/ref/heads/{default_branch}", "--jq", ".object.sha"]
    ).strip()
    estc.gh_json(
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

    base_content = local_pipeline.read_text(encoding="utf-8")
    # Prefer remote default-branch content when present (may already be seeded).
    remote = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{pipeline_rel}?ref={default_branch}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if remote.returncode == 0:
        payload = json.loads(remote.stdout)
        remote_b64 = str(payload.get("content") or "").replace("\n", "")
        if remote_b64:
            base_content = base64.b64decode(remote_b64).decode("utf-8")

    bumped = bump_image_pins(base_content, version)
    commit_sha = estc.put_branch_file(
        repo,
        branch=branch,
        path=pipeline_rel,
        content=bumped,
        message=f"chore(e2e): bump VM image pins to {version}",
    )
    if not commit_sha:
        raise RuntimeError(
            "Forced VM-image bump produced no commit (content already matched)."
        )

    title_template = str(
        e2e.get("title_template")
        or "[main][Automation] Bump VM Image version to {version}"
    )
    title = title_template.format(version=version)
    body = str(e2e.get("body") or "").strip() or (
        "Ephemeral E2E fixture PR for obs:automerge:vm-images."
    )
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
            title,
            "--body",
            body,
            "--label",
            label,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    create_out = f"{create.stderr or ''}{create.stdout or ''}"
    if create.returncode != 0:
        raise RuntimeError(
            f"gh pr create failed: {(create.stderr or create.stdout or '').strip()}"
        )
    pr_number = estc._pr_number_from_gh_output(create.stdout or create_out)
    if pr_number is None:
        raise RuntimeError(f"Could not parse PR number from gh pr create: {create_out}")

    pr = estc.gh_json(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "number,url,headRefName,headRefOid,baseRefName,labels,state",
        ]
    )
    # REST login matches webhook / allow-list identity (not GraphQL app/…).
    author_login = rest_pr_author_login(repo, pr_number)
    return {
        "number": int(pr["number"]),
        "url": pr.get("url"),
        "headRefName": pr.get("headRefName"),
        "headRefOid": pr.get("headRefOid") or commit_sha,
        "baseRefName": pr.get("baseRefName") or default_branch,
        "author_login": author_login,
        "labels": [
            lbl.get("name") for lbl in (pr.get("labels") or []) if lbl.get("name")
        ],
        "branch": branch,
        "version": version,
        "commit_sha": commit_sha,
    }


def list_pr_trigger_runs(repo: str, workflow_file: str) -> list[dict[str, Any]]:
    runs = (
        estc.gh_json(
            [
                "run",
                "list",
                "--repo",
                repo,
                "--workflow",
                workflow_file,
                "--limit",
                "30",
                "--json",
                "databaseId,status,conclusion,event,createdAt,headSha,headBranch,url",
            ]
        )
        or []
    )
    return cast(list[dict[str, Any]], runs)


def _job_conclusion_by_exact_or_suffix(
    run_detail: dict[str, Any] | None,
    *,
    exact_names: tuple[str, ...] = (),
    endswith_suffixes: tuple[str, ...] = (),
) -> str | None:
    """Return conclusion for the first non-skipped job matching exact/suffix names.

    Prefer leaf suffixes (for example `` / automerge / automerge``) so sibling
    jobs under the same reusable call (verify, approve) cannot authorize a
    different named gate.
    """
    if not run_detail:
        return None
    exact = {n.lower() for n in exact_names}
    suffixes = tuple(s.lower() for s in endswith_suffixes)
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion in ("", "skipped"):
            continue
        if name in exact or any(name.endswith(suffix) for suffix in suffixes):
            return conclusion or None
    return None


def dependency_review_job_conclusion(
    run_detail: dict[str, Any] | None,
) -> str | None:
    """Conclusion of the dependency-review leaf job on the PR trigger run."""
    return _job_conclusion_by_exact_or_suffix(
        run_detail,
        exact_names=("dependency-review",),
        endswith_suffixes=(" / dependency-review",),
    )


def dependency_review_job_executed(run_detail: dict[str, Any] | None) -> bool:
    return dependency_review_job_conclusion(run_detail) == "success"


def automerge_job_conclusion(run_detail: dict[str, Any] | None) -> str | None:
    """Conclusion of the merge leaf job (not verify/approve wrappers).

    Nested reusable names look like
    ``run-obs-aw-pull-request / automerge / automerge``. Matching only
    `` / automerge`` would also hit verify/approve siblings.
    """
    return _job_conclusion_by_exact_or_suffix(
        run_detail,
        exact_names=("automerge",),
        endswith_suffixes=(" / automerge / automerge",),
    )


def automerge_job_executed(run_detail: dict[str, Any] | None) -> bool:
    """True when the automerge merge job (not only verify/approve) succeeded."""
    return automerge_job_conclusion(run_detail) == "success"


def approve_job_conclusion(run_detail: dict[str, Any] | None) -> str | None:
    """Conclusion of the approve leaf under the automerge reusable call."""
    return _job_conclusion_by_exact_or_suffix(
        run_detail,
        exact_names=("approve",),
        endswith_suffixes=(" / automerge / approve", " / approve"),
    )


def approve_job_executed(run_detail: dict[str, Any] | None) -> bool:
    return approve_job_conclusion(run_detail) == "success"


def wait_for_pr_route_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int],
    head_branch: str,
    require_job: str,
) -> dict[str, Any] | None:
    """Wait for a completed pull_request trigger run with a named job success.

    Poll the **caller** workflow (``trigger-obs-aw-pull-request.yml``): nested
    ``workflow_call`` jobs are listed on that run. Do not retarget config at
    ``obs-aw-event-pull-request.yml`` (``workflow_call``-only; no listable
    ``pull_request`` runs).

    ``require_job`` is ``dependency-review`` or ``automerge`` (merge leaf only).
    Skipped jobs are ignored (fail closed on pending→skipped races). Approve is
    not a substitute for the merge job.
    """
    excluded = set(exclude_run_ids)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for run in list_pr_trigger_runs(repo, workflow_file):
            run_id = int(run["databaseId"])
            if run_id in excluded:
                continue
            created = estc._parse_gh_time(run["createdAt"])
            if created < since:
                continue
            if (run.get("event") or "").lower() != "pull_request":
                continue
            if head_branch and (run.get("headBranch") or "") != head_branch:
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
                        "databaseId,status,conclusion,url,jobs,createdAt,headSha,event,headBranch",
                    ]
                )
                if detail.get("status") != "completed":
                    time.sleep(interval_seconds)
                    continue
                if require_job == "dependency-review":
                    ok = dependency_review_job_executed(detail)
                elif require_job == "automerge":
                    ok = automerge_job_executed(detail)
                else:
                    raise RuntimeError(f"unknown require_job {require_job!r}")
                if ok:
                    return cast(dict[str, Any], detail)
                excluded.add(run_id)
                break
        time.sleep(interval_seconds)
    return None


def wait_for_label(
    repo: str,
    pr_number: int,
    label: str,
    *,
    timeout_seconds: int,
    interval_seconds: int,
) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        pr = estc.gh_json(
            [
                "pr",
                "view",
                str(pr_number),
                "--repo",
                repo,
                "--json",
                "labels",
            ]
        )
        labels = [
            str(item.get("name") or "")
            for item in ((pr or {}).get("labels") or [])
            if isinstance(item, dict)
        ]
        if label in labels:
            return True
        time.sleep(interval_seconds)
    return False


def find_comment_with_marker(
    repo: str,
    pr_number: int,
    marker: str,
    *,
    since: datetime | None = None,
) -> dict[str, Any] | None:
    for comment in estc._list_issue_comments(repo, pr_number):
        if since is not None:
            created_raw = comment.get("created_at") or comment.get("createdAt") or ""
            if not created_raw:
                continue
            if estc._parse_gh_time(created_raw) < since:
                continue
        body = comment.get("body") or ""
        if marker not in body:
            continue
        login = (comment.get("user") or {}).get("login")
        return {
            "id": comment.get("id"),
            "url": comment.get("html_url"),
            "user": login,
            "created_at": comment.get("created_at"),
            "marker": marker,
        }
    return None


def wait_for_approving_review(
    repo: str,
    pr_number: int,
    *,
    timeout_seconds: int,
    interval_seconds: int,
) -> dict[str, Any] | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        reviews = (
            estc.gh_json(
                [
                    "api",
                    f"repos/{repo}/pulls/{pr_number}/reviews",
                    "--jq",
                    ".",
                ]
            )
            or []
        )
        for review in reviews:
            if not isinstance(review, dict):
                continue
            if (review.get("state") or "").upper() != "APPROVED":
                continue
            user = review.get("user") or {}
            login = str(user.get("login") or "") if isinstance(user, dict) else ""
            return {
                "id": review.get("id"),
                "user": login,
                "state": review.get("state"),
                "submitted_at": review.get("submitted_at"),
            }
        time.sleep(interval_seconds)
    return None


def wait_for_merged_or_auto_merge(
    repo: str,
    pr_number: int,
    *,
    timeout_seconds: int,
    interval_seconds: int,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last: dict[str, Any] = {}
    while time.time() < deadline:
        pr = estc.gh_json(
            [
                "pr",
                "view",
                str(pr_number),
                "--repo",
                repo,
                "--json",
                "state,mergedAt,autoMergeRequest,mergeStateStatus",
            ]
        )
        last = cast(dict[str, Any], pr or {})
        if (last.get("state") or "").upper() == "MERGED" or last.get("mergedAt"):
            return {
                "merged": True,
                "auto_merge_enabled": False,
                "merged_at": last.get("mergedAt"),
                "merge_state_status": last.get("mergeStateStatus"),
            }
        auto = last.get("autoMergeRequest")
        if isinstance(auto, dict) and auto:
            return {
                "merged": False,
                "auto_merge_enabled": True,
                "merged_at": None,
                "merge_state_status": last.get("mergeStateStatus"),
                "auto_merge_request": auto,
            }
        time.sleep(interval_seconds)
    return {
        "merged": False,
        "auto_merge_enabled": False,
        "merged_at": None,
        "merge_state_status": last.get("mergeStateStatus"),
        "timed_out": True,
    }


def run_live_case(
    case_dir: Path,
    cfg: dict[str, Any],
    *,
    run_url: str | None = None,
) -> dict[str, Any]:
    case = _load_json(case_dir / "case.json")
    estc.require_case_mode(case, "live", case_id=str(case.get("id", case_dir.name)))
    trigger = case.get("trigger") or {}
    expectations = case.get("expectations") or {}
    repo = str(cfg.get("consumer_repo") or "elastic/oblt-aw")
    workflow_id = str(case.get("workflow_id") or cfg.get("workflow_id") or WORKFLOW_ID)
    workflow_file = str(
        cfg.get("pull_request_trigger_workflow_file")
        or "trigger-obs-aw-pull-request.yml"
    )
    merge_ready_label = str(cfg.get("merge_ready_label") or "oblt-aw/ai/merge-ready")
    gate_marker = str(
        cfg.get("dependency_collection_gate_marker")
        or "<!-- obs-aw-automerge:dependency-collection-gate -->"
    )
    outcome_marker = str(
        cfg.get("automerge_outcome_gate_marker")
        or "<!-- obs-aw-automerge:outcome-gate -->"
    )
    dr_markers = list(
        expectations.get("dependency_review_comment_markers")
        or cfg.get("dependency_review_comment_markers")
        or ["Labels Applied"]
    )
    allowed_author = str(cfg.get("allowed_pr_author") or ALLOWED_AUTHOR)
    timeout = int(cfg.get("poll_timeout_seconds") or 3600)
    interval = int(cfg.get("poll_interval_seconds") or 20)
    dash_ids = required_dashboard_ids(cfg)

    fixture_meta: dict[str, Any] = {
        "label": FIXTURE_LABEL,
        "branch_prefix": FIXTURE_BRANCH_PREFIX,
    }
    dashboard_ok = False
    pr_info: dict[str, Any] | None = None

    if not trigger.get("require_open_pr", True):
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                "Live E2E requires an open fixture PR "
                "(trigger.require_open_pr must be true)."
            ),
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "run_url": run_url,
        }
    if not trigger.get("force_vm_image_bump", True):
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                "Live E2E requires trigger.force_vm_image_bump so the harness "
                "opens a playground-shaped IMAGE pin PR."
            ),
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "run_url": run_url,
        }

    try:
        dashboard_ok, missing = dashboard_enables_all(repo, dash_ids)
        if expectations.get("dashboard_enabled") and not dashboard_ok:
            return {
                "workflow_id": workflow_id,
                "case_id": case.get("id", case_dir.name),
                "layer": "e2e",
                "mode": "live",
                "agent_invoked": False,
                "blocked": True,
                "block_reason": (
                    f"Dashboard missing required ids on {repo}: {missing}. "
                    "Enable obs:dependency-review, obs:automerge, and "
                    "obs:automerge:vm-images on the Control Plane Dashboard, "
                    "then re-run."
                ),
                "path_gates": {
                    "dashboard_enabled": False,
                    "missing_dashboard_ids": missing,
                },
                "expectations": expectations,
                "run_url": run_url,
            }

        version = str(int(time.time()))
        run_id = os.environ.get("GITHUB_RUN_ID") or str(int(time.time()))
        since = _utc_now().replace(microsecond=0)
        known_run_ids = {
            int(run["databaseId"]) for run in list_pr_trigger_runs(repo, workflow_file)
        }

        pr_info = create_bump_pr(repo, cfg, version=version, run_id=run_id)
        fixture_meta.update(
            {
                "pr_number": pr_info["number"],
                "pr_url": pr_info.get("url"),
                "branch": pr_info.get("branch"),
                "version": version,
            }
        )
        author = str(pr_info.get("author_login") or "")
        if (
            trigger.get("require_github_actions_author", True)
            and author != allowed_author
        ):
            return {
                "workflow_id": workflow_id,
                "case_id": case.get("id", case_dir.name),
                "layer": "e2e",
                "mode": "live",
                "agent_invoked": False,
                "blocked": True,
                "block_reason": (
                    f"Fixture PR author is {author!r}, expected {allowed_author!r} "
                    "(REST user.login). Run this harness under GitHub Actions with "
                    "GITHUB_TOKEN so Contents API commits and gh pr create are "
                    "authored as github-actions[bot] (matches updatecli)."
                ),
                "path_gates": {"dashboard_enabled": dashboard_ok},
                "fixture": fixture_meta,
                "pr_number": pr_info["number"],
                "commit_sha": pr_info.get("commit_sha"),
                "expectations": expectations,
                "run_url": run_url,
            }

        head_branch = str(pr_info.get("headRefName") or pr_info.get("branch") or "")
        dr_run: dict[str, Any] | None = None
        if trigger.get("wait_dependency_review", True):
            estc.log_info(
                f"Waiting for dependency-review on {workflow_file} "
                f"(PR #{pr_info['number']}, branch {head_branch})…"
            )
            dr_run = wait_for_pr_route_run(
                repo,
                workflow_file,
                since=since,
                timeout_seconds=timeout,
                interval_seconds=interval,
                exclude_run_ids=known_run_ids,
                head_branch=head_branch,
                require_job="dependency-review",
            )
            if dr_run is None:
                raise TimeoutError(
                    f"No successful dependency-review job on {workflow_file} "
                    f"within {timeout}s for PR #{pr_info['number']}."
                )
            known_run_ids.add(int(dr_run["databaseId"]))

        merge_ready = wait_for_label(
            repo,
            int(pr_info["number"]),
            merge_ready_label,
            timeout_seconds=min(900, timeout),
            interval_seconds=interval,
        )
        if expectations.get("merge_ready_label_applied") and not merge_ready:
            raise TimeoutError(
                f"Label {merge_ready_label!r} was not applied to PR "
                f"#{pr_info['number']} within timeout after dependency-review."
            )

        dr_comment = None
        if expectations.get("dependency_review_comment"):
            comment_deadline = time.time() + min(900, timeout)
            while time.time() < comment_deadline and dr_comment is None:
                dr_comment = estc.find_agent_comment(
                    repo,
                    int(pr_info["number"]),
                    since=since,
                    markers=dr_markers,
                )
                if dr_comment:
                    break
                time.sleep(interval)

        gate_comment = find_comment_with_marker(
            repo, int(pr_info["number"]), gate_marker, since=since
        )

        am_run: dict[str, Any] | None = None
        if trigger.get("wait_automerge", True) and merge_ready:
            estc.log_info(
                f"Waiting for automerge route on {workflow_file} "
                f"(PR #{pr_info['number']})…"
            )
            # labeled event starts a new run after merge-ready is applied
            am_since = _utc_now().replace(microsecond=0)
            am_run = wait_for_pr_route_run(
                repo,
                workflow_file,
                since=am_since,
                timeout_seconds=timeout,
                interval_seconds=interval,
                exclude_run_ids=known_run_ids,
                head_branch=head_branch,
                require_job="automerge",
            )
            if am_run is None:
                # Also accept a run that started slightly before label poll ended.
                am_run = wait_for_pr_route_run(
                    repo,
                    workflow_file,
                    since=since,
                    timeout_seconds=interval * 3,
                    interval_seconds=interval,
                    exclude_run_ids=known_run_ids,
                    head_branch=head_branch,
                    require_job="automerge",
                )
            if am_run is None:
                raise TimeoutError(
                    f"No successful automerge/approve job on {workflow_file} "
                    f"within {timeout}s for PR #{pr_info['number']}."
                )

        review = wait_for_approving_review(
            repo,
            int(pr_info["number"]),
            timeout_seconds=min(600, timeout),
            interval_seconds=interval,
        )
        merge_state = wait_for_merged_or_auto_merge(
            repo,
            int(pr_info["number"]),
            timeout_seconds=min(900, timeout),
            interval_seconds=interval,
        )
        outcome_gate = find_comment_with_marker(
            repo, int(pr_info["number"]), outcome_marker, since=since
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
        if pr_info is not None:
            blocked["pr_number"] = pr_info.get("number")
            blocked["commit_sha"] = pr_info.get("commit_sha")
            blocked["pr_url"] = pr_info.get("url")
        return blocked

    path_gates = {
        "dashboard_enabled": dashboard_ok,
        "has_open_or_merged_pr": True,
        "author_is_github_actions": author == allowed_author,
    }

    return {
        "workflow_id": workflow_id,
        "case_id": case.get("id", case_dir.name),
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": bool(dr_run),
        "blocked": False,
        "consumer_repo": repo,
        "commit_sha": pr_info.get("commit_sha"),
        "pr_number": pr_info["number"],
        "pr_url": pr_info.get("url"),
        "pr_head_branch": head_branch,
        "pr_base_branch": pr_info.get("baseRefName"),
        "pr_author": author,
        "fixture": fixture_meta,
        "trigger": trigger,
        "dependency_review": {
            "run_seen": dr_run is not None,
            "job_executed": dependency_review_job_executed(dr_run),
            "job_conclusion": dependency_review_job_conclusion(dr_run),
            "run_id": (dr_run or {}).get("databaseId"),
            "url": (dr_run or {}).get("url"),
        },
        "merge_ready_label": {
            "name": merge_ready_label,
            "applied": merge_ready,
        },
        "dependency_review_comment": dr_comment,
        "dependency_collection_gate_comment": gate_comment,
        "automerge": {
            "run_seen": am_run is not None,
            "job_executed": automerge_job_executed(am_run),
            "approve_job_executed": approve_job_executed(am_run),
            "job_conclusion": automerge_job_conclusion(am_run),
            "run_id": (am_run or {}).get("databaseId"),
            "url": (am_run or {}).get("url"),
        },
        "approving_review": review,
        "merge": merge_state,
        "automerge_outcome_gate_comment": outcome_gate,
        "path_gates": path_gates,
        "expectations": expectations,
        "run_url": run_url,
        "harness_notes": [
            (
                "Happy path: forced IMAGE pin bump (playground/updatecli shape) → "
                "trigger-obs-aw-pull-request → dependency-review → "
                "oblt-aw/ai/merge-ready → automerge approve/merge."
            ),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run obs:automerge:vm-images live E2E harness."
    )
    parser.add_argument(
        "--case-id",
        default="vm-images-bump-live",
        help="Case directory name under testdata/.../cases/",
    )
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/automerge-vm-images"),
        help="Root of automerge vm-images live E2E cases",
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
        help="Where to write outcome.json",
    )
    parser.add_argument(
        "--run-url",
        default=os.environ.get("RUN_URL") or "",
        help="Outer E2E workflow run URL",
    )
    args = parser.parse_args(argv)

    cfg = load_e2e_config(args.config_path)
    case_dir = args.testdata_root / "cases" / args.case_id
    if not (case_dir / "case.json").is_file():
        raise SystemExit(f"Missing case.json under {case_dir}")

    args.outcome_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        outcome = run_live_case(
            case_dir,
            cfg,
            run_url=args.run_url or None,
        )
    except (RuntimeError, TimeoutError, TypeError, ValueError, OSError) as exc:
        estc.log_error(str(exc))
        outcome = {
            "workflow_id": WORKFLOW_ID,
            "case_id": args.case_id,
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": str(exc),
            "path_gates": {"dashboard_enabled": False},
            "run_url": args.run_url or None,
        }

    args.outcome_path.write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if outcome.get("blocked"):
        estc.log_error(str(outcome.get("block_reason") or "blocked"))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
