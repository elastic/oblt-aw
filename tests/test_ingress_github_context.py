"""Unit tests for scripts/ingress_github_context.py"""

from __future__ import annotations

import json
import pathlib
import sys

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import ingress_github_context as igc  # noqa: E402


def test_parse_relayed_payload_accepts_double_encoded_json() -> None:
    payload = {
        "action": "synchronize",
        "pull_request": {"number": 42, "title": "Fix deps"},
    }
    raw = json.dumps(json.dumps(payload))
    parsed = igc.parse_relayed_ingress_payload(raw)
    assert parsed == payload


def test_extract_pull_request_context_from_relayed_event() -> None:
    payload = {
        "action": "synchronize",
        "pull_request": {
            "number": 123,
            "title": "Update lodash",
            "head": {"ref": "dependabot/npm/lodash", "sha": "abc123"},
        },
    }
    ctx = igc.extract_relayed_github_context(payload)
    assert ctx.pull_request_number == 123
    assert ctx.pull_request_title == "Update lodash"
    assert ctx.pull_request_head_ref == "dependabot/npm/lodash"
    assert ctx.event_action == "synchronize"


def test_extract_issue_context_from_pr_issue_object() -> None:
    payload = {
        "action": "created",
        "issue": {"number": 99, "title": "Docs", "pull_request": {}},
    }
    ctx = igc.extract_relayed_github_context(
        payload, ingress_event_name="issue_comment"
    )
    assert ctx.pull_request_number == 99
    assert ctx.issue_number == 99


def test_apply_relayed_context_prepends_instructions_and_checkout() -> None:
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 7,
            "title": "Test",
            "head": {"ref": "feature/test", "sha": "deadbeef"},
        },
    }
    additional, setup = igc.apply_relayed_ingress_context(
        json.dumps(payload),
        "Platform rules",
        ["npm ci"],
        ingress_event_name="pull_request",
        ingress_event_action="opened",
    )
    assert "## Relayed ingress context (authoritative)" in additional
    assert "- **pull-request-number**: 7" in additional
    assert additional.index("Relayed ingress context") < additional.index(
        "Platform rules"
    )
    assert setup[0] == "set -euo pipefail"
    assert setup[1].startswith(': "${GH_TOKEN:=${GITHUB_TOKEN')
    assert setup[2] == "gh auth setup-git"
    assert "pull/7/head:feature/test" in setup[3]
    assert setup[4] == "git checkout feature/test"
    assert setup[-1] == "npm ci"


def test_apply_relayed_context_noop_without_target() -> None:
    additional, setup = igc.apply_relayed_ingress_context("{}", "Platform rules", [])
    assert additional == "Platform rules"
    assert setup == []
