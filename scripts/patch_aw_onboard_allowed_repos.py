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

"""Wire run-scoped create-pull-request allowlist into the safe_outputs job.

The onboard markdown sets ``create-pull-request.allowed-repos`` from
``steps.onboard-phase.outputs.allowed_repos``. That expression is valid in the
agent job (where the parse step runs) but resolves empty in ``safe_outputs``.
This post-compile step:

1. Publishes ``allowed_repos`` as an agent job output.
2. Rewrites ``GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG`` to use
   ``needs.agent.outputs.allowed_repos``.

Run from Makefile ``compile-aw`` after ``patch_aw_onboard_edited_label``.
Idempotent.
"""

from __future__ import annotations

import sys
from pathlib import Path

TARGET_LOCK = "gh-aw-onboard-repository.lock.yml"

AGENT_OUTPUT_ANCHOR = (
    "      agentic_engine_timeout: "
    "${{ steps.detect-agent-errors.outputs.agentic_engine_timeout || 'false' }}"
)
AGENT_OUTPUT_LINE = (
    "      allowed_repos: ${{ steps.onboard-phase.outputs.allowed_repos }}\n"
)

STEP_EXPR = "${{ steps.onboard-phase.outputs.allowed_repos }}"
NEEDS_EXPR = "${{ needs.agent.outputs.allowed_repos }}"


def patch_lock(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = text
    changes = 0

    if AGENT_OUTPUT_LINE not in updated:
        if AGENT_OUTPUT_ANCHOR not in updated:
            raise SystemExit(
                f"{path.name}: agent outputs anchor not found; "
                "gh-aw compiler output may have changed — update "
                "scripts/patch_aw_onboard_allowed_repos.py"
            )
        updated = updated.replace(
            f"    outputs:\n{AGENT_OUTPUT_ANCHOR}",
            f"    outputs:\n{AGENT_OUTPUT_LINE}{AGENT_OUTPUT_ANCHOR}",
            1,
        )
        changes += 1

    handler_lines = [
        line
        for line in updated.splitlines()
        if "GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG" in line
    ]
    if not handler_lines:
        raise SystemExit(
            f"{path.name}: GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG not found; "
            "gh-aw compiler output may have changed — update "
            "scripts/patch_aw_onboard_allowed_repos.py"
        )

    new_lines: list[str] = []
    for line in updated.splitlines(keepends=True):
        if "GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG" in line and STEP_EXPR in line:
            new_lines.append(line.replace(STEP_EXPR, NEEDS_EXPR))
            changes += 1
        else:
            new_lines.append(line)
    updated = "".join(new_lines)

    if changes == 0:
        return False
    path.write_text(updated, encoding="utf-8")
    print(f"  patched {path.name} ({changes} change(s))")
    return True


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    lock = root / ".github" / "workflows" / TARGET_LOCK
    if not lock.is_file():
        print(f"skip: {TARGET_LOCK} missing", file=sys.stderr)
        return 0
    changed = patch_lock(lock)
    if changed:
        print(f"Patched allowed_repos wiring in {TARGET_LOCK}")
    else:
        print(f"Already patched or unchanged: {TARGET_LOCK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
