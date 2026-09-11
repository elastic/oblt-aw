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

"""E2E / integration harness for obs:estc-pr-buildkite-detective.

Modes:
- live: drive the real status → trigger → prelude → wrapper → lock → agent
  path against elastic/oblt-aw (production consumer for this slice).
- fixture: deterministic pre-agent gate + recorded Buildkite resolution
  (integration layer; no live agent).
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
from typing import Any

WORKFLOW_ID = "obs:estc-pr-buildkite-detective"
DEFAULT_CONFIG = Path("config/obs/e2e-estc-pr-buildkite-detective.json")
BK_URL_RE = re.compile(r"https://buildkite\.com/([^/]+)/([^/]+)/builds/(\d+)")
ANSI_RE = re.compile(
    r"\x1b(?:\[[0-9;]*[A-Za-z]|_[^\x07]*\x07|[()][AB012]|[=>])"
)
FAIL_STATES = ("failed", "timed_out")
LOG_TAIL = 150
MARKER_PATH = "testdata/agentic/estc-pr-buildkite-detective/e2e-fixture-pr.md"
MARKER_BODY = (
    "# E2E fixture PR\n\n"
    "Kept open for live status→agent E2E of "
    "`obs:estc-pr-buildkite-detective`. Do not merge.\n"
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"\s+", "-", cleaned).lower()[:60].strip("-")


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


# ---------------------------------------------------------------------------
# Fixture / integration helpers (pre-agent path only)
# ---------------------------------------------------------------------------


def evaluate_status_gates(event: dict[str, Any]) -> dict[str, Any]:
    """Mirror obs-aw-event-status / wrapper status filters."""
    state = event.get("state")
    context = event.get("context") or ""
    return {
        "event_name": "status",
        "state_failure": state == "failure",
        "context_contains_buildkite": "buildkite" in context.lower(),
        "context": context,
        "state": state,
    }


def evaluate_open_pr_gate(open_prs: list[dict[str, Any]]) -> dict[str, Any]:
    open_count = sum(1 for pr in open_prs if pr.get("state") == "open")
    return {
        "has_open_pr": open_count > 0,
        "open_pr_count": open_count,
    }


def collect_failed_jobs(
    build_data: dict[str, Any],
    pipeline_slug: str,
    build_url: str,
    child_builds: dict[str, dict[str, Any]],
) -> list[tuple[str, str, dict[str, Any]]]:
    results: list[tuple[str, str, dict[str, Any]]] = []
    for job in build_data.get("jobs") or []:
        if job.get("state") not in FAIL_STATES:
            continue
        if job.get("type") == "script":
            results.append((pipeline_slug, build_url, job))
        elif job.get("type") == "trigger":
            triggered = job.get("triggered_build") or {}
            child_url = triggered.get("web_url", "")
            match = BK_URL_RE.search(child_url)
            if not match:
                continue
            child_key = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
            child = child_builds.get(child_key)
            if child is None:
                continue
            results.extend(
                collect_failed_jobs(child, match.group(2), child_url, child_builds)
            )
    return results


def resolve_buildkite_from_fixtures(
    event: dict[str, Any],
    build: dict[str, Any],
    job_logs: dict[str, str],
    child_builds: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Mirror lock pre-agent Buildkite fetch using recorded payloads."""
    child_builds = child_builds or {}
    commit_sha = (event.get("commit") or {}).get("sha", "")
    target_url = event.get("target_url") or ""
    match = BK_URL_RE.search(target_url)
    if not match:
        return {
            "ok": False,
            "error": f"No Buildkite build URL in target_url: {target_url}",
        }

    bk_org, bk_pipeline, _bk_number = match.group(1), match.group(2), match.group(3)
    build_url = match.group(0)
    pr_info = build.get("pull_request") or {}
    pr_number = pr_info.get("id", "")
    branch = build.get("branch", "")
    event_context = {
        "event_name": "status",
        "commit_sha": commit_sha,
        "build_url": build_url,
        "pipeline": bk_pipeline,
        "branch": branch,
        "pr_number": str(pr_number) if pr_number != "" else "",
    }

    if not pr_number:
        return {
            "ok": False,
            "error": "Build is not associated with a PR; skipping",
            "event_context": event_context,
        }

    if build.get("state") not in ("failed", "failing"):
        return {
            "ok": False,
            "error": f"Build is not finished (state: {build.get('state')}); skipping",
            "event_context": event_context,
        }

    failed = collect_failed_jobs(build, bk_pipeline, build_url, child_builds)
    if not failed:
        return {
            "ok": False,
            "error": (
                f"No failed script jobs in build (build state: {build.get('state')})"
            ),
            "event_context": event_context,
        }

    failure_summaries: list[dict[str, Any]] = []
    for pipeline_slug, job_build_url, job in failed:
        slug = _slugify(str(job.get("name", f"job-{job.get('id', 'unknown')}")))
        log_key = f"{pipeline_slug}-{slug}"
        raw_log = job_logs.get(log_key) or job_logs.get(slug) or ""
        cleaned_lines = [
            ANSI_RE.sub("", line) for line in raw_log.splitlines()
        ][-LOG_TAIL:]
        failure_summaries.append(
            {
                "name": job.get("name"),
                "pipeline": pipeline_slug,
                "build_url": job_build_url,
                "state": job.get("state"),
                "exit_status": job.get("exit_status"),
                "log_key": log_key,
                "log_line_count": len(cleaned_lines),
                "log_has_content": bool(cleaned_lines),
            }
        )

    return {
        "ok": True,
        "org": bk_org,
        "event_context": event_context,
        "failed_job_count": len(failed),
        "failed_jobs": failure_summaries,
        "build_state": build.get("state"),
    }


