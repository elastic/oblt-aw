"""Tests for scripts/obs/automerge_armed_lib.sh merge-error classifiers."""

from __future__ import annotations

import pathlib
import shlex
import subprocess

import pytest

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "scripts"
    / "obs"
    / "automerge_armed_lib.sh"
)

_VALID_SHA = "0123456789abcdef0123456789abcdef01234567"


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
        (
            "Merge commits are not allowed on this repository. Required status check "
            '"ci / build" is pending.'
        ),
        "Pull Request is not mergeable: required status checks have not succeeded.",
        "GitHub Actions is awaiting status checks before merging.",
        "Required status checks are not yet complete.",
        "status checks have not passed yet",
        "Must be green before merging",
        "Blocked: something pending on the base branch",
    ],
)
def test_merge_error_is_pending_checks_matches_retryable(message: str) -> None:
    result = _call("automerge_merge_error_is_pending_checks", message)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "message",
    [
        "Pull Request is not mergeable",
        "Resource not accessible by integration",
        'Validation Failed: {"message":"Base branch was modified"}',
        "HTTP 405: Method Not Allowed",
        "Pull request is not open",
        "already been merged",
        "",
    ],
)
def test_merge_error_is_pending_checks_rejects_non_retryable(message: str) -> None:
    result = _call("automerge_merge_error_is_pending_checks", message)
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize(
    "message",
    [
        "Pull Request already been merged",
        "Error: This pull request has already been merged.",
    ],
)
def test_merge_error_is_already_merged_message_matches(message: str) -> None:
    result = _call("automerge_merge_error_is_already_merged_message", message)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "message",
    [
        "Pull Request is not mergeable",
        "Pull request is closed",
        "required status check is pending",
        "",
    ],
)
def test_merge_error_is_already_merged_message_rejects_other(message: str) -> None:
    result = _call("automerge_merge_error_is_already_merged_message", message)
    assert result.returncode == 1, result.stdout + result.stderr


def test_armed_marker_line_accepts_40_hex_sha() -> None:
    result = _call("automerge_armed_marker_line", _VALID_SHA)
    assert result.returncode == 0
    assert result.stdout == f"<!-- obs-aw-automerge:armed sha={_VALID_SHA} -->"


@pytest.mark.parametrize(
    "sha",
    [
        "abc",
        "0123456789ABCDEF0123456789abcdef01234567",  # uppercase rejected
        "0123456789abcdef0123456789abcdef0123456",  # 39 hex
        "0123456789abcdef0123456789abcdef012345678",  # 41 hex
        "g123456789abcdef0123456789abcdef01234567",
    ],
)
def test_armed_marker_line_rejects_invalid_sha(sha: str) -> None:
    result = _call("automerge_armed_marker_line", sha)
    assert result.returncode == 1
    assert "expected 40-hex sha" in result.stderr


_OTHER_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_BOT = "github-actions[bot]"


def _armed_comments_json(
    *, first_sha: str, first_id: int, second_sha: str, second_id: int
) -> str:
    """Two bot armed markers; first entry is intentionally a different head SHA."""
    return (
        "["
        f'{{"id":{first_id},"user":{{"login":"{_BOT}"}},'
        f'"body":"<!-- obs-aw-automerge:armed sha={first_sha} -->\\n\\nold"}},'
        f'{{"id":{second_id},"user":{{"login":"{_BOT}"}},'
        f'"body":"<!-- obs-aw-automerge:armed sha={second_sha} -->\\n\\ncurrent"}}'
        "]"
    )


def test_find_bot_armed_comment_id_matches_exact_sha_only() -> None:
    comments = _armed_comments_json(
        first_sha=_OTHER_SHA,
        first_id=101,
        second_sha=_VALID_SHA,
        second_id=202,
    )
    result = _call(
        "automerge_find_bot_armed_comment_id_from_json",
        comments,
        _VALID_SHA,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "202"


def test_find_bot_armed_comment_id_ignores_other_head_sha() -> None:
    """Must not return the first marker when selecting a newer head SHA."""
    comments = _armed_comments_json(
        first_sha=_OTHER_SHA,
        first_id=101,
        second_sha=_VALID_SHA,
        second_id=202,
    )
    result = _call(
        "automerge_find_bot_armed_comment_id_from_json",
        comments,
        _OTHER_SHA,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "101"


def test_find_bot_armed_comment_id_empty_when_sha_absent() -> None:
    missing = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    comments = _armed_comments_json(
        first_sha=_OTHER_SHA,
        first_id=101,
        second_sha=_VALID_SHA,
        second_id=202,
    )
    result = _call(
        "automerge_find_bot_armed_comment_id_from_json",
        comments,
        missing,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
