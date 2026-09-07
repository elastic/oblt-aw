"""Tests for scripts/obs/build-fixer-issue-snapshot.sh."""

from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

_root = pathlib.Path(__file__).resolve().parents[1]
_script = _root / "scripts" / "obs" / "build-fixer-issue-snapshot.sh"
_fixture = _root / "tests" / "fixtures" / "fixer-issue-snapshot-1844.json"


@pytest.mark.skipif(not _script.is_file(), reason="snapshot script missing")
def test_build_fixer_issue_snapshot_from_fixture() -> None:
    env = os.environ.copy()
    env["SNAPSHOT_FIXTURE"] = str(_fixture)
    env.pop("GITHUB_OUTPUT", None)
    proc = subprocess.run(
        ["bash", str(_script), "1844"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    out = proc.stdout
    assert "## Issue snapshot" in out
    assert "#1844" in out
    assert "oblt-aw/ai/fix-ready" in out
    assert "oblt-aw/triage/security-supply-chain" in out
    assert "Detailed Action Plan" in out
    assert "Pin @main to SHAs" in out
    # Triage-like comment should appear; plain thank-you may be omitted when
    # MAX_COMMENTS is small enough — default includes both.
    assert "elastic-vault-github-plugin-prod[bot]" in out


@pytest.mark.skipif(not _script.is_file(), reason="snapshot script missing")
def test_build_fixer_issue_snapshot_respects_max_total_chars() -> None:
    env = os.environ.copy()
    env["SNAPSHOT_FIXTURE"] = str(_fixture)
    env["MAX_TOTAL_CHARS"] = "180"
    env.pop("GITHUB_OUTPUT", None)
    proc = subprocess.run(
        ["bash", str(_script), "1844"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert "truncated" in proc.stdout.lower()
    assert len(proc.stdout) < 400
