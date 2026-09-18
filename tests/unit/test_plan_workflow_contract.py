"""Tests for the native plan workflow's execution and prompt boundaries."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PLAN_SOURCE = REPO_ROOT / ".github/workflows/gh-aw-plan.md"
PLAN_WRAPPER = REPO_ROOT / ".github/workflows/obs-aw-plan.yml"


def test_plan_prompt_does_not_interpolate_raw_issue_title() -> None:
    source = PLAN_SOURCE.read_text(encoding="utf-8")

    assert "github.event.issue.title" not in source
    assert "steps.sanitized.outputs.text" in source


def test_plan_wrapper_gates_privileged_resolver_by_author_association() -> None:
    wrapper = PLAN_WRAPPER.read_text(encoding="utf-8")
    association_gate = (
        """contains(fromJSON('["OWNER","MEMBER","COLLABORATOR"]'), """
        "github.event.comment.author_association)"
    )

    assert wrapper.count(association_gate) == 2
    assert "Native GH-AW roles remain the command authorization boundary." in wrapper


def test_plan_workflow_uses_automatic_github_token() -> None:
    source = PLAN_SOURCE.read_text(encoding="utf-8")
    wrapper = PLAN_WRAPPER.read_text(encoding="utf-8")
    plan_job = wrapper.split("  plan:\n", maxsplit=1)[1]

    assert "github-token-policy" not in source
    assert "github-token-policy" not in wrapper
    assert "shared-token-policy" not in wrapper
    assert "id-token: write" not in plan_job