def run_fixture_case(case_dir: Path) -> dict[str, Any]:
    case = _load_json(case_dir / "case.json")
    event = _load_json(case_dir / "status-event.json")
    open_prs = _load_json(case_dir / "open-prs.json")
    build = _load_json(case_dir / "buildkite-build.json")
    job_log_path = case_dir / "job-log.txt"
    job_logs: dict[str, str] = {}
    if job_log_path.is_file():
        job_name = "Unit tests"
        for job in build.get("jobs") or []:
            if job.get("state") in FAIL_STATES and job.get("type") == "script":
                job_name = str(job.get("name") or job_name)
                break
        pipeline = "sandbox-ci"
        target_url = event.get("target_url") or ""
        match = BK_URL_RE.search(target_url)
        if match:
            pipeline = match.group(2)
        slug = _slugify(job_name)
        text = job_log_path.read_text(encoding="utf-8")
        job_logs[f"{pipeline}-{slug}"] = text
        job_logs[slug] = text

    child_builds_path = case_dir / "child-builds.json"
    child_builds: dict[str, dict[str, Any]] = {}
    if child_builds_path.is_file():
        child_builds = _load_json(child_builds_path)

    status_gates = evaluate_status_gates(event)
    pr_gates = evaluate_open_pr_gate(open_prs if isinstance(open_prs, list) else [])
    buildkite = resolve_buildkite_from_fixtures(event, build, job_logs, child_builds)

    path_ready = (
        status_gates["state_failure"]
        and status_gates["context_contains_buildkite"]
        and pr_gates["has_open_pr"]
        and bool(buildkite.get("ok"))
    )

    return {
        "workflow_id": case.get("workflow_id", WORKFLOW_ID),
        "case_id": case.get("id", case_dir.name),
        "layer": "integration",
        "mode": "fixture",
        "agent_invoked": False,
        "shared_proceed": True,
        "path_gates": {
            **status_gates,
            **pr_gates,
            "shared_proceed": True,
            "path_ready": path_ready,
        },
        "buildkite": buildkite,
        "expectations": case.get("expectations", {}),
        "harness_notes": [
            "Fixture mode is an integration check of status gates and recorded "
            "Buildkite resolution; it does not call the live GH-AW agent.",
        ],
    }


# ---------------------------------------------------------------------------
# Live / production E2E
# ---------------------------------------------------------------------------


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


def find_open_e2e_pr(repo: str, label: str) -> dict[str, Any] | None:
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
            "number,url,headRefName,headRefOid,title",
            "--limit",
            "5",
        ]
    )
    if not prs:
        return None
    return prs[0]


def _ensure_label(repo: str, label: str) -> None:
    subprocess.run(
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
        check=False,
    )


