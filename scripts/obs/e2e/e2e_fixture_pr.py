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

"""Shared helpers for E2E harness fixture pull requests.

Fixture PRs default to draft when the under-test path does not require a
ready-for-review PR (avoids CODEOWNERS review requests). Automerge fixtures
must stay ready — do not call ensure_pr_is_draft from that harness.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


def ensure_pr_is_draft(repo: str, pr_number: int) -> dict[str, Any]:
    """Ensure the fixture PR is draft; convert with ``gh pr ready --undo`` if needed.

    Fail closed when conversion fails or the PR remains ready for review.
    Returns the final ``gh pr view`` payload (includes ``isDraft``).
    """
    pr = _view_pr_draft_state(repo, pr_number)
    if pr.get("isDraft") is True:
        return pr

    convert = subprocess.run(
        [
            "gh",
            "pr",
            "ready",
            str(pr_number),
            "--undo",
            "--repo",
            repo,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if convert.returncode != 0:
        detail = (convert.stderr or convert.stdout or "").strip() or (
            f"exit {convert.returncode}"
        )
        raise RuntimeError(
            f"Fixture PR #{pr_number} on {repo} is ready for review and converting "
            f"to draft failed: {detail}. Convert it once with "
            f"`gh pr ready --undo {pr_number} --repo {repo}` and re-run."
        )

    pr = _view_pr_draft_state(repo, pr_number)
    if pr.get("isDraft") is not True:
        raise RuntimeError(
            f"Fixture PR #{pr_number} on {repo} is still ready for review after "
            f"`gh pr ready --undo`. Convert it once with "
            f"`gh pr ready --undo {pr_number} --repo {repo}` and re-run."
        )
    return pr


def _view_pr_draft_state(repo: str, pr_number: int) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "number,url,isDraft,state",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(
            f"Failed to view draft state for PR #{pr_number} on {repo}: {detail}"
        )
    if not proc.stdout.strip():
        raise RuntimeError(
            f"Failed to view draft state for PR #{pr_number} on {repo}: empty response"
        )
    payload = json.loads(proc.stdout)
    if not isinstance(payload, dict):
        raise TypeError(
            f"Failed to view draft state for PR #{pr_number} on {repo}: expected object"
        )
    return payload
