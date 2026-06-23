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
    ("pr_json", "expected"),
    [
        ('{"title":"Fix SEC-030","body":"Fixes #42 with env indirection"}', True),
        ('{"title":"Fixes #42","body":null}', True),
        ('{"title":"Unrelated","body":"No issue link here"}', False),
    ],
)
def test_linked_pr_references_issue(pr_json: str, expected: bool) -> None:
    result = _bash(f"linked_pr_references_issue 42 '{pr_json}'")
    assert result.returncode == (0 if expected else 1)
