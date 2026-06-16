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
Validate that every local *-aw-* workflow invoking a gh-aw-* reusable also calls
aw-resolve-agentic-assets.yml once per agent invocation.

Excludes aw-resolve-agentic-assets.yml and aw-prelude.yml, and distributed trg-* /
trigger-* client entrypoints.
"""

from __future__ import annotations

import pathlib
import re
import sys

from validate_aw_workflow_prelude import list_subject_workflows

GH_AW_USES = re.compile(
    r"^\s+uses:\s*\S+/gh-aw-.+\.ya?ml",
    re.MULTILINE,
)
RESOLVE_AGENTIC_USES = re.compile(
    r"uses:\s*\./\.github/workflows/aw-resolve-agentic-assets\.ya?ml\b",
    re.MULTILINE,
)
PRELUDE_RESOLVED_INSTRUCTIONS = re.compile(
    r"needs\.prelude\.outputs\.resolved-(?:additional-instructions|inputs-json|setup-commands-json)",
)


def validate_workflow(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    agent_calls = len(GH_AW_USES.findall(text))
    if agent_calls == 0:
        return errors

    resolve_calls = len(RESOLVE_AGENTIC_USES.findall(text))
    if resolve_calls < agent_calls:
        errors.append(
            f"{path}: found {agent_calls} gh-aw-* reusable call(s) but only "
            f"{resolve_calls} aw-resolve-agentic-assets.yml call(s); add one resolve job "
            "per agent invocation"
        )

    if PRELUDE_RESOLVED_INSTRUCTIONS.search(text):
        errors.append(
            f"{path}: must use resolve-agentic-assets outputs for asset resolution, "
            "not needs.prelude.outputs.resolved-*"
        )

    return errors


def main() -> int:
    errors: list[str] = []
    subjects = list_subject_workflows()
    if not subjects:
        print("No *-aw-* workflows found to validate.", file=sys.stderr)
        return 1

    for path in subjects:
        errors.extend(validate_workflow(path))

    if errors:
        print("resolve-agentic-assets enforcement failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    agent_workflows = sum(
        1 for path in subjects if GH_AW_USES.search(path.read_text(encoding="utf-8"))
    )
    print(
        f"Validated {len(subjects)} *-aw-* workflow(s); "
        f"{agent_workflows} invoke gh-aw-* and call aw-resolve-agentic-assets.yml."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
