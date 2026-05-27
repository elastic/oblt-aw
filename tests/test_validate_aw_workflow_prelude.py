"""Tests for scripts/validate_aw_workflow_prelude.py."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_aw_workflow_prelude as validator  # noqa: E402


def test_list_subject_workflows_includes_oblt_aw_wrappers() -> None:
    names = {p.name for p in validator.list_subject_workflows()}
    assert "oblt-aw-automerge.yml" in names
    assert "docs-aw-ai-menu.yml" in names
    assert "docs-aw-pr-ai-menu.yml" in names
    assert "aw-prelude.yml" not in names
    assert "trigger-oblt-aw-automerge.yml" not in names


def test_validate_workflow_rejects_missing_prelude(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "oblt-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n  run:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    errors = validator.validate_workflow(bad)
    assert len(errors) == 2


def test_validate_workflow_accepts_prelude_job(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    good = workflows / "oblt-aw-test.yml"
    good.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    assert validator.validate_workflow(good) == []
