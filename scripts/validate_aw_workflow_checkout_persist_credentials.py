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

"""Validate explicit checkout credential hardening in workflow jobs."""

from __future__ import annotations

import pathlib
import sys
from collections.abc import Mapping
from typing import Any

import yaml  # type: ignore[import-untyped]

WORKFLOWS_DIR = pathlib.Path(".github/workflows")


def list_workflow_files() -> list[pathlib.Path]:
    if not WORKFLOWS_DIR.is_dir():
        raise FileNotFoundError(f"Missing directory: {WORKFLOWS_DIR}")
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


def _is_checkout_step(step: Mapping[str, Any]) -> bool:
    uses = step.get("uses")
    return isinstance(uses, str) and uses.startswith("actions/checkout@")


def _persist_credentials_is_false(step: Mapping[str, Any]) -> bool:
    with_cfg = step.get("with")
    if not isinstance(with_cfg, Mapping):
        return False
    value = with_cfg.get("persist-credentials")
    return value is False or value == "false"


def validate_workflow_file(path: pathlib.Path) -> list[str]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict):
        return [f"{path}: workflow file must be a mapping"]

    errors: list[str] = []
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return errors

    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, Mapping) or not _is_checkout_step(step):
                continue
            if _persist_credentials_is_false(step):
                continue
            name = step.get("name")
            step_label = str(name) if isinstance(name, str) and name else f"step #{idx}"
            errors.append(
                f"{path}: job '{job_id}' {step_label} uses actions/checkout "
                "without with.persist-credentials: false"
            )

    return errors


def main() -> int:
    workflow_files = [
        path for path in list_workflow_files() if not path.name.endswith(".lock.yml")
    ]
    if not workflow_files:
        print("No workflow files found to validate.", file=sys.stderr)
        return 1

    errors: list[str] = []
    checkout_steps = 0
    for path in workflow_files:
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(workflow, dict):
            jobs = workflow.get("jobs")
            if isinstance(jobs, dict):
                for job in jobs.values():
                    if not isinstance(job, dict):
                        continue
                    steps = job.get("steps")
                    if not isinstance(steps, list):
                        continue
                    checkout_steps += sum(
                        1
                        for step in steps
                        if isinstance(step, Mapping) and _is_checkout_step(step)
                    )
        errors.extend(validate_workflow_file(path))

    if errors:
        print("checkout credential hardening validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(workflow_files)} workflow file(s); "
        f"{checkout_steps} checkout step(s) set persist-credentials: false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
