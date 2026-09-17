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

"""Discover and run every leaf E2E workflow (e2e-*.yml except the orchestrator)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ORCHESTRATOR_FILENAME = "e2e-all.yml"
DEFAULT_WORKFLOWS_DIR = Path(".github/workflows")
TERMINAL_STATUSES = frozenset({"completed", "cancelled"})
POLL_SECONDS = 15


@dataclass(frozen=True)
class DispatchedRun:
    workflow_file: str
    run_id: int
    url: str


@dataclass(frozen=True)
class FinishedRun:
    workflow_file: str
    run_id: int
    url: str
    conclusion: str


GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _default_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *argv],
        check=False,
        capture_output=True,
        text=True,
    )


def discover_e2e_workflow_files(
    workflows_dir: Path,
    *,
    orchestrator_filename: str = ORCHESTRATOR_FILENAME,
) -> list[Path]:
    """Return sorted leaf E2E workflow paths under ``workflows_dir``."""
    if not workflows_dir.is_dir():
        raise SystemExit(f"workflows directory not found: {workflows_dir}")

    found: list[Path] = []
    for path in sorted(workflows_dir.glob("e2e-*.yml")):
        if path.name == orchestrator_filename:
            continue
        if not path.is_file():
            continue
        found.append(path)
    return found


def has_workflow_dispatch(path: Path) -> bool:
    """Return True when the workflow declares ``on.workflow_dispatch``."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return False
    on = raw.get("on")
    if on is None:
        on = raw.get(True)  # YAML 1.1 may parse bare `on:` as boolean True
    if on == "workflow_dispatch":
        return True
    if isinstance(on, list):
        return "workflow_dispatch" in on
    if isinstance(on, dict):
        return "workflow_dispatch" in on
    return False


def require_dispatchable_workflows(paths: list[Path]) -> list[Path]:
    """Fail closed when no leaf workflows exist or any lack workflow_dispatch."""
    if not paths:
        raise SystemExit(
            "no leaf E2E workflows found "
            f"(expected .github/workflows/e2e-*.yml except {ORCHESTRATOR_FILENAME})"
        )
    missing = [p.name for p in paths if not has_workflow_dispatch(p)]
    if missing:
        raise SystemExit(
            "leaf E2E workflow(s) missing workflow_dispatch: " + ", ".join(missing)
        )
    return paths


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _gh_json(gh: GhRunner, argv: list[str]) -> Any:
    proc = gh(argv)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"gh {' '.join(argv)} failed: {detail}")
    return json.loads(proc.stdout)


def dispatch_workflow(
    workflow_file: str,
    *,
    repo: str,
    ref: str,
    gh: GhRunner,
) -> None:
    proc = gh(
        [
            "workflow",
            "run",
            workflow_file,
            "--repo",
            repo,
            "--ref",
            ref,
        ]
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"failed to dispatch {workflow_file}: {detail}")


