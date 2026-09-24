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

"""Live E2E harness for obs:dependency-review.

Creates an ephemeral same-repo PR that bumps a pinned ``actions/checkout`` SHA
in a fixture workflow, authored as the Vault app via OIDC create-token (avoids
the github-actions[bot] pull_request approval gate), then waits for
dependency-review → analysis comment → merge-ready. Does **not** wait for
automerge/approve/merge.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# scripts/ siblings (e.g. get_enabled_workflows via shared ESTC helpers) when this
# file lives under scripts/obs/e2e/.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_E2E_DIR = Path(__file__).resolve().parent
for _path in (_E2E_DIR, _SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Reuse shared gh / Contents helpers from the ESTC harness and PR-route waiters
# from the automerge harness.
import automerge_vm_images_e2e_harness as automerge
import estc_pr_buildkite_detective_e2e_harness as estc

WORKFLOW_ID = "obs:dependency-review"
DEFAULT_CONFIG = Path("config/obs/e2e-dependency-review.json")
DEFAULT_FIXTURE_WORKFLOW = Path(
    ".github/workflows/e2e-dependency-review-actions-fixture.yml"
)
FIXTURE_LABEL = "e2e:dependency-review"
FIXTURE_BRANCH_PREFIX = "e2e/dependency-review/"
# Seed pin on default branch (actions/checkout v4.2.2).
SEED_CHECKOUT_SHA = "11bd71901bbe5b1630ceea73d27597364c9af683"
SEED_CHECKOUT_VERSION = "v4.2.2"
# Bump target on the fixture PR (actions/checkout v4.3.0).
BUMP_CHECKOUT_SHA = "08eba0b27e820071cde6df949e0beb9ba4906955"
BUMP_CHECKOUT_VERSION = "v4.3.0"
CHECKOUT_PIN_RE = re.compile(
    r"(uses:\s*actions/checkout@)([0-9a-f]{40})(\s*#\s*)(v[\w.]+)"
)
ALLOWED_AUTHOR = "elastic-vault-github-plugin-prod[bot]"

# Re-export shared helpers for unit tests / callers.
rest_pr_author_login = automerge.rest_pr_author_login
author_login_from_rest_pull = automerge.author_login_from_rest_pull
dashboard_enables_all = automerge.dashboard_enables_all
wait_for_pr_route_run = automerge.wait_for_pr_route_run
DEPENDENCY_REVIEW_CONCLUSION_LEAF_SUFFIX = (
    automerge.DEPENDENCY_REVIEW_CONCLUSION_LEAF_SUFFIX
)
dependency_review_job_conclusion = automerge.dependency_review_job_conclusion
dependency_review_job_executed = automerge.dependency_review_job_executed
dependency_review_matched_job_name = automerge.dependency_review_matched_job_name
wait_for_label = automerge.wait_for_label
find_comment_with_marker = automerge.find_comment_with_marker
list_pr_trigger_runs = automerge.list_pr_trigger_runs


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _trigger_bool(
    trigger: dict[str, Any],
    key: str,
    *,
    default: bool,
    aliases: tuple[str, ...] = (),
) -> bool:
    for candidate in (key, *aliases):
        if candidate not in trigger:
            continue
        value = trigger[candidate]
        if isinstance(value, bool):
            return value
        raise TypeError(
            f"trigger {candidate!r} must be bool, got {type(value).__name__}: {value!r}"
        )
    return default


def load_e2e_config(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"E2E config must be a JSON object: {path}")
    return data


def bump_checkout_pin(content: str, *, sha: str, version: str) -> str:
    """Replace the ``actions/checkout@<SHA> # vX.Y.Z`` pin in fixture YAML."""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError(f"checkout bump sha must be a 40-char hex commit: {sha!r}")
    if not version.startswith("v"):
        raise RuntimeError(f"checkout version comment must start with 'v': {version!r}")

    def _replace(match: re.Match[str]) -> str:
        return f"{match.group(1)}{sha}{match.group(3)}{version}"

    updated, count = CHECKOUT_PIN_RE.subn(_replace, content)
    if count < 1:
        raise RuntimeError(
            "fixture workflow has no actions/checkout@<SHA> # vX.Y.Z pin to bump "
            f"(pattern {CHECKOUT_PIN_RE.pattern!r})"
        )
    if count > 1:
        raise RuntimeError(
            f"fixture workflow has {count} actions/checkout pins; expected exactly one"
        )
    return updated


