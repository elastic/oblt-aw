"""Tests for scripts/validate_aw_workflow_resolve_agentic_assets.py."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_aw_workflow_resolve_agentic_assets as validator  # noqa: E402


def test_validate_workflow_skips_non_agent_wrappers(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    no_agent = workflows / "oblt-aw-security-detector.yml"
    no_agent.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n"
        "    with:\n      control-plane-workflow: oblt-aw-security-detector.yml\n"
        "  scan:\n    needs: prelude\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - run: echo scan\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "list_subject_workflows", lambda: [no_agent])
    assert validator.validate_workflow(no_agent) == []


def test_validate_workflow_rejects_gh_aw_without_resolve(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "oblt-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n"
        "    with:\n      control-plane-workflow: oblt-aw-test.yml\n"
        "  agent:\n    needs: prelude\n"
        "    uses: elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "list_subject_workflows", lambda: [bad])
    errors = validator.validate_workflow(bad)
    assert any("resolve-agentic-assets" in err for err in errors)


def test_validate_workflow_rejects_prelude_apm_outputs(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "oblt-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n"
        "  resolve-apm-assets:\n    uses: ./.github/workflows/aw-resolve-agentic-assets.yml\n"
        "  agent:\n    uses: elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main\n"
        "    with:\n"
        "      additional-instructions: ${{ needs.run-aw-prelude.outputs.resolved-additional-instructions }}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "list_subject_workflows", lambda: [bad])
    errors = validator.validate_workflow(bad)
    assert any("resolve-agentic-assets outputs" in err for err in errors)


def test_validate_workflow_accepts_resolve_per_agent_call(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    good = workflows / "oblt-aw-test.yml"
    good.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n"
        "    with:\n      control-plane-workflow: oblt-aw-test.yml\n"
        "  resolve-apm-assets:\n    uses: ./.github/workflows/aw-resolve-agentic-assets.yml\n"
        "    with:\n      control-plane-workflow: oblt-aw-test.yml\n"
        "  agent:\n    needs: [prelude, resolve-apm-assets]\n"
        "    uses: elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main\n"
        "    with:\n"
        "      additional-instructions: ${{ needs.resolve-apm-assets.outputs.resolved-additional-instructions }}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "list_subject_workflows", lambda: [good])
    assert validator.validate_workflow(good) == []
