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

"""Fixture-mode E2E harness for obs:estc-pr-buildkite-detective.

Simulates the status-failure path into the detective pre-agent Buildkite
resolution step using recorded fixtures. Does not invoke a live agent model.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

WORKFLOW_ID = "obs:estc-pr-buildkite-detective"
BK_URL_RE = re.compile(r"https://buildkite\.com/([^/]+)/([^/]+)/builds/(\d+)")
ANSI_RE = re.compile(
    r"\x1b(?:\[[0-9;]*[A-Za-z]|_[^\x07]*\x07|[()][AB012]|[=>])"
)
FAIL_STATES = ("failed", "timed_out")
LOG_TAIL = 150


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"\s+", "-", cleaned).lower()[:60].strip("-")


def evaluate_status_gates(event: dict[str, Any]) -> dict[str, Any]:
    """Mirror obs-aw-event-status / wrapper status filters."""
    event_name = "status"
    state = event.get("state")
    context = event.get("context") or ""
    return {
        "event_name": event_name,
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
        # Default key matches pipeline-slugify(job name) for the fixture build.
        job_logs["sandbox-ci-unit-tests"] = job_log_path.read_text(encoding="utf-8")
        job_logs["unit-tests"] = job_logs["sandbox-ci-unit-tests"]

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
        "layer": "e2e",
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
            "Fixture mode exercises status-failure gating and recorded Buildkite "
            "resolution only; it does not call the live GH-AW agent/lock.",
        ],
    }


def run_live_blocked(case_id: str, sandbox_repo: str | None) -> dict[str, Any]:
    return {
        "workflow_id": WORKFLOW_ID,
        "case_id": case_id,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": False,
        "pass": False,
        "blocked": True,
        "block_reason": (
            "Live sandbox E2E is not wired yet. Sandbox consumer repository is "
            "Unknown (recommended: elastic/oblt-aw-sandbox). See "
            "docs/testing/estc-pr-buildkite-detective-e2e.md."
        ),
        "sandbox_repo": sandbox_repo or "Unknown",
        "path_gates": {},
        "buildkite": {"ok": False, "error": "live mode blocked"},
        "expectations": {},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run estc-pr-buildkite-detective E2E harness (fixture or live)."
    )
    parser.add_argument(
        "--mode",
        choices=("fixture", "live"),
        default="fixture",
        help="fixture uses recorded payloads; live requires a sandbox (Unknown).",
    )
    parser.add_argument(
        "--case-id",
        default="status-failure-open-pr",
        help="Case directory name under testdata/.../cases/",
    )
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/estc-pr-buildkite-detective"),
        help="Root of ESTC detective E2E fixtures",
    )
    parser.add_argument(
        "--outcome-path",
        type=Path,
        required=True,
        help="Where to write the machine-readable harness outcome JSON",
    )
    parser.add_argument(
        "--sandbox-repo",
        default="",
        help="Optional sandbox consumer owner/name for live mode",
    )
    parser.add_argument(
        "--run-url",
        default="",
        help="Optional GitHub Actions run URL to embed in the outcome",
    )
    args = parser.parse_args(argv)

    if args.mode == "live":
        outcome = run_live_blocked(args.case_id, args.sandbox_repo or None)
        outcome["run_url"] = args.run_url or None
        args.outcome_path.parent.mkdir(parents=True, exist_ok=True)
        args.outcome_path.write_text(
            json.dumps(outcome, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"mode": "live", "blocked": True}, indent=2))
        return 2

    case_dir = args.testdata_root / "cases" / args.case_id
    if not case_dir.is_dir():
        raise SystemExit(f"Case directory not found: {case_dir}")

    outcome = run_fixture_case(case_dir)
    outcome["run_url"] = args.run_url or None
    args.outcome_path.parent.mkdir(parents=True, exist_ok=True)
    args.outcome_path.write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote harness outcome to {args.outcome_path}")
    return 0 if outcome["path_gates"].get("path_ready") else 1


if __name__ == "__main__":
    sys.exit(main())
