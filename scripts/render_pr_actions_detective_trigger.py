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

"""Replace the PR Actions Detective ``workflows:`` placeholder in a client trigger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import PR_ACTIONS_DETECTIVE_WORKFLOWS_PLACEHOLDER


def render_workflows_placeholder(content: str, workflows: list[str]) -> str:
    """
    Substitute the distribute placeholder with a JSON array of workflow names.

    Raises ``SystemExit`` when the placeholder is missing or ``workflows`` is empty.
    """
    if not workflows:
        raise SystemExit(
            "refuse to render empty pr-actions-detective-workflows "
            "(omit the trigger instead)"
        )
    if PR_ACTIONS_DETECTIVE_WORKFLOWS_PLACEHOLDER not in content:
        raise SystemExit(
            "missing pr-actions-detective workflows placeholder "
            f"{PR_ACTIONS_DETECTIVE_WORKFLOWS_PLACEHOLDER} in trigger file"
        )
    return content.replace(
        PR_ACTIONS_DETECTIVE_WORKFLOWS_PLACEHOLDER,
        json.dumps(workflows),
        1,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render on.workflow_run.workflows from "
            "pr-actions-detective-workflows into a client trigger YAML."
        )
    )
    parser.add_argument(
        "--path",
        required=True,
        type=Path,
        help="Path to trigger-obs-aw-workflow-run.yml in the target checkout",
    )
    parser.add_argument(
        "--workflows-json",
        required=True,
        help="JSON array of GitHub Actions workflow name: values to monitor",
    )
    args = parser.parse_args(argv)

    try:
        workflows = json.loads(args.workflows_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --workflows-json: {exc}") from exc
    if not isinstance(workflows, list) or not all(
        isinstance(name, str) and name.strip() for name in workflows
    ):
        raise SystemExit("--workflows-json must be a JSON array of non-empty strings")
    names = [name.strip() for name in workflows]

    path: Path = args.path
    if not path.is_file():
        raise SystemExit(f"trigger file not found: {path}")

    rendered = render_workflows_placeholder(path.read_text(encoding="utf-8"), names)
    path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
