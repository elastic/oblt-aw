"""Tests for scripts/aw_release_prepare_pointers_branch.sh helpers."""

from __future__ import annotations

import pathlib
import shlex
import subprocess

import pytest

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "scripts"
    / "aw_release_prepare_pointers_branch.sh"
)
POINTERS = "config/release-pointers.json"


def _bash(
    function_call: str,
    *,
    cwd: pathlib.Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{SCRIPT}" && {function_call}'],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )


def _call(
    function: str,
    *args: str,
    cwd: pathlib.Path | None = None,
) -> subprocess.CompletedProcess[str]:
    quoted = " ".join(shlex.quote(a) for a in args)
    return _bash(f"{function} {quoted}", cwd=cwd)


def _git(cwd: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def pointer_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / "config").mkdir()
    (repo / POINTERS).write_text('{"version":1,"current":"aaa"}\n', encoding="utf-8")
    _git(repo, "add", POINTERS)
    _git(repo, "commit", "-m", "base pointers")
    return repo


def test_require_pointers_base_matches_tip_when_identical(
    pointer_repo: pathlib.Path,
) -> None:
    base = _git(pointer_repo, "rev-parse", "HEAD")
    _git(pointer_repo, "commit", "--allow-empty", "-m", "unrelated tip advance")
    tip = "HEAD"
    result = _call(
        "aw_release_require_pointers_base_matches_tip",
        base,
        tip,
        POINTERS,
        cwd=pointer_repo,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_require_pointers_base_matches_tip_rejects_divergence(
    pointer_repo: pathlib.Path,
) -> None:
    base = _git(pointer_repo, "rev-parse", "HEAD")
    (pointer_repo / POINTERS).write_text(
        '{"version":1,"current":"bbb"}\n',
        encoding="utf-8",
    )
    _git(pointer_repo, "add", POINTERS)
    _git(pointer_repo, "commit", "-m", "newer tip pointers")
    result = _call(
        "aw_release_require_pointers_base_matches_tip",
        base,
        "HEAD",
        POINTERS,
        cwd=pointer_repo,
    )
    assert result.returncode == 1, result.stdout
    assert "differs from plan base" in result.stdout + result.stderr


def test_require_pointers_base_matches_tip_rejects_presence_mismatch(
    pointer_repo: pathlib.Path,
) -> None:
    base = _git(pointer_repo, "rev-parse", "HEAD")
    _git(pointer_repo, "rm", POINTERS)
    _git(pointer_repo, "commit", "-m", "drop pointers on tip")
    result = _call(
        "aw_release_require_pointers_base_matches_tip",
        base,
        "HEAD",
        POINTERS,
        cwd=pointer_repo,
    )
    assert result.returncode == 1, result.stdout
    assert "presence differs" in result.stdout + result.stderr


def test_prepare_stays_on_default_branch_not_pr_branch(
    tmp_path: pathlib.Path,
) -> None:
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare")

    repo = tmp_path / "work"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / "config").mkdir()
    (repo / POINTERS).write_text('{"version":1,"current":"aaa"}\n', encoding="utf-8")
    _git(repo, "add", POINTERS)
    _git(repo, "commit", "-m", "base pointers")
    _git(repo, "branch", "-M", "main")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "main")
    plan_base = _git(repo, "rev-parse", "HEAD")

    planned = '{"version":1,"current":"promoted"}\n'
    (repo / POINTERS).write_text(planned, encoding="utf-8")

    github_output = tmp_path / "github_output"
    runner_temp = tmp_path / "runner_temp"
    runner_temp.mkdir()

    result = _call(
        "aw_release_prepare_pointers_branch",
        "main",
        plan_base,
        "release/pointers",
        "37283431427",
        POINTERS,
        str(github_output),
        str(runner_temp),
        cwd=repo,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert _git(repo, "symbolic-ref", "--short", "HEAD") == "main"
    local_branches = _git(repo, "branch", "--list")
    assert "release/pointers-37283431427" not in local_branches
    assert (repo / POINTERS).read_text(encoding="utf-8") == planned
    assert "has_changes=true" in github_output.read_text(encoding="utf-8")
    assert "for release/pointers-37283431427" in result.stdout


def test_require_pointers_base_matches_tip_ok_when_both_absent(
    tmp_path: pathlib.Path,
) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / "README").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "no pointers")
    base = _git(repo, "rev-parse", "HEAD")
    result = _call(
        "aw_release_require_pointers_base_matches_tip",
        base,
        "HEAD",
        POINTERS,
        cwd=repo,
    )
    assert result.returncode == 0, result.stderr + result.stdout
