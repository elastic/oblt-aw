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
Fail docs that attribute framework ownership to the control plane.

The control plane only enables and gates. Framework / oblt-aw owns routes,
locks, schedule clients, distribution, and runtime. See docs/glossary.md.
"""

from __future__ import annotations

import pathlib
import re
import sys

import validate_docs_toc as docs_toc
import yaml  # type: ignore[import-untyped]

DOCS_DIR = pathlib.Path("docs")
DOCSET_PATH = DOCS_DIR / "docset.yml"

# Strip fenced code so example YAML/shell cannot trip prose checks.
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

# Match "control plane" when not immediately "Control Plane dashboard", then a
# framework-ownership verb + object.
_ANTI_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\bcontrol[- ]plane\b(?!\s+dashboard)\s+"
            r"(?:still\s+)?(?:owns|own|runs|run|manages|manage|hosts|host)\s+"
            r"(?:runtime|locks?|lock\s+files?|aw\s+compilation|compilation|"
            r"schedule\s+clients?|distribution|capability\s+wiring)",
            re.IGNORECASE,
        ),
        (
            "control plane does not own framework runtime/locks/clients/"
            "distribution; use framework / oblt-aw"
        ),
    ),
    (
        re.compile(
            r"\bwhile\s+the\s+control[- ]plane\b(?!\s+dashboard)\s+"
            r"(?:still\s+)?owns\b",
            re.IGNORECASE,
        ),
        (
            "do not say the control plane owns framework concerns; "
            "split framework vs control plane"
        ),
    ),
)


def _prose_lines(markdown: str) -> list[tuple[int, str]]:
    """Return 1-based line numbers and text with fences removed."""
    cleaned = _FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), markdown)
    return [(i, line) for i, line in enumerate(cleaned.splitlines(), start=1)]


def find_terminology_errors(
    *,
    docs_dir: pathlib.Path = DOCS_DIR,
    docset_path: pathlib.Path = DOCSET_PATH,
) -> list[str]:
    """Return human-readable errors for control-plane / framework mix-ups."""
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

    errors: list[str] = []
    for rel in sorted(docs_toc.discover_markdown_pages(docs_dir, exclude_raw)):
        text = (docs_dir / rel).read_text(encoding="utf-8")
        for line_no, line in _prose_lines(text):
            for pattern, hint in _ANTI_PATTERNS:
                if pattern.search(line):
                    errors.append(
                        f"{rel}:{line_no}: {hint} (matched: {line.strip()!r})"
                    )
    return errors


def main() -> int:
    errors = find_terminology_errors()
    if errors:
        print("Docs terminology check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"Validated docs control-plane terminology under {DOCS_DIR.as_posix()}/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
