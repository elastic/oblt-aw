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
Validate that every *-aw-* workflow under .github/workflows/ calls aw-prelude.yml.

Excludes aw-prelude.yml itself (the shared prelude implementation).
"""

from __future__ import annotations

import pathlib
import re
import sys

WORKFLOWS_DIR = pathlib.Path(".github/workflows")
AW_WORKFLOW_PATTERN = re.compile(r".+-aw-.+\.ya?ml$")
PRELUDE_USES = re.compile(
    r"uses:\s*\./\.github/workflows/aw-prelude\.ya?ml\b",
    re.MULTILINE,
)
PRELUDE_JOB = re.compile(r"^\s+prelude:\s*$", re.MULTILINE)


def list_subject_workflows() -> list[pathlib.Path]:
    if not WORKFLOWS_DIR.is_dir():
        raise SystemExit(f"Missing directory: {WORKFLOWS_DIR}")
    paths = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    return [
        p
        for p in paths
        if AW_WORKFLOW_PATTERN.match(p.name)
        and p.name != "aw-prelude.yml"
        and not p.name.startswith("trg-")
    ]


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
    subjects = list_subject_workflows()
    if not subjects:
        print("No *-aw-* workflows found to validate.", file=sys.stderr)
        return 1

    for path in subjects:
        errors.extend(validate_workflow(path))

    if errors:
        print("aw-prelude enforcement failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"Validated {len(subjects)} *-aw-* workflow(s) call aw-prelude.yml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
