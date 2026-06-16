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

"""Validate COPILOT_GITHUB_TOKEN is optional when declared in *-aw-* workflows."""

from __future__ import annotations

import pathlib
import re
import sys

import yaml  # type: ignore[import-untyped]

WORKFLOWS_DIR = pathlib.Path(".github/workflows")
AW_WORKFLOW_PATTERN = re.compile(r".+-aw-.+\.ya?ml$")


def list_subject_workflows() -> list[pathlib.Path]:
    if not WORKFLOWS_DIR.is_dir():
        raise SystemExit(f"Missing directory: {WORKFLOWS_DIR}")
    paths = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    return [
        path
        for path in paths
        if AW_WORKFLOW_PATTERN.match(path.name)
        and path.name not in {"aw-prelude.yml", "aw-resolve-apm-assets.yml"}
        and not path.name.startswith(("trg-", "trigger-"))
    ]


def validate_workflow(path: pathlib.Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []

    on_block = data.get("on", data.get(True))
    if not isinstance(on_block, dict):
        return []

    workflow_call = on_block.get("workflow_call")
    if not isinstance(workflow_call, dict):
        return []

    secrets = workflow_call.get("secrets")
    if not isinstance(secrets, dict):
        return []

    token_secret = secrets.get("COPILOT_GITHUB_TOKEN")
    if not isinstance(token_secret, dict):
        return []

    if token_secret.get("required") is True:
        return [
            (
                f"{path}: workflow_call.secrets.COPILOT_GITHUB_TOKEN.required "
                "must be false"
            )
        ]
    return []


def main() -> int:
    errors: list[str] = []
    subjects = list_subject_workflows()
    if not subjects:
        print("No *-aw-* workflows found to validate.", file=sys.stderr)
        return 1

    for path in subjects:
        errors.extend(validate_workflow(path))

    if errors:
        print("COPILOT_GITHUB_TOKEN optionality validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(subjects)} *-aw-* workflow(s): "
        "COPILOT_GITHUB_TOKEN is optional when declared."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
