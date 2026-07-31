"""
Unit tests for scripts/sync_control_plane_dashboard.py

Tests the pure-logic functions (parse_checkbox_state, maturity_badge,
build_dashboard_body) in isolation, without touching the network or gh CLI.
"""

from __future__ import annotations

import sys
import pathlib


_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import sync_control_plane_dashboard as scpd  # noqa: E402


def _obs_section(workflows: list[dict]) -> list[tuple[str, str, list[dict]]]:
    return [("obs", "Observability", workflows)]


# ── parse_checkbox_state ──────────────────────────────────────────────────────


class TestParseCheckboxState:
    """Tests checkbox parsing behavior for dashboard bodies."""

    def test_returns_all_checked_workflows_when_all_enabled(self) -> None:
        body = """
- [x] <!-- oblt-aw:obs:dependency-review --> dependency-review
- [x] <!-- oblt-aw:obs:agent-suggestions --> agent-suggestions
- [x] <!-- oblt-aw:obs:autodoc --> autodoc
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {
            "obs:dependency-review": True,
            "obs:agent-suggestions": True,
            "obs:autodoc": True,
        }

    def test_returns_all_unchecked_when_none_enabled(self) -> None:
        body = """
- [ ] <!-- oblt-aw:obs:dependency-review --> dependency-review
- [ ] <!-- oblt-aw:obs:agent-suggestions --> agent-suggestions
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {
            "obs:dependency-review": False,
            "obs:agent-suggestions": False,
        }

    def test_returns_only_checked_workflows_for_mixed_state(self) -> None:
        body = """
- [x] <!-- oblt-aw:obs:dependency-review --> dependency-review
- [ ] <!-- oblt-aw:obs:agent-suggestions --> agent-suggestions
- [x] <!-- oblt-aw:obs:autodoc --> autodoc
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {
            "obs:dependency-review": True,
            "obs:agent-suggestions": False,
            "obs:autodoc": True,
        }

    def test_returns_empty_dict_for_empty_body(self) -> None:
        assert scpd.parse_checkbox_state("") == {}
        assert scpd.parse_checkbox_state(None) == {}

    def test_ignores_malformed_lines_without_oblt_aw_comment(self) -> None:
        body = """