def ensure_e2e_pr(repo: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Find or create the long-lived E2E fixture PR via the GitHub API only."""
    e2e_pr = cfg["e2e_pr"]
    existing = find_open_e2e_pr(repo, e2e_pr["label"])
    if existing:
        return existing

    _ensure_label(repo, e2e_pr["label"])
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
        f"message=chore(e2e): keep ESTC detective fixture PR marker",
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
            e2e_pr["label"],
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if create.returncode != 0 and "already exists" not in (create.stderr + create.stdout):
        # PR may already exist without label.
        pass

    created = find_open_e2e_pr(repo, e2e_pr["label"])
    if created:
        return created

    prs = gh_json(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--head",
            branch,
            "--json",
            "number,url,headRefName,headRefOid,title",
            "--limit",
            "1",
        ]
    )
    if not prs:
        raise RuntimeError(
            f"Failed to ensure E2E PR on {repo} branch {branch}. "
            f"Create an open PR labeled {e2e_pr['label']!r}."
        )
    subprocess.run(
        [
            "gh",
            "pr",
            "edit",
            str(prs[0]["number"]),
            "--repo",
            repo,
            "--add-label",
            e2e_pr["label"],
        ],
        check=False,
    )
    return prs[0]


def resolve_no_open_pr_sha(repo: str) -> str:
    """Pick default-branch HEAD when it has no open PR association."""
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
    sha = gh_text(
        ["api", f"repos/{repo}/commits/{default_branch}", "--jq", ".sha"]
    ).strip()
    pulls = gh_json(
        [
            "api",
            f"repos/{repo}/commits/{sha}/pulls",
            "--jq",
            '[.[] | select(.state=="open")]',
        ]
    )
    if pulls:
        raise RuntimeError(
            f"Default branch HEAD {sha[:12]} still has open PRs; "
            "cannot run no-open-pr case safely."
        )
    return sha


def clear_detective_comments(repo: str, pr_number: int, markers: list[str]) -> int:
    comments = gh_json(
        [
            "api",
            f"repos/{repo}/issues/{pr_number}/comments?per_page=100",
            "--jq",
            ".",
        ]
    )
    deleted = 0
    for comment in comments or []:
        body = comment.get("body") or ""
        if not all(marker in body for marker in markers):
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


def post_commit_status(
    repo: str,
    sha: str,
    *,
    state: str,
    context: str,
    description: str,
    target_url: str | None,
) -> dict[str, Any]:
    args = [
        "api",
        "--method",
        "POST",
        f"repos/{repo}/statuses/{sha}",
        "-f",
        f"state={state}",
        "-f",
        f"context={context}",
        "-f",
        f"description={description[:140]}",
    ]
    if target_url:
        args.extend(["-f", f"target_url={target_url}"])
    return gh_json(args)


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
) -> dict[str, Any] | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for run in list_status_trigger_runs(repo, workflow_file):
            created = _parse_gh_time(run["createdAt"])
            if created < since:
                continue
            run_id = int(run["databaseId"])
            while time.time() < deadline:
                detail = gh_json(
                    [
                        "run",
                        "view",
                        str(run_id),
                        "--repo",
                        repo,
                        "--json",
                        "databaseId,status,conclusion,url,jobs,createdAt",
                    ]
                )
                if detail.get("status") == "completed":
                    return detail
                time.sleep(interval_seconds)
            return detail
        time.sleep(interval_seconds)
    return None


def status_job_executed(run_detail: dict[str, Any] | None) -> bool:
    if not run_detail:
        return False
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        if "run-obs-aw-status" in name or name.endswith("obs-aw-status"):
            return (job.get("conclusion") or "") not in ("skipped", "")
    # If jobs are not expanded, treat a non-skipped conclusion as executed.
    conclusion = (run_detail.get("conclusion") or "").lower()
    return conclusion not in ("", "skipped")


def agent_job_invoked(run_detail: dict[str, Any] | None) -> bool:
    if not run_detail:
        return False
    for job in run_detail.get("jobs") or []:
        name = (job.get("name") or "").lower()
        if "estc-pr-buildkite-detective" in name:
            return (job.get("conclusion") or "") not in ("skipped", "")
        if "buildkite" in name and "detective" in name:
            return (job.get("conclusion") or "") not in ("skipped", "")
    return False


def _buildkite_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return dict(cfg.get("buildkite_failure") or {})


def resolve_buildkite_org_pipeline(cfg: dict[str, Any]) -> tuple[str, str]:
    bk = _buildkite_cfg(cfg)
    org = (
        os.environ.get(str(bk.get("org_env") or "E2E_BUILDKITE_ORG"), "").strip()
        or str(bk.get("org_default") or "elastic")
    )
    pipeline = (
        os.environ.get(
            str(bk.get("pipeline_env") or "E2E_BUILDKITE_PIPELINE"), ""
        ).strip()
        or str(bk.get("pipeline_default") or "oblt-aw-e2e-estc-fail")
    )
    return org, pipeline


def buildkite_api_token(cfg: dict[str, Any]) -> str | None:
    bk = _buildkite_cfg(cfg)
    token_env = str(bk.get("token_env") or "E2E_BUILDKITE_API_TOKEN")
    token = os.environ.get(token_env, "").strip()
    return token or None


def placeholder_buildkite_url(cfg: dict[str, Any]) -> str:
    org, pipeline = resolve_buildkite_org_pipeline(cfg)
    return f"https://buildkite.com/{org}/{pipeline}/builds/0"


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
        raise RuntimeError(f"Buildkite create build returned unexpected payload: {created}")
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


def ensure_failed_buildkite_target_url(
    cfg: dict[str, Any],
    *,
    commit: str,
    branch: str,
    pr_number: int | None,
    case_id: str,
) -> tuple[str, dict[str, Any]]:
    """Create a failed Buildkite build and return (web_url, build_meta).

    Optional override: env named by ``buildkite_target_url_env`` skips create.
    """
    override_env = str(cfg.get("buildkite_target_url_env") or "E2E_ESTC_BUILDKITE_TARGET_URL")
    override = os.environ.get(override_env, "").strip()
    if override:
        return override, {
            "source": "override_env",
            "env": override_env,
            "web_url": override,
        }

    token = buildkite_api_token(cfg)
    if not token:
        bk = _buildkite_cfg(cfg)
        token_env = str(bk.get("token_env") or "E2E_BUILDKITE_API_TOKEN")
        raise RuntimeError(
            f"Missing {token_env} (write_builds + read). "
            f"Or set {override_env} to a readable failed build URL."
        )

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
    return web_url, {
        "source": "created",
        "org": org,
        "pipeline": pipeline,
        "number": number,
        "state": state,
        "web_url": web_url,
        "pull_request_id": pr_number,
    }


def needs_real_failed_buildkite(trigger: dict[str, Any], expectations: dict[str, Any]) -> bool:
    if trigger.get("create_failed_buildkite_build"):
        return True
    if not trigger.get("use_buildkite_target_url"):
        return False
    if str(trigger.get("status_state") or "") != "failure":
        return False
    return bool(
        expectations.get("agent_invoked") or expectations.get("expect_agent_comment")
    )


def find_agent_comment(
    repo: str,
    pr_number: int,
    *,
    since: datetime,
    markers: list[str],
) -> dict[str, Any] | None:
    comments = gh_json(
        [
            "api",
            f"repos/{repo}/issues/{pr_number}/comments?per_page=100",
            "--jq",
            ".",
        ]
    )
    for comment in comments or []:
        created_raw = comment.get("created_at") or comment.get("createdAt") or ""
        if not created_raw:
            continue
        created = _parse_gh_time(created_raw)
        if created < since:
            continue
        body = comment.get("body") or ""
        if all(marker in body for marker in markers):
            return {
                "id": comment.get("id"),
                "url": comment.get("html_url"),
                "user": (comment.get("user") or {}).get("login"),
                "created_at": comment.get("created_at"),
            }
    return None


def run_live_case(
    case_dir: Path,
    cfg: dict[str, Any],
    *,
    run_url: str | None = None,
) -> dict[str, Any]:
    case = _load_json(case_dir / "case.json")
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
    if needs_real_failed_buildkite(trigger, expectations):
        override_env = str(
            cfg.get("buildkite_target_url_env") or "E2E_ESTC_BUILDKITE_TARGET_URL"
        )
        override = os.environ.get(override_env, "").strip()
        if not override and not buildkite_api_token(cfg):
            bk = _buildkite_cfg(cfg)
            token_env = str(bk.get("token_env") or "E2E_BUILDKITE_API_TOKEN")
            return {
                "workflow_id": workflow_id,
                "case_id": case.get("id", case_dir.name),
                "layer": "e2e",
                "mode": "live",
                "agent_invoked": False,
                "blocked": True,
                "block_reason": (
                    f"Missing {token_env} (write_builds + read). "
                    f"Or set {override_env} to a readable failed build URL."
                ),
                "path_gates": {"dashboard_enabled": dashboard_ok},
                "expectations": expectations,
                "run_url": run_url,
            }

    require_open_pr = bool(trigger.get("require_open_pr", True))
    pr_info: dict[str, Any] | None = None
    if require_open_pr:
        pr_info = ensure_e2e_pr(repo, cfg)
        # Refresh OID after possible marker commit.
        refreshed = find_open_e2e_pr(repo, cfg["e2e_pr"]["label"]) or pr_info
        pr_info = refreshed
        sha = pr_info["headRefOid"]
        pr_number = int(pr_info["number"])
        e2e_branch = str(
            (pr_info.get("headRefName") or cfg.get("e2e_pr", {}).get("branch") or "")
        )
    else:
        sha = resolve_no_open_pr_sha(repo)
        pr_number = 0
        e2e_branch = "main"

    target_url: str | None = None
    buildkite_meta: dict[str, Any] | None = None
    if trigger.get("use_buildkite_target_url"):
        if needs_real_failed_buildkite(trigger, expectations):
            try:
                target_url, buildkite_meta = ensure_failed_buildkite_target_url(
                    cfg,
                    commit=sha,
                    branch=e2e_branch or str(cfg.get("e2e_pr", {}).get("branch") or "main"),
                    pr_number=pr_number or None,
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
        else:
            target_url = placeholder_buildkite_url(cfg)
            buildkite_meta = {"source": "placeholder", "web_url": target_url}

    if require_open_pr and trigger.get("clear_prior_detective_comments"):
        clear_detective_comments(repo, pr_number, markers)

    context = str(cfg.get("status_context") or "buildkite/elastic/oblt-aw-e2e")
    if not trigger.get("context_contains_buildkite", True):
        context = "ci/oblt-aw-e2e-non-buildkite"

    state = str(trigger.get("status_state") or "failure")
    description = f"oblt-aw e2e {case.get('id')} {int(time.time())}"
    since = _utc_now().replace(microsecond=0)

    status_payload = post_commit_status(
        repo,
        sha,
        state=state,
        context=context,
        description=description,
        target_url=target_url if trigger.get("use_buildkite_target_url") else None,
    )

    workflow_file = str(
        cfg.get("status_trigger_workflow_file") or "trigger-obs-aw-status.yml"
    )
    timeout = int(cfg.get("poll_timeout_seconds") or 2400)
    interval = int(cfg.get("poll_interval_seconds") or 20)
    expect_job = bool(expectations.get("status_job_executed"))
    poll_timeout = timeout if expect_job else min(180, timeout)

    run_detail = wait_for_new_run(
        repo,
        workflow_file,
        since=since,
        timeout_seconds=poll_timeout,
        interval_seconds=interval,
    )

    job_executed = status_job_executed(run_detail)
    invoked = agent_job_invoked(run_detail)
    comment = None
    if require_open_pr and expectations.get("expect_agent_comment"):
        comment_deadline = time.time() + min(900, timeout)
        while time.time() < comment_deadline and comment is None:
            comment = find_agent_comment(
                repo, pr_number, since=since, markers=markers
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
                        "databaseId,status,conclusion,url,jobs,createdAt",
                    ]
                )
                invoked = agent_job_invoked(run_detail)
            time.sleep(interval)
    elif require_open_pr:
        comment = find_agent_comment(repo, pr_number, since=since, markers=markers)

    path_gates = {
        "dashboard_enabled": dashboard_ok,
        "state_failure": state == "failure",
        "context_contains_buildkite": "buildkite" in context.lower(),
        "has_open_pr": require_open_pr,
        "shared_proceed": dashboard_ok,
        "path_ready": bool(
            state == "failure"
            and "buildkite" in context.lower()
            and require_open_pr
            and dashboard_ok
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
        "pr_number": pr_number or None,
        "pr_url": (pr_info or {}).get("url"),
        "status": {
            "state": state,
            "context": context,
            "target_url": target_url,
            "description": description,
            "api_url": (status_payload or {}).get("url"),
        },
        "buildkite": buildkite_meta,
        "status_trigger": {
            "run_seen": run_detail is not None,
            "job_executed": job_executed,
            "run_id": (run_detail or {}).get("databaseId"),
            "conclusion": (run_detail or {}).get("conclusion"),
            "url": (run_detail or {}).get("url"),
        },
        "agent_comment": comment,
        "path_gates": path_gates,
        "expectations": expectations,
        "run_url": run_url,
        "harness_notes": [
            "Live mode posts a real commit status on elastic/oblt-aw and observes "
            "the production client trigger → orchestrator → wrapper → lock → agent path.",
            "Happy-path Buildkite target_url comes from a freshly created intentional "
            "failure build (or E2E_ESTC_BUILDKITE_TARGET_URL override).",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run estc-pr-buildkite-detective E2E / integration harness."
    )
    parser.add_argument(
        "--mode",
        choices=("fixture", "live"),
        default="live",
        help="live drives production status→agent path; fixture is integration-only.",
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
        help="Root of ESTC detective fixtures/cases",
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

    if args.mode == "live":
        cfg = load_e2e_config(args.config_path)
        outcome = run_live_case(case_dir, cfg, run_url=args.run_url or None)
    else:
        outcome = run_fixture_case(case_dir)
        outcome["run_url"] = args.run_url or None

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
    if args.mode == "fixture":
        return 0 if outcome.get("path_gates", {}).get("path_ready") else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
