#!/usr/bin/env python3
# Copyright 2026-2027 Elasticsearch B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Build gh-aw prompt and setup overrides from relayed ingress event JSON."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RelayedGitHubContext:
    event_name: str | None
    event_action: str | None
    pull_request_number: int | None
    pull_request_title: str | None
    pull_request_head_ref: str | None
    pull_request_head_sha: str | None
    issue_number: int | None
    comment_id: int | None
    discussion_number: int | None

    @property
    def has_actionable_target(self) -> bool:
        return any(
            value is not None
            for value in (
                self.pull_request_number,
                self.issue_number,
                self.comment_id,
                self.discussion_number,
            )
        )


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def parse_relayed_ingress_payload(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None
    return payload


def extract_relayed_github_context(
    payload: dict[str, Any],
    *,
    ingress_event_name: str | None = None,
    ingress_event_action: str | None = None,
) -> RelayedGitHubContext:
    pull_request = payload.get("pull_request")
    issue = payload.get("issue")
    comment = payload.get("comment")
    discussion = payload.get("discussion")
    inputs = payload.get("inputs")

    pull_request_number: int | None = None
    pull_request_title: str | None = None
    pull_request_head_ref: str | None = None
    pull_request_head_sha: str | None = None

    if isinstance(pull_request, dict):
        pull_request_number = _positive_int(pull_request.get("number"))
        pull_request_title = _optional_str(pull_request.get("title"))
        head = pull_request.get("head")
        if isinstance(head, dict):
            pull_request_head_ref = _optional_str(head.get("ref"))
            pull_request_head_sha = _optional_str(head.get("sha"))

    issue_number = (
        _positive_int(issue.get("number")) if isinstance(issue, dict) else None
    )
    if (
        pull_request_number is None
        and isinstance(issue, dict)
        and issue.get("pull_request") is not None
    ):
        pull_request_number = issue_number
        pull_request_title = _optional_str(issue.get("title"))

    if isinstance(inputs, dict):
        if pull_request_number is None:
            pull_request_number = _positive_int(inputs.get("pull_request_number"))
        if issue_number is None:
            issue_number = _positive_int(inputs.get("issue_number"))

    event_name = _optional_str(ingress_event_name) or _optional_str(
        payload.get("event_name")
    )
    event_action = _optional_str(ingress_event_action) or _optional_str(
        payload.get("action")
    )

    return RelayedGitHubContext(
        event_name=event_name,
        event_action=event_action,
        pull_request_number=pull_request_number,
        pull_request_title=pull_request_title,
        pull_request_head_ref=pull_request_head_ref,
        pull_request_head_sha=pull_request_head_sha,
        issue_number=issue_number,
        comment_id=_positive_int(comment.get("id"))
        if isinstance(comment, dict)
        else None,
        discussion_number=_positive_int(discussion.get("number"))
        if isinstance(discussion, dict)
        else None,
    )


def build_relayed_context_instructions(ctx: RelayedGitHubContext) -> str:
    if not ctx.has_actionable_target:
        return ""

    lines = [
        "## Relayed ingress context (authoritative)",
        "",
        "This run reached the agent through the oblt-aw entrypoint (`workflow_dispatch` relay).",
        "The built-in GitHub context block above may show empty PR/issue identifiers — ignore those empty values.",
        "Use the relayed values below for MCP calls, analysis, comments, labels, and checkout.",
        "",
    ]

    if ctx.event_name:
        lines.append(f"- **relay-event-name**: {ctx.event_name}")
    if ctx.event_action:
        lines.append(f"- **relay-event-action**: {ctx.event_action}")
    if ctx.pull_request_number is not None:
        lines.append(f"- **pull-request-number**: {ctx.pull_request_number}")
    if ctx.pull_request_title:
        lines.append(f"- **pull-request-title**: {ctx.pull_request_title}")
    if ctx.pull_request_head_ref:
        lines.append(f"- **pull-request-head-ref**: {ctx.pull_request_head_ref}")
    if ctx.pull_request_head_sha:
        lines.append(f"- **pull-request-head-sha**: {ctx.pull_request_head_sha}")
    if ctx.issue_number is not None:
        lines.append(f"- **issue-number**: {ctx.issue_number}")
    if ctx.comment_id is not None:
        lines.append(f"- **comment-id**: {ctx.comment_id}")
    if ctx.discussion_number is not None:
        lines.append(f"- **discussion-number**: {ctx.discussion_number}")

    lines.extend(
        [
            "",
            "Rules:",
            "- Do not emit `missing_data` for pull request or issue numbers when relayed values above are present.",
            "- Prefer GitHub MCP tools (`pull_request_read`, `issue_read`, and related methods) with these relayed numbers.",
            "- Treat relayed pull-request/issue numbers as the workflow target even when built-in context shows `#` or blank values.",
        ]
    )
    return "\n".join(lines)


def build_relayed_setup_commands(ctx: RelayedGitHubContext) -> list[str]:
    if ctx.pull_request_number is None or not ctx.pull_request_head_ref:
        return []

    ref = ctx.pull_request_head_ref
    pr_number = ctx.pull_request_number
    return [
        "set -euo pipefail",
        ': "${GH_TOKEN:=${GITHUB_TOKEN:?GitHub token required for relayed PR checkout}}"',
        "gh auth setup-git",
        # Fetch to FETCH_HEAD only: refspec updates to the checked-out branch fail in CI.
        f"git fetch origin {shlex.quote(f'pull/{pr_number}/head')}",
        f"git checkout -B {shlex.quote(ref)} FETCH_HEAD",
    ]


def apply_relayed_ingress_context(
    payload_json: str,
    additional_instructions: str,
    setup_commands: list[str],
    *,
    ingress_event_name: str | None = None,
    ingress_event_action: str | None = None,
) -> tuple[str, list[str]]:
    payload = parse_relayed_ingress_payload(payload_json)
    if payload is None:
        return additional_instructions, setup_commands

    ctx = extract_relayed_github_context(
        payload,
        ingress_event_name=ingress_event_name,
        ingress_event_action=ingress_event_action,
    )
    relayed_block = build_relayed_context_instructions(ctx)
    if not relayed_block:
        return additional_instructions, setup_commands

    relayed_setup = build_relayed_setup_commands(ctx)
    merged_setup = relayed_setup + setup_commands

    platform = additional_instructions.strip()
    merged_additional = f"{relayed_block}\n\n{platform}" if platform else relayed_block
    return merged_additional, merged_setup