def required_dashboard_ids(cfg: dict[str, Any]) -> list[str]:
    raw = cfg.get("required_dashboard_ids") or ["obs:dependency-review"]
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("required_dashboard_ids must be a non-empty list")
    ids = [str(item).strip() for item in raw if str(item).strip()]
    if not ids:
        raise RuntimeError("required_dashboard_ids resolved empty")
    return ids


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
            "E2E fixture for obs:dependency-review",
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


def seed_fixture_workflow_on_default_branch(
    repo: str,
    *,
    default_branch: str,
    workflow_path: Path,
) -> str | None:
    """Create the fixture workflow on the default branch only when missing.

    Refuses to overwrite an existing remote file whose content differs (default
    branch is not a silent write target for live E2E). No-ops when content
    already matches.
    """
    if not workflow_path.is_file():
        raise RuntimeError(f"Fixture workflow missing at {workflow_path}")
    content = workflow_path.read_text(encoding="utf-8")
    remote_path = str(workflow_path).replace("\\", "/")
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
            f"Fixture workflow {remote_path} already exists on {default_branch} "
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
        message="chore(e2e): seed dependency-review Actions pin fixture workflow",
    )


def delete_fixture_branch(repo: str, branch: str) -> None:
    """Delete a fixture head branch ref (best-effort helpers call this on rollback)."""
    delete = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "DELETE",
            f"repos/{repo}/git/refs/heads/{branch}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if delete.returncode == 0:
        return
    combined = f"{delete.stderr or ''}{delete.stdout or ''}".lower()
    if "not found" in combined or "does not exist" in combined:
        return
    raise RuntimeError(
        f"Failed to delete fixture branch {branch!r}: "
        f"{(delete.stderr or delete.stdout or '').strip() or f'exit {delete.returncode}'}"
    )


