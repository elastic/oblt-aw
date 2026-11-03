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
Validate that every publishable docs Markdown page is listed in docs/docset.yml.

Codex / docs-builder fails the preview build when a ``docs/**/*.md`` file exists
but is missing from the ``toc:`` tree (error: "is not listed in the table of
contents"). Run this in CI so new pages cannot land without a toc entry.
"""

from __future__ import annotations

import pathlib
import sys
from collections.abc import Iterable, Mapping, Sequence
from fnmatch import fnmatch

import yaml  # type: ignore[import-untyped]

DOCS_DIR = pathlib.Path("docs")
DOCSET_PATH = DOCS_DIR / "docset.yml"


def _normalize_toc_path(raw: str, folder: str) -> str:
    rel = raw.removeprefix("./")
    if folder:
        return f"{folder}/{rel}".strip("/")
    return rel.strip("/")


def collect_toc_paths(nodes: Sequence[object] | None, folder: str = "") -> set[str]:
    """Collect ``file`` / ``hidden`` paths relative to ``docs/`` from a toc tree."""
    out: set[str] = set()
    if not nodes:
        return out
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        child_folder = node.get("folder")
        if isinstance(child_folder, str) and child_folder:
            nested = f"{folder}/{child_folder}".strip("/") if folder else child_folder
            children = node.get("children")
            if isinstance(children, Sequence) and not isinstance(
                children, (str, bytes)
            ):
                out |= collect_toc_paths(list(children), nested)
            continue
        for key in ("file", "hidden"):
            value = node.get(key)
            if isinstance(value, str) and value:
                out.add(_normalize_toc_path(value, folder))
    return out


def is_excluded(rel_posix: str, patterns: Iterable[str]) -> bool:
    """Return True when *rel_posix* matches a docset ``exclude`` glob."""
    name = pathlib.PurePosixPath(rel_posix).name
    for pattern in patterns:
        if pattern == "**/README.md" and name == "README.md":
            return True
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if rel_posix == prefix or rel_posix.startswith(f"{prefix}/"):
                return True
        if fnmatch(rel_posix, pattern):
            return True
        # Patterns without **/ still match nested paths (e.g. examples/**).
        if "/" not in pattern.rstrip("*") and fnmatch(name, pattern):
            return True
    return False


def discover_markdown_pages(
    docs_dir: pathlib.Path, exclude_patterns: Sequence[str]
) -> set[str]:
    pages: set[str] = set()
    for path in docs_dir.rglob("*.md"):
        rel = path.relative_to(docs_dir).as_posix()
        if is_excluded(rel, exclude_patterns):
            continue
        pages.add(rel)
    return pages


def validate_docset(
    docs_dir: pathlib.Path = DOCS_DIR,
    docset_path: pathlib.Path = DOCSET_PATH,
) -> list[str]:
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

    toc = data.get("toc")
    if not isinstance(toc, list):
        return [f"{docset_path.as_posix()}: toc must be a list"]

    toc_paths = collect_toc_paths(toc)
    pages = discover_markdown_pages(docs_dir, exclude_raw)

    errors: list[str] = []
    missing = sorted(pages - toc_paths)
    if missing:
        joined = ", ".join(missing)
        errors.append(
            "docs Markdown pages missing from docs/docset.yml toc "
            f"(Codex preview will fail): {joined}"
        )

    orphan = sorted(toc_paths - pages)
    # Orphans that match exclude are still bad toc entries pointing at filtered files.
    if orphan:
        joined = ", ".join(orphan)
        errors.append(
            f"docs/docset.yml toc entries with no matching docs/*.md file: {joined}"
        )

    return errors


def main() -> int:
    errors = validate_docset()
    if errors:
        for err in errors:
            print(f"error: {err}", file=sys.stderr)
        return 1
    pages = discover_markdown_pages(
        DOCS_DIR,
        yaml.safe_load(DOCSET_PATH.read_text(encoding="utf-8")).get("exclude") or [],
    )
    print(
        f"Validated docs toc: {len(pages)} Markdown page(s) listed in "
        f"{DOCSET_PATH.as_posix()}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
