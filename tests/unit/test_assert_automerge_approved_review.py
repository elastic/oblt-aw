"""Tests for scripts/obs/assert_automerge_approved_review.sh."""

from __future__ import annotations

import json
import pathlib
import shlex
import subprocess

import pytest

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "scripts"
    / "obs"
    / "assert_automerge_approved_review.sh"
)

_HEAD = "0123456789abcdef0123456789abcdef01234567"
_OTHER = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_AUTHOR = "github-actions[bot]"
_APPROVER = "elastic-vault-github-plugin-prod[bot]"


def _bash(function_call: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{SCRIPT}" && {function_call}'],
        capture_output=True,
        text=True,
        check=False,
    )


def _has_approval(
    reviews: list[dict], *, author: str = _AUTHOR, sha: str = _HEAD
) -> subprocess.CompletedProcess[str]:
    payload = shlex.quote(json.dumps(reviews))
    return _bash(
        f"automerge_reviews_have_non_author_approval {payload} "
        f"{shlex.quote(author)} {shlex.quote(sha)}"
    )


def _review(
    *,
    state: str,
    login: str,
    commit_id: str = _HEAD,
    review_id: int = 1,
) -> dict:
    return {
        "id": review_id,
        "state": state,
        "user": {"login": login},
        "commit_id": commit_id,
    }


def test_approved_non_author_for_head_passes() -> None:
    result = _has_approval(
        [_review(state="APPROVED", login=_APPROVER)],
    )
    assert result.returncode == 0, result.stderr


def test_comment_only_fails() -> None:
    result = _has_approval(
        [_review(state="COMMENTED", login=_APPROVER)],
    )
    assert result.returncode == 1, result.stdout


def test_empty_reviews_fails() -> None:
    result = _has_approval([])
    assert result.returncode == 1, result.stdout


def test_self_approve_alone_fails() -> None:
    result = _has_approval(
        [_review(state="APPROVED", login=_AUTHOR)],
    )
    assert result.returncode == 1, result.stdout


def test_approved_on_other_sha_fails() -> None:
    result = _has_approval(
        [_review(state="APPROVED", login=_APPROVER, commit_id=_OTHER)],
    )
    assert result.returncode == 1, result.stdout


def test_case_insensitive_approved_state() -> None:
    result = _has_approval(
        [_review(state="approved", login=_APPROVER)],
    )
    assert result.returncode == 0, result.stderr


def test_invalid_sha_fails_closed() -> None:
    payload = shlex.quote(json.dumps([_review(state="APPROVED", login=_APPROVER)]))
    result = _bash(
        f"automerge_reviews_have_non_author_approval {payload} "
        f"{shlex.quote(_AUTHOR)} not-a-sha"
    )
    assert result.returncode == 1
    assert "40-hex" in result.stderr


@pytest.mark.parametrize(
    "state",
    ["CHANGES_REQUESTED", "DISMISSED", "PENDING"],
)
def test_non_approved_states_fail(state: str) -> None:
    result = _has_approval([_review(state=state, login=_APPROVER)])
    assert result.returncode == 1, result.stdout