def cleanup_fixture_pr(repo: str, pr_number: int, branch: str | None) -> None:
    """Close the ephemeral fixture PR and delete its head branch."""
    close = subprocess.run(
        [
            "gh",
            "pr",
            "close",
            str(pr_number),
            "--repo",
            repo,
            "--delete-branch",
            "--comment",
            "Closing ephemeral obs:dependency-review E2E fixture PR.",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if close.returncode == 0:
        return
    combined = f"{close.stderr or ''}{close.stdout or ''}".lower()
    if "already closed" in combined or "not open" in combined:
        if branch:
            delete_fixture_branch(repo, branch)
        return
    raise RuntimeError(
        f"Failed to close fixture PR #{pr_number}: "
        f"{(close.stderr or close.stdout or '').strip() or f'exit {close.returncode}'}"
    )


def normalize_fixture_branch_prefix(raw: str | None) -> str:
    """Return a fixture branch prefix that matches the event-orchestrator skip guard.

    Production skip uses ``startsWith(head.ref, 'e2e/dependency-review/')``.
    Validation must use that full prefix (including the trailing slash) so values
    like ``e2e/dependency-review-malicious/`` fail closed instead of bypassing
    the automerge skip while still carrying the fixture label.
    """
    branch_prefix = str(raw or FIXTURE_BRANCH_PREFIX).strip() or FIXTURE_BRANCH_PREFIX
    if not branch_prefix.endswith("/"):
        branch_prefix = f"{branch_prefix}/"
    if branch_prefix != FIXTURE_BRANCH_PREFIX:
        raise RuntimeError(
            f"e2e_pr.branch_prefix {branch_prefix!r} must equal "
            f"{FIXTURE_BRANCH_PREFIX!r} (exact event-guard prefix, including '/')"
        )
    return branch_prefix


def create_pin_bump_pr(
    repo: str,
    cfg: dict[str, Any],
    *,
    run_id: str,
) -> dict[str, Any]:
    """Create a same-repo PR that bumps the fixture actions/checkout pin."""
    e2e = cfg.get("e2e_pr") or {}
    label = str(e2e.get("label") or FIXTURE_LABEL).strip() or FIXTURE_LABEL
    if label != FIXTURE_LABEL:
        raise RuntimeError(
            f"e2e_pr.label {label!r} must be {FIXTURE_LABEL!r} "
            "(CI skip guards require the canonical fixture label)."
        )
    branch_prefix = normalize_fixture_branch_prefix(
        str(e2e.get("branch_prefix") or FIXTURE_BRANCH_PREFIX)
    )
    branch = f"{branch_prefix}{run_id}"
    workflow_rel = str(
        cfg.get("fixture_workflow_path") or DEFAULT_FIXTURE_WORKFLOW
    ).replace("\\", "/")
    local_workflow = Path(workflow_rel)
    if not local_workflow.is_file():
        raise RuntimeError(f"Fixture workflow missing at {local_workflow}")

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
    seed_fixture_workflow_on_default_branch(
        repo, default_branch=default_branch, workflow_path=local_workflow
    )
    base_sha = estc.gh_text(
        ["api", f"repos/{repo}/git/ref/heads/{default_branch}", "--jq", ".object.sha"]
    ).strip()

    created_branch: str | None = None
    created_pr: int | None = None
    try:
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
        created_branch = branch

        base_content = local_workflow.read_text(encoding="utf-8")
        remote = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/contents/{workflow_rel}?ref={default_branch}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if remote.returncode == 0:
            payload = json.loads(remote.stdout)
            remote_b64 = str(payload.get("content") or "").replace("\n", "")
            if remote_b64:
                base_content = base64.b64decode(remote_b64).decode("utf-8")

        bumped = bump_checkout_pin(
            base_content, sha=BUMP_CHECKOUT_SHA, version=BUMP_CHECKOUT_VERSION
        )
        commit_sha = estc.put_branch_file(
            repo,
            branch=branch,
            path=workflow_rel,
            content=bumped,
            message=(
                f"chore(e2e): bump actions/checkout pin to "
                f"{BUMP_CHECKOUT_SHA[:12]} ({BUMP_CHECKOUT_VERSION})"
            ),
        )
        if not commit_sha:
            raise RuntimeError(
                "Forced actions/checkout pin bump produced no commit "
                "(content already matched)."
            )

        title = str(
            e2e.get("title_template")
            or "[e2e] Bump actions/checkout pin for dependency-review"
        )
        body = str(e2e.get("body") or "").strip() or (
            "Ephemeral E2E fixture PR for obs:dependency-review (Actions pin bump)."
        )
        repo_owner = repo.partition("/")[0]
        head_ref = f"{repo_owner}:{branch}" if repo_owner else branch
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
                head_ref,
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
            raise RuntimeError(
                f"Could not parse PR number from gh pr create: {create_out}"
            )
        created_pr = pr_number

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
            "checkout_sha": BUMP_CHECKOUT_SHA,
            "checkout_version": BUMP_CHECKOUT_VERSION,
            "commit_sha": commit_sha,
        }
    except (RuntimeError, OSError, TypeError, ValueError):
        if created_pr is not None:
            try:
                cleanup_fixture_pr(repo, created_pr, created_branch)
            except (RuntimeError, OSError, TypeError, ValueError) as rollback_exc:
                estc.log_error(
                    f"Rollback cleanup failed for partial fixture PR "
                    f"#{created_pr}: {rollback_exc}"
                )
        elif created_branch is not None:
            try:
                delete_fixture_branch(repo, created_branch)
            except (RuntimeError, OSError, TypeError, ValueError) as rollback_exc:
                estc.log_error(
                    f"Rollback delete failed for partial fixture branch "
                    f"{created_branch!r}: {rollback_exc}"
                )
        raise


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
        "seed_checkout_sha": SEED_CHECKOUT_SHA,
        "seed_checkout_version": SEED_CHECKOUT_VERSION,
        "bump_checkout_sha": BUMP_CHECKOUT_SHA,
        "bump_checkout_version": BUMP_CHECKOUT_VERSION,
    }
    dashboard_ok = False
    pr_info: dict[str, Any] | None = None
    outcome: dict[str, Any] | None = None

    # Fail closed: validate trigger bool types before any remote mutation.
    # Raw trigger.get(...) treats strings like "false" as truthy.
    try:
        require_open_pr = _trigger_bool(trigger, "require_open_pr", default=True)
        force_actions_pin_bump = _trigger_bool(
            trigger, "force_actions_pin_bump", default=True
        )
        require_allowed_pr_author = _trigger_bool(
            trigger, "require_allowed_pr_author", default=True
        )
        wait_dependency_review = _trigger_bool(
            trigger, "wait_dependency_review", default=True
        )
    except TypeError as exc:
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": str(exc),
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "trigger": trigger,
            "run_url": run_url,
        }

    if not require_open_pr:
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
            "trigger": trigger,
            "run_url": run_url,
        }
    if not force_actions_pin_bump:
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                "Live E2E requires trigger.force_actions_pin_bump so the harness "
                "opens an Actions pin-bump fixture PR."
            ),
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "trigger": trigger,
            "run_url": run_url,
        }
    if not wait_dependency_review:
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                "Live E2E requires trigger.wait_dependency_review so the harness "
                "waits for the named dependency-review leaf before side-effect "
                "checks (reject before any remote mutation)."
            ),
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "trigger": trigger,
            "run_url": run_url,
        }
    if not require_allowed_pr_author:
        return {
            "workflow_id": workflow_id,
            "case_id": case.get("id", case_dir.name),
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "blocked": True,
            "block_reason": (
                "Live E2E requires trigger.require_allowed_pr_author so the "
                "harness rejects non-Vault fixture PR authors before any "
                "remote mutation."
            ),
            "path_gates": {"dashboard_enabled": False},
            "expectations": expectations,
            "trigger": trigger,
            "run_url": run_url,
        }

    try:
        dashboard_ok, missing = dashboard_enables_all(repo, dash_ids)
        if expectations.get("dashboard_enabled") and not dashboard_ok:
            outcome = {
                "workflow_id": workflow_id,
                "case_id": case.get("id", case_dir.name),
                "layer": "e2e",
                "mode": "live",
                "agent_invoked": False,
                "blocked": True,
                "block_reason": (
                    f"Dashboard missing required ids on {repo}: {missing}. "
                    "Enable obs:dependency-review on the Control Plane Dashboard, "
                    "then re-run."
                ),
                "path_gates": {
                    "dashboard_enabled": False,
                    "missing_dashboard_ids": missing,
                },
                "expectations": expectations,
                "run_url": run_url,
            }
            return outcome

        run_id = os.environ.get("GITHUB_RUN_ID") or str(int(time.time()))
        since = _utc_now().replace(microsecond=0)
        known_run_ids = {
            int(run["databaseId"]) for run in list_pr_trigger_runs(repo, workflow_file)
        }

        pr_info = create_pin_bump_pr(repo, cfg, run_id=run_id)
        fixture_meta.update(
            {
                "pr_number": pr_info["number"],
                "pr_url": pr_info.get("url"),
                "branch": pr_info.get("branch"),
            }
        )
        author = str(pr_info.get("author_login") or "")
        if require_allowed_pr_author and author != allowed_author:
            outcome = {
                "workflow_id": workflow_id,
                "case_id": case.get("id", case_dir.name),
                "layer": "e2e",
                "mode": "live",
                "agent_invoked": False,
                "blocked": True,
                "block_reason": (
                    f"Fixture PR author is {author!r}, expected {allowed_author!r} "
                    "(REST user.login). Run under GitHub Actions with Vault "
                    "create-token using workflow-token-policy from "
                    "config/e2e.json (see e2e-dependency-review.yml) "
                    "so Contents API commits and gh pr create are authored as "
                    "the Vault app (pull_request workflows then run without "
                    "maintainer Approve-and-run)."
                ),
                "path_gates": {"dashboard_enabled": dashboard_ok},
                "fixture": fixture_meta,
                "pr_number": pr_info["number"],
                "commit_sha": pr_info.get("commit_sha"),
                "expectations": expectations,
                "run_url": run_url,
            }
            return outcome

        head_branch = str(pr_info.get("headRefName") or pr_info.get("branch") or "")
        dr_run: dict[str, Any] | None = None
        if wait_dependency_review:
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
                if dr_comment is None:
                    remaining = comment_deadline - time.time()
                    if remaining <= 0:
                        break
                    time.sleep(min(interval, remaining))
            if dr_comment is None:
                raise TimeoutError(
                    f"No dependency-review comment with markers {dr_markers!r} "
                    f"on PR #{pr_info['number']} within timeout."
                )

        path_gates = {
            "dashboard_enabled": dashboard_ok,
            "has_open_or_merged_pr": True,
            "author_matches_allowed": author == allowed_author,
        }
        outcome = {
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
                "matched_job_name": dependency_review_matched_job_name(dr_run),
                "run_id": (dr_run or {}).get("databaseId"),
                "url": (dr_run or {}).get("url"),
            },
            "merge_ready_label": {
                "name": merge_ready_label,
                "applied": merge_ready,
            },
            "dependency_review_comment": dr_comment,
            "path_gates": path_gates,
            "expectations": expectations,
            "run_url": run_url,
            "harness_notes": [
                (
                    "Happy path: forced actions/checkout pin bump → "
                    "trigger-obs-aw-pull-request → dependency-review → "
                    "analysis comment → oblt-aw/ai/merge-ready "
                    "(no automerge wait)."
                ),
            ],
        }
    except (RuntimeError, TimeoutError, TypeError, ValueError, OSError) as exc:
        outcome = {
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
            outcome["pr_number"] = pr_info.get("number")
            outcome["commit_sha"] = pr_info.get("commit_sha")
            outcome["pr_url"] = pr_info.get("url")
    finally:
        if pr_info is not None:
            try:
                cleanup_fixture_pr(
                    repo,
                    int(pr_info["number"]),
                    str(pr_info.get("branch") or pr_info.get("headRefName") or "")
                    or None,
                )
                fixture_meta["cleaned_up"] = True
            except (RuntimeError, OSError, TypeError, ValueError) as cleanup_exc:
                estc.log_error(
                    f"Fixture PR cleanup failed for #{pr_info.get('number')}: "
                    f"{cleanup_exc}"
                )
                fixture_meta["cleanup_error"] = str(cleanup_exc)
                fixture_meta["cleaned_up"] = False

    if outcome is None:
        raise RuntimeError("Live E2E harness produced no outcome")
    # Fail closed: cleanup leaks must not leave a green live outcome.
    if fixture_meta.get("cleanup_error"):
        outcome["fixture"] = fixture_meta
        if not outcome.get("blocked"):
            outcome["blocked"] = True
            outcome["block_reason"] = (
                "Fixture PR cleanup failed after the live run: "
                f"{fixture_meta['cleanup_error']}"
            )
        elif "cleanup" not in str(outcome.get("block_reason") or "").lower():
            outcome["block_reason"] = (
                f"{outcome.get('block_reason')}; "
                f"cleanup also failed: {fixture_meta['cleanup_error']}"
            )
    elif fixture_meta.get("cleaned_up"):
        outcome["fixture"] = fixture_meta
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run obs:dependency-review live E2E harness."
    )
    parser.add_argument(
        "--case-id",
        default="actions-pin-bump-live",
        help="Case directory name under testdata/.../cases/",
    )
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/dependency-review"),
        help="Root of dependency-review live E2E cases",
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
