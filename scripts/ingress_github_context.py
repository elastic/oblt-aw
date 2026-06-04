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

"""Build gh-aw prompt and setup overrides from relayed ingress event JSON.

Relay payload contract (attributes used by ingress and wrappers):
docs/workflows/relayed-event-payload.md
"""

from __future__ import annotations

import copy
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


# GitHub documents a 65,535-character maximum payload for workflow_dispatch inputs (combined).
# See https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatchinputs
WORKFLOW_DISPATCH_INPUT_MAX_CHARS = 65_535
# Reserve space for sibling dispatch inputs (trigger-source, event-name, caller-ref, …).
DISPATCH_SIBLING_INPUTS_RESERVED_CHARS = 2048
RELAY_EVENT_JSON_MAX_CHARS = (
    WORKFLOW_DISPATCH_INPUT_MAX_CHARS - DISPATCH_SIBLING_INPUTS_RESERVED_CHARS
)

# Truncation caps (truncated mode only). See docs/workflows/relayed-event-payload.md.
TRUNCATE_COMMENT_BODY_MAX_CHARS = 8192
TRUNCATE_COMMENT_BODY_SUFFIX_CHARS = 512
TRUNCATE_CHANGES_BODY_FROM_MAX_CHARS = 8192
TRUNCATE_TITLE_MAX_CHARS = 512
TRUNCATE_DESCRIPTION_MAX_CHARS = 512

RELAY_PREPARE_MODE_PASSTHROUGH = "passthrough"
RELAY_PREPARE_MODE_SLIM = "slim"
RELAY_PREPARE_MODE_TRUNCATED = "truncated"


def _slim_label_list(labels: Any) -> list[dict[str, str]] | None:
    if not isinstance(labels, list):
        return None
    out: list[dict[str, str]] = []
    for item in labels:
        if isinstance(item, dict):
            name = _optional_str(item.get("name"))
            if name:
                out.append({"name": name})
    return out or None


