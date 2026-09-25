# Copyright 2026-2027 Elasticsearch B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Unit tests for Actions commit.verification REST collector."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts" / "obs"))

from collect_actions_commit_verification import (
    DEFAULT_OUTPUT,
    FACTS_SOURCE,
    action_api_repo,
    build_facts,
    extract_action_sha_pins,
    fetch_commit_verification,
    git_diff,
    main,
)


def test_action_api_repo_strips_nested_path() -> None:
    assert (
        action_api_repo("github/codeql-action/upload-sarif") == "github/codeql-action"
    )
    assert action_api_repo("actions/checkout") == "actions/checkout"


def test_extract_action_sha_pins_from_added_diff_lines() -> None:
    sha_a = "08eba0b27e820071cde6df949e0beb9ba4906955"
    sha_b = "11bd71901bbe5b1630ceea73d27597364c9af683"
    diff = f"""
diff --git a/.github/workflows/e2e.yml b/.github/workflows/e2e.yml
--- a/.github/workflows/e2e.yml
+++ b/.github/workflows/e2e.yml
-      - uses: actions/checkout@{sha_b} # v4.2.2
+      - uses: actions/checkout@{sha_a} # v4.3.0
+      - uses: "github/codeql-action/upload-sarif@{sha_a}"
"""
    pins = extract_action_sha_pins(diff)
    assert ("actions/checkout", sha_a) in pins
    assert ("github/codeql-action/upload-sarif", sha_a) in pins
    assert ("actions/checkout", sha_b) not in pins


def test_extract_ignores_non_sha_and_context_lines() -> None:
    diff = """
+++ b/.github/workflows/x.yml
+      - uses: actions/checkout@v4
+      - uses: actions/setup-node@v4.1.0
-      - uses: actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955
"""
    assert extract_action_sha_pins(diff) == []


def test_fetch_commit_verification_true() -> None:
    def gh_run(argv: list[str]) -> SimpleNamespace:
        assert "repos/actions/checkout/commits/abc" in " ".join(argv)
        return SimpleNamespace(
            returncode=0,
            stdout='{"verified": true, "reason": "valid"}',
            stderr="",
        )

    result = fetch_commit_verification("actions/checkout", "abc", gh_run=gh_run)
    assert result == {"verified": True, "reason": "valid", "error": None}


def test_fetch_commit_verification_false() -> None:
    def gh_run(_argv: list[str]) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=0,
            stdout='{"verified": false, "reason": "unsigned"}',
            stderr="",
        )

    result = fetch_commit_verification("ruby/setup-ruby", "def", gh_run=gh_run)
    assert result["verified"] is False
    assert result["reason"] == "unsigned"
    assert result["error"] is None


def test_fetch_commit_verification_api_error() -> None:
    def gh_run(_argv: list[str]) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="gh: Not Found")

    result = fetch_commit_verification("missing/repo", "deadbeef", gh_run=gh_run)
    assert result["verified"] is None
    assert result["error"] == "gh: Not Found"


def test_build_facts_maps_pins(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_fetch(repo: str, sha: str, *, gh_run=None) -> dict:
        calls.append((repo, sha))
        return {"verified": True, "reason": "valid", "error": None}

    monkeypatch.setattr(
        "collect_actions_commit_verification.fetch_commit_verification",
        fake_fetch,
    )
    sha = "08eba0b27e820071cde6df949e0beb9ba4906955"
    facts = build_facts([("github/codeql-action/upload-sarif", sha)])
    assert facts["version"] == 1
    assert facts["source"] == FACTS_SOURCE
    assert facts["pins"] == [
        {
            "action": "github/codeql-action/upload-sarif",
            "repo": "github/codeql-action",
            "sha": sha,
            "verified": True,
            "reason": "valid",
            "error": None,
        }
    ]
    assert calls == [("github/codeql-action", sha)]


def test_pull_request_diff_filters_workflow_patches() -> None:
    from collect_actions_commit_verification import pull_request_diff

    sha = "08eba0b27e820071cde6df949e0beb9ba4906955"

    def gh_run(argv: list[str]) -> SimpleNamespace:
        assert "pulls/99/files" in " ".join(argv)
        payload = [
            {
                "filename": ".github/workflows/ci.yml",
                "patch": f"+      - uses: actions/checkout@{sha}\n",
            },
            {
                "filename": "README.md",
                "patch": f"+uses: actions/checkout@{sha}\n",
            },
            {"filename": ".github/workflows/big.yml", "patch": None},
        ]
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    text = pull_request_diff("elastic/oblt-aw", 99, gh_run=gh_run)
    assert f"actions/checkout@{sha}" in text
    assert extract_action_sha_pins(text) == [("actions/checkout", sha)]


def test_main_writes_facts_from_diff_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha = "08eba0b27e820071cde6df949e0beb9ba4906955"
    diff_path = tmp_path / "pr.diff"
    diff_path.write_text(
        f"+      - uses: actions/checkout@{sha}\n",
        encoding="utf-8",
    )
    out = tmp_path / DEFAULT_OUTPUT

    def fake_fetch(repo: str, pin_sha: str, *, gh_run=None) -> dict:
        assert repo == "actions/checkout"
        assert pin_sha == sha
        return {"verified": True, "reason": "valid", "error": None}

    monkeypatch.setattr(
        "collect_actions_commit_verification.fetch_commit_verification",
        fake_fetch,
    )
    assert main(["--diff-file", str(diff_path), "--output", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["pins"][0]["verified"] is True
    assert payload["pins"][0]["sha"] == sha


def test_git_diff_failure_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a, **_k):
        return subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: bad revision"
        )

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(RuntimeError, match="git diff failed"):
        git_diff("nope...HEAD", paths=[".github/workflows"])
