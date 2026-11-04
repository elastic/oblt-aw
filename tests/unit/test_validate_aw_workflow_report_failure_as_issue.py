"""Tests for scripts/validate_aw_workflow_report_failure_as_issue.py."""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_aw_workflow_report_failure_as_issue as validator

ROUTE_RE = re.compile(r"^(?:docs|obs|security)-aw-.+\.ya?ml$")


def test_skips_non_route_basenames(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "aw-prelude.yml"
    path.write_text(
        "name: Prelude\non:\n  workflow_call:\njobs:\n"
        "  agent:\n"
        "    uses: elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main\n"
        "    with:\n      additional-instructions: hi\n",
        encoding="utf-8",
    )
    assert validator.validate_workflow(path, ROUTE_RE) == []


def test_skips_docs_actions_locks_without_input(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "docs-aw-ai-menu.yml"
    path.write_text(
        "name: Docs\non:\n  workflow_call:\njobs:\n"
        "  agent:\n"
        "    uses: elastic/docs-actions/.github/workflows/gh-aw-issue-triage.lock.yml@v1\n"
        "    with:\n      model: gpt\n",
        encoding="utf-8",
    )
    assert validator.validate_workflow(path, ROUTE_RE) == []
    assert (
        "gh-aw-issue-triage.lock.yml"
        in validator.DOCS_ACTIONS_LOCKS_WITHOUT_REPORT_FAILURE_INPUT
    )
    assert (
        "gh-aw-issue-triage.lock.yml"
        not in validator.LOCKS_WITHOUT_REPORT_FAILURE_INPUT
    )


def test_requires_report_failure_for_ai_github_actions_issue_triage(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "obs-aw-issue-triage.yml"
    path.write_text(
        "name: Issue Triage\non:\n  workflow_call:\njobs:\n"
        "  agent:\n"
        "    uses: elastic/ai-github-actions/.github/workflows/"
        "gh-aw-issue-triage.lock.yml@main\n"
        "    with:\n"
        "      additional-instructions: hi\n",
        encoding="utf-8",
    )
    errors = validator.validate_workflow(path, ROUTE_RE)
    assert len(errors) == 1
    assert "report-failure-as-issue: false" in errors[0]


def test_rejects_missing_report_failure_override(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "obs-aw-test.yml"
    path.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  agent:\n"
        "    uses: elastic/ai-github-actions/.github/workflows/gh-aw-mention-in-issue.lock.yml@main\n"
        "    with:\n"
        "      additional-instructions: hi\n",
        encoding="utf-8",
    )
    errors = validator.validate_workflow(path, ROUTE_RE)
    assert len(errors) == 1
    assert "report-failure-as-issue: false" in errors[0]


def test_accepts_report_failure_false(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "obs-aw-test.yml"
    path.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  agent:\n"
        "    uses: elastic/ai-github-actions/.github/workflows/gh-aw-mention-in-issue.lock.yml@main\n"
        "    with:\n"
        "      additional-instructions: hi\n"
        "      report-failure-as-issue: false\n",
        encoding="utf-8",
    )
    assert validator.validate_workflow(path, ROUTE_RE) == []


def test_skips_locks_without_input(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "obs-aw-detector.yml"
    path.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  agent:\n"
        "    uses: elastic/ai-github-actions/.github/workflows/"
        "gh-aw-log-searching-agent.lock.yml@main\n"
        "    with:\n"
        "      workflow: ci.yml\n",
        encoding="utf-8",
    )
    assert validator.validate_workflow(path, ROUTE_RE) == []


def test_skips_in_repo_dependency_review_lock(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "obs-aw-dependency-review.yml"
    path.write_text(
        "name: Dependency Review\non:\n  workflow_call:\njobs:\n"
        "  dependency-review:\n"
        "    uses: elastic/oblt-aw/.github/workflows/"
        "gh-aw-dependency-review.lock.yml@main\n"
        "    with:\n"
        "      additional-instructions: hi\n"
        "      github-token-policy: token-policy-x\n",
        encoding="utf-8",
    )
    assert validator.validate_workflow(path, ROUTE_RE) == []
    assert (
        "gh-aw-dependency-review.lock.yml"
        in validator.LOCKS_WITHOUT_REPORT_FAILURE_INPUT
    )


def test_main_passes_on_repo_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Smoke: real org route workflows must satisfy the gate after this change.
    assert validator.main() == 0
