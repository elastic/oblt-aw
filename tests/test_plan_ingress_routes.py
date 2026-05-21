"""
Unit tests for scripts/plan_ingress_routes.py (route planning)
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import plan_ingress_routes as routes  # noqa: E402
from plan_ingress_routes import RoutePlanContext, plan_routes  # noqa: E402


def _ctx(**overrides: object) -> RoutePlanContext:
    base = {
        "event_name": "pull_request",
        "event_action": "opened",
        "effective_raw": "",
        "enabled_workflows": [],
        "allowed_pr_authors": ["dependabot[bot]"],
        "allowed_issue_authors": [],
        "pull_request_user_login": "dependabot[bot]",
        "pull_request_labels": [],
        "issue_labels": [],
        "issue_is_pull_request": False,
        "comment_body": "",
        "comment_author_association": "",
        "status_state": "",
        "status_context": "",
        "labeled_label_name": "",
    }
    base.update(overrides)
    return RoutePlanContext(**base)  # type: ignore[arg-type]


class TestPlanRoutesPullRequest:
    def test_bot_pr_dependency_review_only(self) -> None:
        result = plan_routes(_ctx())
        assert result.routes == ["dependency-review"]
        assert not result.unsupported_trigger

    def test_human_pr_no_routes(self) -> None:
        result = plan_routes(_ctx(pull_request_user_login="human-user"))
        assert result.routes == []

    def test_automerge_requires_merge_ready_label(self) -> None:
        result = plan_routes(_ctx(pull_request_labels=["oblt-aw/ai/merge-ready"]))
        assert result.routes == ["automerge", "dependency-review"]

    def test_dashboard_disables_route(self) -> None:
        result = plan_routes(
            _ctx(
                effective_raw="dashboard",
                enabled_workflows=["obs:autodoc"],
            )
        )
        assert result.routes == []


class TestPlanRoutesSchedule:
    def test_schedule_all_default_enabled(self) -> None:
        result = plan_routes(
            _ctx(
                event_name="schedule",
                event_action="",
                pull_request_user_login="",
            )
        )
        assert "agent-suggestions" in result.routes
        assert "autodoc" in result.routes
        assert "security-detector" in result.routes
        assert "resource-not-accessible-by-integration-detector" in result.routes


class TestPlanRoutesIssues:
    def test_issue_opened_triage(self) -> None:
        result = plan_routes(
            _ctx(
                event_name="issues",
                event_action="opened",
                effective_raw="dashboard",
                enabled_workflows=["obs:issue-triage"],
            )
        )
        assert result.routes == ["issue-triage"]

    def test_issue_comment_implement(self) -> None:
        result = plan_routes(
            _ctx(
                event_name="issue_comment",
                event_action="created",
                comment_body="/ai implement fix",
                comment_author_association="MEMBER",
                effective_raw="dashboard",
                enabled_workflows=["obs:issue-fixer"],
            )
        )
        assert result.routes == ["issue-fixer"]


class TestUnsupportedTrigger:
    def test_push_not_supported(self) -> None:
        result = plan_routes(_ctx(event_name="push", event_action=""))
        assert result.unsupported_trigger
        assert result.routes == []


class TestContextFromEnv:
    def test_parse_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EVENT_NAME", "pull_request")
        monkeypatch.setenv("EVENT_ACTION", "opened")
        monkeypatch.setenv("EFFECTIVE_RAW", "")
        monkeypatch.setenv("ENABLED_WORKFLOWS_JSON", "[]")
        monkeypatch.setenv("ALLOWED_PR_AUTHORS_JSON", json.dumps(["bot"]))
        monkeypatch.setenv("ALLOWED_ISSUE_AUTHORS_JSON", "[]")
        monkeypatch.setenv("PR_USER_LOGIN", "bot")
        monkeypatch.setenv("PR_LABELS_CSV", "oblt-aw/ai/merge-ready")
        ctx = routes.context_from_env(os.environ)
        result = plan_routes(ctx)
        assert "automerge" in result.routes
