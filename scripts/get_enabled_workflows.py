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
Read the oblt-aw/dashboard issue and write normalized enabled-workflows JSON to
GITHUB_OUTPUT (for ingress gating).

Emits compound workflow ids ``org:workflow-id`` (for example ``obs:agent-suggestions``).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

from common import (
    LEGACY_DEFAULT_ORG_KEY,
    append_multiline_github_output,
    compound_workflow_key,
    enabled_compound_ids_from_dashboard_body,
)


def normalize_enabled_workflows_json(raw: str) -> str:
    """Match workflow jq normalization: strip, JSON array, or token scan."""
    stripped = raw.strip()
    if len(stripped) == 0:
        return "[]"
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            out: list[str] = []
            for item in parsed:
                if not isinstance(item, str):
                    raise ValueError("not string array")
                item = item.strip()
                if not item:
                    continue
                if ":" in item:
                    out.append(item)
                else:
                    out.append(compound_workflow_key(LEGACY_DEFAULT_ORG_KEY, item))
            return json.dumps(out, separators=(",", ":"))
        raise ValueError("not an array")
    except (json.JSONDecodeError, ValueError):
        tokens = re.split(r"[\s,;]+", stripped)
        seen: set[str] = set()
        unique: list[str] = []
        for token in tokens:
            if not token:
                continue
            if ":" in token:
                norm = token
            else:
                norm = compound_workflow_key(LEGACY_DEFAULT_ORG_KEY, token)
            if norm not in seen:
                seen.add(norm)
                unique.append(norm)
        return json.dumps(unique, separators=(",", ":"))


def parse_enabled_ids_from_body(body: str) -> str:
    """Return JSON array string of enabled compound ids from dashboard body."""
    ids = enabled_compound_ids_from_dashboard_body(body)
    if not ids:
        return "[]"
    return json.dumps(ids, separators=(",", ":"))


def fetch_dashboard_body(github_repository: str) -> tuple[str | None, bool]:
    """
    Return (body, gh_failed).

    body is None when the issue is missing or empty; gh_failed True when gh
    errored (caller should default RAW to '[]' like the shell workflow).
    """
    url = f"repos/{github_repository}/issues?labels=oblt-aw/dashboard&state=open"
    try:
        proc = subprocess.run(
            [
                "gh",
                "api",
                url,
                "--jq",
                "if length > 0 then .[0].body else empty end",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(
            f"Error invoking gh api: {exc}; defaulting to no workflows enabled",
            file=sys.stderr,
        )
        return None, True
    if proc.returncode != 0:
        print(
            "Error fetching dashboard issue via 'gh api'; "
            "defaulting to no workflows enabled",
            file=sys.stderr,
        )
        return None, True
    text = proc.stdout.strip()
    if not text:
        return None, False
    return text, False


def main() -> None:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY is not set")

    body, gh_failed = fetch_dashboard_body(repo)
    if gh_failed:
        raw = "[]"
    elif body is None:
        raw = ""
        print("No dashboard issue found, defaulting to all workflows enabled")
    else:
        enabled = parse_enabled_ids_from_body(body)
        if enabled == "[]":
            raw = "[]"
            print("Dashboard exists but no checkboxes checked, no workflows will run")
        else:
            raw = enabled

    normalized = normalize_enabled_workflows_json(raw)
    append_multiline_github_output("enabled-workflows", normalized)
    append_multiline_github_output("effective-raw", raw)


if __name__ == "__main__":
    main()
