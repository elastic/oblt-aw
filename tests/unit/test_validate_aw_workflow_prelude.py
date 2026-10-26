"""Tests for scripts/validate_aw_workflow_prelude.py."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import common
import validate_aw_workflow_prelude as validator

ORG_KEYS = common.discover_org_keys_sorted(pathlib.Path("config"))


def test_list_subject_workflows_includes_route_wrappers() -> None:
    names = {p.name for p in validator.list_subject_workflows()}
    assert "obs-aw-automerge.yml" in names
    assert "obs-aw-pr-actions-detective.yml" in names
    assert "docs-aw-ai-menu.yml" in names
    assert "docs-aw-pr-ai-menu-collect.yml" in names
    assert "docs-aw-pr-ai-menu.yml" in names
    assert "aw-prelude.yml" not in names
    assert "docs-aw-event-issues.yml" not in names
    assert "e2e-trigger-obs-aw-schedule.yml" not in names
    assert "obs-aw-event-workflow-run.yml" not in names
    assert "security-aw-event-issues.yml" not in names
    assert "security-aw-event-issue-comment.yml" not in names
    assert "trg-oblt-aw-automerge.yml" not in names
    assert "gh-aw-estc-pr-buildkite-detective.lock.yml" not in names


def test_list_subject_workflows_excludes_gh_aw_locks(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "obs-aw-example.yml").write_text("name: Example\n", encoding="utf-8")
    (workflows / "gh-aw-estc-pr-buildkite-detective.lock.yml").write_text(
        "name: Lock\n", encoding="utf-8"
    )
    (workflows / "gh-aw-estc-pr-buildkite-detective.md").write_text(
        "# source\n", encoding="utf-8"
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    names = {p.name for p in validator.list_subject_workflows()}
    assert names == {"obs-aw-example.yml"}


def test_route_pattern_covers_every_discovered_org_key() -> None:
    assert ORG_KEYS, "expected at least one org under config/"
    pattern = validator.route_pattern()
    for org_key in ORG_KEYS:
        assert pattern.match(f"{org_key}-aw-example.yml")
        assert pattern.match(f"{org_key}-aw-example.yaml")
    assert not pattern.match("unknownorg-aw-example.yml")
    # Event orchestrators match the route basename pattern; subject discovery
    # still excludes them via EVENT_ORCHESTRATOR_PATTERN.
    assert pattern.match(f"{ORG_KEYS[0]}-aw-event-issues.yml")


def test_build_route_pattern_requires_org_keys() -> None:
    with pytest.raises(ValueError, match="at least one org key"):
        validator.build_route_pattern([])
    pattern = validator.build_route_pattern(["zeta", "alpha"])
    assert pattern.pattern == r"^(?:alpha|zeta)-aw-.+\.ya?ml$"
    assert pattern.match("alpha-aw-x.yml")
    assert pattern.match("zeta-aw-x.yml")
    assert not pattern.match("beta-aw-x.yml")


@pytest.mark.parametrize("org_key", ORG_KEYS)
def test_validate_workflow_rejects_missing_shared_proceed(
    org_key: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / f"{org_key}-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\njobs:\n  run:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    errors = validator.validate_workflow(bad)
    assert len(errors) == 1
    assert "shared-proceed" in errors[0]


@pytest.mark.parametrize("org_key", ORG_KEYS)
def test_validate_workflow_rejects_missing_shared_proceed_job_guard(
    org_key: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / f"{org_key}-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\n    inputs:\n      shared-proceed:\n"
        "        required: true\n        type: string\njobs:\n  run:\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    errors = validator.validate_workflow(bad)
    assert len(errors) == 1
    assert "inputs.shared-proceed" in errors[0]


@pytest.mark.parametrize("org_key", ORG_KEYS)
def test_validate_workflow_rejects_inline_prelude(
    org_key: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / f"{org_key}-aw-test.yml"
    bad.write_text(
        "name: Test\non:\n  workflow_call:\n    inputs:\n      shared-proceed:\n        required: true\n        type: string\njobs:\n"
        f"  run-aw-prelude:\n    uses: ./.github/workflows/aw-prelude.yml\n"
        f"    with:\n      control-plane-workflows: '[\"{org_key}-aw-test.yml\"]'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    errors = validator.validate_workflow(bad)
    assert any("run-aw-prelude job" in err for err in errors)
    assert any("must not call aw-prelude.yml" in err for err in errors)


@pytest.mark.parametrize("org_key", ORG_KEYS)
def test_validate_workflow_accepts_shared_proceed_route(
    org_key: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    good = workflows / f"{org_key}-aw-test.yml"
    good.write_text(
        "name: Test\non:\n  workflow_call:\n    inputs:\n      shared-proceed:\n        required: true\n        type: string\njobs:\n  run:\n    if: inputs.shared-proceed == 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    assert validator.validate_workflow(good) == []
