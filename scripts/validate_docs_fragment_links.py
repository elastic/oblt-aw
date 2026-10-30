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
Validate relative Markdown ``#fragment`` links under ``docs/``.

Codex / docs-builder fails the preview build when a link targets a heading
fragment that does not exist (for example guessing ``#11-…`` while Slugify
keeps the period as ``#11.-…``). Prefer custom ``[anchor]`` on numbered
headings when cross-linking. Run this in CI next to ``validate_docs_toc.py``.
"""

from __future__ import annotations

import pathlib
import re
import sys
import unicodedata
from collections.abc import Iterable
from urllib.parse import unquote, urlparse

import validate_docs_toc as docs_toc
import yaml  # type: ignore[import-untyped]

DOCS_DIR = pathlib.Path("docs")
DOCSET_PATH = DOCS_DIR / "docset.yml"

# Inline Markdown links: [text](target) — ignore images (![).
_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_CUSTOM_ANCHOR_RE = re.compile(r"\[#?([A-Za-z0-9._-]+)\]\s*$")


def slugify_heading(text: str) -> str:
    """Approximate docs-builder / Slugify.Core default heading ids.

    Keeps letters, digits, ``.``, and ``-`` (so ``11.`` and
    ``release-pointers.json`` retain their periods). Other punctuation is
    dropped; whitespace becomes ``-``.
    """
    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = without_marks.lower()
    pieces: list[str] = []
    for ch in lowered:
        if ch.isalnum() or ch in ".-":
            pieces.append(ch)
        elif ch.isspace() or ch == "_":
            pieces.append("-")
    collapsed = re.sub(r"-{2,}", "-", "".join(pieces)).strip("-")
    return collapsed


def heading_anchors(markdown: str) -> set[str]:
    """Return default and custom anchors for ATX headings in *markdown*."""
    anchors: set[str] = set()
    for match in _HEADING_RE.finditer(markdown):
        raw = match.group(2).rstrip()
        custom = _CUSTOM_ANCHOR_RE.search(raw)
        if custom:
            anchors.add(custom.group(1).lower())
            title = raw[: custom.start()].rstrip()
        else:
            title = raw
        if title:
            anchors.add(slugify_heading(title))
    return anchors


def _split_link_target(raw: str) -> tuple[str, str]:
    """Return ``(path_or_empty, fragment)`` for a Markdown link destination."""
    target = raw.strip()
    if not target:
        return "", ""
    # Optional title: path "title" or path 'title'
    if target[0] in "\"'":
        return "", ""
    if " " in target or "\t" in target:
        target = target.split(None, 1)[0]
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https", "mailto", "oblt-aw"}:
        return "", ""
    path = unquote(parsed.path or "")
    fragment = unquote(parsed.fragment or "")
    return path, fragment


def iter_relative_fragment_links(
    source: pathlib.Path,
    markdown: str,
    docs_root: pathlib.Path,
) -> Iterable[tuple[int, str, pathlib.Path, str]]:
    """Yield ``(line, raw_target, dest_path, fragment)`` for in-docset links."""
    root = docs_root.resolve()
    for match in _LINK_RE.finditer(markdown):
        raw_target = match.group(2)
        path_part, fragment = _split_link_target(raw_target)
        if not fragment:
            continue
        line = markdown.count("\n", 0, match.start()) + 1
        if path_part in {"", "."}:
            dest = source.resolve()
        else:
            dest = (source.parent / path_part).resolve()
        try:
            dest.relative_to(root)
        except ValueError:
            continue
        if not dest.is_file() or dest.suffix.lower() != ".md":
            continue
        yield line, raw_target, dest, fragment


def validate_fragment_links(
    docs_dir: pathlib.Path = DOCS_DIR,
    docset_path: pathlib.Path = DOCSET_PATH,
) -> list[str]:
    """Return human-readable errors for missing relative heading fragments."""
    if not docset_path.is_file():
        return [f"missing docset file: {docset_path.as_posix()}"]

    data = yaml.safe_load(docset_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return [f"{docset_path.as_posix()}: expected mapping root"]

    exclude_raw = data.get("exclude") or []
    if not isinstance(exclude_raw, list) or not all(
        isinstance(item, str) for item in exclude_raw
    ):
        return [f"{docset_path.as_posix()}: exclude must be a list of strings"]

    docs_root = docs_dir.resolve()
    pages = docs_toc.discover_markdown_pages(docs_dir, exclude_raw)
    anchor_cache: dict[pathlib.Path, set[str]] = {}
    errors: list[str] = []

    for rel in sorted(pages):
        source = docs_dir / rel
        text = source.read_text(encoding="utf-8")
        for line, raw_target, dest, fragment in iter_relative_fragment_links(
            source, text, docs_root
        ):
            if dest not in anchor_cache:
                anchor_cache[dest] = heading_anchors(dest.read_text(encoding="utf-8"))
            anchors = anchor_cache[dest]
            if fragment in anchors or fragment.lower() in anchors:
                continue
            try:
                dest_rel = dest.relative_to(docs_root).as_posix()
            except ValueError:
                dest_rel = dest.as_posix()
            errors.append(
                f"{rel}:{line}: fragment `{fragment}` does not exist in "
                f"{dest_rel} (link target `{raw_target}`; Codex preview will fail)"
            )

    return errors


def main() -> int:
    errors = validate_fragment_links()
    if errors:
        for err in errors:
            print(f"error: {err}", file=sys.stderr)
        return 1
    print(
        f"Validated docs relative Markdown fragment links under {DOCS_DIR.as_posix()}/."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
