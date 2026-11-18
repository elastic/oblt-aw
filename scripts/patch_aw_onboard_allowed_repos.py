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

"""Wire run-scoped onboard allowlists into the compiled lock file.

The onboard markdown sets ``create-pull-request.allowed-repos`` from
``steps.onboard-phase.outputs.allowed_repos``. That expression is valid in the
agent job (where the parse step runs) but resolves empty in ``safe_outputs``.
Compile-time ``tools.github.allowed-repos`` is platform-only (DIFC starts before
parse). This post-compile step:

1. Publishes ``allowed_repos`` as an agent job output.
2. Rewrites ``GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG`` to use
   ``needs.agent.outputs.allowed_repos``.
3. Points ``GH_AW_GITHUB_REPOS`` and the MCP gateway ``repos`` guard at
   ``steps.onboard-phase.outputs.allowed_repos_json`` (platform + consumer).
4. Points both MCP ``write-sink.accept`` lists at
   ``steps.onboard-phase.outputs.allowed_sinks_json`` (``private:<repo>``
   tags for the same validated set; preserves ``sink-visibility``).

Run from Makefile ``compile-aw`` after ``patch_aw_onboard_edited_label``.
Idempotent.
"""

from __future__ import annotations

import re
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
REPOS_JSON_EXPR = "${{ steps.onboard-phase.outputs.allowed_repos_json }}"
SINKS_JSON_EXPR = "${{ steps.onboard-phase.outputs.allowed_sinks_json }}"

GITHUB_REPOS_STATIC = re.compile(
    r"^(\s*GH_AW_GITHUB_REPOS:\s*)'\[\"elastic/[^\"]+\"(?:,\s*\"elastic/[^\"]+\")*\]'\s*$",
    re.MULTILINE,
)
GITHUB_REPOS_REPLACEMENT = rf"\1'{REPOS_JSON_EXPR}'"

# Multiline MCP gateway guard only (never touch compact DIFC_PROXY_POLICY).
MCP_REPOS_STATIC = re.compile(
    r'^(\s*"repos":\s*)\[\n'
    r'(?:\s*"elastic/[^"]+",?\n)+'
    r"(\s*)\]",
    re.MULTILINE,
)
MCP_REPOS_REPLACEMENT = r"\1${GH_AW_GITHUB_REPOS}"

# Both safeoutputs and public-code-search write-sink.accept lists.
WRITE_SINK_ACCEPT_STATIC = re.compile(
    r'^(\s*"accept":\s*)\[\n'
    r'(?:\s*"private:elastic/[^"]+",?\n)+'
    r"(\s*)\]",
    re.MULTILINE,
)
WRITE_SINK_ACCEPT_REPLACEMENT = r"\1${GH_AW_GITHUB_SINKS}"
WRITE_SINK_ACCEPT_RUNTIME = '"accept": ${GH_AW_GITHUB_SINKS}'


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

    if REPOS_JSON_EXPR not in updated or "GH_AW_GITHUB_REPOS:" not in updated:
        # Still need to wire runtime JSON even when already partially patched.
        pass

    replaced_github_repos, github_count = GITHUB_REPOS_STATIC.subn(
        GITHUB_REPOS_REPLACEMENT, updated, count=1
    )
    if github_count:
        updated = replaced_github_repos
        changes += github_count
    elif f"GH_AW_GITHUB_REPOS: '{REPOS_JSON_EXPR}'" not in updated:
        raise SystemExit(
            f"{path.name}: GH_AW_GITHUB_REPOS platform list not found; "
            "gh-aw compiler output may have changed — update "
            "scripts/patch_aw_onboard_allowed_repos.py"
        )

    # Prefer the MCP gateway multiline list; leave DIFC_PROXY_POLICY compile-time.
    if '"repos": ${GH_AW_GITHUB_REPOS}' not in updated:
        replaced_mcp, mcp_count = MCP_REPOS_STATIC.subn(
            MCP_REPOS_REPLACEMENT, updated, count=1
        )
        if mcp_count == 0:
            raise SystemExit(
                f"{path.name}: MCP guard repos list not found; "
                "gh-aw compiler output may have changed — update "
                "scripts/patch_aw_onboard_allowed_repos.py"
            )
        updated = replaced_mcp
        changes += mcp_count

    if 'repos":${GH_AW_GITHUB_REPOS}' in updated and "DIFC_PROXY_POLICY" in updated:
        # Recover if an older patch rewrote DIFC to a runtime env expansion.
        difc_fixed = re.sub(
            r"(DIFC_PROXY_POLICY: '\{\"allow-only\":\{\"min-integrity\":\"none\","
            r"\"repos\":)\$\{GH_AW_GITHUB_REPOS\}(\}\}')",
            r'\1["elastic/catalog-info","elastic/oblt-aw",'
            r'"elastic/observability-github-secrets",'
            r'"elastic/observability-github-settings"]\2',
            updated,
            count=1,
        )
        if difc_fixed != updated:
            updated = difc_fixed
            changes += 1

    # Derive write-sink.accept from the same validated repos (no wildcard).
    if WRITE_SINK_ACCEPT_RUNTIME not in updated:
        replaced_sinks, sink_count = WRITE_SINK_ACCEPT_STATIC.subn(
            WRITE_SINK_ACCEPT_REPLACEMENT, updated
        )
        if sink_count == 0:
            raise SystemExit(
                f"{path.name}: write-sink.accept lists not found; "
                "gh-aw compiler output may have changed — update "
                "scripts/patch_aw_onboard_allowed_repos.py"
            )
        updated = replaced_sinks
        changes += sink_count
    if '"sink-visibility": "${GH_AW_SINK_VISIBILITY}"' not in updated:
        raise SystemExit(
            f"{path.name}: sink-visibility runtime expansion missing after "
            "write-sink patch; refuse to drop visibility guard"
        )

    # Ensure Start MCP Gateway exports the runtime JSON for heredoc expansion.
    gateway_env_anchor = (
        "      - name: Start MCP Gateway\n        id: start-mcp-gateway\n        env:\n"
    )
    if "id: start-mcp-gateway" in updated:
        if gateway_env_anchor not in updated:
            raise SystemExit(
                f"{path.name}: Start MCP Gateway env anchor not found; "
                "gh-aw compiler output may have changed — update "
                "scripts/patch_aw_onboard_allowed_repos.py"
            )
        gateway_inserts: list[str] = []
        if f"GH_AW_GITHUB_REPOS: {REPOS_JSON_EXPR}" not in updated:
            gateway_inserts.append(f"          GH_AW_GITHUB_REPOS: {REPOS_JSON_EXPR}\n")
        if f"GH_AW_GITHUB_SINKS: {SINKS_JSON_EXPR}" not in updated:
            gateway_inserts.append(f"          GH_AW_GITHUB_SINKS: {SINKS_JSON_EXPR}\n")
        if gateway_inserts:
            updated = updated.replace(
                gateway_env_anchor,
                gateway_env_anchor + "".join(gateway_inserts),
                1,
            )
            changes += len(gateway_inserts)

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
