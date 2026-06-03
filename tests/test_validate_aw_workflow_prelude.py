"""Tests for scripts/validate_aw_workflow_prelude.py."""

from __future__ import annotations

import pathlib
import sys


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_aw_workflow_prelude as validator  # noqa: E402


def test_list_workflow_files_includes_docs_and_oblt_wrappers() -> None:
    names = {p.name for p in validator.list_workflow_files()}
    assert "oblt-aw-automerge.yml" in names
    assert "docs-aw-ai-menu.yml" in names
    assert "docs-aw-pr-ai-menu.yml" in names
    assert "oblt-aw-ingress.yml" not in names
    assert "docs-aw-ingress.yml" not in names
    assert "aw-prelude.yml" not in names
    assert "trg-oblt-aw-automerge.yml" not in names


def test_validate_aw_wrapper_rejects_prelude_job(tmp_path: pathlib.Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "docs-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n",
        encoding="utf-8",
    )
    errors = validator.validate_aw_wrapper_no_prelude(bad)
    assert len(errors) == 2


def test_validate_aw_wrapper_accepts_without_prelude(tmp_path: pathlib.Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    good = workflows / "docs-aw-test.yml"
    good.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n"
        "  run:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    assert validator.validate_aw_wrapper_no_prelude(good) == []


def test_validate_ingress_requires_prelude_and_route_jobs(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "docs-aw-ingress.yml"
    bad.write_text(
        "name: Ingress\non:\n  workflow_call:\njobs:\n  prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n",
        encoding="utf-8",
    )
    errors = validator.validate_ingress(bad)
    assert any("route-*" in err for err in errors)
