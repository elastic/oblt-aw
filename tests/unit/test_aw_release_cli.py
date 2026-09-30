"""Unit tests for scripts/aw_release_promote.py and aw_release_rollback.py."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import aw_release_promote as promote_cli
import aw_release_rollback as rollback_cli


def test_promote_push_from_plan(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = {
        "semver": "v0.0.1",
        "current_tag": "v0",
        "next_tag": "next",
        "previous_tag": "previous",
    }
    plan_path = tmp_path / "promote-plan.json"
    plan_path.write_text(
        json.dumps({"plan": plan}, indent=2) + "\n",
        encoding="utf-8",
    )
    seen: list[dict[str, object]] = []

    def fake_push(p: dict[str, object], *, remote: str = "origin") -> None:
        del remote
        seen.append(p)

    monkeypatch.setattr(promote_cli, "push_promote_tags", fake_push)
    assert promote_cli.main(["--push-from-plan", str(plan_path)]) == 0
    assert seen == [plan]


def test_rollback_push_from_plan(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = {
        "current_tag": "v0",
        "next_tag": "next",
        "previous_tag": "previous",
    }
    plan_path = tmp_path / "rollback-plan.json"
    plan_path.write_text(
        json.dumps({"plan": plan}, indent=2) + "\n",
        encoding="utf-8",
    )
    seen: list[dict[str, object]] = []

    def fake_push(p: dict[str, object], *, remote: str = "origin") -> None:
        del remote
        seen.append(p)

    monkeypatch.setattr(rollback_cli, "push_rollback_tags", fake_push)
    assert rollback_cli.main(["--push-from-plan", str(plan_path)]) == 0
    assert seen == [plan]


def test_promote_requires_sha_without_push_from_plan() -> None:
    with pytest.raises(SystemExit) as exc:
        promote_cli.main(["--release-type", "patch"])
    assert exc.value.code == 2
