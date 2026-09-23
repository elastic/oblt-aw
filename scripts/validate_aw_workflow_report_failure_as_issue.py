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
Validate obs-aw-* callers set report-failure-as-issue: false on gh-aw locks.

Locks that do not expose the workflow_call input are listed in
LOCKS_WITHOUT_REPORT_FAILURE_INPUT and skipped.
"""

from __future__ import annotations

import pathlib
import re
import sys

from validate_aw_workflow_prelude import list_subject_workflows

# Basename of the lock / reusable workflow (no path, no @ref).
LOCKS_WITHOUT_REPORT_FAILURE_INPUT: frozenset[str] = frozenset(
    {
        # No report-failure-as-issue workflow_call input (findings via create_issue).
        "gh-aw-log-searching-agent.lock.yml",
        # In-repo lock: failure reporting baked via obs-defaults; no caller input.
        "gh-aw-estc-pr-buildkite-detective.lock.yml",
        "gh-aw-docs-patrol.lock.yml",
    }
)

GH_AW_USES_LINE = re.compile(
    r"^\s+uses:\s*(?P<ref>\S+/gh-aw-[A-Za-z0-9-]+(?:\.lock)?\.ya?ml)(?:@\S+)?\s*$",
    re.MULTILINE,
)
REPORT_FAILURE_FALSE = re.compile(
    r"^\s+report-failure-as-issue:\s*false\s*(?:#.*)?$",
    re.MULTILINE,
)
OBS_AW_ROUTE = re.compile(r"^obs-aw-.+\.ya?ml$")


def _lock_basename(uses_ref: str) -> str:
    return uses_ref.rsplit("/", 1)[-1]


def _job_blocks(text: str) -> list[tuple[str, str]]:
    """Return (job_id, job_body) for each top-level job under ``jobs:``."""
    lines = text.splitlines()
    jobs_idx = next(
        (i for i, line in enumerate(lines) if line.startswith("jobs:")), None
    )
    if jobs_idx is None:
        return []

    blocks: list[tuple[str, str]] = []
    i = jobs_idx + 1
    while i < len(lines):
        line = lines[i]
        if not line.startswith("  ") or line.startswith("   "):
            if line.strip() == "" or line.startswith("#"):
                i += 1
                continue
            break
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if not match:
            i += 1
            continue
        job_id = match.group(1)
        start = i + 1
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if re.match(r"^  [A-Za-z0-9_-]+:\s*$", nxt):
                break
            if nxt and not nxt.startswith(" ") and not nxt.startswith("#"):
                break
            i += 1
        blocks.append((job_id, "\n".join(lines[start:i])))
    return blocks


def validate_workflow(path: pathlib.Path) -> list[str]:
    if not OBS_AW_ROUTE.match(path.name):
        return []

    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    for job_id, body in _job_blocks(text):
        uses_match = None
        for line in body.splitlines():
            uses_match = GH_AW_USES_LINE.match(line)
            if uses_match:
                break
        if uses_match is None:
            continue

        basename = _lock_basename(uses_match.group("ref"))
        if basename in LOCKS_WITHOUT_REPORT_FAILURE_INPUT:
            continue

        if not REPORT_FAILURE_FALSE.search(body):
            errors.append(
                f"{path}: job `{job_id}` calls `{basename}` without "
                "`report-failure-as-issue: false` (required to suppress [aw] "
                "failure meta-issues; intentional create_issue findings are unchanged)"
            )

    return errors


def main() -> int:
    errors: list[str] = []
    subjects = [p for p in list_subject_workflows() if OBS_AW_ROUTE.match(p.name)]
    if not subjects:
        print("No obs-aw-* workflows found to validate.", file=sys.stderr)
        return 1

    for path in subjects:
        errors.extend(validate_workflow(path))

    if errors:
        print("report-failure-as-issue enforcement failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    checked = sum(
        1
        for path in subjects
        if GH_AW_USES_LINE.search(path.read_text(encoding="utf-8"))
    )
    print(
        f"Validated {len(subjects)} obs-aw-* workflow(s); "
        f"{checked} invoke gh-aw-* with report-failure-as-issue: false "
        "(or an exempt lock without that input)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
