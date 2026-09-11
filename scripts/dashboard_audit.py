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

"""
Audit Control Plane Dashboard checkbox enable/disable changes.

Posts issue comments on the dashboard issue (when / what / who). Deactivations
ask for a reason and @mention @elastic/observablt-ci. Sync resets use a fixed
automation reason.

Related issue: https://github.com/elastic/observability-robots/issues/4899
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from common import parse_checkbox_states_from_dashboard_body

logger = logging.getLogger(__name__)

AUDIT_TEAM_MENTION = "@elastic/observablt-ci"
AUDIT_MARKER_PREFIX = "<!-- aw:dashboard-audit:"
AWAITING_REASON_STATUS = "awaiting-reason"
COMPLETE_STATUS = "complete"
SYNC_SOURCE = "sync"
USER_SOURCE = "user"

_MARKER_RE = re.compile(
    r"<!-- aw:dashboard-audit:"
    r"status=(?P<status>awaiting-reason|complete)\s+"
    r"entry-id=(?P<entry_id>[a-zA-Z0-9-]+)\s+"
    r"compound-id=(?P<compound_id>[a-z0-9:-]+)\s+"
    r"source=(?P<source>user|sync)\s*"
    r"-->"
)


@dataclass(frozen=True)
class CheckboxDelta:
    """One compound-id enablement change between two dashboard bodies."""

    compound_id: str
    enabled_before: bool
    enabled_after: bool

    @property
    def is_activation(self) -> bool:
        return (not self.enabled_before) and self.enabled_after

    @property
    def is_deactivation(self) -> bool:
        return self.enabled_before and (not self.enabled_after)

    @property
    def direction(self) -> str:
        return "enabled" if self.enabled_after else "disabled"


def setup_logging() -> None:
    """Configure logging to stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def diff_checkbox_states(
    before: dict[str, bool], after: dict[str, bool]
) -> list[CheckboxDelta]:
    """
    Return enablement deltas between two checkbox state maps.

    - Keys present only in ``after`` and enabled → activation.
    - Keys present only in ``before`` and enabled → deactivation.
    - Keys present in both with different bool → activation or deactivation.
    - New unchecked rows and removed unchecked rows are ignored (not user toggles).
    """
    deltas: list[CheckboxDelta] = []
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        if old is None and new is True:
            deltas.append(CheckboxDelta(key, False, True))
        elif new is None and old is True:
            deltas.append(CheckboxDelta(key, True, False))
        elif old is not None and new is not None and old != new:
            deltas.append(CheckboxDelta(key, old, new))
    return deltas


def diff_dashboard_bodies(before_body: str, after_body: str) -> list[CheckboxDelta]:
    """Diff checkbox markers between two dashboard issue bodies."""
    return diff_checkbox_states(
        parse_checkbox_states_from_dashboard_body(before_body or ""),
        parse_checkbox_states_from_dashboard_body(after_body or ""),
    )


def _format_marker(
    *,
    status: str,
    entry_id: str,
    compound_id: str,
    source: str,
) -> str:
    return (
        f"{AUDIT_MARKER_PREFIX}status={status} entry-id={entry_id} "
        f"compound-id={compound_id} source={source} -->"
    )


def format_activation_comment(
    *,
    when: str,
    who: str,
    delta: CheckboxDelta,
    entry_id: str,
    source: str = USER_SOURCE,
) -> str:
    """Build an activation audit comment (no team mention)."""
    marker = _format_marker(
        status=COMPLETE_STATUS,
        entry_id=entry_id,
        compound_id=delta.compound_id,
        source=source,
    )
    return "\n".join(
        [
            marker,
            "## Control Plane Dashboard audit",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| **When** | {when} |",
            f"| **What** | `{delta.compound_id}` — {delta.direction} |",
            f"| **Who** | @{who.lstrip('@')} |",
            "",
        ]
    )


def format_deactivation_comment(
    *,
    when: str,
    who: str,
    delta: CheckboxDelta,
    entry_id: str,
    reason: str | None = None,
    source: str = USER_SOURCE,
) -> str:
    """Build a deactivation audit comment; omit team mention for sync source."""
    status = COMPLETE_STATUS if reason else AWAITING_REASON_STATUS
    marker = _format_marker(
        status=status,
        entry_id=entry_id,
        compound_id=delta.compound_id,
        source=source,
    )
    reason_line = (
        reason if reason else "_(awaiting — reply on this issue with the reason)_"
    )
    lines = [
        marker,
        "## Control Plane Dashboard audit",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **When** | {when} |",
        f"| **What** | `{delta.compound_id}` — {delta.direction} |",
        f"| **Who** | @{who.lstrip('@')} |",
        f"| **Reason** | {reason_line} |",
        "",
    ]
    if not reason and source == USER_SOURCE:
        lines.extend(
            [
                "Please reply to this issue with the **deactivation reason** for "
                f"`{delta.compound_id}` (a short comment is enough).",
                "",
                AUDIT_TEAM_MENTION,
                "",
            ]
        )
    elif reason and source == USER_SOURCE:
        lines.extend([AUDIT_TEAM_MENTION, ""])
    return "\n".join(lines)


