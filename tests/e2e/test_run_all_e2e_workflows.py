"""Unit tests for leaf E2E discovery and dispatch orchestration."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import run_all_e2e_workflows as runner


def test_discover_excludes_orchestrator_and_sorts(tmp_path: pathlib.Path) -> None:
    (tmp_path / "e2e-b.yml").write_text("on:\n  workflow_dispatch:\n", encoding="utf-8")
    (tmp_path / "e2e-a.yml").write_text("on:\n  workflow_dispatch:\n", encoding="utf-8")
    (tmp_path / "e2e-all.yml").write_text(
        "on:\n  workflow_dispatch:\n", encoding="utf-8"
    )
    (tmp_path / "ci.yml").write_text("on:\n  push:\n", encoding="utf-8")

    found = runner.discover_e2e_workflow_files(tmp_path)
    assert [p.name for p in found] == ["e2e-a.yml", "e2e-b.yml"]


def test_has_workflow_dispatch_variants(tmp_path: pathlib.Path) -> None:
    mapping = tmp_path / "map.yml"
    mapping.write_text("on:\n  workflow_dispatch:\n", encoding="utf-8")
    assert runner.has_workflow_dispatch(mapping)

    listed = tmp_path / "list.yml"
    listed.write_text("on: [push, workflow_dispatch]\n", encoding="utf-8")
    assert runner.has_workflow_dispatch(listed)

    scalar = tmp_path / "scalar.yml"
    scalar.write_text("on: workflow_dispatch\n", encoding="utf-8")
    assert runner.has_workflow_dispatch(scalar)

    push_only = tmp_path / "push.yml"
    push_only.write_text("on:\n  push:\n", encoding="utf-8")
    assert not runner.has_workflow_dispatch(push_only)


def test_require_dispatchable_fails_when_empty(tmp_path: pathlib.Path) -> None:
    with pytest.raises(SystemExit, match="no leaf E2E workflows"):
        runner.require_dispatchable_workflows(
            runner.discover_e2e_workflow_files(tmp_path)
        )


def test_require_dispatchable_fails_without_dispatch(tmp_path: pathlib.Path) -> None:
    (tmp_path / "e2e-bad.yml").write_text("on:\n  push:\n", encoding="utf-8")
    paths = runner.discover_e2e_workflow_files(tmp_path)
    with pytest.raises(SystemExit, match="missing workflow_dispatch"):
        runner.require_dispatchable_workflows(paths)


def test_require_dispatchable_accepts_repo_workflows() -> None:
    paths = runner.require_dispatchable_workflows(
        runner.discover_e2e_workflow_files(ROOT / ".github" / "workflows")
    )
    names = {p.name for p in paths}
    assert "e2e-all.yml" not in names
    assert "e2e-automerge-vm-images.yml" in names
    assert "e2e-estc-pr-buildkite-detective.yml" in names


def test_run_all_aggregates_failure(tmp_path: pathlib.Path) -> None:
    (tmp_path / "e2e-ok.yml").write_text(
        "on:\n  workflow_dispatch:\n", encoding="utf-8"
    )
    (tmp_path / "e2e-fail.yml").write_text(
        "on:\n  workflow_dispatch:\n", encoding="utf-8"
    )

    created = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    calls: list[list[str]] = []

    def fake_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if argv[:2] == ["workflow", "run"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:2] == ["run", "list"]:
            workflow = argv[argv.index("--workflow") + 1]
            run_id = 11 if workflow == "e2e-ok.yml" else 22
            payload = [
                {
                    "databaseId": run_id,
                    "url": f"https://example.test/{run_id}",
                    "status": "completed",
                    "conclusion": "success" if run_id == 11 else "failure",
                    "createdAt": created,
                    "headBranch": "main",
                    "event": "workflow_dispatch",
                }
            ]
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")
        if argv[:2] == ["run", "view"]:
            run_id = int(argv[2])
            payload = {
                "databaseId": run_id,
                "url": f"https://example.test/{run_id}",
                "status": "completed",
                "conclusion": "success" if run_id == 11 else "failure",
            }
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")
        raise AssertionError(f"unexpected gh argv: {argv}")

    # Freeze "now" so find_dispatched_run accepts createdAt.
    original_utc = runner._utc_now
    runner._utc_now = lambda: datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    try:
        code = runner.run_all(
            workflows_dir=tmp_path,
            repo="elastic/oblt-aw",
            ref="main",
            gh=fake_gh,
        )
    finally:
        runner._utc_now = original_utc

    assert code == 1
    dispatched = [c for c in calls if c[:2] == ["workflow", "run"]]
    assert {c[2] for c in dispatched} == {"e2e-ok.yml", "e2e-fail.yml"}
