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
Validate local *-aw-* route workflows and registry coherence.

Route reusables (obs-aw-*, docs-aw-*) receive shared event context from
*-aw-event-* orchestrators and declare workflow_call input shared-proceed.
"""

from __future__ import annotations

import pathlib
import re
import sys

from workflow_registry import validate_registry_against_workflows

WORKFLOWS_DIR = pathlib.Path(".github/workflows")
CONFIG_DIR = pathlib.Path("config")
AW_WORKFLOW_PATTERN = re.compile(r".+-aw-.+\.ya?ml$")
EVENT_ORCHESTRATOR_PATTERN = re.compile(r".+-aw-event-.+\.ya?ml$")
ROUTE_PATTERN = re.compile(r"^(?:obs|docs)-aw-.+\.ya?ml$")
PRELUDE_USES = re.compile(
    r"uses:\s*\./\.github/workflows/aw-prelude\.ya?ml\b",
    re.MULTILINE,
)
PRELUDE_JOB = re.compile(r"^\s+(?:prelude|run-aw-prelude):\s*$", re.MULTILINE)
SHARED_PROCEED_INPUT = re.compile(r"^\s+shared-proceed:\s*$", re.MULTILINE)


def list_subject_workflows() -> list[pathlib.Path]:
    if not WORKFLOWS_DIR.is_dir():
        raise SystemExit(f"Missing directory: {WORKFLOWS_DIR}")
    paths = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    return [
        p
        for p in paths
        if AW_WORKFLOW_PATTERN.match(p.name)
        and not p.name.startswith("aw-")
        and not EVENT_ORCHESTRATOR_PATTERN.match(p.name)
        and not p.name.startswith(("trg-", "trigger-"))
    ]


def validate_route(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if PRELUDE_JOB.search(text):
        errors.append(
            f"{path}: route workflows must not define a prelude or run-aw-prelude job"
        )
    if PRELUDE_USES.search(text):
        errors.append(f"{path}: route workflows must not call aw-prelude.yml")
    if not SHARED_PROCEED_INPUT.search(text):
        errors.append(f"{path}: must declare workflow_call input shared-proceed")
    return errors


def validate_workflow(path: pathlib.Path) -> list[str]:
    if ROUTE_PATTERN.match(path.name):
        return validate_route(path)
    return []


def validate_registry_for_subjects(subject_workflow_names: set[str]) -> list[str]:
    errors = validate_registry_against_workflows(
        CONFIG_DIR,
        WORKFLOWS_DIR,
        subject_workflow_names,
    )
    routes = {name for name in subject_workflow_names if ROUTE_PATTERN.match(name)}
    filtered: list[str] = []
    for err in errors:
        path_name = err.split(":", 1)[0].split("/")[-1]
        if path_name in routes and "must pass workflow-basename matching this file" in err:
            continue
        filtered.append(err)
    return filtered


def main() -> int:
    errors: list[str] = []
    subjects = list_subject_workflows()
    if not subjects:
        print("No *-aw-* workflows found to validate.", file=sys.stderr)
        return 1

    for path in subjects:
        errors.extend(validate_workflow(path))

    errors.extend(validate_registry_for_subjects({path.name for path in subjects}))

    if errors:
        print("aw workflow route validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(subjects)} *-aw-* workflow(s): "
        "routes declare shared-proceed; event orchestrators call aw-prelude.yml."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
