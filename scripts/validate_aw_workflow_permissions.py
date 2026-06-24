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
Validate reusable-workflow caller job permissions against callee requirements.

For every job that calls a reusable workflow, the caller job must grant at least
the maximum permission scope required by any job in the callee workflow, including
nested reusable workflows (for example gh-aw-* lock files in elastic/ai-github-actions).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import yaml  # type: ignore[import-untyped]

from workflow_permissions import (
    WorkflowPermissionResolver,
    effective_job_permissions,
    is_reusable_workflow_job,
    parse_reusable_workflow_uses,
    permission_deficits,
)

WORKFLOWS_DIR = pathlib.Path(".github/workflows")


def list_workflow_files() -> list[pathlib.Path]:
    if not WORKFLOWS_DIR.is_dir():
        raise FileNotFoundError(f"Missing directory: {WORKFLOWS_DIR}")
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


def validate_workflow_file(
    path: pathlib.Path,
    resolver: WorkflowPermissionResolver,
) -> list[str]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict):
        return [f"{path}: workflow file must be a mapping"]

    errors: list[str] = []
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return errors

    root_permissions = workflow.get("permissions")
    for job_id, job in jobs.items():
        if not isinstance(job, dict) or not is_reusable_workflow_job(job):
            continue

        uses = job.get("uses")
        if not isinstance(uses, str):
            continue

        workflow_ref = parse_reusable_workflow_uses(uses)
        if workflow_ref is None:
            continue

        caller_permissions = effective_job_permissions(root_permissions, job)
        try:
            required_permissions = resolver.callee_requirements(workflow_ref)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            errors.append(f"{path}: job '{job_id}' cannot resolve callee {uses}: {exc}")
            continue

        deficits = permission_deficits(caller_permissions, required_permissions)
        for scope, caller_level, required_level in deficits:
            errors.append(
                f"{path}: job '{job_id}' calls {uses} but grants "
                f"{scope}: {caller_level or 'none'} while callee requires "
                f"{scope}: {required_level}"
            )

    return errors


def main() -> int:
    errors: list[str] = []
    workflow_files = list_workflow_files()
    if not workflow_files:
        print("No workflow files found to validate.", file=sys.stderr)
        return 1

    resolver = WorkflowPermissionResolver(WORKFLOWS_DIR)
    reusable_call_count = 0

    for path in workflow_files:
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        jobs: dict[str, Any] = (
            workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
        )
        reusable_call_count += sum(
            1
            for job in jobs.values()
            if isinstance(job, dict) and is_reusable_workflow_job(job)
        )
        errors.extend(validate_workflow_file(path, resolver))

    if errors:
        print("reusable workflow permission validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(workflow_files)} workflow file(s); "
        f"{reusable_call_count} reusable-workflow call(s) have aligned permissions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
