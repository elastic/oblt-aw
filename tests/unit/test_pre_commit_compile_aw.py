"""Tests for scripts/pre_commit_compile_aw.sh lock drift detection."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import textwrap

import pytest

SCRIPT_SRC = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "pre_commit_compile_aw.sh"
)
LOCK_REL = pathlib.Path(".github/workflows/example.lock.yml")


def _git(cwd: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _write_makefile(repo: pathlib.Path, body: str) -> None:
    (repo / "Makefile").write_text(textwrap.dedent(body), encoding="utf-8")


@pytest.fixture
def compile_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    # Avoid "dubious ownership" noise in sandboxes.
    _git(repo, "config", "commit.gpgsign", "false")

    scripts = repo / "scripts"
    scripts.mkdir()
    shutil.copy2(SCRIPT_SRC, scripts / "pre_commit_compile_aw.sh")

    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "example.lock.yml").write_text("name: example\n", encoding="utf-8")
    _git(repo, "add", str(LOCK_REL), "scripts/pre_commit_compile_aw.sh")
    _git(repo, "commit", "-m", "base lock")
    return repo


def _run_hook(repo: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/pre_commit_compile_aw.sh"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


def test_unstaged_regenerated_tracked_lock_fails(compile_repo: pathlib.Path) -> None:
    _write_makefile(
        compile_repo,
        """\
        .PHONY: compile-aw
        compile-aw:
        \t@printf 'name: regenerated\\n' > .github/workflows/example.lock.yml
        """,
    )
    result = _run_hook(compile_repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "gh-aw lock files were regenerated" in result.stdout
    assert str(LOCK_REL) in result.stdout


def test_untracked_regenerated_lock_fails(compile_repo: pathlib.Path) -> None:
    _write_makefile(
        compile_repo,
        """\
        .PHONY: compile-aw
        compile-aw:
        \t@printf 'name: new\\n' > .github/workflows/new.lock.yml
        """,
    )
    result = _run_hook(compile_repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "gh-aw lock files were regenerated" in result.stdout
    assert "new.lock.yml" in result.stdout


def test_staged_matching_locks_succeed_on_rerun(compile_repo: pathlib.Path) -> None:
    _write_makefile(
        compile_repo,
        """\
        .PHONY: compile-aw
        compile-aw:
        \t@printf 'name: regenerated\\n' > .github/workflows/example.lock.yml
        """,
    )
    first = _run_hook(compile_repo)
    assert first.returncode == 1, first.stdout + first.stderr
    _git(compile_repo, "add", str(LOCK_REL))

    # Next compile is a no-op; staged lock matches the worktree.
    _write_makefile(
        compile_repo,
        """\
        .PHONY: compile-aw
        compile-aw:
        \t@true
        """,
    )
    second = _run_hook(compile_repo)
    assert second.returncode == 0, second.stdout + second.stderr


def test_compile_failure_propagates(compile_repo: pathlib.Path) -> None:
    _write_makefile(
        compile_repo,
        """\
        .PHONY: compile-aw
        compile-aw:
        \t@echo compile failed >&2
        \t@exit 2
        """,
    )
    result = _run_hook(compile_repo)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "compile failed" in result.stderr
