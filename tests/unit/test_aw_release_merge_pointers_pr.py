"""Tests for scripts/aw_release_merge_pointers_pr.sh helpers."""

from __future__ import annotations

import pathlib
import shlex
import subprocess

import pytest

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "scripts"
    / "aw_release_merge_pointers_pr.sh"
)


def _bash(function_call: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{SCRIPT}" && {function_call}'],
        capture_output=True,
        text=True,
        check=False,
    )


def _call(function: str, *args: str) -> subprocess.CompletedProcess[str]:
    quoted = " ".join(shlex.quote(a) for a in args)
    return _bash(f"{function} {quoted}")


@pytest.mark.parametrize(
    "message",
    [
        "Required status checks are not yet complete.",
        "Pull Request is not mergeable",
        "Reviews are required before merging",
        "waiting for Copilot code review",
        "Base branch was modified",
        "Must be green before merging",
    ],
)
def test_merge_error_is_retryable_matches(message: str) -> None:
    result = _call("aw_release_merge_error_is_retryable", message)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "message",
    [
        "Resource not accessible by integration",
        "HTTP 403: Forbidden",
        "Validation Failed: unexpected",
        "",
    ],
)
def test_merge_error_is_retryable_rejects(message: str) -> None:
    result = _call("aw_release_merge_error_is_retryable", message)
    assert result.returncode == 1, result.stdout + result.stderr
