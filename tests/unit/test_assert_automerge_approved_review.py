"""Tests for scripts/obs/assert_automerge_approved_review.sh."""

from __future__ import annotations

import json
import os
import pathlib
import shlex
import subprocess
import textwrap

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
_APPROVER_2 = "other-reviewer[bot]"


def _bash(
    function_call: str, *, env: dict[str, str] | None = None
) -> subprocess.completedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{SCRIPT}" && {function_call}'],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _has_approval(
    reviews: list[dict], *, author: str = _AUTHOR, sha: str = _HEAD
) -> subprocess.completedProcess[str]:
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


def _install_fake_gh(tmp_path: pathlib.Path, script: str) -> dict[str, str]:
    gh_path = tmp_path / "gh"
    gh_path.write_text(textwrap.dedent(script), encoding="utf-8")
    gh_path.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    return env


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


def test_approved_then_changes_requested_fails() -> None:
    result = _has_approval(
        [
            _review(state="APPROVED", login=_APPROVER, review_id=1),
            _review(state="CHANGES_REQUESTED", login=_APPROVER, review_id=2),
        ]
    )
    assert result.returncode == 1, result.stdout


def test_changes_requested_then_approved_passes() -> None:
    result = _has_approval(
        [
            _review(state="CHANGES_REQUESTED", login=_APPROVER, review_id=1),
            _review(state="APPROVED", login=_APPROVER, review_id=2),
        ]
    )
    assert result.returncode == 0, result.stderr


def test_later_commented_does_not_clear_approval() -> None:
    result = _has_approval(
        [
            _review(state="APPROVED", login=_APPROVER, review_id=1),
            _review(state="COMMENTED", login=_APPROVER, review_id=2),
        ]
    )
    assert result.returncode == 0, result.stderr


def test_second_reviewer_changes_requested_does_not_block_other_approval() -> None:
    result = _has_approval(
        [
            _review(state="APPROVED", login=_APPROVER, review_id=1),
            _review(state="CHANGES_REQUESTED", login=_APPROVER_2, review_id=2),
        ]
    )
    assert result.returncode == 0, result.stderr


def test_assert_wrapper_approved_succeeds(tmp_path: pathlib.Path) -> None:
    reviews = json.dumps([_review(state="APPROVED", login=_APPROVER)])
    env = _install_fake_gh(
        tmp_path,
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        if [[ "${{1:-}}" == "api" && "${{2:-}}" == *"/reviews" ]]; then
          printf '%s\\n' {shlex.quote(reviews)}
          exit 0
        fi
        echo "unexpected gh args: $*" >&2
        exit 99
        """,
    )
    result = _bash(
        f"automerge_assert_pr_has_approved_review owner/repo 1 "
        f"{shlex.quote(_AUTHOR)} {_HEAD}",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "ASSERT_REASON=ok" in result.stdout


def test_assert_wrapper_comment_only_is_missing_approval(
    tmp_path: pathlib.Path,
) -> None:
    reviews = json.dumps([_review(state="COMMENTED", login=_APPROVER)])
    env = _install_fake_gh(
        tmp_path,
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        if [[ "${{1:-}}" == "api" && "${{2:-}}" == *"/reviews" ]]; then
          printf '%s\\n' {shlex.quote(reviews)}
          exit 0
        fi
        echo "unexpected gh args: $*" >&2
        exit 99
        """,
    )
    result = _bash(
        f"automerge_assert_pr_has_approved_review owner/repo 1 "
        f"{shlex.quote(_AUTHOR)} {_HEAD}",
        env=env,
    )
    assert result.returncode == 2, result.stdout
    assert "ASSERT_REASON=missing_approval" in result.stdout


def test_assert_wrapper_api_error_is_verify_failed(tmp_path: pathlib.Path) -> None:
    env = _install_fake_gh(
        tmp_path,
        """\
        #!/usr/bin/env bash
        echo "boom" >&2
        exit 1
        """,
    )
    result = _bash(
        f"automerge_assert_pr_has_approved_review owner/repo 1 "
        f"{shlex.quote(_AUTHOR)} {_HEAD}",
        env=env,
    )
    assert result.returncode == 1, result.stdout
    assert "ASSERT_REASON=verify_failed" in result.stdout
    assert "Failed to list reviews" in result.stderr


def test_require_pr_head_sha_rejects_drift(tmp_path: pathlib.Path) -> None:
    env = _install_fake_gh(
        tmp_path,
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        # emulate: gh api ... --jq '.head.sha'
        if [[ "$*" == *"--jq"* ]]; then
          printf '%s\\n' {_OTHER}
          exit 0
        fi
        echo "unexpected gh args: $*" >&2
        exit 99
        """,
    )
    result = _bash(
        f"automerge_require_pr_head_sha owner/repo 1 {_HEAD}",
        env=env,
    )
    assert result.returncode == 1
    assert "PR head moved" in result.stderr


def test_require_pr_head_sha_matches(tmp_path: pathlib.Path) -> None:
    env = _install_fake_gh(
        tmp_path,
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        if [[ "$*" == *"--jq"* ]]; then
          printf '%s\\n' {_HEAD}
          exit 0
        fi
        echo "unexpected gh args: $*" >&2
        exit 99
        """,
    )
    result = _bash(
        f"automerge_require_pr_head_sha owner/repo 1 {_HEAD}",
        env=env,
    )
    assert result.returncode == 0, result.stderr
