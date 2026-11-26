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

"""Check Phase 2 on an elastic/oblt-aw onboard issue after catalog-info merge.

Used by ``.github/workflows/oblt-aw-onboard-phase2-bridge.yml`` in
``elastic/catalog-info``. Canonical copy lives under
``platform/catalog-info/`` in ``elastic/oblt-aw`` and is mirrored into
catalog-info.

Environment:

- ``GH_TOKEN`` — token with ``issues: write`` on ``elastic/oblt-aw``
- ``PR_BODY`` — merged pull request body (Related issue link)
- ``PR_TITLE`` — merged pull request title (``[oblt-aw][onboard] …``)
- ``PR_URL`` — optional HTML URL for the comment
- ``OBLT_AW_REPO`` — default ``elastic/oblt-aw``
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

_RELATED_ISSUE_RE = re.compile(
    r"(?im)(?:^|\n)\s*Related issue:\s*"
    r"(?:https://github\.com/elastic/oblt-aw/issues/|elastic/oblt-aw#|#)"
    r"(\d+)\b"
)
_CONSUMER_REPO_RE = re.compile(r"\belastic/[A-Za-z0-9._-]+\b")
_PHASE2_UNCHECKED_RE = re.compile(
    r"^(\s*-\s*\[)[ ](\]\s*\*\*Phase 2)",
    re.MULTILINE | re.IGNORECASE,
)
_PHASE2_CHECKED_RE = re.compile(
    r"^\s*-\s*\[[xX]\]\s*\*\*Phase 2",
    re.MULTILINE | re.IGNORECASE,
)
_ONBOARD_LABEL = "oblt-aw/onboard/repository"


def normalize_newlines(text: str) -> str:
    """Normalize CRLF / CR to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_related_issue_number(body: str) -> int | None:
    """Return the oblt-aw issue number from a ``Related issue:`` line."""
    match = _RELATED_ISSUE_RE.search(normalize_newlines(body))
    if not match:
        return None
    return int(match.group(1))


def extract_consumer_repo(title: str) -> str | None:
    """Return the first ``elastic/<repo>`` slug from a PR title, if any."""
    match = _CONSUMER_REPO_RE.search(title)
    return match.group(0) if match else None


def check_phase2_box(body: str) -> tuple[str, bool]:
    """Check the Phase 2 task-list item. Return ``(new_body, changed)``."""
    normalized = normalize_newlines(body)
    if _PHASE2_CHECKED_RE.search(normalized):
        return normalized, False
    updated, count = _PHASE2_UNCHECKED_RE.subn(r"\1x\2", normalized, count=1)
    if count != 1:
        raise ValueError("Phase 2 checkbox line not found in issue body")
    return updated, True


def _gh_env(token: str) -> dict[str, str]:
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    env["GITHUB_TOKEN"] = token
    # Bypass any localhost DIFC proxy if inherited.
    env["GITHUB_API_URL"] = "https://api.github.com"
    return env


def _gh_api(
    token: str,
    endpoint: str,
    *,
    method: str = "GET",
    raw_fields: dict[str, str] | None = None,
    json_body: dict[str, object] | None = None,
) -> object:
    cmd = ["gh", "api", endpoint, "--method", method]
    stdin = None
    if json_body is not None:
        cmd.extend(["--input", "-"])
        stdin = json.dumps(json_body)
    elif raw_fields:
        for key, value in raw_fields.items():
            cmd.extend(["-f", f"{key}={value}"])
    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        env=_gh_env(token),
        input=stdin,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh api {method} {endpoint} failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout)


def find_open_onboard_issue(
    token: str, repo_full: str, consumer_repo: str
) -> int | None:
    """Find an open onboard issue whose body mentions ``consumer_repo``."""
    # Search is best-effort fallback when Related issue is missing.
    query = (
        f'repo:{repo_full} is:issue is:open label:"{_ONBOARD_LABEL}" "{consumer_repo}"'
    )
    result = _gh_api(
        token,
        "search/issues",
        raw_fields={"q": query, "per_page": "5"},
    )
    assert isinstance(result, dict)
    items = result.get("items")
    if not isinstance(items, list) or not items:
        return None
    first = items[0]
    if not isinstance(first, dict):
        return None
    number = first.get("number")
    return int(number) if isinstance(number, int) else None


def resolve_issue_number(
    token: str, repo_full: str, pr_body: str, pr_title: str
) -> int:
    """Resolve the onboard issue from Related issue or title fallback search."""
    related = parse_related_issue_number(pr_body)
    if related is not None:
        return related
    consumer = extract_consumer_repo(pr_title)
    if not consumer:
        raise SystemExit(
            "Cannot resolve onboard issue: no Related issue line and no elastic/<repo> in title"
        )
    found = find_open_onboard_issue(token, repo_full, consumer)
    if found is None:
        raise SystemExit(
            f"Cannot resolve onboard issue for {consumer}: add "
            f"'Related issue: https://github.com/{repo_full}/issues/<n>' to the catalog PR body"
        )
    print(
        f"::warning::Related issue missing; using open onboard issue #{found} for {consumer}"
    )
    return found


def main() -> int:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        print("::error::GH_TOKEN is required", file=sys.stderr)
        return 1
    pr_body = os.environ.get("PR_BODY", "")
    pr_title = os.environ.get("PR_TITLE", "")
    pr_url = os.environ.get("PR_URL", "").strip()
    repo_full = os.environ.get("OBLT_AW_REPO", "elastic/oblt-aw")

    issue_number = resolve_issue_number(token, repo_full, pr_body, pr_title)
    issue = _gh_api(token, f"repos/{repo_full}/issues/{issue_number}")
    assert isinstance(issue, dict)
    labels = issue.get("labels") or []
    label_names = {
        str(item.get("name", "")) for item in labels if isinstance(item, dict)
    }
    if _ONBOARD_LABEL not in label_names:
        raise SystemExit(
            f"Issue #{issue_number} lacks label {_ONBOARD_LABEL}; refusing to edit"
        )
    body = str(issue.get("body") or "")
    new_body, changed = check_phase2_box(body)
    if not changed:
        print(f"Phase 2 already checked on {repo_full}#{issue_number}; nothing to do")
        return 0

    _gh_api(
        token,
        f"repos/{repo_full}/issues/{issue_number}",
        method="PATCH",
        json_body={"body": new_body},
    )
    comment = (
        "Phase 1 catalog-info PR merged"
        + (f" ({pr_url})" if pr_url else "")
        + ". Checking **Phase 2 — Remaining PRs** so onboarding can continue."
        + "\n\n"
        + "If Phase 2 aborts because TokenPolicies are not live yet, wait a few minutes "
        + "and check Phase 2 again (or re-apply the onboard label after the gate passes)."
    )
    _gh_api(
        token,
        f"repos/{repo_full}/issues/{issue_number}/comments",
        method="POST",
        json_body={"body": comment},
    )
    print(f"Checked Phase 2 on {repo_full}#{issue_number}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
