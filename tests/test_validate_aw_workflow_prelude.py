"""Tests for scripts/validate_aw_workflow_prelude.py."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_aw_workflow_prelude as validator  # noqa: E402


def test_list_subject_workflows_includes_route_wrappers() -> None:
    names = {p.name for p in validator.list_subject_workflows()}
    assert "obs-aw-automerge.yml" in names
    assert "docs-aw-ai-menu.yml" in names
    assert "docs-aw-pr-ai-menu-collect.yml" in names
    assert "docs-aw-pr-ai-menu.yml" in names
    assert "aw-prelude.yml" not in names
    assert "docs-aw-event-issues.yml" not in names
    assert "trg-oblt-aw-automerge.yml" not in names


def test_validate_workflow_rejects_missing_shared_proceed(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "docs-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n  run:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    errors = validator.validate_workflow(bad)
    assert len(errors) == 1
    assert "shared-proceed" in errors[0]


def test_validate_workflow_rejects_inline_prelude(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "docs-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\n    inputs:\n      shared-proceed:\n        required: true\n        type: string\njobs:\n"
        "  run-aw-prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n"
        "    with:\n      control-plane-workflows: '[\"docs-aw-test.yml\"]'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    errors = validator.validate_workflow(bad)
    assert any("run-aw-prelude job" in err for err in errors)
    assert any("must not call aw-prelude.yml" in err for err in errors)


def test_validate_workflow_accepts_shared_proceed_route(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    good = workflows / "obs-aw-test.yml"
    good.write_text(
        "name: Test\non:\n  workflow_call:\n    inputs:\n      shared-proceed:\n        required: true\n        type: string\njobs:\n  run:\n    if: inputs.shared-proceed == 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    assert validator.validate_workflow(good) == []
