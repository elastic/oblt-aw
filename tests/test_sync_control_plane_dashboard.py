"""
Unit tests for scripts/sync_control_plane_dashboard.py

Tests the pure-logic functions (parse_checkbox_state, maturity_badge,
build_dashboard_body) in isolation, without touching the network or gh CLI.
"""

from __future__ import annotations

import sys


# Make the scripts/ package importable without installation.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "scripts"))

import sync_control_plane_dashboard as scpd  # noqa: E402


# ── parse_checkbox_state ──────────────────────────────────────────────────────


class TestParseCheckboxState:
    """Tests checkbox parsing behavior for dashboard bodies."""

    def test_returns_all_checked_workflows_when_all_enabled(self) -> None:
        body = """
- [x] <!-- oblt-aw:dependency-review -->
- [x] <!-- oblt-aw:agent-suggestions -->
- [x] <!-- oblt-aw:autodoc -->
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {
            "dependency-review": True,
            "agent-suggestions": True,
            "autodoc": True,
        }

    def test_returns_all_unchecked_when_none_enabled(self) -> None:
        body = """
- [ ] <!-- oblt-aw:dependency-review -->
- [ ] <!-- oblt-aw:agent-suggestions -->
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {
            "dependency-review": False,
            "agent-suggestions": False,
        }

    def test_returns_only_checked_workflows_for_mixed_state(self) -> None:
        body = """
- [x] <!-- oblt-aw:dependency-review -->
- [ ] <!-- oblt-aw:agent-suggestions -->
- [x] <!-- oblt-aw:autodoc -->
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {
            "dependency-review": True,
            "agent-suggestions": False,
            "autodoc": True,
        }

    def test_returns_empty_dict_for_empty_body(self) -> None:
        assert scpd.parse_checkbox_state("") == {}
        assert scpd.parse_checkbox_state(None) == {}

    def test_ignores_malformed_lines_without_oblt_aw_comment(self) -> None:
        body = """
- [x] some other text
- [ ] <!-- oblt-aw:valid-id -->
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {"valid-id": False}

    def test_handles_long_workflow_ids(self) -> None:
        body = "- [x] <!-- oblt-aw:resource-not-accessible-by-integration-detector -->"
        result = scpd.parse_checkbox_state(body)
        assert result == {"resource-not-accessible-by-integration-detector": True}


# ── maturity_badge ────────────────────────────────────────────────────────────


class TestMaturityBadge:
    def test_stable_returns_green_badge(self) -> None:
        assert scpd.maturity_badge("stable") == "🟢 stable"

    def test_early_adoption_returns_yellow_badge(self) -> None:
        assert scpd.maturity_badge("early-adoption") == "🟡 early-adoption"

    def test_experimental_returns_orange_badge(self) -> None:
        assert scpd.maturity_badge("experimental") == "🟠 experimental"

    def test_unknown_maturity_returns_raw_value(self) -> None:
        assert scpd.maturity_badge("custom") == "custom"


# ── build_dashboard_body ────────────────────────────────────────────────────────


class TestBuildDashboardBody:
    def test_builds_body_with_defaults_when_no_existing_body(self) -> None:
        workflows = [
            {
                "id": "agent-suggestions",
                "name": "Agent Suggestions",
                "description": "Suggests agentic workflows.",
                "maturity": "stable",
                "default_enabled": True,
            },
        ]
        body = scpd.build_dashboard_body(workflows, None)
        assert "## Control Plane Dashboard" in body
        assert "oblt-aw:agent-suggestions" in body
        assert "- [x]" in body
        assert "🟢 stable" in body

    def test_preserves_user_checkbox_state_from_existing_body(self) -> None:
        workflows = [
            {"id": "wf-a", "name": "A", "description": "Desc", "default_enabled": True},
            {"id": "wf-b", "name": "B", "description": "Desc", "default_enabled": True},
        ]
        existing = "- [ ] <!-- oblt-aw:wf-a -->\n- [x] <!-- oblt-aw:wf-b -->"
        body = scpd.build_dashboard_body(workflows, existing)
        assert "<!-- oblt-aw:wf-a -->" in body
        assert "<!-- oblt-aw:wf-b -->" in body
        # wf-a was unchecked by user
        lines = body.split("\n")
        wf_a_line = next(line for line in lines if "oblt-aw:wf-a" in line)
        wf_b_line = next(line for line in lines if "oblt-aw:wf-b" in line)
        assert "- [ ]" in wf_a_line
        assert "- [x]" in wf_b_line

    def test_uses_default_enabled_when_workflow_not_in_existing_body(self) -> None:
        workflows = [
            {
                "id": "new-wf",
                "name": "New",
                "description": "New workflow",
                "default_enabled": False,
            },
        ]
        body = scpd.build_dashboard_body(workflows, None)
        lines = body.split("\n")
        wf_line = next(line for line in lines if "oblt-aw:new-wf" in line)
        assert "- [ ]" in wf_line

    def test_includes_instructions_section(self) -> None:
        workflows = [
            {"id": "x", "name": "X", "description": "", "default_enabled": True}
        ]
        body = scpd.build_dashboard_body(workflows, None)
        assert "### Instructions" in body
        assert "Enable a workflow" in body
        assert "Disable a workflow" in body