def format_sync_batch_comment(
    *,
    when: str,
    who: str,
    deltas: list[CheckboxDelta],
    reason: str,
    entry_id: str,
) -> str:
    """Build one sync audit comment covering all checkbox deltas."""
    marker = (
        f"{AUDIT_MARKER_PREFIX}status={COMPLETE_STATUS} entry-id={entry_id} "
        f"compound-id=batch source={SYNC_SOURCE} -->"
    )
    rows = [f"| `{d.compound_id}` | {d.direction} |" for d in deltas]
    return "\n".join(
        [
            marker,
            "## Control Plane Dashboard audit (sync)",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| **When** | {when} |",
            f"| **Who** | @{who.lstrip('@')} |",
            f"| **Reason** | {reason} |",
            "",
            "| What | Direction |",
            "|------|-----------|",
            *rows,
            "",
        ]
    )


def parse_audit_marker(body: str) -> dict[str, str] | None:
    """Parse the first aw:dashboard-audit marker in a comment body."""
    match = _MARKER_RE.search(body or "")
    if not match:
        return None
    return {
        "status": match.group("status"),
        "entry_id": match.group("entry_id"),
        "compound_id": match.group("compound_id"),
        "source": match.group("source"),
    }


def is_bot_actor(login: str, *, sender_type: str | None = None) -> bool:
    """Return True when the actor looks like automation (skip user-path audit)."""
    if (sender_type or "").lower() == "bot":
        return True
    normalized = (login or "").lower()
    return normalized.endswith("[bot]") or normalized in {
        "github-actions[bot]",
        "github-actions",
    }


def gh_api(
    method: str,
    path: str,
    token: str,
    *,
    data: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    """Call GitHub REST API via gh CLI."""
    cmd = ["gh", "api", "-X", method, path, "-H", "Accept: application/vnd.github+json"]
    env = {**os.environ, "GH_TOKEN": token}
    if data is not None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            cmd.extend(["--input", f.name])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if result.returncode != 0:
                logger.error("gh api failed: %s", result.stderr)
                raise RuntimeError(f"gh api failed: {result.stderr}")
            return cast(
                dict[str, Any],
                json.loads(result.stdout) if result.stdout.strip() else {},
            )
        finally:
            Path(f.name).unlink(missing_ok=True)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        logger.error("gh api failed: %s", result.stderr)
        raise RuntimeError(f"gh api failed: {result.stderr}")
    raw: dict[str, Any] | list[Any] = (
        json.loads(result.stdout) if result.stdout.strip() else []
    )
    return raw


def create_issue_comment(
    owner: str, repo: str, issue_number: int, token: str, body: str
) -> dict[str, Any]:
    """Post a comment on an issue."""
    path = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
    return cast(dict[str, Any], gh_api("POST", path, token, data={"body": body}))


def update_issue_comment(
    owner: str, repo: str, comment_id: int, token: str, body: str
) -> dict[str, Any]:
    """Update an existing issue comment."""
    path = f"/repos/{owner}/{repo}/issues/comments/{comment_id}"
    return cast(dict[str, Any], gh_api("PATCH", path, token, data={"body": body}))


def list_issue_comments(
    owner: str, repo: str, issue_number: int, token: str
) -> list[dict[str, Any]]:
    """List issue comments (first page, up to 100)."""
    path = (
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        f"?per_page=100&sort=created&direction=desc"
    )
    raw = gh_api("GET", path, token)
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw]


def post_user_checkbox_audits(
    *,
    owner: str,
    repo: str,
    issue_number: int,
    token: str,
    before_body: str,
    after_body: str,
    actor: str,
    when: str,
) -> int:
    """Diff bodies and post per-delta audit comments. Returns number of comments."""
    deltas = diff_dashboard_bodies(before_body, after_body)
    if not deltas:
        logger.info("No checkbox deltas; skipping audit comments")
        return 0
    posted = 0
    for delta in deltas:
        entry_id = str(uuid.uuid4())
        if delta.is_activation:
            body = format_activation_comment(
                when=when, who=actor, delta=delta, entry_id=entry_id
            )
        elif delta.is_deactivation:
            body = format_deactivation_comment(
                when=when, who=actor, delta=delta, entry_id=entry_id
            )
        else:
            continue
        create_issue_comment(owner, repo, issue_number, token, body)
        posted += 1
        logger.info(
            "Posted audit for %s (%s) on %s/%s#%s",
            delta.compound_id,
            delta.direction,
            owner,
            repo,
            issue_number,
        )
    return posted


