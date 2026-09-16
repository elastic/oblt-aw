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
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

WORKFLOW_ID = "obs:estc-pr-buildkite-detective"
DEFAULT_CONFIG = Path("config/obs/e2e-estc-pr-buildkite-detective.json")
FAIL_STATES = ("failed", "timed_out")
MARKER_PATH = "testdata/agentic/estc-pr-buildkite-detective/e2e-fixture-pr.md"
MARKER_BODY = (
    "# E2E fixture PR\n\n"
    "Kept open for live status→agent E2E of "
    "`obs:estc-pr-buildkite-detective`. Do not merge.\n"
)
DEFAULT_FIXTURE_TITLE = "[e2e] ESTC detective fixture"
DEFAULT_FIXTURE_BODY = (
    "Long-lived fixture PR for `obs:estc-pr-buildkite-detective`. Do not merge."
)
FAIL_PIPELINE_PATH = Path(".buildkite/pipeline.e2e-estc-fail.yml")
# Default GitHub status from Buildkite publish_commit_status (buildkite/<pipeline>).
DEFAULT_STATUS_CONTEXT_TEMPLATE = "buildkite/{pipeline}"
# Long-lived fixture branch (shared; workflow concurrency serializes live runs).
FIXTURE_BRANCH = "e2e/estc-pr-buildkite-detective"
FIXTURE_LABEL = "e2e:estc-pr-buildkite-detective"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_gh_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _running_in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def log_info(message: str) -> None:
    print(message, flush=True)


def log_error(message: str) -> None:
    """Print a failure line; emit a GitHub Actions error annotation when applicable."""
    if _running_in_github_actions():
        # Actions annotations are single-line; keep the first line primary.
        first = message.splitlines()[0] if message else "E2E harness error"
        print(f"::error::{first}", flush=True)
    print(message, file=sys.stderr, flush=True)


def summarize_commit_statuses(
    statuses: list[dict[str, Any]], *, limit: int = 12
) -> str:
    """Compact one-line-per-status dump for timeout diagnostics."""
    if not statuses:
        return "(none)"
    lines: list[str] = []
    for status in statuses[:limit]:
        ctx = status.get("context") or "?"
        state = status.get("state") or "?"
        url = status.get("target_url") or ""
        creator = ""
        raw_creator = status.get("creator")
        if isinstance(raw_creator, dict):
            creator = str(raw_creator.get("login") or "")
        created = status.get("created_at") or ""
        lines.append(
            f"- context={ctx!r} state={state!r} creator={creator!r} "
            f"created_at={created!r} target_url={url!r}"
        )
    if len(statuses) > limit:
        lines.append(f"- … {len(statuses) - limit} more")
    return "\n".join(lines)


def require_routable_buildkite_status_context(context: str) -> str:
    """Reject status contexts that cannot match trigger-obs-aw-status routing.

    Client/control-plane status triggers only run when the context contains the
    lowercase substring ``buildkite``.
    """
    ctx = str(context or "").strip()
    if not ctx:
        raise RuntimeError(
            "expected Buildkite status context is empty; derive "
            "buildkite/<pipeline> from the resolved fail pipeline."
        )
    if "buildkite" not in ctx.lower():
        raise RuntimeError(
            f"status context {ctx!r} does not contain 'buildkite'; "
            "trigger-obs-aw-status.yml / obs-aw-event-status.yml will not route it. "
            "Use Buildkite's default publish context (buildkite/<pipeline>)."
        )
    return ctx


def expected_buildkite_status_context(cfg: dict[str, Any]) -> str:
    """GitHub status context Buildkite ``publish_commit_status`` will emit.

    Always ``buildkite/<resolved pipeline>`` (catalog publisher). Optional
    ``expected_status_context`` / ``status_context`` must match exactly or the
    harness fails closed. Non-default ``status_context_template`` is rejected.
    """
    template = str(cfg.get("status_context_template") or "").strip()
    if template and template != DEFAULT_STATUS_CONTEXT_TEMPLATE:
        raise RuntimeError(
            f"status_context_template {template!r} is not allowed; "
            "Buildkite publish_commit_status always emits "
            f"{DEFAULT_STATUS_CONTEXT_TEMPLATE!r} "
            "(buildkite/<pipeline>). Remove the template override."
        )
    _, pipeline = resolve_buildkite_org_pipeline(cfg)
    derived = require_routable_buildkite_status_context(f"buildkite/{pipeline}")
    override = str(
        cfg.get("expected_status_context") or cfg.get("status_context") or ""
    ).strip()
    if override and override != derived:
        raise RuntimeError(
            f"status context override {override!r} does not match Buildkite "
            f"publish context {derived!r} for resolved pipeline {pipeline!r}. "
            "Remove the override or align E2E_BUILDKITE_PIPELINE / config "
            "defaults (publish_commit_status emits buildkite/<pipeline> only)."
        )
    return derived


