"""Tests for scripts/validate_aw_workflow_copilot_token_optional.py."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_aw_workflow_copilot_token_optional as validator  # noqa: E402


def test_validate_workflow_rejects_required_true(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "oblt-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\n    secrets:\n      COPILOT_GITHUB_TOKEN:\n        required: true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    errors = validator.validate_workflow(bad)
    assert any("must be false" in err for err in errors)


def test_validate_workflow_accepts_required_false(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    good = workflows / "oblt-aw-test.yml"
    good.write_text(
        "name: Test\non:\n  workflow_call:\n    secrets:\n      COPILOT_GITHUB_TOKEN:\n        required: false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    assert validator.validate_workflow(good) == []


def test_validate_workflow_skips_when_secret_not_declared(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    no_secret = workflows / "docs-aw-test.yml"
    no_secret.write_text(
        "name: Test\non:\n  workflow_call:\n    inputs:\n      shared-proceed:\n        required: true\n        type: string\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    assert validator.validate_workflow(no_secret) == []


def test_list_subject_workflows_excludes_non_subject_files(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    for name in (
        "oblt-aw-event-issues.yml",
        "docs-aw-ai-menu.yml",
        "trigger-oblt-aw-issues.yml",
        "trg-oblt-aw-automerge.yml",
        "aw-prelude.yml",
        "aw-resolve-apm-assets.yml",
    ):
        (workflows / name).write_text("name: Test\n", encoding="utf-8")

    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    names = {path.name for path in validator.list_subject_workflows()}
    assert "oblt-aw-event-issues.yml" in names
    assert "docs-aw-ai-menu.yml" in names
    assert "trigger-oblt-aw-issues.yml" not in names
    assert "trg-oblt-aw-automerge.yml" not in names
    assert "aw-prelude.yml" not in names
    assert "aw-resolve-apm-assets.yml" not in names
