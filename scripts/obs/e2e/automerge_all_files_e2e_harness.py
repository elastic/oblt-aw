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

"""Live E2E harness for obs:automerge:all-files + consumer trigger-label policy.

Creates a stacked temporary base with ``apm.yml`` policy (trusted at base SHA),
opens a Vault-authored marker PR against that base (path matches only
``all-files``), optionally applies the custom trigger label, then asserts
automerge approve/merge (happy) or no approve/merge (negative).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import automerge_vm_images_e2e_harness as am_vm
import dependency_review_e2e_harness as dr_e2e
import estc_pr_buildkite_detective_e2e_harness as estc

WORKFLOW_ID = "obs:automerge"
DEFAULT_CONFIG = Path("config/obs/e2e-automerge-all-files.json")
FIXTURE_LABEL = "e2e:automerge-all-files"
FIXTURE_BRANCH_PREFIX = "e2e/automerge-all-files/"
BASE_BRANCH_PREFIX = "e2e/automerge-all-files/base/"
CUSTOM_TRIGGER_LABEL = "e2e:automerge-all-files-ready"
DEFAULT_MARKER_PATH = "e2e-fixtures/automerge-all-files/marker.txt"
DEFAULT_POLICY_APM = Path("testdata/agentic/automerge-all-files/policy-apm.yml")
ALLOWED_AUTHOR = "elastic-vault-github-plugin-prod[bot]"
AUTOMERGE_MERGE_LEAF_SUFFIX = " / automerge / automerge"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)  # noqa: UP017


def load_e2e_config(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"E2E config must be a JSON object: {path}")
    return data


def required_dashboard_ids(cfg: dict[str, Any]) -> list[str]:
    raw = cfg.get("required_dashboard_ids") or [
        "obs:automerge",
        "obs:automerge:all-files",
    ]
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("required_dashboard_ids must be a non-empty list")
    ids = [str(item).strip() for item in raw if str(item).strip()]
    if not ids:
        raise RuntimeError("required_dashboard_ids resolved empty")
    return ids


def checkout_sha() -> str:
    """SHA of the workspace checked out by the E2E job.

    Prefer ``git rev-parse HEAD`` so a ``checkout-ref`` that differs from the
    workflow event ``GITHUB_SHA`` still seeds fixtures from the tree under test.
    """
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def ensure_label(repo: str, label: str, *, description: str) -> None:
    proc = subprocess.run(
        [
            "gh",
            "label",
            "create",
            label,
            "--repo",
            repo,
            "--description",
            description,
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


def create_ref(repo: str, *, branch: str, sha: str) -> None:
    estc.gh_json(
        [
            "api",
            "--method",
            "POST",
            f"repos/{repo}/git/refs",
            "-f",
            f"ref=refs/heads/{branch}",
            "-f",
            f"sha={sha}",
        ]
    )


def add_pr_label(repo: str, pr_number: int, label: str) -> None:
    proc = subprocess.run(
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
    if proc.returncode != 0:
        raise RuntimeError(
            f"Failed to add label {label!r} to PR #{pr_number}: "
            f"{(proc.stderr or proc.stdout or '').strip() or f'exit {proc.returncode}'}"
        )


def pr_has_label(repo: str, pr_number: int, label: str) -> bool:
    pr = estc.gh_json(
        ["pr", "view", str(pr_number), "--repo", repo, "--json", "labels"]
    )
    names = [
        str(item.get("name") or "")
        for item in ((pr or {}).get("labels") or [])
        if isinstance(item, dict)
    ]
    return label in names


def automerge_matched_job_name(run_detail: dict[str, Any] | None) -> str | None:
    match = am_vm._job_match_by_exact_or_suffix(
        run_detail,
        exact_names=("automerge",),
        endswith_suffixes=(AUTOMERGE_MERGE_LEAF_SUFFIX,),
    )
    return match[0] if match else None


def wait_for_any_pr_route_run(
    repo: str,
    workflow_file: str,
    *,
    since: datetime,
    timeout_seconds: int,
    interval_seconds: int,
    exclude_run_ids: set[int],
    head_branch: str,
) -> dict[str, Any] | None:
    """Wait for any completed pull_request caller run for ``head_branch``."""
    excluded = set(exclude_run_ids)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for run in am_vm.list_pr_trigger_runs(repo, workflow_file):
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
                        (
                            "databaseId,status,conclusion,url,jobs,createdAt,"
                            "headSha,event,headBranch"
                        ),
                    ]
                )
                if detail.get("status") != "completed":
                    time.sleep(interval_seconds)
                    continue
                return cast(dict[str, Any], detail)
            excluded.add(run_id)
            break
        time.sleep(interval_seconds)
    return None


def create_stacked_policy_fixture(
    repo: str,
    cfg: dict[str, Any],
    *,
    run_id: str,
) -> dict[str, Any]:
    """Create base (policy) + head (marker) branches and open the fixture PR."""
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
    if branch_prefix != FIXTURE_BRANCH_PREFIX:
        raise RuntimeError(
            f"e2e_pr.branch_prefix {branch_prefix!r} must equal "
            f"{FIXTURE_BRANCH_PREFIX!r}"
        )
    base_prefix = (
        str(e2e.get("base_branch_prefix") or BASE_BRANCH_PREFIX).strip()
        or BASE_BRANCH_PREFIX
    )
    if base_prefix != BASE_BRANCH_PREFIX:
        raise RuntimeError(
            f"e2e_pr.base_branch_prefix {base_prefix!r} must equal "
            f"{BASE_BRANCH_PREFIX!r}"
        )

    custom_label = (
        str(cfg.get("custom_trigger_label") or CUSTOM_TRIGGER_LABEL).strip()
        or CUSTOM_TRIGGER_LABEL
    )
    if custom_label != CUSTOM_TRIGGER_LABEL:
        raise RuntimeError(
            f"custom_trigger_label {custom_label!r} must be {CUSTOM_TRIGGER_LABEL!r}"
        )
    marker_path = (
        str(cfg.get("fixture_marker_path") or DEFAULT_MARKER_PATH).strip()
        or DEFAULT_MARKER_PATH
    )
    policy_path = Path(str(cfg.get("policy_apm_path") or DEFAULT_POLICY_APM))
    if not policy_path.is_file():
        raise RuntimeError(f"Policy apm.yml missing at {policy_path}")
    policy_content = policy_path.read_text(encoding="utf-8")
    if CUSTOM_TRIGGER_LABEL not in policy_content:
        raise RuntimeError(
            f"Policy apm.yml at {policy_path} must list {CUSTOM_TRIGGER_LABEL!r}"
        )

    ensure_label(
        repo,
        label,
        description="E2E fixture for obs:automerge:all-files",
    )
    ensure_label(
        repo,
        custom_label,
        description="Custom Automerge trigger label for all-files E2E",
    )

    tip_sha = checkout_sha()
    base_branch = f"{base_prefix}{run_id}"
    head_branch = f"{branch_prefix}{run_id}"
    create_ref(repo, branch=base_branch, sha=tip_sha)
    try:
        policy_sha = estc.put_branch_file(
            repo,
            branch=base_branch,
            path="apm.yml",
            content=policy_content,
            message="chore(e2e): seed automerge all-files policy apm.yml",
        )
        if not policy_sha:
            raise RuntimeError("Seeding apm.yml on base produced no commit")

        base_tip = estc.gh_text(
            [
                "api",
                f"repos/{repo}/git/ref/heads/{base_branch}",
                "--jq",
                ".object.sha",
            ]
        ).strip()
        create_ref(repo, branch=head_branch, sha=base_tip)
        marker_body = (
            f"automerge-all-files e2e marker\nrun_id={run_id}\n"
            f"created_at={_utc_now().isoformat()}\n"
        )
        marker_sha = estc.put_branch_file(
            repo,
            branch=head_branch,
            path=marker_path,
            content=marker_body,
            message="chore(e2e): all-files marker for custom trigger label",
        )
        if not marker_sha:
            raise RuntimeError("Marker commit produced no change")
    except Exception:
        for branch in (head_branch, base_branch):
            try:
                dr_e2e.delete_fixture_branch(repo, branch)
            except RuntimeError:
                pass
        raise

    title_template = str(
        e2e.get("title_template")
        or "[e2e][automerge-all-files] Custom trigger label fixture {run_id}"
    )
    title = title_template.format(run_id=run_id)
    body = str(e2e.get("body") or "").strip() or (
        "Ephemeral E2E fixture PR for obs:automerge:all-files."
    )
    # Ready PR (no --draft): validateAutomergePr excludes drafts.
    create = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--base",
            base_branch,
            "--head",
            head_branch,
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
        for branch in (head_branch, base_branch):
            try:
                dr_e2e.delete_fixture_branch(repo, branch)
            except RuntimeError:
                pass
        raise RuntimeError(
            f"gh pr create failed: {(create.stderr or create.stdout or '').strip()}"
        )
    pr_number: int | None = None
    try:
        pr_number = estc._pr_number_from_gh_output(create.stdout or create_out)
        if pr_number is None:
            raise RuntimeError(
                f"Could not parse PR number from gh pr create: {create_out}"
            )

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
        author_login = am_vm.rest_pr_author_login(repo, pr_number)
        return {
            "number": int(pr["number"]),
            "url": pr.get("url"),
            "headRefName": pr.get("headRefName") or head_branch,
            "headRefOid": pr.get("headRefOid") or marker_sha,
            "baseRefName": pr.get("baseRefName") or base_branch,
            "author_login": author_login,
            "labels": [
                lbl.get("name") for lbl in (pr.get("labels") or []) if lbl.get("name")
            ],
            "branch": head_branch,
            "base_branch": base_branch,
            "commit_sha": marker_sha,
            "policy_commit_sha": policy_sha,
            "marker_path": marker_path,
            "custom_trigger_label": custom_label,
            "fixture_label": label,
        }
    except Exception:
        cleanup_stacked_fixture(
            repo,
            pr_number=pr_number,
            head_branch=head_branch,
            base_branch=base_branch,
            merged=False,
        )
        raise


# GitHub refs can briefly remain visible after a successful DELETE.
_CLEANUP_ABSENCE_ATTEMPTS = 5
_CLEANUP_ABSENCE_SLEEP_SECONDS = 2.0


def _delete_fixture_branch_until_absent(
    repo: str,
    branch: str,
    *,
    errors: list[str],
    attempts: int | None = None,
    sleep_seconds: float | None = None,
) -> bool:
    """Delete ``branch`` and poll until the ref is gone.

    Returns True when the branch is absent. Records an error and returns False
    when delete fails or the ref remains after retries (never soft-succeeds).
    """
    max_attempts = _CLEANUP_ABSENCE_ATTEMPTS if attempts is None else attempts
    pause_seconds = (
        _CLEANUP_ABSENCE_SLEEP_SECONDS if sleep_seconds is None else sleep_seconds
    )
    for attempt in range(1, max_attempts + 1):
        try:
            if not dr_e2e.fixture_branch_exists(repo, branch):
                return True
            dr_e2e.delete_fixture_branch(repo, branch)
        except RuntimeError as exc:
            errors.append(str(exc))
            return False
        try:
            if not dr_e2e.fixture_branch_exists(repo, branch):
                return True
        except RuntimeError as exc:
            errors.append(str(exc))
            return False
        if attempt < max_attempts:
            time.sleep(pause_seconds)
    errors.append(
        f"Fixture branch {branch!r} still present after {max_attempts} delete attempts"
    )
    return False


def cleanup_stacked_fixture(
    repo: str,
    *,
    pr_number: int | None,
    head_branch: str | None,
    base_branch: str | None,
    merged: bool,
) -> dict[str, Any]:
    """Close unmerged PRs and delete stacked base/head branches; verify absence."""
    errors: list[str] = []
    if pr_number is not None and not merged:
        try:
            dr_e2e.cleanup_fixture_pr(repo, pr_number, head_branch)
        except RuntimeError as exc:
            errors.append(str(exc))
            if head_branch:
                _delete_fixture_branch_until_absent(repo, head_branch, errors=errors)
    elif head_branch:
        _delete_fixture_branch_until_absent(repo, head_branch, errors=errors)

    if base_branch:
        _delete_fixture_branch_until_absent(repo, base_branch, errors=errors)

    head_absent = True
    base_absent = True
    if head_branch:
        try:
            head_absent = not dr_e2e.fixture_branch_exists(repo, head_branch)
        except RuntimeError as exc:
            errors.append(str(exc))
            head_absent = False
        if not head_absent and not any(head_branch in err for err in errors):
            errors.append(f"Fixture head branch {head_branch!r} still present")
    if base_branch:
        try:
            base_absent = not dr_e2e.fixture_branch_exists(repo, base_branch)
        except RuntimeError as exc:
            errors.append(str(exc))
            base_absent = False
        if not base_absent and not any(base_branch in err for err in errors):
            errors.append(f"Fixture base branch {base_branch!r} still present")

    completed = bool(head_absent and base_absent and not errors)
    result: dict[str, Any] = {
        "completed": completed,
        "head_absent": head_absent,
        "base_absent": base_absent,
    }
    if errors:
        result["error"] = "; ".join(errors)
    return result


def _blocked(
    *,
    workflow_id: str,
    case_id: str,
    reason: str,
    run_url: str | None,
    expectations: dict[str, Any],
    trigger: dict[str, Any],
    dashboard_ok: bool = False,
    fixture_meta: dict[str, Any] | None = None,
    pr_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "workflow_id": workflow_id,
        "case_id": case_id,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": False,
        "blocked": True,
        "block_reason": reason,
        "path_gates": {"dashboard_enabled": dashboard_ok},
        "expectations": expectations,
        "trigger": trigger,
        "run_url": run_url,
    }
    if fixture_meta is not None:
        out["fixture"] = fixture_meta
    if pr_info is not None:
        out["pr_number"] = pr_info.get("number")
        out["commit_sha"] = pr_info.get("commit_sha")
        out["pr_url"] = pr_info.get("url")
        out["pr_head_branch"] = pr_info.get("headRefName") or pr_info.get("branch")
        out["pr_base_branch"] = pr_info.get("baseRefName") or pr_info.get("base_branch")
        out["pr_author"] = pr_info.get("author_login")
    return out


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
    custom_label = (
        str(cfg.get("custom_trigger_label") or CUSTOM_TRIGGER_LABEL).strip()
        or CUSTOM_TRIGGER_LABEL
    )
    gate_marker = str(
        cfg.get("dependency_collection_gate_marker")
        or "<!-- obs-aw-automerge:dependency-collection-gate -->"
    )
    allowed_author = str(cfg.get("allowed_pr_author") or ALLOWED_AUTHOR)
    timeout = int(cfg.get("poll_timeout_seconds") or 3600)
    interval = int(cfg.get("poll_interval_seconds") or 20)
    negative_settle = int(cfg.get("negative_settle_seconds") or 180)
    dash_ids = required_dashboard_ids(cfg)
    case_id = str(case.get("id", case_dir.name))

    fixture_meta: dict[str, Any] = {
        "label": FIXTURE_LABEL,
        "branch_prefix": FIXTURE_BRANCH_PREFIX,
        "base_branch_prefix": BASE_BRANCH_PREFIX,
        "custom_trigger_label": custom_label,
    }
    dashboard_ok = False
    pr_info: dict[str, Any] | None = None
    merged = False
    cleanup_result: dict[str, Any] | None = None

    # Fail closed: required flags default false when omitted so a missing key
    # cannot authorize remote mutation.
    required_true_keys = (
        "require_open_pr",
        "force_stacked_policy_base",
        "require_allowed_pr_author",
    )
    for key in required_true_keys:
        try:
            value = am_vm._trigger_bool(trigger, key, default=False)
        except TypeError as exc:
            return _blocked(
                workflow_id=workflow_id,
                case_id=case_id,
                reason=str(exc),
                run_url=run_url,
                expectations=expectations,
                trigger=trigger,
            )
        if not value:
            return _blocked(
                workflow_id=workflow_id,
                case_id=case_id,
                reason=(
                    f"Live E2E requires trigger.{key}=true before remote "
                    "mutation (fail closed)."
                ),
                run_url=run_url,
                expectations=expectations,
                trigger=trigger,
            )

    apply_custom = am_vm._trigger_bool(
        trigger, "apply_custom_trigger_label", default=False
    )
    wait_automerge = am_vm._trigger_bool(trigger, "wait_automerge", default=False)
    expect_merge = am_vm._trigger_bool(trigger, "expect_merge", default=False)
    wait_verify_skip = am_vm._trigger_bool(trigger, "wait_verify_skip", default=False)

    # Fail closed: reject inconsistent trigger combos before remote mutation.
    if apply_custom != expect_merge or wait_automerge != expect_merge:
        return _blocked(
            workflow_id=workflow_id,
            case_id=case_id,
            reason=(
                "Live E2E requires apply_custom_trigger_label and wait_automerge "
                "to match expect_merge before remote mutation "
                f"(apply_custom={apply_custom}, wait_automerge={wait_automerge}, "
                f"expect_merge={expect_merge})."
            ),
            run_url=run_url,
            expectations=expectations,
            trigger=trigger,
        )
    if expect_merge:
        if not (apply_custom and wait_automerge):
            return _blocked(
                workflow_id=workflow_id,
                case_id=case_id,
                reason=(
                    "Happy-path live E2E requires apply_custom_trigger_label=true "
                    "and wait_automerge=true when expect_merge=true."
                ),
                run_url=run_url,
                expectations=expectations,
                trigger=trigger,
            )
    elif not wait_verify_skip:
        return _blocked(
            workflow_id=workflow_id,
            case_id=case_id,
            reason=(
                "Negative live E2E requires wait_verify_skip=true so a verify "
                "attempt is observed before asserting no automerge."
            ),
            run_url=run_url,
            expectations=expectations,
            trigger=trigger,
        )

    try:
        dashboard_ok, missing = am_vm.dashboard_enables_all(repo, dash_ids)
        if expectations.get("dashboard_enabled") and not dashboard_ok:
            return _blocked(
                workflow_id=workflow_id,
                case_id=case_id,
                reason=(
                    f"Dashboard missing required ids on {repo}: {missing}. "
                    "Enable obs:automerge and obs:automerge:all-files on the "
                    "Control Plane Dashboard, then re-run."
                ),
                run_url=run_url,
                expectations=expectations,
                trigger=trigger,
                dashboard_ok=False,
            )

        run_id = os.environ.get("GITHUB_RUN_ID") or str(int(time.time()))
        # Matrix jobs share GITHUB_RUN_ID; disambiguate stacked branch names.
        case_slug = case_id.replace("_", "-")
        unique_run = f"{run_id}-{case_slug}"
        since = _utc_now().replace(microsecond=0)
        known_run_ids = {
            int(run["databaseId"])
            for run in am_vm.list_pr_trigger_runs(repo, workflow_file)
        }

        pr_info = create_stacked_policy_fixture(repo, cfg, run_id=unique_run)
        fixture_meta.update(
            {
                "pr_number": pr_info["number"],
                "pr_url": pr_info.get("url"),
                "branch": pr_info.get("branch"),
                "base_branch": pr_info.get("base_branch"),
                "marker_path": pr_info.get("marker_path"),
                "policy_commit_sha": pr_info.get("policy_commit_sha"),
            }
        )
        author = str(pr_info.get("author_login") or "")
        if author != allowed_author:
            cleanup_result = cleanup_stacked_fixture(
                repo,
                pr_number=int(pr_info["number"]),
                head_branch=str(pr_info.get("branch") or ""),
                base_branch=str(pr_info.get("base_branch") or ""),
                merged=False,
            )
            fixture_meta["cleaned_up"] = cleanup_result.get("completed") is True
            fixture_meta["cleanup_error"] = cleanup_result.get("error")
            fixture_meta["head_absent"] = cleanup_result.get("head_absent")
            fixture_meta["base_absent"] = cleanup_result.get("base_absent")
            return _blocked(
                workflow_id=workflow_id,
                case_id=case_id,
                reason=(
                    f"Fixture PR author is {author!r}, expected {allowed_author!r} "
                    "(REST user.login). Run under GitHub Actions with Vault "
                    "create-token using workflow-token-policy from "
                    "config/e2e.json so Contents API commits and gh pr create "
                    "are authored as the Vault app."
                ),
                run_url=run_url,
                expectations=expectations,
                trigger=trigger,
                dashboard_ok=dashboard_ok,
                fixture_meta=fixture_meta,
                pr_info=pr_info,
            )

        head_branch = str(pr_info.get("headRefName") or pr_info.get("branch") or "")
        base_branch = str(
            pr_info.get("baseRefName") or pr_info.get("base_branch") or ""
        )

        custom_applied = False
        if apply_custom:
            add_pr_label(repo, int(pr_info["number"]), custom_label)
            custom_applied = am_vm.wait_for_label(
                repo,
                int(pr_info["number"]),
                custom_label,
                timeout_seconds=min(300, timeout),
                interval_seconds=interval,
            )
            if not custom_applied:
                raise TimeoutError(
                    f"Custom trigger label {custom_label!r} was not visible on "
                    f"PR #{pr_info['number']} after add."
                )

        am_run: dict[str, Any] | None = None
        route_run: dict[str, Any] | None = None
        if wait_automerge:
            estc.log_info(
                f"Waiting for automerge merge leaf on {workflow_file} "
                f"(PR #{pr_info['number']}, branch {head_branch})…"
            )
            am_run = am_vm.wait_for_pr_route_run(
                repo,
                workflow_file,
                since=since,
                timeout_seconds=timeout,
                interval_seconds=interval,
                exclude_run_ids=known_run_ids,
                head_branch=head_branch,
                require_job="automerge",
            )
            if am_run is None:
                raise TimeoutError(
                    f"No successful automerge merge leaf on {workflow_file} "
                    f"within {timeout}s for PR #{pr_info['number']}."
                )
            known_run_ids.add(int(am_run["databaseId"]))
        elif wait_verify_skip:
            estc.log_info(
                f"Waiting for a completed PR route run on {workflow_file} "
                f"(expect no automerge merge leaf)…"
            )
            route_run = wait_for_any_pr_route_run(
                repo,
                workflow_file,
                since=since,
                timeout_seconds=min(900, timeout),
                interval_seconds=interval,
                exclude_run_ids=known_run_ids,
                head_branch=head_branch,
            )
            if route_run is None:
                raise TimeoutError(
                    f"No completed pull_request run on {workflow_file} "
                    f"within timeout for PR #{pr_info['number']} "
                    "(negative case needs a verify attempt)."
                )
            verify_match = am_vm._job_match_by_exact_or_suffix(
                route_run,
                endswith_suffixes=(" / automerge / verify",),
            )
            if verify_match is None:
                raise RuntimeError(
                    f"Negative case PR #{pr_info['number']}: completed "
                    f"{workflow_file} run had no non-skipped automerge verify "
                    "job (prelude/route skip is not evidence of label rejection)."
                )
            merge_leaf_early = am_vm._job_match_by_exact_or_suffix(
                route_run,
                exact_names=("automerge",),
                endswith_suffixes=(AUTOMERGE_MERGE_LEAF_SUFFIX,),
            )
            if merge_leaf_early is not None:
                raise RuntimeError(
                    f"Negative case PR #{pr_info['number']} saw automerge merge "
                    f"leaf {merge_leaf_early[0]!r} "
                    f"(conclusion={merge_leaf_early[1]!r}) on the verify run."
                )
            known_run_ids.add(int(route_run["databaseId"]))
            # Settle briefly so a late labeled automerge cannot sneak past.
            settle_deadline = time.time() + negative_settle
            while time.time() < settle_deadline:
                late = am_vm.wait_for_pr_route_run(
                    repo,
                    workflow_file,
                    since=since,
                    timeout_seconds=interval,
                    interval_seconds=interval,
                    exclude_run_ids=known_run_ids,
                    head_branch=head_branch,
                    require_job="automerge",
                )
                if late is not None:
                    am_run = late
                    break
                time.sleep(interval)

        review = None
        if expect_merge or wait_automerge:
            review = am_vm.wait_for_approving_review(
                repo,
                int(pr_info["number"]),
                timeout_seconds=min(600, timeout),
                interval_seconds=interval,
            )

        merge_state: dict[str, Any]
        if expect_merge:
            merge_wait = max(timeout, 900)
            merge_state = am_vm.wait_for_merged(
                repo,
                int(pr_info["number"]),
                timeout_seconds=merge_wait,
                interval_seconds=interval,
            )
            merged = bool(merge_state.get("merged"))
            if not merged:
                raise TimeoutError(
                    f"PR #{pr_info['number']} did not merge within {merge_wait}s."
                )
        else:
            # Negative: confirm still not merged after settle.
            pr_now = estc.gh_json(
                [
                    "pr",
                    "view",
                    str(pr_info["number"]),
                    "--repo",
                    repo,
                    "--json",
                    "state,mergedAt,mergeStateStatus",
                ]
            )
            merged = bool(
                (pr_now or {}).get("mergedAt")
                or (str((pr_now or {}).get("state") or "").upper() == "MERGED")
            )
            merge_state = {
                "merged": merged,
                "merged_at": (pr_now or {}).get("mergedAt"),
                "merge_state_status": (pr_now or {}).get("mergeStateStatus"),
            }
            if merged:
                raise RuntimeError(
                    f"Negative case PR #{pr_info['number']} unexpectedly merged."
                )
            merge_leaf_late = am_vm._job_match_by_exact_or_suffix(
                am_run,
                exact_names=("automerge",),
                endswith_suffixes=(AUTOMERGE_MERGE_LEAF_SUFFIX,),
            )
            if merge_leaf_late is not None or am_vm.automerge_job_executed(am_run):
                raise RuntimeError(
                    f"Negative case saw automerge merge leaf on "
                    f"PR #{pr_info['number']} "
                    f"(match={merge_leaf_late!r})."
                )

        if not apply_custom:
            custom_applied = pr_has_label(repo, int(pr_info["number"]), custom_label)
        merge_ready_applied = pr_has_label(
            repo, int(pr_info["number"]), merge_ready_label
        )
        gate_comment = am_vm.find_comment_with_marker(
            repo, int(pr_info["number"]), gate_marker, since=since
        )
        if not expect_merge and not apply_custom:
            # Re-check approve absence without long wait.
            review = None
            reviews = (
                estc.gh_json(
                    [
                        "api",
                        f"repos/{repo}/pulls/{pr_info['number']}/reviews",
                        "--jq",
                        ".",
                    ]
                )
                or []
            )
            for item in reviews:
                if not isinstance(item, dict):
                    continue
                if (item.get("state") or "").upper() == "APPROVED":
                    user = item.get("user") or {}
                    login = (
                        str(user.get("login") or "") if isinstance(user, dict) else ""
                    )
                    review = {
                        "id": item.get("id"),
                        "user": login,
                        "state": item.get("state"),
                        "submitted_at": item.get("submitted_at"),
                    }
                    break
    except (RuntimeError, TimeoutError, TypeError, ValueError, OSError) as exc:
        if pr_info is not None:
            cleanup_result = cleanup_stacked_fixture(
                repo,
                pr_number=int(pr_info["number"]),
                head_branch=str(pr_info.get("branch") or ""),
                base_branch=str(pr_info.get("base_branch") or ""),
                merged=False,
            )
            fixture_meta["cleaned_up"] = cleanup_result.get("completed") is True
            fixture_meta["cleanup_error"] = cleanup_result.get("error")
            fixture_meta["head_absent"] = cleanup_result.get("head_absent")
            fixture_meta["base_absent"] = cleanup_result.get("base_absent")
        return _blocked(
            workflow_id=workflow_id,
            case_id=case_id,
            reason=str(exc),
            run_url=run_url,
            expectations=expectations,
            trigger=trigger,
            dashboard_ok=dashboard_ok,
            fixture_meta=fixture_meta,
            pr_info=pr_info,
        )

    cleanup_result = cleanup_stacked_fixture(
        repo,
        pr_number=int(pr_info["number"]),
        head_branch=head_branch,
        base_branch=base_branch,
        merged=merged,
    )
    fixture_meta["cleaned_up"] = cleanup_result.get("completed") is True
    fixture_meta["cleanup_error"] = cleanup_result.get("error")
    fixture_meta["head_absent"] = cleanup_result.get("head_absent")
    fixture_meta["base_absent"] = cleanup_result.get("base_absent")
    if cleanup_result.get("error") or not cleanup_result.get("completed"):
        return _blocked(
            workflow_id=workflow_id,
            case_id=case_id,
            reason=(
                "Fixture cleanup failed or left stacked branches present: "
                f"{cleanup_result}"
            ),
            run_url=run_url,
            expectations=expectations,
            trigger=trigger,
            dashboard_ok=dashboard_ok,
            fixture_meta=fixture_meta,
            pr_info=pr_info,
        )

    evidence_run = am_run if am_run is not None else route_run
    path_gates = {
        "dashboard_enabled": dashboard_ok,
        "has_open_or_merged_pr": True,
        "author_matches_allowed": author == allowed_author,
    }
    return {
        "workflow_id": workflow_id,
        "case_id": case_id,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": bool(evidence_run),
        "blocked": False,
        "consumer_repo": repo,
        "commit_sha": pr_info.get("commit_sha"),
        "pr_number": pr_info["number"],
        "pr_url": pr_info.get("url"),
        "pr_head_branch": head_branch,
        "pr_base_branch": base_branch,
        "pr_author": author,
        "fixture": fixture_meta,
        "trigger": trigger,
        "custom_trigger_label": {
            "name": custom_label,
            "applied": custom_applied,
        },
        "merge_ready_label": {
            "name": merge_ready_label,
            "applied": merge_ready_applied,
        },
        "dependency_collection_gate_comment": gate_comment,
        "automerge": {
            "run_seen": am_run is not None,
            "job_executed": am_vm.automerge_job_executed(am_run),
            "approve_job_executed": am_vm.approve_job_executed(am_run),
            "job_conclusion": am_vm.automerge_job_conclusion(am_run),
            "matched_job_name": automerge_matched_job_name(am_run),
            "run_id": (am_run or {}).get("databaseId"),
            "url": (am_run or {}).get("url"),
        },
        "approving_review": review,
        "merge": merge_state,
        "path_gates": path_gates,
        "expectations": expectations,
        "run_url": run_url,
        "harness_notes": [
            (
                "Stacked base apm.yml policy + all-files marker PR; custom "
                "trigger label path (merge-ready not required)."
            ),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run obs:automerge:all-files live E2E harness."
    )
    parser.add_argument(
        "--case-id",
        default="all-files-custom-label-live",
        help="Case directory name under testdata/.../cases/",
    )
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/automerge-all-files"),
        help="Root of automerge all-files live E2E cases",
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
