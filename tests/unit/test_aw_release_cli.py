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


def test_promote_create_release_from_plan(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = {
        "bootstrap": False,
        "previous_semver": "v0.0.0",
        "semver": "v0.0.1",
        "sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
    plan_path = tmp_path / "promote-plan.json"
    plan_path.write_text(
        json.dumps({"plan": plan}, indent=2) + "\n",
        encoding="utf-8",
    )
    seen: list[dict[str, object]] = []

    def fake_create(
        *,
        semver: str,
        sha: str,
        previous_semver: str = "",
        bootstrap: bool = False,
    ) -> None:
        seen.append(
            {
                "bootstrap": bootstrap,
                "previous_semver": previous_semver,
                "semver": semver,
                "sha": sha,
            }
        )

    monkeypatch.setattr(promote_cli, "create_github_release", fake_create)
    assert promote_cli.main(["--create-release-from-plan", str(plan_path)]) == 0
    assert seen == [
        {
            "bootstrap": False,
            "previous_semver": "v0.0.0",
            "semver": "v0.0.1",
            "sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        }
    ]


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


def test_promote_skips_immutable_create_when_tag_already_at_sha(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sha = "a" * 40
    pointers = {
        "schema_version": 1,
        "major": 0,
        "tags": {"current": "v0", "next": "next", "previous": "previous"},
        "pointers": {
            "current": {"sha": "", "semver": "", "updated_at": ""},
            "next": {"sha": "", "semver": "", "updated_at": ""},
            "previous": {"sha": "", "semver": "", "updated_at": ""},
        },
    }
    pointers_path = tmp_path / "release-pointers.json"
    pointers_path.write_text(json.dumps(pointers) + "\n", encoding="utf-8")
    moved: list[str] = []

    monkeypatch.setattr(promote_cli, "resolve_sha", lambda ref: sha)
    monkeypatch.setattr(
        promote_cli, "require_ancestor_of", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        promote_cli,
        "create_immutable_semver_tag",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        promote_cli,
        "move_tag",
        lambda tag, target, *, message: moved.append(tag),
    )
    monkeypatch.setattr(promote_cli, "utc_now_iso", lambda: "2026-01-01T00:00:00+00:00")

    assert (
        promote_cli.main(
            [
                "--sha",
                sha,
                "--release-type",
                "patch",
                "--pointers-path",
                str(pointers_path),
                "--require-ancestor-of",
                "origin/main",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "already points at" in out
    assert moved == ["previous", "v0", "next"]
    saved = json.loads(pointers_path.read_text(encoding="utf-8"))
    assert saved["pointers"]["current"]["sha"] == sha
    assert saved["pointers"]["current"]["semver"] == "v0.0.0"
