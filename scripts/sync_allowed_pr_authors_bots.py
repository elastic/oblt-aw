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
Sync GH-AW ``on.bots`` / ``trusted-users`` / prompt author bullets from
``config/obs/allowed_pr_authors.json``.

GH-AW cannot take ``on.bots`` from a workflow_call input or fragment, so the
compiled locks must keep a static copy. This script keeps that copy generated
from the JSON allow list (single authored source of truth).

Usage:
  python3 scripts/sync_allowed_pr_authors_bots.py          # write
  python3 scripts/sync_allowed_pr_authors_bots.py --check   # exit 1 on drift
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOW_JSON = ROOT / "config" / "obs" / "allowed_pr_authors.json"

BEGIN_BOTS = "  # BEGIN synced-from:config/obs/allowed_pr_authors.json:bots"
END_BOTS = "  # END synced-from:config/obs/allowed_pr_authors.json:bots"
BEGIN_TRUSTED = (
    "    # BEGIN synced-from:config/obs/allowed_pr_authors.json:trusted-users"
)
END_TRUSTED = "    # END synced-from:config/obs/allowed_pr_authors.json:trusted-users"
AUTOAPPROVE = ROOT / ".github" / "workflows" / "gh-aw-autoapprove.md"
DEPENDENCY_REVIEW = ROOT / ".github" / "workflows" / "gh-aw-dependency-review.md"

# Legacy blocks (pre-marker) so the first sync can upgrade in place.
_LEGACY_BOTS = re.compile(
    r"(?ms)^  # Hardcoded to config/obs/allowed_pr_authors\.json[^\n]*\n"
    r"  bots:\n(?:    - \"[^\"]+\"\n)+"
)
_LEGACY_TRUSTED = re.compile(
    r"(?m)^    # Override obs-defaults trusted-users[^\n]*\n"
    r'    trusted-users: "[^"]+"\s*$'
)
# Prompt bullets only — no HTML markers (gh-aw strips them and leaves blank lines).
_PROMPT_AUTHOR_SECTION = re.compile(
    r"(?ms)^(Canonical list \(from `config/obs/allowed_pr_authors\.json`"
    r"[^\n]*:\n\n)"
    r"(?:<!-- BEGIN synced-from:config/obs/allowed_pr_authors\.json:prompt -->\n)?"
    r"(?:- `[^\n]+`\n)+"
    r"(?:<!-- END synced-from:config/obs/allowed_pr_authors\.json:prompt -->\n)?"
)

_MARKED_BOTS = re.compile(
    re.escape(BEGIN_BOTS) + r".*?" + re.escape(END_BOTS) + r"\n?",
    re.DOTALL,
)
_MARKED_TRUSTED = re.compile(
    re.escape(BEGIN_TRUSTED) + r".*?" + re.escape(END_TRUSTED),
    re.DOTALL,
)


def load_authors(path: pathlib.Path = ALLOW_JSON) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SystemExit(f"{path}: expected a non-empty JSON array of logins")
    authors: list[str] = []
    for item in data:
        if not isinstance(item, str) or not item.strip():
            raise SystemExit(f"{path}: every entry must be a non-empty string")
        authors.append(item)
    return authors


def render_bots_block(authors: list[str]) -> str:
    lines = [BEGIN_BOTS, "  bots:"]
    lines.extend(f'    - "{name}"' for name in authors)
    lines.append(END_BOTS)
    # Trailing newline: legacy match consumes the final bot line's \\n.
    return "\n".join(lines) + "\n"


def render_trusted_block(authors: list[str]) -> str:
    csv = ",".join(authors)
    # No trailing newline: legacy `$` leaves the line-ending \\n in place.
    return "\n".join(
        [
            BEGIN_TRUSTED,
            f'    trusted-users: "{csv}"',
            END_TRUSTED,
        ]
    )


def render_prompt_bullets(authors: list[str]) -> str:
    return "\n".join(f"- `{name}`" for name in authors) + "\n"


def _replace_or_upgrade(
    text: str,
    *,
    marked: re.Pattern[str],
    legacy: re.Pattern[str],
    replacement: str,
    label: str,
    path: pathlib.Path,
) -> str:
    if marked.search(text):
        return marked.sub(replacement, text, count=1)
    match = legacy.search(text)
    if match is None:
        raise SystemExit(f"{path}: missing {label} block to sync")
    return text[: match.start()] + replacement + text[match.end() :]


def sync_frontmatter_bots_trusted(
    text: str, authors: list[str], path: pathlib.Path
) -> str:
    text = _replace_or_upgrade(
        text,
        marked=_MARKED_BOTS,
        legacy=_LEGACY_BOTS,
        replacement=render_bots_block(authors),
        label="on.bots",
        path=path,
    )
    text = _replace_or_upgrade(
        text,
        marked=_MARKED_TRUSTED,
        legacy=_LEGACY_TRUSTED,
        replacement=render_trusted_block(authors),
        label="trusted-users",
        path=path,
    )
    return text


def sync_autoapprove_prompt(text: str, authors: list[str], path: pathlib.Path) -> str:
    match = _PROMPT_AUTHOR_SECTION.search(text)
    if match is None:
        raise SystemExit(f"{path}: missing prompt author bullets to sync")
    # Keep the "Canonical list..." lead-in; replace only the bullet list.
    return (
        text[: match.start()]
        + match.group(1)
        + render_prompt_bullets(authors)
        + text[match.end() :]
    )


def sync_file(path: pathlib.Path, authors: list[str], *, with_prompt: bool) -> str:
    original = path.read_text(encoding="utf-8")
    updated = sync_frontmatter_bots_trusted(original, authors, path)
    if with_prompt:
        updated = sync_autoapprove_prompt(updated, authors, path)
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any target would change (do not write)",
    )
    args = parser.parse_args(argv)
    authors = load_authors()

    targets: list[tuple[pathlib.Path, bool]] = [
        (AUTOAPPROVE, True),
        (DEPENDENCY_REVIEW, False),
    ]
    dirty: list[pathlib.Path] = []
    for path, with_prompt in targets:
        updated = sync_file(path, authors, with_prompt=with_prompt)
        current = path.read_text(encoding="utf-8")
        if updated == current:
            continue
        dirty.append(path)
        if not args.check:
            path.write_text(updated, encoding="utf-8")
            print(f"updated {path.relative_to(ROOT)}")

    if args.check:
        if dirty:
            for path in dirty:
                print(f"drift: {path.relative_to(ROOT)}", file=sys.stderr)
            print(
                "Run: python3 scripts/sync_allowed_pr_authors_bots.py",
                file=sys.stderr,
            )
            return 1
        print("allowed_pr_authors bot lists are in sync")
        return 0

    if not dirty:
        print("already in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
