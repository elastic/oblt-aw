"""
Unit tests for scripts/dashboard_audit.py

Pure-logic coverage for checkbox diffs, comment formatting, marker parsing,
and bot-actor detection. Network / gh CLI paths are not exercised here.
"""

from __future__ import annotations

import pathlib
import sys

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import dashboard_audit as da  # noqa: E402


class TestDiffCheckboxStates:
    def test_detects_activation_and_deactivation(self) -> None:
        before = {"obs:automerge": True, "obs:autodoc": False}
        after = {"obs:automerge": False, "obs:autodoc": True}
        deltas = da.diff_checkbox_states(before, after)
        assert {(d.compound_id, d.direction) for d in deltas} == {
            ("obs:automerge", "disabled"),
            ("obs:autodoc", "enabled"),
        }

    def test_ignores_unchanged(self) -> None:
        state = {"obs:automerge": True, "docs:ai-menu": False}
        assert da.diff_checkbox_states(state, state) == []

    def test_new_enabled_row_is_activation(self) -> None:
        deltas = da.diff_checkbox_states({}, {"obs:automerge": True})
        assert len(deltas) == 1
        assert deltas[0].is_activation

    def test_new_unchecked_row_ignored(self) -> None:
        assert da.diff_checkbox_states({}, {"obs:automerge": False}) == []

    def test_removed_enabled_row_is_deactivation(self) -> None:
        deltas = da.diff_checkbox_states({"obs:automerge": True}, {})
        assert len(deltas) == 1
        assert deltas[0].is_deactivation

    def test_removed_unchecked_row_ignored(self) -> None:
        assert da.diff_checkbox_states({"obs:automerge": False}, {}) == []

    def test_subfeature_compound_ids(self) -> None:
        before = {"obs:automerge:github-actions": True}
        after = {"obs:automerge:github-actions": False}
        deltas = da.diff_checkbox_states(before, after)
        assert deltas[0].compound_id == "obs:automerge:github-actions"
        assert deltas[0].is_deactivation


class TestDiffDashboardBodies:
    def test_parses_markers_and_diffs(self) -> None:
        before = """
- [x] <!-- oblt-aw:obs:automerge --> Automerge
- [ ] <!-- oblt-aw:docs:ai-menu --> AI Menu
"""
        after = """
- [ ] <!-- oblt-aw:obs:automerge --> Automerge
- [x] <!-- oblt-aw:docs:ai-menu --> AI Menu
"""
        deltas = da.diff_dashboard_bodies(before, after)
        by_id = {d.compound_id: d for d in deltas}
        assert by_id["obs:automerge"].is_deactivation
        assert by_id["docs:ai-menu"].is_activation


class TestCommentFormatting:
    def test_activation_has_no_team_mention(self) -> None:
        delta = da.CheckboxDelta("obs:automerge", False, True)
        body = da.format_activation_comment(
            when="2026-07-28T12:00:00Z",
            who="alice",
            delta=delta,
            entry_id="e1",
        )
        assert "aw:dashboard-audit:status=complete" in body
        assert "`obs:automerge` — enabled" in body
        assert "@alice" in body
        assert da.AUDIT_TEAM_MENTION not in body

    def test_deactivation_awaiting_mentions_team(self) -> None:
        delta = da.CheckboxDelta("obs:automerge", True, False)
        body = da.format_deactivation_comment(
            when="2026-07-28T12:00:00Z",
            who="bob",
            delta=delta,
            entry_id="e2",
        )
        assert "status=awaiting-reason" in body
        assert "awaiting" in body.lower()
        assert da.AUDIT_TEAM_MENTION in body

    def test_deactivation_with_reason_is_complete(self) -> None:
        delta = da.CheckboxDelta("obs:automerge", True, False)
        body = da.format_deactivation_comment(
            when="2026-07-28T12:00:00Z",
            who="bob",
            delta=delta,
            entry_id="e2",
            reason="too noisy",
        )
        assert "status=complete" in body
        assert "too noisy" in body
        assert da.AUDIT_TEAM_MENTION in body

    def test_sync_batch_comment(self) -> None:
        deltas = [
            da.CheckboxDelta("obs:automerge", True, False),
            da.CheckboxDelta("docs:ai-menu", False, True),
        ]
        body = da.format_sync_batch_comment(
            when="2026-07-28T12:00:00Z",
            who="oblt-aw-sync",
            deltas=deltas,
            reason="force-sync-defaults",
            entry_id="batch-1",
        )
        assert "source=sync" in body
        assert "force-sync-defaults" in body
        assert "`obs:automerge`" in body
        assert "`docs:ai-menu`" in body
        assert da.AUDIT_TEAM_MENTION not in body


class TestParseAuditMarker:
    def test_parses_marker(self) -> None:
        body = da.format_deactivation_comment(
            when="t",
            who="u",
            delta=da.CheckboxDelta("obs:autodoc", True, False),
            entry_id="abc-123",
        )
        meta = da.parse_audit_marker(body)
        assert meta == {
            "status": "awaiting-reason",
            "entry_id": "abc-123",
            "compound_id": "obs:autodoc",
            "source": "user",
        }

    def test_returns_none_without_marker(self) -> None:
        assert da.parse_audit_marker("just a comment") is None


class TestIsBotActor:
    def test_bot_type(self) -> None:
        assert da.is_bot_actor("anything", sender_type="Bot")

    def test_bot_suffix(self) -> None:
        assert da.is_bot_actor("my-app[bot]")

    def test_human(self) -> None:
        assert not da.is_bot_actor("fr4nc1sc0-r4m0n", sender_type="User")


class TestFindAwaitingComment:
    def test_single_awaiting(self) -> None:
        body = da.format_deactivation_comment(
            when="t",
            who="u",
            delta=da.CheckboxDelta("obs:automerge", True, False),
            entry_id="e1",
        )
        comments = [{"id": 1, "body": body}]
        assert da._find_awaiting_comment(comments, "because flaky") is comments[0]

    def test_matches_compound_id_when_multiple(self) -> None:
        a = da.format_deactivation_comment(
            when="t",
            who="u",
            delta=da.CheckboxDelta("obs:automerge", True, False),
            entry_id="e1",
        )
        b = da.format_deactivation_comment(
            when="t",
            who="u",
            delta=da.CheckboxDelta("obs:autodoc", True, False),
            entry_id="e2",
        )
        comments = [{"id": 1, "body": a}, {"id": 2, "body": b}]
        found = da._find_awaiting_comment(comments, "disable obs:autodoc for now")
        assert found is not None
        assert found["id"] == 2
