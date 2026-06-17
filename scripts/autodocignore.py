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
Resolve `.oblt-aw.autodocignore` patterns for the autodoc agentic workflow.

Patterns use gitignore (gitwildmatch) semantics, matching `.gitignore` behavior.
"""

from __future__ import annotations

from pathlib import Path

from pathspec import PathSpec
from pathspec.pattern import Pattern

AUTODOCIGNORE_FILENAME = ".oblt-aw.autodocignore"
AUTODOC_WORKFLOW_ID = "autodoc"


def parse_autodocignore_lines(content: str) -> list[str]:
    """Return non-empty, non-comment pattern lines from an ignore file body."""
    patterns: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)
    return patterns


def _load_autodocignore_spec(repo_root: Path) -> PathSpec[Pattern] | None:
    """Load gitwildmatch patterns from `.oblt-aw.autodocignore` when present."""
    path = repo_root / AUTODOCIGNORE_FILENAME
    if not path.is_file():
        return None
    patterns = parse_autodocignore_lines(path.read_text(encoding="utf-8"))
    if not patterns:
        return None
    return PathSpec.from_lines("gitignore", patterns)


def build_autodocignore_instructions(repo_root: Path) -> str | None:
    """
    Build additional agent instructions when `.oblt-aw.autodocignore` exists.

    Returns None when the file is missing or contains no active patterns.
    """
    path = repo_root / AUTODOCIGNORE_FILENAME
    if not path.is_file():
        return None

    patterns = parse_autodocignore_lines(path.read_text(encoding="utf-8"))
    if not patterns:
        return None

    pattern_lines = "\n".join(f"- `{pattern}`" for pattern in patterns)
    return (
        f"**Repository autodoc ignore file (`{AUTODOCIGNORE_FILENAME}`):** "
        "This repository defines paths that autodoc must never modify. "
        "Patterns follow `.gitignore` (gitwildmatch) semantics, including `*`, "
        "`**`, leading `/`, trailing `/`, and `!` negation.\n\n"
        "**Mandatory constraints:**\n"
        "- Do not propose documentation findings that require editing ignored paths.\n"
        "- Do not modify, create, or delete files that match any pattern below.\n"
        "- If an issue or checklist item targets an ignored path, skip that item and "
        "note in the PR or issue body that it was excluded by "
        f"`{AUTODOCIGNORE_FILENAME}`.\n\n"
        "**Active patterns:**\n"
        f"{pattern_lines}"
    )


def resolve_autodocignore_instructions(repo_root: Path, workflow_id: str) -> str:
    """Return autodoc ignore instructions for the autodoc workflow, else empty."""
    if workflow_id != AUTODOC_WORKFLOW_ID:
        return ""
    instructions = build_autodocignore_instructions(repo_root)
    return instructions or ""
