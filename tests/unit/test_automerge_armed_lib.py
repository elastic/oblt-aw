"""Tests for scripts/obs/automerge_armed_lib.sh merge-error classifiers."""

from __future__ import annotations

import os
import pathlib
import shlex
import subprocess
import textwrap

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "obs" / "automerge_armed_lib.sh"
ASSERT_SCRIPT = ROOT / "scripts" / "obs" / "assert_automerge_approved_review.sh"

_VALID_SHA = "0123456789abcdef0123456789abcdef01234567"
_OTHER_SHA_HEAD = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _bash(function_call: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{SCRIPT}" && {function_call}'],
        capture_output=True,
        text=True,
        check=False,
    )


def _bash_merge(
    function_call: str, *, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Source assert + armed helpers (squash merge needs require_pr_head_sha)."""
    return subprocess.run(
        [
            "bash",
            "-c",
            f'source "{ASSERT_SCRIPT}" && source "{SCRIPT}" && {function_call}',
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _install_fake_gh(tmp_path: pathlib.Path, script: str) -> dict[str, str]:
    gh_path = tmp_path / "gh"
    gh_path.write_text(textwrap.dedent(script), encoding="utf-8")
    gh_path.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    return env


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


_OTHER_SHA = _OTHER_SHA_HEAD
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


_MERGE_READY_LABELS_JQ = '["oblt-aw/ai/merge-ready"]'
_EMPTY_LABELS_JQ = "[]"
_PR_AUTHOR = "github-actions[bot]"
_APPROVER = "elastic-vault-github-plugin-prod[bot]"


def _approved_reviews_json(*, head_sha: str = _VALID_SHA) -> str:
    return (
        "["
        f'{{"id":1,"state":"APPROVED","user":{{"login":"{_APPROVER}"}},'
        f'"commit_id":"{head_sha}"}}'
        "]"
    )


def _dismissed_after_approved_reviews_json(*, head_sha: str = _VALID_SHA) -> str:
    return (
        "["
        f'{{"id":1,"state":"APPROVED","user":{{"login":"{_APPROVER}"}},'
        f'"commit_id":"{head_sha}"}},'
        f'{{"id":2,"state":"DISMISSED","user":{{"login":"{_APPROVER}"}},'
        f'"commit_id":"{head_sha}"}}'
        "]"
    )


def _fake_gh_squash_script(
    *,
    head_sha: str,
    labels_json: str | None = _MERGE_READY_LABELS_JQ,
    labels_exit: int = 0,
    reviews_json: str | None = None,
    reviews_exit: int = 0,
    allow_merge: bool = True,
    merge_body: str = "",
    merge_exit: int = 0,
) -> str:
    """Stub gh for head SHA, labels, reviews, and optional merge PUT."""
    if reviews_json is None:
        reviews_json = _approved_reviews_json(head_sha=head_sha)
    if allow_merge:
        merge_block = f"""\
        if [[ "$*" == *"pulls/"*"/merge"* ]]; then
          if [[ "$*" != *"sha={head_sha}"* ]]; then
            echo "merge must bind asserted sha; got: $*" >&2
            exit 2
          fi
          if [[ {merge_exit} -ne 0 ]]; then
            echo {shlex.quote(merge_body or "merge failed")} >&2
            exit {merge_exit}
          fi
          echo '{{"merged":true}}'
          exit 0
        fi
        """
    else:
        merge_block = """\
        if [[ "$*" == *"pulls/"*"/merge"* ]]; then
          echo "merge must not run: $*" >&2
          exit 99
        fi
        """
    labels_block = f"""\
        if [[ "$*" == *"--jq"* && "$*" == *".labels"* ]]; then
          if [[ {labels_exit} -ne 0 ]]; then
            echo "label api boom" >&2
            exit {labels_exit}
          fi
          printf '%s\\n' {shlex.quote(labels_json or "[]")}
          exit 0
        fi
        """
    reviews_block = f"""\
        if [[ "${{1:-}}" == "api" && "${{2:-}}" == *"/reviews"* ]]; then
          if [[ {reviews_exit} -ne 0 ]]; then
            echo "reviews api boom" >&2
            exit {reviews_exit}
          fi
          printf '%s\\n' {shlex.quote(reviews_json)}
          exit 0
        fi
        """
    return f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        if [[ "$*" == *"--jq"* && "$*" == *".head.sha"* ]]; then
          printf '%s\\n' {head_sha}
          exit 0
        fi
        {labels_block}
        {reviews_block}
        {merge_block}
        echo "unexpected gh args: $*" >&2
        exit 99
        """


def _squash(sha: str = _VALID_SHA) -> str:
    return f"automerge_squash_merge_at_sha owner/repo 1 {sha} {shlex.quote(_PR_AUTHOR)}"


def test_squash_merge_at_sha_binds_expected_sha(tmp_path: pathlib.Path) -> None:
    """Merge PUT must include -f sha=<asserted>; head drift before merge fails closed."""
    env = _install_fake_gh(
        tmp_path,
        _fake_gh_squash_script(head_sha=_VALID_SHA, merge_body="", merge_exit=0),
    )
    result = _bash_merge(_squash(), env=env)
    assert result.returncode == 0, result.stderr
    assert "MERGE_RESULT=merged" in result.stdout


def test_squash_merge_at_sha_rejects_head_drift(tmp_path: pathlib.Path) -> None:
    env = _install_fake_gh(
        tmp_path,
        _fake_gh_squash_script(head_sha=_OTHER_SHA_HEAD, allow_merge=False),
    )
    result = _bash_merge(_squash(), env=env)
    assert result.returncode == 1
    assert "MERGE_RESULT=merge_failed" in result.stdout
    assert "PR head moved" in result.stderr


def test_squash_merge_at_sha_pending_checks_is_not_ready(
    tmp_path: pathlib.Path,
) -> None:
    env = _install_fake_gh(
        tmp_path,
        _fake_gh_squash_script(
            head_sha=_VALID_SHA,
            merge_body='required status check "ci" is pending',
            merge_exit=1,
        ),
    )
    result = _bash_merge(_squash(), env=env)
    assert result.returncode == 0, result.stderr
    assert "MERGE_RESULT=not_ready" in result.stdout


def test_squash_merge_at_sha_skips_when_merge_ready_label_removed(
    tmp_path: pathlib.Path,
) -> None:
    """Unchanged head without merge-ready must not merge or arm."""
    env = _install_fake_gh(
        tmp_path,
        _fake_gh_squash_script(
            head_sha=_VALID_SHA,
            labels_json=_EMPTY_LABELS_JQ,
            allow_merge=False,
        ),
    )
    result = _bash_merge(_squash(), env=env)
    assert result.returncode == 0, result.stderr
    assert "MERGE_RESULT=skipped" in result.stdout
    assert "Missing label" in result.stderr


def test_squash_merge_at_sha_label_api_error_is_merge_failed(
    tmp_path: pathlib.Path,
) -> None:
    """Label lookup errors must not soft-skip as intentional opt-out."""
    env = _install_fake_gh(
        tmp_path,
        _fake_gh_squash_script(
            head_sha=_VALID_SHA,
            labels_exit=1,
            allow_merge=False,
        ),
    )
    result = _bash_merge(_squash(), env=env)
    assert result.returncode == 1
    assert "MERGE_RESULT=merge_failed" in result.stdout
    assert "Could not verify" in result.stderr


def test_squash_merge_at_sha_fails_when_approval_dismissed(
    tmp_path: pathlib.Path,
) -> None:
    """Dismissal between assert and merge must fail closed before REST PUT."""
    env = _install_fake_gh(
        tmp_path,
        _fake_gh_squash_script(
            head_sha=_VALID_SHA,
            reviews_json=_dismissed_after_approved_reviews_json(),
            allow_merge=False,
        ),
    )
    result = _bash_merge(_squash(), env=env)
    assert result.returncode == 1
    assert "MERGE_RESULT=merge_failed" in result.stdout
    assert "Approval no longer present" in result.stderr
