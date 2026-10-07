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

"""Collect GitHub Actions commit.verification facts via REST (not MCP).

Parses SHA-pinned ``uses:`` lines from a unified diff (typically the PR
workflow diff) and writes a JSON facts file the dependency-review agent must
prefer over MCP ``get_commit`` for the Actions commit-verification gate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = "actions-commit-verification.json"
FACTS_VERSION = 1
FACTS_SOURCE = "github-rest-commit-verification"

# owner/repo or owner/repo/path@40-hex (optional quotes / trailing comment).
_USES_SHA_RE = re.compile(
    r"""(?x)
    uses:\s*
    ['"]?
    (?P<action>
      [A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+
      (?:/[A-Za-z0-9_.-]+)*
    )
    @
    (?P<sha>[0-9a-f]{40})
    ['"]?
    """
)


def action_api_repo(action: str) -> str:
    """Map ``owner/repo[/path…]`` action ref to the GitHub ``owner/repo`` API id."""
    parts = action.split("/")
    if len(parts) < 2:
        raise ValueError(f"invalid action ref (need owner/repo): {action!r}")
    return f"{parts[0]}/{parts[1]}"


def extract_action_sha_pins(diff_text: str) -> list[tuple[str, str]]:
    """Return unique ``(action, sha)`` pins from added lines in a unified diff."""
    found: dict[tuple[str, str], None] = {}
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        match = _USES_SHA_RE.search(line[1:])
        if match is None:
            continue
        action = match.group("action")
        sha = match.group("sha")
        found[(action, sha)] = None
    return list(found.keys())


def fetch_commit_verification(
    repo: str,
    sha: str,
    *,
    gh_run: Any | None = None,
) -> dict[str, Any]:
    """Return verification fields for ``repo`` at ``sha`` via ``gh api``.

    On success: ``verified`` is bool, ``reason`` is str|None, ``error`` is None.
    On failure: ``verified`` is None, ``reason`` is None, ``error`` is a message.
    """
    runner = gh_run or _default_gh_run
    proc = runner(
        [
            "gh",
            "api",
            f"repos/{repo}/commits/{sha}",
            "--jq",
            "{verified: .commit.verification.verified, reason: .commit.verification.reason}",
        ]
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        return {"verified": None, "reason": None, "error": err}
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {
            "verified": None,
            "reason": None,
            "error": f"invalid JSON from gh api: {exc}",
        }
    verified = payload.get("verified")
    if not isinstance(verified, bool):
        return {
            "verified": None,
            "reason": None,
            "error": "commit.verification.verified missing or not a bool",
        }
    reason = payload.get("reason")
    return {
        "verified": verified,
        "reason": reason if isinstance(reason, str) else None,
        "error": None,
    }


def build_facts(
    pins: list[tuple[str, str]],
    *,
    gh_run: Any | None = None,
) -> dict[str, Any]:
    """Build the facts document for ``pins`` (action, sha)."""
    entries: list[dict[str, Any]] = []
    for action, sha in pins:
        api_repo = action_api_repo(action)
        verification = fetch_commit_verification(api_repo, sha, gh_run=gh_run)
        entries.append(
            {
                "action": action,
                "repo": api_repo,
                "sha": sha,
                "verified": verification["verified"],
                "reason": verification["reason"],
                "error": verification["error"],
            }
        )
    return {
        "version": FACTS_VERSION,
        "source": FACTS_SOURCE,
        "pins": entries,
    }


def flatten_slurped_pages(payload: Any) -> list[Any]:
    """Flatten ``gh api --paginate --slurp`` output into a single list.

    ``--slurp`` wraps each page (itself a JSON array) in an outer array.
    """
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise TypeError(
            f"expected list from paginated gh api, got {type(payload).__name__}"
        )
    if not payload:
        return []
    if all(isinstance(page, list) for page in payload):
        flat: list[Any] = []
        for page in payload:
            flat.extend(page)
        return flat
    # Single-page response may already be a flat list of objects.
    return payload


def pull_request_diff(repo: str, pull_number: int, *, gh_run: Any | None = None) -> str:
    """Return concatenated file patches for a pull request via ``gh api``."""
    runner = gh_run or _default_gh_run
    proc = runner(
        [
            "gh",
            "api",
            f"repos/{repo}/pulls/{pull_number}/files",
            "--paginate",
            "--slurp",
        ]
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        raise RuntimeError(f"failed to list PR files: {err}")
    try:
        payload = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON listing PR files: {exc}") from exc
    files = flatten_slurped_pages(payload)
    patches: list[str] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename") or "")
        if not filename.startswith(".github/workflows/"):
            continue
        patch = item.get("patch")
        if isinstance(patch, str) and patch.strip():
            patches.append(patch)
    return "\n".join(patches)


def git_diff(range_spec: str, *, paths: list[str], cwd: Path | None = None) -> str:
    """Return ``git diff`` text for ``range_spec`` limited to ``paths``."""
    cmd = ["git", "diff", range_spec, "--"] + paths
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        raise RuntimeError(f"git diff failed: {err}")
    return proc.stdout or ""


def write_facts(path: Path, facts: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(facts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _default_gh_run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect Actions commit.verification via GitHub REST into a JSON "
            "facts file for dependency-review."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT),
        help=f"Facts JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--git-range",
        default="",
        help="git diff range (e.g. BASE_SHA...HEAD). Ignored when --diff-file or --pull-number is set.",
    )
    parser.add_argument(
        "--diff-file",
        type=Path,
        default=None,
        help="Read a unified diff from this file instead of running git diff.",
    )
    parser.add_argument(
        "--github-repo",
        default="",
        help="owner/name for --pull-number (default: $GITHUB_REPOSITORY).",
    )
    parser.add_argument(
        "--pull-number",
        type=int,
        default=0,
        help="Load patches via pulls/{n}/files API (preferred in Actions; works with shallow clones).",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Pathspec for git diff (repeatable). Default: .github/workflows",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Working directory for git diff (default: .)",
    )
    args = parser.parse_args(argv)

    paths = list(args.path) if args.path else [".github/workflows"]
    if args.diff_file is not None:
        diff_text = args.diff_file.read_text(encoding="utf-8")
    elif args.pull_number > 0:
        repo = (args.github_repo or os.environ.get("GITHUB_REPOSITORY") or "").strip()
        if not repo:
            parser.error(
                "--github-repo or GITHUB_REPOSITORY is required with --pull-number"
            )
        diff_text = pull_request_diff(repo, args.pull_number)
    elif args.git_range:
        diff_text = git_diff(args.git_range, paths=paths, cwd=args.repo_root.resolve())
    else:
        parser.error("provide --pull-number, --git-range, or --diff-file")

    pins = extract_action_sha_pins(diff_text)
    facts = build_facts(pins)
    write_facts(args.output, facts)
    print(
        f"Wrote {args.output} with {len(facts['pins'])} Actions SHA pin(s)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