def post_sync_checkbox_audits(
    *,
    owner: str,
    repo: str,
    issue_number: int,
    token: str,
    before_body: str | None,
    after_body: str,
    actor: str,
    reason: str,
    when: str | None = None,
) -> int:
    """Post a batched sync audit comment when sync changed checkboxes."""
    deltas = diff_dashboard_bodies(before_body or "", after_body)
    if not deltas:
        logger.info("Sync produced no checkbox deltas; skipping audit")
        return 0
    stamp = when or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = format_sync_batch_comment(
        when=stamp,
        who=actor,
        deltas=deltas,
        reason=reason,
        entry_id=str(uuid.uuid4()),
    )
    create_issue_comment(owner, repo, issue_number, token, body)
    logger.info(
        "Posted sync audit (%s deltas, reason=%s) on %s/%s#%s",
        len(deltas),
        reason,
        owner,
        repo,
        issue_number,
    )
    return 1


def _find_awaiting_comment(
    comments: list[dict[str, Any]], reply_body: str
) -> dict[str, Any] | None:
    """Pick the awaiting-reason audit comment to update for a human reply."""
    awaiting: list[tuple[dict[str, Any], dict[str, str]]] = []
    for comment in comments:
        meta = parse_audit_marker(str(comment.get("body") or ""))
        if meta and meta["status"] == AWAITING_REASON_STATUS:
            awaiting.append((comment, meta))
    if not awaiting:
        return None
    if len(awaiting) == 1:
        return awaiting[0][0]
    for comment, meta in awaiting:
        if meta["compound_id"] and meta["compound_id"] in reply_body:
            return comment
    # Newest first from API; take the most recent awaiting entry.
    return awaiting[0][0]


def record_deactivation_reason(
    *,
    owner: str,
    repo: str,
    issue_number: int,
    token: str,
    reply_body: str,
    reply_author: str,
) -> bool:
    """
    Update an awaiting-reason audit comment with the human reply as the reason.

    Returns True when a comment was updated.
    """
    if AUDIT_MARKER_PREFIX in (reply_body or ""):
        logger.info("Ignoring comment that contains an audit marker")
        return False
    if is_bot_actor(reply_author):
        logger.info("Ignoring bot comment for reason recording")
        return False
    reason = (reply_body or "").strip()
    if not reason:
        logger.info("Empty reason reply; skipping")
        return False

    comments = list_issue_comments(owner, repo, issue_number, token)
    target = _find_awaiting_comment(comments, reason)
    if target is None:
        logger.info("No awaiting-reason audit comment found")
        return False

    old_body = str(target.get("body") or "")
    meta = parse_audit_marker(old_body)
    if meta is None:
        return False

    when_match = re.search(r"\|\s*\*\*When\*\*\s*\|\s*([^|]+)\|", old_body)
    who_match = re.search(r"\|\s*\*\*Who\*\*\s*\|\s*@?([^|]+)\|", old_body)
    when = (when_match.group(1).strip() if when_match else "") or datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    who = who_match.group(1).strip() if who_match else "unknown"

    delta = CheckboxDelta(meta["compound_id"], True, False)
    # Escape pipe characters so the reason stays in one table cell.
    safe_reason = reason.replace("\n", " ").replace("|", "\\|")
    safe_reason = f"{safe_reason} _(recorded from @{reply_author.lstrip('@')})_"
    new_body = format_deactivation_comment(
        when=when,
        who=who,
        delta=delta,
        entry_id=meta["entry_id"],
        reason=safe_reason,
        source=meta.get("source", USER_SOURCE),
    )
    comment_id = int(target["id"])
    update_issue_comment(owner, repo, comment_id, token, new_body)
    logger.info(
        "Recorded deactivation reason for %s on comment %s",
        meta["compound_id"],
        comment_id,
    )
    return True


def _require_token() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN or GITHUB_TOKEN must be set")
    return token


def _split_repo(repo: str) -> tuple[str, str]:
    owner, _, name = repo.partition("/")
    if not name:
        raise SystemExit(f"Invalid repo format: {repo}. Expected owner/repo")
    return owner, name


