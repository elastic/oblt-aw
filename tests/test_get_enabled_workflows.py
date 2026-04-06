"""
Unit tests for scripts/get_enabled_workflows.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import get_enabled_workflows as gew  # noqa: E402


class TestNormalizeEnabledWorkflowsJson:
    def test_empty_string(self) -> None:
        assert gew.normalize_enabled_workflows_json("") == "[]"
        assert gew.normalize_enabled_workflows_json("   ") == "[]"

    def test_valid_json_array(self) -> None:
        assert gew.normalize_enabled_workflows_json('["a","b"]') == '["a","b"]'
        assert gew.normalize_enabled_workflows_json(' [ "x" ] ') == '["x"]'

    def test_invalid_json_falls_back_to_scan(self) -> None:
        out = gew.normalize_enabled_workflows_json("not-json foo-bar")
        assert out == '["not-json","foo-bar"]'

    def test_non_array_json_falls_back(self) -> None:
        out = gew.normalize_enabled_workflows_json('{"a":1}')
        assert out != "[]"


class TestParseEnabledIdsFromBody:
    def test_checkboxes(self) -> None:
        body = "- [x] <!-- oblt-aw:automerge -->\n- [x] <!-- oblt-aw:security -->\n"
        out = gew.parse_enabled_ids_from_body(body)
        assert out == '["automerge","security"]'

    def test_none_checked(self) -> None:
        body = "- [ ] <!-- oblt-aw:automerge\n"
        assert gew.parse_enabled_ids_from_body(body) == "[]"
