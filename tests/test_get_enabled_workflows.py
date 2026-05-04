"""
Unit tests for scripts/get_enabled_workflows.py
"""

from __future__ import annotations

import pathlib
import sys

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import get_enabled_workflows as gew  # noqa: E402


class TestNormalizeEnabledWorkflowsJson:
    def test_empty_string(self) -> None:
        assert gew.normalize_enabled_workflows_json("") == "[]"
        assert gew.normalize_enabled_workflows_json("   ") == "[]"

    def test_valid_json_array_compound(self) -> None:
        assert (
            gew.normalize_enabled_workflows_json('["obs:a","docs:b"]')
            == '["obs:a","docs:b"]'
        )

    def test_valid_json_array_bare_ids_get_obs_prefix(self) -> None:
        assert (
            gew.normalize_enabled_workflows_json('["agent-suggestions"]')
            == '["obs:agent-suggestions"]'
        )

    def test_invalid_json_falls_back_to_scan(self) -> None:
        out = gew.normalize_enabled_workflows_json("not-json foo-bar")
        assert out == '["obs:not-json","obs:foo-bar"]'

    def test_non_array_json_falls_back(self) -> None:
        out = gew.normalize_enabled_workflows_json('{"a":1}')
        assert out != "[]"


class TestParseEnabledIdsFromBody:
    def test_checkboxes_compound(self) -> None:
        body = "- [x] <!-- oblt-aw:obs:automerge -->\n- [x] <!-- oblt-aw:obs:security -->\n"
        out = gew.parse_enabled_ids_from_body(body)
        assert out == '["obs:automerge","obs:security"]'

    def test_legacy_two_part_obs(self) -> None:
        body = "- [x] <!-- oblt-aw:automerge -->\n"
        out = gew.parse_enabled_ids_from_body(body)
        assert out == '["obs:automerge"]'

    def test_none_checked(self) -> None:
        body = "- [ ] <!-- oblt-aw:obs:automerge\n"
        assert gew.parse_enabled_ids_from_body(body) == "[]"
