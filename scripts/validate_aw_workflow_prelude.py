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
Validate that every local *-aw-* workflow under .github/workflows/ calls aw-prelude.yml
and is registered in config/<org>/workflow-registry.json.

Excludes aw-prelude.yml itself (the shared prelude implementation) and distributed
trg-* and trigger-* client entrypoints, which call elastic/oblt-aw reusable workflows remotely.
"""

from __future__ import annotations

import pathlib
import re
import sys

from workflow_registry import validate_registry_against_workflows

WORKFLOWS_DIR = pathlib.Path(".github/workflows")
CONFIG_DIR = pathlib.Path("config")
AW_WORKFLOW_PATTERN = re.compile(r".+-aw-.+\.ya?ml$")

# pull_request events force issues:none, so the collect leg of the split-workflow
# pattern cannot call aw-prelude (which needs issues:read for dashboard gating).
# Gating is enforced by the downstream docs-aw-pr-ai-menu.yml (workflow_run leg).
PRELUDE_EXEMPT: frozenset[str] = frozenset({"docs-aw-pr-ai-menu-collect.yml"})

PRELUDE_USES = re.compile(
    r"uses:\s*\./\.github/workflows/aw-prelude\.ya?ml\b",
    re.MULTILINE,
)
PRELUDE_JOB = re.compile(r"^\s+prelude:\s*$", re.MULTILINE)


def list_registry_workflows() -> list[pathlib.Path]:
    """All local *-aw-* reusable workflows that must be registered (excludes prelude + client entrypoints)."""
    if not WORKFLOWS_DIR.is_dir():
        raise SystemExit(f"Missing directory: {WORKFLOWS_DIR}")
    paths = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    return [
        p
        for p in paths
        if AW_WORKFLOW_PATTERN.match(p.name)
        and p.name != "aw-prelude.yml"
        and not p.name.startswith(("trg-", "trigger-"))
    ]


def list_subject_workflows() -> list[pathlib.Path]:
    """Registry workflows that must also call aw-prelude (excludes PRELUDE_EXEMPT)."""
    return [p for p in list_registry_workflows() if p.name not in PRELUDE_EXEMPT]


def validate_workflow(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if not PRELUDE_JOB.search(text):
        errors.append(f"{path}: missing job id 'prelude'")
    if not PRELUDE_USES.search(text):
        errors.append(
            f"{path}: must call './.github/workflows/aw-prelude.yml' via a prelude job"
        )
    return errors


def main() -> int:
    errors: list[str] = []
    registry_workflows = list_registry_workflows()
    subjects = [p for p in registry_workflows if p.name not in PRELUDE_EXEMPT]
    if not registry_workflows:
        print("No *-aw-* workflows found to validate.", file=sys.stderr)
        return 1

    for path in subjects:
        errors.extend(validate_workflow(path))

    errors.extend(
        validate_registry_against_workflows(
            CONFIG_DIR,
            WORKFLOWS_DIR,
            {path.name for path in registry_workflows},
            skip_declaration_check=PRELUDE_EXEMPT,
        )
    )

    if errors:
        print("aw-prelude enforcement failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(subjects)} *-aw-* workflow(s) call aw-prelude.yml "
        f"and {len(registry_workflows)} match workflow-registry.json."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
