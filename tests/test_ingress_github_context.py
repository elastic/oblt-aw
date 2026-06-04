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


def test_apply_relayed_context_instructs_mcp_for_missing_webhook_fields() -> None:
    payload = {
        "pull_request": {
            "number": 3,
            "head": {"ref": "fix", "sha": "abc"},
        },
    }
    additional, _setup = igc.apply_relayed_ingress_context(
        json.dumps(payload),
        "",
        [],
        ingress_event_name="pull_request",
    )
    assert "GitHub data not guaranteed in the relay payload" in additional
    assert "pull_request_read" in additional
    assert "issue_read" in additional


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
    assert setup[3] == "git fetch origin pull/7/head"
    assert setup[4] == "git checkout -B feature/test FETCH_HEAD"
    assert setup[-1] == "npm ci"


def test_build_relayed_setup_commands_uses_fetch_head_for_checked_out_branch() -> None:
    ctx = igc.RelayedGitHubContext(
        event_name="pull_request",
        event_action="synchronize",
        pull_request_number=55,
        pull_request_title="Bump terragrunt",
        pull_request_head_ref="updatecli_main_terragrunt/version",
        pull_request_head_sha="abc123",
        issue_number=None,
        comment_id=None,
        discussion_number=None,
    )
    setup = igc.build_relayed_setup_commands(ctx)
    assert setup[3] == "git fetch origin pull/55/head"
    assert setup[4] == "git checkout -B updatecli_main_terragrunt/version FETCH_HEAD"
    assert ":updatecli_main_terragrunt/version" not in setup[3]


def test_apply_relayed_context_noop_without_target() -> None:
    additional, setup = igc.apply_relayed_ingress_context("{}", "Platform rules", [])
    assert additional == "Platform rules"
    assert setup == []


def test_prepare_relayed_event_passthrough_when_small() -> None:
    event = {"action": "opened", "pull_request": {"number": 1, "extra": "kept"}}
    payload, mode = igc.prepare_relayed_github_event(event, max_chars=10_000)
    assert mode == igc.RELAY_PREPARE_MODE_PASSTHROUGH
    assert payload["pull_request"]["extra"] == "kept"


def test_prepare_relayed_event_slims_large_pull_request() -> None:
    event = {
        "action": "synchronize",
        "pull_request": {
            "number": 1234,
            "title": "Large change",
            "head": {"ref": "feature/x", "sha": "abc"},
            "user": {"login": "dependabot[bot]", "id": 999},
            "labels": [{"id": 1, "name": "oblt-aw/triage/foo"}],
            "body": "x" * 50_000,
            "commits": [{"sha": "a" * 40}] * 200,
            "files": [{"filename": f"path/{i}.go"} for i in range(500)],
        },
    }
    payload, mode = igc.prepare_relayed_github_event(event)
    payload_json, json_mode = igc.prepare_relayed_github_event_json(event)

    assert mode == igc.RELAY_PREPARE_MODE_SLIM
    assert json_mode == igc.RELAY_PREPARE_MODE_SLIM
    assert payload["pull_request"]["number"] == 1234
    assert payload["pull_request"]["head"] == {"ref": "feature/x", "sha": "abc"}
    assert payload["pull_request"]["labels"] == [{"name": "oblt-aw/triage/foo"}]
    assert "body" not in payload["pull_request"]
    assert "commits" not in payload["pull_request"]
    assert len(payload_json) < igc.RELAY_EVENT_JSON_MAX_CHARS
    assert len(json.dumps(event)) > igc.RELAY_EVENT_JSON_MAX_CHARS


def test_prepare_relayed_event_truncates_huge_comment_body() -> None:
    event = {
        "action": "created",
        "issue": {"number": 1, "labels": [{"name": "x"}]},
        "comment": {
            "id": 9,
            "body": "/ai implement\n" + ("z" * 70_000),
            "author_association": "MEMBER",
            "user": {"login": "alice"},
        },
    }
    slim = igc.slim_relayed_github_event(event)
    assert igc._relay_json_size(slim) > igc.RELAY_EVENT_JSON_MAX_CHARS

    payload, mode = igc.prepare_relayed_github_event(event)
    assert mode == igc.RELAY_PREPARE_MODE_TRUNCATED
    assert payload["comment"]["body"].startswith("/ai implement")
    assert len(payload["comment"]["body"]) < len(event["comment"]["body"])
    assert igc._relay_json_size(payload) <= igc.RELAY_EVENT_JSON_MAX_CHARS


def test_slim_relayed_github_event_preserves_issue_comment_routing_fields() -> None:
    event = {
        "action": "created",
        "issue": {
            "number": 9,
            "labels": [{"name": "oblt-aw/ai/fix-ready"}],
        },
        "comment": {
            "id": 42,
            "body": "/ai implement",
            "author_association": "MEMBER",
            "user": {"login": "octocat"},
        },
    }
    slim = igc.slim_relayed_github_event(event)
    assert slim["issue"]["number"] == 9
    assert slim["comment"]["body"] == "/ai implement"
    assert slim["comment"]["author_association"] == "MEMBER"


def test_slim_relayed_github_event_marks_pr_issues() -> None:
    event = {"issue": {"number": 5, "pull_request": {"url": "https://example/pr"}}}
    slim = igc.slim_relayed_github_event(event)
    assert slim["issue"]["pull_request"] == {}
