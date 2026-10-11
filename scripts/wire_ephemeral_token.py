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

"""Wire minted create-token outputs into compiled GH-AW lock files.

The gh-aw compiler rejects mixed steps.* || secrets.* github-token expressions.
This post-process prefers create-token step outputs, then caller secrets, then
GITHUB_TOKEN. It also adds id-token: write to jobs that mint tokens.

Lock files are processed when they contain a create-token step (for example from
gh-aw-fragments/ephemeral-github-token.md) or a github-token-policy
workflow_call input. The script is idempotent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MINTED_PREFIX = "steps.create-token.outputs.token || "

# Longer fallback chains first so the short GH_AW_GITHUB_TOKEN suffix is not
# rewritten inside MCP-token expressions.
REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (
        "${{ secrets.GH_AW_GITHUB_MCP_SERVER_TOKEN || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}",
        "${{ "
        + MINTED_PREFIX
        + "secrets.GH_AW_GITHUB_MCP_SERVER_TOKEN || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}",
    ),
    (
        "${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}",
        "${{ "
        + MINTED_PREFIX
        + "secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}",
    ),
    (
        "${{ secrets.GH_AW_GITHUB_TOKEN }}",
        "${{ " + MINTED_PREFIX + "secrets.GH_AW_GITHUB_TOKEN }}",
    ),
)

ID_TOKEN_LINE = "      id-token: write"
STEP_PREFIX = "      - "
_EXPR_RE = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")


def _job_blocks(text: str) -> list[tuple[int, int]]:
    """Return (start, end) line-index spans for top-level jobs.* blocks."""
    lines = text.splitlines(keepends=True)
    jobs_idx = None
    for i, line in enumerate(lines):
        if line == "jobs:\n" or line == "jobs:":
            jobs_idx = i
            break
    if jobs_idx is None:
        return []

    starts: list[int] = []
    for i in range(jobs_idx + 1, len(lines)):
        line = lines[i]
        if (
            line.startswith("  ")
            and not line.startswith("    ")
            and line.strip().endswith(":")
        ):
            starts.append(i)
            continue
        if line and not line.startswith(" ") and line.strip():
            break
    spans: list[tuple[int, int]] = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(lines)
        spans.append((start, end))
    return spans


def _rewrite_line(line: str) -> str:
    """Prefer minted step outputs in one token-expression line."""
    if "create-token.outputs.token" in line:
        return line
    for old, new in REPLACEMENTS:
        if old in line:
            return line.replace(old, new)
    return line


def _extract_expression(line: str) -> str | None:
    """Return the inner `${{ ... }}` expression from one YAML line."""
    match = _EXPR_RE.search(line)
    if match is None:
        return None
    return match.group(1).strip()


def _rewrite_step_token_input(lines: list[str], start: int, end: int) -> None:
    """Use env indirection for secrets-based with.github-token expressions."""
    with_token_idx: int | None = None
    with_token_expr: str | None = None

    for i in range(start, end):
        line = lines[i]
        if line.strip().startswith("github-token:"):
            with_token_idx = i
            with_token_expr = _extract_expression(line)

    if with_token_idx is None or with_token_expr is None:
        return
    if with_token_expr == "env.GH_TOKEN":
        return
    if "secrets." not in with_token_expr:
        return

    with_indent = lines[with_token_idx].split("github-token:")[0]
    step_prop_indent = with_indent[:-2]
    env_line = f"{step_prop_indent}env:\n"
    gh_token_line = f"{step_prop_indent}  GH_TOKEN: ${{{{ {with_token_expr} }}}}\n"

    env_start: int | None = None
    for i in range(start, end):
        if lines[i] == env_line:
            env_start = i
            break

    if env_start is not None:
        env_end = env_start + 1
        while env_end < end:
            line = lines[env_end]
            if not line.startswith(f"{step_prop_indent}  "):
                break
            env_end += 1

        gh_idx: int | None = None
        for i in range(env_start + 1, env_end):
            if lines[i].strip().startswith("GH_TOKEN:"):
                gh_idx = i
                break

        if gh_idx is not None:
            lines[gh_idx] = gh_token_line
        else:
            lines.insert(env_end, gh_token_line)
            if env_end <= with_token_idx:
                with_token_idx += 1
    else:
        lines.insert(with_token_idx, gh_token_line)
        lines.insert(with_token_idx, env_line)
        with_token_idx += 2

    lines[with_token_idx] = f"{with_indent}github-token: ${{{{ env.GH_TOKEN }}}}\n"


def _rewrite_job_steps_with_env_indirection(
    lines: list[str], start: int, end: int
) -> None:
    """Apply github-token env-indirection for one job block in-place."""
    step_starts = [i for i in range(start, end) if lines[i].startswith(STEP_PREFIX)]
    if not step_starts:
        return
    for idx, step_start in enumerate(step_starts):
        step_end = step_starts[idx + 1] if idx + 1 < len(step_starts) else end
        _rewrite_step_token_input(lines, step_start, step_end)


def wire_token_expressions(text: str) -> str:
    """Prefer minted step outputs only inside jobs that mint create-token.

    Non-minting jobs (for example detection) keep secrets.* fallbacks so they
    do not reference a missing steps.create-token output.
    """
    lines = text.splitlines(keepends=True)
    spans = _job_blocks(text)
    # No parseable jobs (or empty jobs): never invent steps.create-token refs.
    # should_process can still be true via github-token-policy alone.
    if not spans:
        return text

    minting = {
        (start, end)
        for start, end in spans
        if "id: create-token" in "".join(lines[start:end])
    }
    rewritten: list[str] = []
    for i, line in enumerate(lines):
        in_minting = any(start <= i < end for start, end in minting)
        rewritten.append(_rewrite_line(line) if in_minting else line)
    rewritten_lines = "".join(rewritten).splitlines(keepends=True)
    for start, end in minting:
        _rewrite_job_steps_with_env_indirection(rewritten_lines, start, end)
    return "".join(rewritten_lines)


def ensure_id_token_write(text: str) -> str:
    """Add id-token: write to permissions of jobs that mint create-token."""
    lines = text.splitlines(keepends=True)
    spans = _job_blocks(text)
    inserts: list[tuple[int, str]] = []
    for start, end in spans:
        block = "".join(lines[start:end])
        if "id: create-token" not in block:
            continue
        if "id-token: write" in block:
            continue
        perm_rel = None
        for j, line in enumerate(lines[start:end]):
            if line == "    permissions:\n":
                perm_rel = j
                break
        if perm_rel is None:
            continue
        inserts.append((start + perm_rel + 1, ID_TOKEN_LINE + "\n"))

    for idx, line in sorted(inserts, reverse=True):
        lines.insert(idx, line)
    return "".join(lines)


def should_process(text: str) -> bool:
    """True when the lock mints create-token or declares github-token-policy."""
    return "id: create-token" in text or "github-token-policy:" in text


def process_lock_file(path: Path) -> bool:
    """Rewrite one lock file. Return True when the file changed."""
    original = path.read_text(encoding="utf-8")
    if not should_process(original):
        return False
    updated = wire_token_expressions(original)
    updated = ensure_id_token_write(updated)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    workflows = repo_root / ".github" / "workflows"
    changed = 0
    for lock_file in sorted(workflows.rglob("*.lock.yml")):
        if process_lock_file(lock_file):
            print(f"  wired {lock_file.relative_to(workflows)}")
            changed += 1
    print(f"Wired ephemeral token outputs in {changed} lock file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
