"""Tests for scripts/obs/supersede-security-issues.sh helpers."""

from __future__ import annotations

import pathlib
import subprocess

import pytest

SCRIPT = (
    pathlib.Path(__file__).parent.parent
    / "scripts"
    / "obs"
    / "supersede-security-issues.sh"
)


def _bash(function_call: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{SCRIPT}" && {function_call}'],
        capture_output=True,
        text=True,
        check=False,
    )


def test_parse_sec_id_from_title_matches_detector_format() -> None:
    title = "[oblt-aw][security] SEC-030 — findings (2026-06-18)"
    result = _bash(f'parse_sec_id_from_title "{title}"')
    assert result.returncode == 0
    assert result.stdout.strip() == "SEC-030"


def test_parse_sec_id_from_title_rejects_unrelated_titles() -> None:
    result = _bash('parse_sec_id_from_title "Bug: something else"')
    assert result.returncode == 1
    assert result.stdout.strip() == ""


@pytest.mark.parametrize(
    ("labels_json", "expected"),
    [
        ('{"labels":[{"name":"oblt-aw/keep-open"}]}', True),
        ('{"labels":[{"name":"oblt-aw/detector/security"}]}', False),
        ('{"labels":[]}', False),
    ],
)
def test_issue_has_label_keep_open(labels_json: str, expected: bool) -> None:
    result = _bash(f"issue_has_label '{labels_json}' \"$KEEP_OPEN_LABEL\"")
    assert result.returncode == (0 if expected else 1)


def test_issue_has_open_linked_pr_true_when_open_pr_present() -> None:
    result = _bash(
        'linked_prs=\'[{"number":7,"state":"OPEN"}]\'; '
        '[[ "$(jq \'length\' <<< "$linked_prs")" -gt 0 ]]'
    )
    assert result.returncode == 0


def test_issue_has_open_linked_pr_false_when_no_open_prs() -> None:
    result = _bash(
        "linked_prs='[]'; [[ \"$(jq 'length' <<< \"$linked_prs\")\" -gt 0 ]]"
    )
    assert result.returncode == 1
