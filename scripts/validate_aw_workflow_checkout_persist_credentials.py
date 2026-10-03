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
Validate workflow checkout steps set with.persist-credentials: false.

SEC-031 (`zizmor` `artipacked`) is reduced by preventing implicit git credential
persistence from actions/checkout steps in hand-authored workflows.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import yaml  # type: ignore[import-untyped]

WORKFLOWS_DIR = pathlib.Path(".github/workflows")
def list_workflows() -> list[pathlib.Path]:
    if not WORKFLOWS_DIR.is_dir():
        raise SystemExit(f"Missing directory: {WORKFLOWS_DIR}")
    paths = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    return [
        path
        for path in paths
        if not path.name.endswith(".lock.yml") and not path.name.endswith(".lock.yaml")
    ]


def validate_workflow(path: pathlib.Path) -> tuple[list[str], int]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict):
        return [f"{path}: workflow file must be a mapping"], 0

    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return [], 0

    errors: list[str] = []
    checkout_count = 0

    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue

        steps = job.get("steps")
        if not isinstance(steps, list):
            continue

        for step_index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue

            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.startswith("actions/checkout"):
                continue

            checkout_count += 1
            with_data: Any = step.get("with")
            if not isinstance(with_data, dict):
                errors.append(
                    f"{path}: job '{job_id}' step #{step_index} "
                    "must set with.persist-credentials: false"
                )
                continue

            persist = with_data.get("persist-credentials")
            if persist is False:
                continue
            if isinstance(persist, str) and persist.strip().lower() == "false":
                continue

            if "persist-credentials" not in with_data:
                errors.append(
                    f"{path}: job '{job_id}' step #{step_index} "
                    "must set with.persist-credentials: false"
                )
            else:
                errors.append(
                    f"{path}: job '{job_id}' step #{step_index} "
                    "sets persist-credentials to a non-false value"
                )

    return errors, checkout_count


def main() -> int:
    workflows = list_workflows()
    if not workflows:
        print("No workflow files found to validate.", file=sys.stderr)
        return 1

    errors: list[str] = []
    total_checkouts = 0
    for path in workflows:
        workflow_errors, count = validate_workflow(path)
        total_checkouts += count
        errors.extend(workflow_errors)

    if errors:
        print("checkout persist-credentials validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(workflows)} workflow file(s); "
        f"{total_checkouts} checkout step(s) set persist-credentials: false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