- [x] some other text
- [ ] <!-- oblt-aw:obs:valid-id --> valid
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {"obs:valid-id": False}

    def test_handles_long_workflow_ids(self) -> None:
        body = (
            "- [x] <!-- oblt-aw:obs:resource-not-accessible-by-integration --> resource"
        )
        result = scpd.parse_checkbox_state(body)
        assert result == {"obs:resource-not-accessible-by-integration": True}

    def test_ignores_pattern_in_middle_of_line(self) -> None:
        body = "See - [x] <!-- oblt-aw:obs:not-at-start --> for details"
        result = scpd.parse_checkbox_state(body)
        assert result == {}

    def test_legacy_two_part_maps_to_obs(self) -> None:
        body = "- [x] <!-- oblt-aw:automerge --> Automerge\n"
        assert scpd.parse_checkbox_state(body) == {"obs:automerge": True}

    def test_parses_sub_feature_checkboxes(self) -> None:
        body = """
- [x] <!-- oblt-aw:obs:automerge --> Automerge
  - [ ] <!-- oblt-aw:obs:automerge:github-actions --> GitHub Actions
  - [x] <!-- oblt-aw:obs:automerge:terraform --> Terraform
"""
        result = scpd.parse_checkbox_state(body)
        assert result == {
            "obs:automerge": True,
            "obs:automerge:github-actions": False,
            "obs:automerge:terraform": True,
        }


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
        body = scpd.build_dashboard_body(_obs_section(workflows), None)
        assert "## Control Plane Dashboard" in body
        assert "oblt-aw:obs:agent-suggestions" in body
        assert "- [x]" in body
        assert "🟢 stable" in body
        assert "### Observability (obs)" in body

    def test_preserves_user_checkbox_state_from_existing_body(self) -> None:
        workflows = [
            {"id": "wf-a", "name": "A", "description": "Desc", "default_enabled": True},
            {"id": "wf-b", "name": "B", "description": "Desc", "default_enabled": True},
        ]
        existing = (
            "- [ ] <!-- oblt-aw:obs:wf-a --> A\n- [x] <!-- oblt-aw:obs:wf-b --> B"
        )
        body = scpd.build_dashboard_body(_obs_section(workflows), existing)
        assert "<!-- oblt-aw:obs:wf-a -->" in body
        assert "<!-- oblt-aw:obs:wf-b -->" in body
        lines = body.split("\n")
        wf_a_line = next(line for line in lines if "oblt-aw:obs:wf-a" in line)
        wf_b_line = next(line for line in lines if "oblt-aw:obs:wf-b" in line)
        assert "- [ ]" in wf_a_line
        assert "- [x]" in wf_b_line

    def test_force_sync_defaults_overwrites_existing_checkbox_state(self) -> None:
        workflows = [
            {
                "id": "wf-a",
                "name": "A",
                "description": "Desc",
                "default_enabled": False,
            },
            {"id": "wf-b", "name": "B", "description": "Desc", "default_enabled": True},
        ]
        existing = (
            "- [x] <!-- oblt-aw:obs:wf-a --> A\n- [ ] <!-- oblt-aw:obs:wf-b --> B"
        )
        body = scpd.build_dashboard_body(
            _obs_section(workflows),
            existing,
            force_sync_defaults=True,
        )
        lines = body.split("\n")
        wf_a_line = next(line for line in lines if "oblt-aw:obs:wf-a" in line)
        wf_b_line = next(line for line in lines if "oblt-aw:obs:wf-b" in line)
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
        body = scpd.build_dashboard_body(_obs_section(workflows), None)
        lines = body.split("\n")
        wf_line = next(line for line in lines if "oblt-aw:obs:new-wf" in line)
        assert "- [ ]" in wf_line

    def test_includes_instructions_section(self) -> None:
        workflows = [
            {"id": "x", "name": "X", "description": "", "default_enabled": True}
        ]
        body = scpd.build_dashboard_body(_obs_section(workflows), None)
        assert "### Instructions" in body
        assert "Enable a workflow" in body
        assert "Disable a workflow" in body
        assert "Audit trail" in body
        assert "@elastic/observablt-ci" in body

    def test_multi_org_sections(self) -> None:
        obs_wf = [{"id": "a", "name": "A", "description": "", "default_enabled": True}]
        docs_wf = [
            {"id": "b", "name": "B", "description": "", "default_enabled": False}
        ]
        sections = [
            ("obs", "Observability", obs_wf),
            ("docs", "Documentation", docs_wf),
        ]
        body = scpd.build_dashboard_body(sections, None)
        assert "### Observability (obs)" in body
        assert "### Documentation (docs)" in body
        assert "oblt-aw:obs:a" in body
        assert "oblt-aw:docs:b" in body

    def test_renders_sub_feature_checkboxes_indented(self) -> None:
        workflows = [
            {
                "id": "automerge",
                "name": "Automerge",
                "description": "Desc",
                "default_enabled": False,
                "sub_features": [
                    {
                        "id": "github-actions",
                        "name": "GitHub Actions",
                        "default_enabled": True,
                    },
                    {
                        "id": "python-dependencies",
                        "name": "Python",
                        "default_enabled": False,
                    },
                ],
            }
        ]
        body = scpd.build_dashboard_body(_obs_section(workflows), None)
        lines = body.split("\n")
        parent_line = next(
            line for line in lines if "oblt-aw:obs:automerge -->" in line
        )
        gh_line = next(
            line for line in lines if "oblt-aw:obs:automerge:github-actions -->" in line
        )
        py_line = next(
            line
            for line in lines
            if "oblt-aw:obs:automerge:python-dependencies -->" in line
        )
        assert parent_line.startswith("- [ ]")
        assert gh_line.startswith("  - [x]")
        assert py_line.startswith("  - [ ]")

    def test_renders_security_sub_features(self) -> None:
        workflows = [
            {
                "id": "security",
                "name": "Security",
                "description": "Desc",
                "default_enabled": False,
                "sub_features": [
                    {
                        "id": "injection",
                        "name": "Injection Detection",
                        "default_enabled": True,
                    },
                    {
                        "id": "supply-chain",
                        "name": "Supply-chain Hardening",
                        "default_enabled": True,
                    },
                ],
            }
        ]
        body = scpd.build_dashboard_body(_obs_section(workflows), None)
        assert "oblt-aw:obs:security:injection" in body
        assert "oblt-aw:obs:security:supply-chain" in body
        lines = body.split("\n")
        injection_line = next(
            line for line in lines if "oblt-aw:obs:security:injection" in line
        )
        assert injection_line.startswith("  - [x]")
