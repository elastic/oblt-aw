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
Validate aw-prelude placement for control-plane workflows.

- *-aw-* wrappers (except ingress) must not call aw-prelude; ingress owns prelude.
- oblt-aw-ingress.yml and docs-aw-ingress.yml must call aw-prelude.yml and define route-* jobs.
"""

from __future__ import annotations

import pathlib
import re
import sys

from workflow_registry import validate_registry_against_workflows

WORKFLOWS_DIR = pathlib.Path(".github/workflows")
CONFIG_DIR = pathlib.Path("config")
AW_WORKFLOW_PATTERN = re.compile(r".+-aw-.+\.ya?ml$")
PRELUDE_USES = re.compile(
    r"uses:\s*\./\.github/workflows/aw-prelude\.ya?ml\b",
    re.MULTILINE,
)
PRELUDE_JOB = re.compile(r"^\s+prelude:\s*$", re.MULTILINE)
INGRESS_FILES = ("oblt-aw-ingress.yml", "docs-aw-ingress.yml")
ROUTE_JOB_PATTERN = re.compile(r"^\s+route-[\w-]+:\s*$", re.MULTILINE)


def list_workflow_files() -> list[pathlib.Path]:
    if not WORKFLOWS_DIR.is_dir():
        raise SystemExit(f"Missing directory: {WORKFLOWS_DIR}")
    paths = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    return [
        p
        for p in paths
        if AW_WORKFLOW_PATTERN.match(p.name)
        and p.name != "aw-prelude.yml"
        and p.name not in INGRESS_FILES
        and not p.name.startswith(("trg-", "trigger-"))
    ]


def list_aw_wrappers(paths: list[pathlib.Path]) -> list[pathlib.Path]:
    return [p for p in paths if p.name not in INGRESS_FILES]


def validate_aw_wrapper_no_prelude(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if PRELUDE_JOB.search(text):
        errors.append(
            f"{path}: must not define a prelude job (aw-prelude runs in ingress only)"
        )
    if PRELUDE_USES.search(text):
        errors.append(
            f"{path}: must not call aw-prelude.yml (prelude and route gating run in ingress)"
        )
    return errors


def validate_ingress(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if not PRELUDE_JOB.search(text):
        errors.append(f"{path}: missing job id 'prelude'")
    if not PRELUDE_USES.search(text):
        errors.append(f"{path}: must call './.github/workflows/aw-prelude.yml'")
    if not ROUTE_JOB_PATTERN.search(text):
        errors.append(f"{path}: missing route-* dispatch job(s)")
    return errors


def main() -> int:
    paths = list_workflow_files()
    if not paths:
        print("No *-aw-* workflows found to validate.", file=sys.stderr)
        return 1

    wrappers = list_aw_wrappers(paths)
    errors: list[str] = []
    for path in wrappers:
        errors.extend(validate_aw_wrapper_no_prelude(path))

    for ingress_name in INGRESS_FILES:
        ingress = WORKFLOWS_DIR / ingress_name
        if ingress.is_file():
            errors.extend(validate_ingress(ingress))
        else:
            errors.append(f"{ingress}: missing ingress workflow")

    registry_subjects = {path.name for path in wrappers}
    errors.extend(
        validate_registry_against_workflows(
            CONFIG_DIR,
            WORKFLOWS_DIR,
            registry_subjects,
        )
    )

    if errors:
        print("aw-prelude enforcement failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(wrappers)} *-aw wrapper(s) and "
        f"{len(INGRESS_FILES)} ingress workflow(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