def find_dispatched_run(
    workflow_file: str,
    *,
    repo: str,
    ref: str,
    dispatched_at: datetime,
    gh: GhRunner,
    timeout_seconds: int = 180,
    poll_seconds: int = POLL_SECONDS,
) -> DispatchedRun:
    """Locate the workflow_dispatch run created at or after ``dispatched_at``."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        runs = _gh_json(
            gh,
            [
                "run",
                "list",
                "--workflow",
                workflow_file,
                "--repo",
                repo,
                "--event",
                "workflow_dispatch",
                "--limit",
                "20",
                "--json",
                "databaseId,url,status,conclusion,createdAt,headBranch,event",
            ],
        )
        if not isinstance(runs, list):
            raise TypeError(
                f"unexpected run list payload for {workflow_file}: {type(runs).__name__}"
            )
        for item in runs:
            if not isinstance(item, dict):
                continue
            created_raw = str(item.get("createdAt") or "")
            if not created_raw:
                continue
            created = _parse_iso8601(created_raw)
            if created < dispatched_at:
                continue
            head_branch = str(item.get("headBranch") or "")
            if head_branch and head_branch != ref:
                continue
            return DispatchedRun(
                workflow_file=workflow_file,
                run_id=int(item["databaseId"]),
                url=str(item.get("url") or ""),
            )
        time.sleep(poll_seconds)
    raise TimeoutError(
        f"timed out waiting for dispatched run of {workflow_file} on ref {ref}"
    )


def wait_for_run(
    run: DispatchedRun,
    *,
    repo: str,
    gh: GhRunner,
    timeout_seconds: int = 10_800,
    poll_seconds: int = POLL_SECONDS,
) -> FinishedRun:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        payload = _gh_json(
            gh,
            [
                "run",
                "view",
                str(run.run_id),
                "--repo",
                repo,
                "--json",
                "databaseId,url,status,conclusion",
            ],
        )
        if not isinstance(payload, dict):
            raise TypeError(
                f"unexpected run view payload for {run.workflow_file}: "
                f"{type(payload).__name__}"
            )
        status = str(payload.get("status") or "")
        if status in TERMINAL_STATUSES:
            conclusion = str(payload.get("conclusion") or "")
            return FinishedRun(
                workflow_file=run.workflow_file,
                run_id=run.run_id,
                url=str(payload.get("url") or run.url),
                conclusion=conclusion or "unknown",
            )
        time.sleep(poll_seconds)
    raise TimeoutError(
        f"timed out waiting for {run.workflow_file} run {run.run_id} to finish"
    )


def dispatch_and_wait(
    workflow_file: str,
    *,
    repo: str,
    ref: str,
    gh: GhRunner,
) -> FinishedRun:
    dispatched_at = _utc_now()
    # Small skew cushion so createdAt comparisons are not flaky.
    dispatched_at = dispatched_at.replace(microsecond=0)
    dispatch_workflow(workflow_file, repo=repo, ref=ref, gh=gh)
    run = find_dispatched_run(
        workflow_file,
        repo=repo,
        ref=ref,
        dispatched_at=dispatched_at,
        gh=gh,
    )
    print(f"dispatched {workflow_file}: {run.url}", flush=True)
    finished = wait_for_run(run, repo=repo, gh=gh)
    print(
        f"finished {workflow_file}: conclusion={finished.conclusion} {finished.url}",
        flush=True,
    )
    return finished


def run_all(
    *,
    workflows_dir: Path,
    repo: str,
    ref: str,
    gh: GhRunner | None = None,
) -> int:
    runner = gh or _default_gh
    paths = require_dispatchable_workflows(discover_e2e_workflow_files(workflows_dir))
    names = [p.name for p in paths]
    print(f"running {len(names)} E2E workflow(s): {', '.join(names)}", flush=True)

    results: list[FinishedRun] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, len(names))) as pool:
        futures = {
            pool.submit(
                dispatch_and_wait,
                name,
                repo=repo,
                ref=ref,
                gh=runner,
            ): name
            for name in names
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - surface any worker failure
                errors.append(f"{name}: {exc}")

    print("\nE2E summary:", flush=True)
    failed = False
    for item in sorted(results, key=lambda r: r.workflow_file):
        mark = "ok" if item.conclusion == "success" else "FAIL"
        if item.conclusion != "success":
            failed = True
        print(
            f"  [{mark}] {item.workflow_file} conclusion={item.conclusion} {item.url}",
            flush=True,
        )
    for err in errors:
        failed = True
        print(f"  [FAIL] {err}", flush=True)

    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Discover and run all leaf E2E workflows in parallel."
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=DEFAULT_WORKFLOWS_DIR,
        help="Directory containing workflow YAML files",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository (owner/name)",
    )
    parser.add_argument(
        "--ref",
        required=True,
        help="Git ref to dispatch each leaf workflow on",
    )
    args = parser.parse_args(argv)
    return run_all(workflows_dir=args.workflows_dir, repo=args.repo, ref=args.ref)


if __name__ == "__main__":
    sys.exit(main())