def normalize_e2e_pr_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return cfg with the canonical long-lived fixture PR fields filled in."""
    e2e = dict(cfg.get("e2e_pr") or {})
    configured_label = str(e2e.get("label") or "").strip()
    if configured_label and configured_label != FIXTURE_LABEL:
        raise RuntimeError(
            f"e2e_pr.label {configured_label!r} must be {FIXTURE_LABEL!r} "
            "(CI/agent skip guards require the canonical fixture label)."
        )
    branch = str(e2e.get("branch") or FIXTURE_BRANCH).strip()
    if branch != FIXTURE_BRANCH:
        raise RuntimeError(
            f"e2e_pr.branch {branch!r} must be the long-lived fixture "
            f"{FIXTURE_BRANCH!r}."
        )
    e2e["label"] = FIXTURE_LABEL
    e2e["branch"] = FIXTURE_BRANCH
    e2e["title"] = str(e2e.get("title") or "").strip() or DEFAULT_FIXTURE_TITLE
    e2e["body"] = str(e2e.get("body") or "").strip() or DEFAULT_FIXTURE_BODY
    out = dict(cfg)
    out["e2e_pr"] = e2e
    return out


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


def commit_sha_from_contents_put(payload: Any) -> str:
    """Extract the new commit SHA from a GitHub Contents API PUT response."""
    if not isinstance(payload, dict):
        raise TypeError(
            f"Contents PUT response must be a mapping, got {type(payload).__name__}"
        )
    commit = payload.get("commit")
    if not isinstance(commit, dict):
        raise TypeError(
            "Contents PUT response missing commit object; cannot bind Buildkite "
            "build to the fixture tip."
        )
    sha = str(commit.get("sha") or "").strip()
    if not sha:
        raise RuntimeError(
            "Contents PUT response missing commit.sha; cannot bind Buildkite "
            "build to the fixture tip."
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


def _notify_github_commit_status_contexts(notify: Any) -> list[str]:
    """Extract ``github_commit_status.context`` values from a notify list."""
    if notify is None:
        return []
    if not isinstance(notify, list):
        raise TypeError(f"Buildkite notify must be a list, got {type(notify).__name__}")
    contexts: list[str] = []
    for item in notify:
        if not isinstance(item, dict) or "github_commit_status" not in item:
            continue
        gcs = item.get("github_commit_status")
        if not isinstance(gcs, dict):
            raise TypeError(
                "github_commit_status notify entry must be a mapping with context"
            )
        ctx = str(gcs.get("context") or "").strip()
        if not ctx:
            raise RuntimeError(
                "github_commit_status notify entry is missing a non-empty context"
            )
        contexts.append(ctx)
    return contexts


def fail_pipeline_github_commit_status_contexts(
    content: str, *, pipeline_path: Path | str = FAIL_PIPELINE_PATH
) -> list[str]:
    """Assert fail-pipeline YAML has no github_commit_status notify entries.

    Statuses come from catalog ``publish_commit_status``. Any pipeline- or
    step-level ``github_commit_status`` notify can double-fire the detective.
    Parses YAML so comment-only mentions cannot pass or fail the gate.
    Returns an empty list when the pipeline is clean.
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise RuntimeError(f"{pipeline_path} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise TypeError(f"{pipeline_path} must parse to a mapping")
    contexts = _notify_github_commit_status_contexts(data.get("notify"))
    if contexts:
        raise RuntimeError(
            f"{pipeline_path} must not declare pipeline-level github_commit_status "
            f"notify (found {contexts}); statuses come from "
            "publish_commit_status (buildkite/<pipeline>). Extra notify contexts "
            "double-fire trigger-obs-aw-status.yml."
        )
    steps = data.get("steps") or []
    if isinstance(steps, list):
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            step_contexts = _notify_github_commit_status_contexts(step.get("notify"))
            if step_contexts:
                raise RuntimeError(
                    f"{pipeline_path} step[{idx}] declares github_commit_status "
                    f"context(s) {step_contexts}; do not use notify — "
                    "publish_commit_status alone must publish the status."
                )
    return []


def assert_fail_pipeline_status_context_matches(
    cfg: dict[str, Any],
    *,
    pipeline_path: Path | None = None,
) -> str:
    """Ensure fail-pipeline YAML has no notify and return the expected status context."""
    path = pipeline_path if pipeline_path is not None else FAIL_PIPELINE_PATH
    if not path.is_file():
        raise RuntimeError(
            f"Fail pipeline YAML missing at {path}; cannot validate notify."
        )
    content = path.read_text(encoding="utf-8")
    fail_pipeline_github_commit_status_contexts(content, pipeline_path=path)
    return expected_buildkite_status_context(cfg)


def sync_fail_pipeline_to_fixture_branch(
    repo: str,
    *,
    branch: str,
    pipeline_path: Path | None = None,
    expected_context: str | None = None,
) -> str | None:
    """Ensure the fixture branch tip includes the fail-pipeline YAML from this checkout.

    Buildkite uploads ``.buildkite/pipeline.e2e-estc-fail.yml`` from the build
    commit. ``expected_context`` is accepted for call-site compatibility; status
    publish comes from catalog ``publish_commit_status``, not YAML notify.

    Returns the Contents API commit SHA when a sync commit was made, or ``None``
    when the remote file was already current. Callers must use that SHA for the
    Buildkite build / status wait — do not re-read ``headRefOid`` from the PR
    API after a write (it can lag and leave the status on a non-HEAD commit).
    """
    path = pipeline_path if pipeline_path is not None else FAIL_PIPELINE_PATH
    if not path.is_file():
        raise RuntimeError(
            f"Fail pipeline YAML missing at {path}; cannot sync fixture branch."
        )
    content = path.read_text(encoding="utf-8")
    fail_pipeline_github_commit_status_contexts(content, pipeline_path=path)
    if expected_context is not None:
        require_routable_buildkite_status_context(expected_context)
    # Always write under the canonical repo path so Buildkite's pipeline upload
    # finds the file on the fixture commit (local tmp paths must not leak).
    remote_path = str(FAIL_PIPELINE_PATH).replace("\\", "/")
    synced_sha = put_branch_file(
        repo,
        branch=branch,
        path=remote_path,
        content=content,
        message="chore(e2e): sync ESTC fail pipeline onto fixture branch",
    )
    if synced_sha:
        log_info(
            f"Synced {remote_path} onto {repo}@{branch} "
            f"(commit {synced_sha[:12]}) for Buildkite fail pipeline."
        )
    else:
        log_info(f"{remote_path} already current on {repo}@{branch}.")
    return synced_sha


def load_e2e_config(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"E2E config must be a JSON object: {path}")
    return normalize_e2e_pr_config(data)


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


def _gh_pr_list_head_filter(branch: str) -> str:
    """Return ``gh pr list --head`` value for a same-repo branch.

    ``gh`` expects the bare branch name for same-repo heads. The
    ``owner:branch`` form returns an empty list for in-repo PRs (verified
    against ``elastic/oblt-aw`` fixture branch lookups).
    """
    return branch


def _pr_number_from_gh_output(text: str) -> int | None:
    """Parse a pull request number from ``gh pr create`` stdout/stderr."""
    match = re.search(r"/pull/(\d+)\b", text)
    if not match:
        return None
    return int(match.group(1))


def _list_prs_by_head(
    repo: str, *, branch: str, state: str, limit: int = 5
) -> list[dict[str, Any]]:
    """List same-repo PRs on ``branch`` with the given ``state``."""
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
    """Return the open same-repo PR with ``label`` on ``branch``, or None."""
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
            "ESTC detective E2E fixture PR (long-lived)",
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


def _find_closed_fixture_pr(
    repo: str, *, branch: str, label: str
) -> dict[str, Any] | None:
    """Most recent closed same-repo PR on the fixture branch with ``label``.

    Unlabeled closed PRs on a reserved branch are ignored so reopen never
    treats an unrelated PR as the fixture.
    """
    matched = _list_prs_by_head(repo, branch=branch, state="closed", limit=5)
    labeled = [pr for pr in matched if _pr_has_label(pr, label)]
    return labeled[0] if labeled else None


def ensure_e2e_pr(repo: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Find, reopen, or create the long-lived E2E fixture PR via the GitHub API.

    Reuses an existing open PR on the fixture branch, or reopens a closed one
    on the same branch. Never closes or deletes the fixture.
    """
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
    create_out = f"{create.stderr or ''}{create.stdout or ''}"
    if create.returncode == 0:
        # Prefer the create URL over label search (label index can lag).
        created_number = _pr_number_from_gh_output(create.stdout or create_out)
        if created_number is not None:
            return _require_pr_label(repo, created_number, label)
    elif "already exists" not in create_out.lower():
        # Fall through to reopen / label recovery below.
        pass

    created = find_open_e2e_pr(repo, label, branch=branch)
    if created:
        return _require_pr_label(repo, int(created["number"]), label)

    # Closed fixture PR on the same branch: reopen (create may have failed).
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
    started = time.time()
    attempt = 0
    log_info(
        f"Waiting up to {timeout_seconds}s for GitHub commit status "
        f"context={context!r} state={state!r} target_url={target_url!r} "
        f"on {sha[:12]}…"
    )
    while time.time() < deadline:
        attempt += 1
        statuses = list_commit_statuses(repo, sha)
        matched = match_commit_status(
            statuses,
            context=context,
            state=state,
            target_url=target_url,
            since=since,
        )
        if matched:
            log_info(
                f"Observed matching commit status after {int(time.time() - started)}s "
                f"(attempt {attempt})."
            )
            return matched
        if attempt == 1 or attempt % 3 == 0:
            remaining = max(0, int(deadline - time.time()))
            log_info(
                f"Status not yet matched (attempt {attempt}, {remaining}s left). "
                f"Current statuses on {sha[:12]}:\n"
                f"{summarize_commit_statuses(statuses)}"
            )
        time.sleep(interval_seconds)
    return None


def commit_status_timeout_block_reason(
    *,
    repo: str,
    sha: str,
    context: str,
    state: str,
    target_url: str | None,
    timeout_seconds: int,
) -> str:
    """Build a block_reason that includes the statuses actually present on the SHA."""
    try:
        statuses = list_commit_statuses(repo, sha)
        snapshot = summarize_commit_statuses(statuses)
    except (RuntimeError, TypeError, ValueError, OSError) as exc:
        snapshot = f"(failed to list statuses: {exc})"
    return (
        f"Timed out after {timeout_seconds}s waiting for GitHub commit status "
        f"context={context!r} state={state!r} target_url={target_url!r} "
        f"on {sha}. Buildkite should publish this via provider_settings "
        f"publish_commit_status (default context buildkite/<pipeline>); without it "
        f"the live status→agent path cannot run. "
        f"Statuses observed on the SHA:\n{snapshot}"
    )


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
    """Wait for a workflow run created after ``since`` that executed the status job.

    Correlates by excluding known run IDs and optional ``event`` (default
    ``status``). Does **not** filter on ``headSha``: status-triggered runs use
    the default-branch tip as ``GITHUB_SHA`` / run ``headSha``, while the status
    commit is ``github.event.sha``.

    Skipped status-route jobs (typical for Buildkite ``pending`` statuses that
    still fire ``on: status``) are ignored so the harness does not bind to them
    before the failure-triggered run completes.

    Returns ``None`` if no matching completed run with a successful status-route
    job appears before the deadline (in-progress matches are not treated as seen).
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
                if detail.get("status") != "completed":
                    time.sleep(interval_seconds)
                    continue
                # Fail closed: only bind when the named status-route job succeeded.
                # Pending→skipped runs complete first and must not win the race.
                if status_job_executed(detail):
                    return cast(dict[str, Any], detail)
                excluded.add(run_id)
                break
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
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "run_url": run_url,
        }

    dashboard_ok = False
    sha: str | None = None
    target_pr_number: int | None = None
    buildkite_meta: dict[str, Any] = {}
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

        # Capture before Buildkite create so we observe the status-triggered run.
        since = _utc_now().replace(microsecond=0)
        workflow_file_early = str(
            cfg.get("status_trigger_workflow_file") or "trigger-obs-aw-status.yml"
        )
        known_run_ids = {
            int(run["databaseId"])
            for run in list_status_trigger_runs(repo, workflow_file_early)
        }

        expected_ctx = assert_fail_pipeline_status_context_matches(cfg)
        if not buildkite_api_token(cfg):
            bk = _buildkite_cfg(cfg)
            token_env = str(bk.get("token_env") or "BUILDKITE_TOKEN")
            raise RuntimeError(f"Missing {token_env} (write_builds + read).")
        if e2e_branch:
            synced_sha = sync_fail_pipeline_to_fixture_branch(
                repo,
                branch=e2e_branch,
                expected_context=expected_ctx,
            )
            if synced_sha:
                # Bind Buildkite to the Contents PUT tip. Re-resolving the PR
                # head OID after sync can return the pre-sync SHA and leave the
                # commit status on a non-HEAD commit (invisible in PR Checks).
                sha = synced_sha
        target_url, buildkite_meta = ensure_failed_buildkite_target_url(
            cfg,
            commit=sha,
            branch=e2e_branch or str(cfg.get("e2e_pr", {}).get("branch") or "main"),
            pr_number=target_pr_number,
            case_id=str(case.get("id", case_dir.name)),
        )

        state = str(trigger.get("status_state") or "failure")
        timeout = int(cfg.get("poll_timeout_seconds") or 2400)
        interval = int(cfg.get("poll_interval_seconds") or 20)
        context = expected_buildkite_status_context(cfg)
        status_timeout = int(
            cfg.get("status_observe_timeout_seconds") or min(300, timeout)
        )
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
                "block_reason": commit_status_timeout_block_reason(
                    repo=repo,
                    sha=sha,
                    context=context,
                    state=state,
                    target_url=target_url,
                    timeout_seconds=status_timeout,
                ),
                "path_gates": {"dashboard_enabled": dashboard_ok},
                "buildkite": buildkite_meta,
                "fixture": fixture_meta,
                "commit_sha": sha,
                "pr_number": target_pr_number,
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
        if run_detail is None:
            raise TimeoutError(
                f"No successful status-route run for {workflow_file_early!r} "
                f"within {timeout}s after the Buildkite failure status "
                f"(commit {sha}, context {context!r})."
            )

        job_executed = status_job_executed(run_detail)
        job_conclusion = status_job_conclusion(run_detail)
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
        if buildkite_meta:
            blocked["buildkite"] = buildkite_meta
        if sha is not None:
            blocked["commit_sha"] = sha
        if target_pr_number is not None:
            blocked["pr_number"] = target_pr_number
        return blocked

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
        "pr_number": target_pr_number,
        "pr_url": pr_info.get("url"),
        "pr_head_branch": e2e_branch,
        "pr_base_branch": resolved_base,
        "fixture": fixture_meta,
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
                "Happy path only: long-lived fixture PR → intentional Buildkite "
                "failure → Buildkite publishes GitHub commit status → "
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
    buildkite = outcome.get("buildkite")
    if isinstance(buildkite, dict) and buildkite:
        summary["buildkite"] = {
            k: buildkite.get(k)
            for k in (
                "source",
                "web_url",
                "state",
                "number",
                "org",
                "pipeline",
                "fail_log_marker_verified",
            )
            if k in buildkite
        }
    status = outcome.get("status")
    if isinstance(status, dict) and status:
        summary["status"] = {
            k: status.get(k)
            for k in ("state", "context", "target_url", "publisher")
            if k in status
        }
    print(json.dumps(summary, indent=2), flush=True)

    if outcome.get("blocked"):
        reason = str(outcome.get("block_reason") or "blocked")
        log_error(f"E2E harness blocked: {reason}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