def _read_body(path: str | None, inline: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return inline or ""


def _load_event_payload(path: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(Path(path).read_text(encoding="utf-8")))


def main() -> int:
    """CLI entry point for workflow and sync callers."""
    parser = argparse.ArgumentParser(description="Control Plane Dashboard audit")
    sub = parser.add_subparsers(dest="command", required=True)

    user_cmd = sub.add_parser(
        "checkbox-delta", help="Audit user checkbox edits on a dashboard issue"
    )
    user_cmd.add_argument("--repo", default="")
    user_cmd.add_argument("--issue-number", type=int, default=0)
    user_cmd.add_argument("--actor", default="")
    user_cmd.add_argument("--sender-type", default="")
    user_cmd.add_argument("--when", default="")
    user_cmd.add_argument("--before-body-file", default="")
    user_cmd.add_argument("--after-body-file", default="")
    user_cmd.add_argument("--before-body", default="")
    user_cmd.add_argument("--after-body", default="")
    user_cmd.add_argument(
        "--event-path",
        default="",
        help="Path to GitHub event JSON (GITHUB_EVENT_PATH); fills missing fields",
    )

    reason_cmd = sub.add_parser(
        "record-reason", help="Record a deactivation reason from an issue comment"
    )
    reason_cmd.add_argument("--repo", default="")
    reason_cmd.add_argument("--issue-number", type=int, default=0)
    reason_cmd.add_argument("--comment-author", default="")
    reason_cmd.add_argument("--comment-body-file", default="")
    reason_cmd.add_argument("--comment-body", default="")
    reason_cmd.add_argument(
        "--event-path",
        default="",
        help="Path to GitHub event JSON (GITHUB_EVENT_PATH); fills missing fields",
    )

    args = parser.parse_args()
    setup_logging()
    token = _require_token()

    event: dict[str, Any] = {}
    if args.event_path:
        event = _load_event_payload(args.event_path)

    if args.command == "checkbox-delta":
        issue = cast(dict[str, Any], event.get("issue") or {})
        sender = cast(dict[str, Any], event.get("sender") or {})
        changes = cast(dict[str, Any], event.get("changes") or {})
        body_change = cast(dict[str, Any], changes.get("body") or {})
        repo = args.repo or cast(str, event.get("repository", {}).get("full_name", ""))
        if not repo and "repository" in event:
            r = cast(dict[str, Any], event["repository"])
            repo = f"{r.get('owner', {}).get('login', '')}/{r.get('name', '')}"
        issue_number = args.issue_number or int(issue.get("number") or 0)
        actor = args.actor or str(sender.get("login") or "")
        sender_type = args.sender_type or str(sender.get("type") or "")
        when = args.when or str(issue.get("updated_at") or "")
        before = _read_body(args.before_body_file or None, args.before_body)
        after = _read_body(args.after_body_file or None, args.after_body)
        if args.event_path:
            if not before:
                before = str(body_change.get("from") or "")
            if not after:
                after = str(issue.get("body") or "")
        if not repo or not issue_number:
            raise SystemExit(
                "checkbox-delta requires --repo/--issue-number or --event-path"
            )
        owner, repo_name = _split_repo(repo)
        if is_bot_actor(actor, sender_type=sender_type):
            logger.info(
                "Skipping user-path audit for automation actor %s (type=%s)",
                actor,
                sender_type or "unknown",
            )
            return 0
        if not before.strip():
            logger.info(
                "No previous body in event.changes; skipping (likely a non-body edit)"
            )
            return 0
        when = when or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        post_user_checkbox_audits(
            owner=owner,
            repo=repo_name,
            issue_number=issue_number,
            token=token,
            before_body=before,
            after_body=after,
            actor=actor,
            when=when,
        )
        return 0

    if args.command == "record-reason":
        issue = cast(dict[str, Any], event.get("issue") or {})
        comment = cast(dict[str, Any], event.get("comment") or {})
        user = cast(dict[str, Any], comment.get("user") or {})
        repo = args.repo or ""
        if not repo and "repository" in event:
            r = cast(dict[str, Any], event["repository"])
            repo = f"{r.get('owner', {}).get('login', '')}/{r.get('name', '')}"
        issue_number = args.issue_number or int(issue.get("number") or 0)
        author = args.comment_author or str(user.get("login") or "")
        body = _read_body(args.comment_body_file or None, args.comment_body)
        if args.event_path and not body:
            body = str(comment.get("body") or "")
        if not repo or not issue_number:
            raise SystemExit(
                "record-reason requires --repo/--issue-number or --event-path"
            )
        owner, repo_name = _split_repo(repo)
        record_deactivation_reason(
            owner=owner,
            repo=repo_name,
            issue_number=issue_number,
            token=token,
            reply_body=body,
            reply_author=author,
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
