"""Tests for scripts/validate_trigger_workflow_permissions.py."""

from __future__ import annotations

import pathlib
import sys


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_trigger_workflow_permissions as validator  # noqa: E402


def test_list_trigger_templates_includes_obs_and_docs() -> None:
    names = {p.name for p in validator.list_trigger_templates()}
    assert "trg-oblt-aw-automerge.yml" in names
    assert "trg-docs-aw-pr-ai-menu.yml" in names


def test_collect_reusable_permissions_unions_jobs() -> None:
    repo_root = pathlib.Path(__file__).parent.parent
    perms = validator.collect_reusable_permissions(
        repo_root / ".github/workflows/oblt-aw-duplicate-issue-detector.yml"
    )
    assert perms["issues"] == "write"
    assert "discussions" not in perms


def test_gh_aw_lock_permissions_cover_issue_triage() -> None:
    locks = validator.load_lock_permissions()
    key = "elastic/ai-github-actions@main:gh-aw-issue-triage.lock.yml"
    assert locks[key]["discussions"] == "write"


def test_compare_permissions_flags_unnecessary_scope() -> None:
    path = pathlib.Path("trg-example.yml")
    errors = validator.compare_permissions(
        path,
        {"contents": "read", "issues": "write", "checks": "read"},
        {"contents": "read", "issues": "write"},
    )
    assert any("checks" in err and "unnecessary" in err for err in errors)


def test_compare_permissions_flags_excessive_level() -> None:
    path = pathlib.Path("trg-example.yml")
    errors = validator.compare_permissions(
        path,
        {"contents": "write", "issues": "write"},
        {"contents": "read", "issues": "write"},
    )
    assert any("contents" in err and "only requires read" in err for err in errors)


def test_validate_trigger_templates_in_repo() -> None:
    errors: list[str] = []
    for trigger in validator.list_trigger_templates():
        errors.extend(validator.validate_trigger(trigger))
    assert errors == []
