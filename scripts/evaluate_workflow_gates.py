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
Evaluate dashboard gates for multiple control-plane workflows at once.

Used by aw-prelude.yml so event-scoped orchestrators run dashboard and
allow-list loading once, then fan out per-route proceed flags.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from common import write_outputs
from workflow_registry import (
    ControlPlaneWorkflowIndexEntry,
    build_control_plane_workflow_index,
    prefer_index_entry,
)


def _proceed_for_compound_id(
    effective_raw: str, enabled_workflows_json: str, compound_id: str
) -> bool:
    if not effective_raw:
        return False
    enabled = json.loads(enabled_workflows_json)
    if not isinstance(enabled, list):
        raise TypeError("enabled-workflows must be a JSON array")
    enabled_set = set(enabled)
    if compound_id not in enabled_set:
        return False
    parts = compound_id.split(":")
    if len(parts) == 3:
        parent_id = f"{parts[0]}:{parts[1]}"
        return parent_id in enabled_set
    return True


def evaluate_gates(
    config_dir: Path,
    control_plane_workflows: list[str],
    effective_raw: str,
    enabled_workflows_json: str,
    *,
    org_key: str | None = None,
) -> dict[str, str]:
    index = build_control_plane_workflow_index(config_dir)
    proceed_by_workflow: dict[str, str] = {}
    for basename in control_plane_workflows:
        if basename not in index:
            known = ", ".join(sorted(index))
            raise ValueError(
                f"control-plane workflow {basename!r} is not listed in any "
                f"workflow-registry.json inner_workflows (known: {known})"
            )
        # Shared common services list the same basename under multiple orgs.
        # When org_key is set (tip aw-prelude), evaluate only that org's
        # compound id. When omitted (released @v0 prelude + tip scripts),
        # prefer the implementation-org entry so callers keep working.
        org_entries: tuple[ControlPlaneWorkflowIndexEntry, ...]
        if org_key is None:
            org_entries = (prefer_index_entry(index[basename], basename),)
        else:
            org_entries = tuple(
                entry for entry in index[basename] if entry.org_key == org_key
            )
            if not org_entries:
                labeled = (
                    ", ".join(sorted({entry.org_key for entry in index[basename]}))
                    or "(none)"
                )
                raise ValueError(
                    f"control-plane workflow {basename!r} is not listed for org "
                    f"{org_key!r} (present under: {labeled})"
                )
        allowed = any(
            _proceed_for_compound_id(
                effective_raw, enabled_workflows_json, entry.compound_id
            )
            for entry in org_entries
        )
        proceed_by_workflow[basename] = "true" if allowed else "false"
    return proceed_by_workflow


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate dashboard gates for multiple control-plane workflows"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Config root containing per-org workflow-registry.json trees",
    )
    parser.add_argument(
        "--control-plane-workflows",
        required=True,
        help="JSON array of workflow basenames under .github/workflows/",
    )
    parser.add_argument(
        "--effective-raw",
        default="",
        help="Raw dashboard read ('' means no dashboard issue; no workflows enabled)",
    )
    parser.add_argument(
        "--enabled-workflows",
        default="[]",
        help="Normalized JSON array of compound org:workflow-id strings",
    )
    parser.add_argument(
        "--org-key",
        default="",
        help=(
            "Invoking org key (config/<org-key>/); gates only that org's "
            "compound ids. Optional for released @v0 preludes that omit it "
            "(falls back to the implementation-org index entry)."
        ),
    )
    args = parser.parse_args()

    try:
        workflows = json.loads(args.control_plane_workflows)
    except json.JSONDecodeError as exc:
        print(f"Invalid --control-plane-workflows JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(workflows, list) or not workflows:
        print(
            "--control-plane-workflows must be a non-empty JSON array",
            file=sys.stderr,
        )
        return 1
    if not all(isinstance(name, str) and name for name in workflows):
        print(
            "--control-plane-workflows must contain non-empty strings",
            file=sys.stderr,
        )
        return 1
    org_key = args.org_key.strip() if isinstance(args.org_key, str) else ""
    if not org_key:
        org_key_arg: str | None = None
    else:
        org_key_arg = org_key

    try:
        proceed_by_workflow = evaluate_gates(
            args.config_dir,
            workflows,
            args.effective_raw,
            args.enabled_workflows,
            org_key=org_key_arg,
        )
    except (ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = json.dumps(proceed_by_workflow, separators=(",", ":"))
    if os.getenv("GITHUB_OUTPUT"):
        write_outputs({"proceed-by-workflow": payload})
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