def slim_relayed_github_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return the minimal github.event fields required by ingress routing and agents."""
    slim: dict[str, Any] = {}

    if action := _optional_str(event.get("action")):
        slim["action"] = action

    inputs = event.get("inputs")
    if isinstance(inputs, dict):
        slim_inputs: dict[str, Any] = {}
        for key in ("issue_number", "pull_request_number"):
            if key in inputs:
                slim_inputs[key] = inputs[key]
        if slim_inputs:
            slim["inputs"] = slim_inputs

    for key in ("state", "context", "description", "target_url", "sha"):
        if key in event and event[key] is not None:
            slim[key] = event[key]

    changes = event.get("changes")
    if isinstance(changes, dict):
        body_change = changes.get("body")
        if isinstance(body_change, dict) and "from" in body_change:
            slim["changes"] = {"body": {"from": body_change["from"]}}

    pull_request = event.get("pull_request")
    if isinstance(pull_request, dict):
        slim_pr: dict[str, Any] = {}
        if number := _positive_int(pull_request.get("number")):
            slim_pr["number"] = number
        if title := _optional_str(pull_request.get("title")):
            slim_pr["title"] = title
        user = pull_request.get("user")
        if isinstance(user, dict):
            login = _optional_str(user.get("login"))
            if login:
                slim_pr["user"] = {"login": login}
        head = pull_request.get("head")
        if isinstance(head, dict):
            slim_head: dict[str, str] = {}
            if ref := _optional_str(head.get("ref")):
                slim_head["ref"] = ref
            if sha := _optional_str(head.get("sha")):
                slim_head["sha"] = sha
            if slim_head:
                slim_pr["head"] = slim_head
        if labels := _slim_label_list(pull_request.get("labels")):
            slim_pr["labels"] = labels
        if slim_pr:
            slim["pull_request"] = slim_pr

    issue = event.get("issue")
    if isinstance(issue, dict):
        slim_issue: dict[str, Any] = {}
        if number := _positive_int(issue.get("number")):
            slim_issue["number"] = number
        if title := _optional_str(issue.get("title")):
            slim_issue["title"] = title
        if issue.get("pull_request") is not None:
            slim_issue["pull_request"] = {}
        if labels := _slim_label_list(issue.get("labels")):
            slim_issue["labels"] = labels
        if slim_issue:
            slim["issue"] = slim_issue

    comment = event.get("comment")
    if isinstance(comment, dict):
        slim_comment: dict[str, Any] = {}
        if comment_id := _positive_int(comment.get("id")):
            slim_comment["id"] = comment_id
        if isinstance(comment.get("body"), str):
            slim_comment["body"] = comment["body"]
        if assoc := _optional_str(comment.get("author_association")):
            slim_comment["author_association"] = assoc
        user = comment.get("user")
        if isinstance(user, dict):
            login = _optional_str(user.get("login"))
            if login:
                slim_comment["user"] = {"login": login}
        if slim_comment:
            slim["comment"] = slim_comment

    label = event.get("label")
    if isinstance(label, dict):
        if name := _optional_str(label.get("name")):
            slim["label"] = {"name": name}

    discussion = event.get("discussion")
    if isinstance(discussion, dict):
        if number := _positive_int(discussion.get("number")):
            slim["discussion"] = {"number": number}

    workflow_run = event.get("workflow_run")
    if isinstance(workflow_run, dict):
        slim_wr: dict[str, Any] = {}
        if run_id := _positive_int(workflow_run.get("id")):
            slim_wr["id"] = run_id
        if conclusion := _optional_str(workflow_run.get("conclusion")):
            slim_wr["conclusion"] = conclusion
        if wr_event := _optional_str(workflow_run.get("event")):
            slim_wr["event"] = wr_event
        if slim_wr:
            slim["workflow_run"] = slim_wr

    return slim


def _relay_json_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, separators=(",", ":")))


def _truncate_text(
    value: str,
    max_chars: int,
    *,
    preserve_suffix_chars: int = 0,
) -> str:
    if len(value) <= max_chars:
        return value
    if preserve_suffix_chars > 0 and max_chars > preserve_suffix_chars + 32:
        prefix_len = max_chars - preserve_suffix_chars - 3
        return f"{value[:prefix_len]}...{value[-preserve_suffix_chars:]}"
    return value[:max_chars]


def truncate_relayed_github_event(event: dict[str, Any]) -> dict[str, Any]:
    """Shorten long non-routing strings in an already-slimmed relay payload."""
    truncated = copy.deepcopy(event)

    changes = truncated.get("changes")
    if isinstance(changes, dict):
        body = changes.get("body")
        if isinstance(body, dict) and isinstance(body.get("from"), str):
            body["from"] = _truncate_text(
                body["from"], TRUNCATE_CHANGES_BODY_FROM_MAX_CHARS
            )

    comment = truncated.get("comment")
    if isinstance(comment, dict) and isinstance(comment.get("body"), str):
        comment["body"] = _truncate_text(
            comment["body"],
            TRUNCATE_COMMENT_BODY_MAX_CHARS,
            preserve_suffix_chars=TRUNCATE_COMMENT_BODY_SUFFIX_CHARS,
        )

    pull_request = truncated.get("pull_request")
    if isinstance(pull_request, dict) and isinstance(pull_request.get("title"), str):
        pull_request["title"] = _truncate_text(
            pull_request["title"], TRUNCATE_TITLE_MAX_CHARS
        )

    issue = truncated.get("issue")
    if isinstance(issue, dict) and isinstance(issue.get("title"), str):
        issue["title"] = _truncate_text(issue["title"], TRUNCATE_TITLE_MAX_CHARS)

    if isinstance(truncated.get("description"), str):
        truncated["description"] = _truncate_text(
            truncated["description"], TRUNCATE_DESCRIPTION_MAX_CHARS
        )

    return truncated


def prepare_relayed_github_event(
    event: dict[str, Any],
    *,
    max_chars: int = RELAY_EVENT_JSON_MAX_CHARS,
) -> tuple[dict[str, Any], str]:
    """Return relay payload and mode: passthrough, slim, or truncated."""
    if _relay_json_size(event) <= max_chars:
        return event, RELAY_PREPARE_MODE_PASSTHROUGH

    slim = slim_relayed_github_event(event)
    if _relay_json_size(slim) <= max_chars:
        return slim, RELAY_PREPARE_MODE_SLIM

    truncated = truncate_relayed_github_event(slim)
    if _relay_json_size(truncated) <= max_chars:
        return truncated, RELAY_PREPARE_MODE_TRUNCATED

    msg = (
        "relayed github.event JSON exceeds workflow_dispatch budget after slim and "
        f"truncation ({_relay_json_size(truncated)} > {max_chars} chars)"
    )
    raise ValueError(msg)


def prepare_relayed_github_event_json(
    event: dict[str, Any],
    *,
    max_chars: int = RELAY_EVENT_JSON_MAX_CHARS,
) -> tuple[str, str]:
    """Serialize relay payload for event-payload-json; returns (json, mode)."""
    payload, mode = prepare_relayed_github_event(event, max_chars=max_chars)
    return json.dumps(payload, separators=(",", ":")), mode


def slim_relayed_github_event_json(event: dict[str, Any]) -> str:
    """Serialize after prepare (passthrough, slim, or truncated). Prefer prepare_* APIs."""
    payload_json, _mode = prepare_relayed_github_event_json(event)
    return payload_json


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
            "- Treat relayed pull-request/issue numbers as the workflow target even when built-in context shows `#` or blank values.",
            "- Do not rely on the built-in GitHub Actions `github.event` webhook object on this run (entrypoint is `workflow_dispatch`).",
            "",
            "GitHub data not guaranteed in the relay payload:",
            "- The trigger may passthrough, slim, or truncate the webhook JSON to satisfy `workflow_dispatch` input size limits.",
            "- Large or verbose webhook fields are omitted or shortened: PR/issue bodies, diffs, `files`/`commits` lists, reviews, checks, and similar bloat.",
            "- Authoritative content must be loaded by the agent using GitHub MCP with the relayed numbers above, including when a field was truncated:",
            "  - `pull_request_read` — PR metadata, description, files, reviews, commits, and CI-related context",
            "  - `issue_read` — issue or PR-discussion body, labels, and timeline (use issue number; PRs are issues in the API)",
            "  - Comment and review APIs — full comment bodies when the relay only preserved a prefix for routing",
            "- Prefer MCP results over relayed JSON for any analysis, quoting, labels, or code changes.",
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
