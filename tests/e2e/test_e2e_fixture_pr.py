"""Unit tests for shared E2E fixture PR draft helpers."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import e2e_fixture_pr as fixture_pr


class _Proc:
    def __init__(self, code: int = 0, out: str = "", err: str = "") -> None:
        self.returncode = code
        self.stdout = out
        self.stderr = err


def test_ensure_pr_is_draft_noop_when_already_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_k: object) -> _Proc:
        calls.append(list(cmd))
        if cmd[:3] == ["gh", "pr", "view"]:
            return _Proc(
                0,
                out=json.dumps(
                    {
                        "number": 10,
                        "url": "https://example.test/pr/10",
                        "isDraft": True,
                        "state": "OPEN",
                    }
                ),
            )
        raise AssertionError(cmd)

    monkeypatch.setattr(fixture_pr.subprocess, "run", fake_run)
    pr = fixture_pr.ensure_pr_is_draft("elastic/oblt-aw", 10)
    assert pr["isDraft"] is True
    assert not any(c[:3] == ["gh", "pr", "ready"] for c in calls)


def test_ensure_pr_is_draft_converts_ready_pr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    views = {"n": 0}

    def fake_run(cmd: list[str], **_k: object) -> _Proc:
        calls.append(list(cmd))
        if cmd[:3] == ["gh", "pr", "view"]:
            views["n"] += 1
            draft = views["n"] > 1
            return _Proc(
                0,
                out=json.dumps(
                    {
                        "number": 10,
                        "url": "https://example.test/pr/10",
                        "isDraft": draft,
                        "state": "OPEN",
                    }
                ),
            )
        if cmd[:3] == ["gh", "pr", "ready"] and "--undo" in cmd:
            return _Proc(0)
        raise AssertionError(cmd)

    monkeypatch.setattr(fixture_pr.subprocess, "run", fake_run)
    pr = fixture_pr.ensure_pr_is_draft("elastic/oblt-aw", 10)
    assert pr["isDraft"] is True
    assert any(c[:3] == ["gh", "pr", "ready"] and "--undo" in c for c in calls)


def test_ensure_pr_is_draft_fails_closed_on_convert_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: list[str], **_k: object) -> _Proc:
        if cmd[:3] == ["gh", "pr", "view"]:
            return _Proc(
                0,
                out=json.dumps(
                    {
                        "number": 10,
                        "url": "https://example.test/pr/10",
                        "isDraft": False,
                        "state": "OPEN",
                    }
                ),
            )
        if cmd[:3] == ["gh", "pr", "ready"]:
            return _Proc(1, err="permission denied")
        raise AssertionError(cmd)

    monkeypatch.setattr(fixture_pr.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="converting to draft failed"):
        fixture_pr.ensure_pr_is_draft("elastic/oblt-aw", 10)


def test_ensure_pr_is_draft_fails_closed_when_still_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: list[str], **_k: object) -> _Proc:
        if cmd[:3] == ["gh", "pr", "view"]:
            return _Proc(
                0,
                out=json.dumps(
                    {
                        "number": 10,
                        "url": "https://example.test/pr/10",
                        "isDraft": False,
                        "state": "OPEN",
                    }
                ),
            )
        if cmd[:3] == ["gh", "pr", "ready"]:
            return _Proc(0)
        raise AssertionError(cmd)

    monkeypatch.setattr(fixture_pr.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="still ready for review"):
        fixture_pr.ensure_pr_is_draft("elastic/oblt-aw", 10)
