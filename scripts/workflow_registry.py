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
Load and validate per-org workflow-registry.json files.

Each workflow entry maps a dashboard ``id`` to one or more control-plane reusable
workflow files under ``.github/workflows/``, derived from ``ingress_routes``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from common import compound_workflow_key, discover_org_config_dirs
from oblt_aw_route_specs import RegistryParseError, parse_workflow_ingress_routes

CONTROL_PLANE_WORKFLOW_NAME = re.compile(r"^[a-z0-9-]+-aw-[a-z0-9-]+\.ya?ml$")
LEGACY_CONTROL_PLANE_WORKFLOW = re.compile(
    r"control-plane-workflow:\s*([^\s#]+)",
    re.MULTILINE,
)
LEGACY_ENABLED_WORKFLOW_ID = re.compile(
    r"enabled-workflow-id:\s*([^\s#]+)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class RegistryWorkflowEntry:
    org_key: str
    workflow_id: str
    control_plane_workflows: tuple[str, ...]

    @property
    def compound_id(self) -> str:
        return compound_workflow_key(self.org_key, self.workflow_id)


def load_workflow_registry(org_dir: Path) -> dict[str, object]:
    path = org_dir / "workflow-registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{org_dir}: workflow-registry.json must be a JSON object")
    return data


def parse_registry_entries(org_dir: Path) -> list[RegistryWorkflowEntry]:
    raw = load_workflow_registry(org_dir)
    workflows = raw.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError(
            f"{org_dir}: workflow-registry.json must contain a workflows array"
        )

    org_key = org_dir.name
    entries: list[RegistryWorkflowEntry] = []
    for index, item in enumerate(workflows):
        if not isinstance(item, dict):
            raise ValueError(f"{org_dir}: workflows[{index}] must be an object")
        workflow_id = item.get("id")
        if not isinstance(workflow_id, str) or not workflow_id:
            raise ValueError(
                f"{org_dir}: workflows[{index}].id must be a non-empty string"
            )

        context = f"{org_dir}: workflows[{index}]"
        try:
            route_specs = parse_workflow_ingress_routes(
                item,
                org_key=org_key,
                context=context,
            )
        except RegistryParseError as exc:
            raise ValueError(str(exc)) from exc

        normalized: list[str] = []
        for route_spec in route_specs:
            name = route_spec.workflow_file
            if not CONTROL_PLANE_WORKFLOW_NAME.match(name):
                raise ValueError(
                    f"{org_dir}: workflows[{index}] ingress route "
                    f"{route_spec.route_id!r} must resolve to *-aw-*.yml, got {name!r}"
                )
            normalized.append(name)
        entries.append(
            RegistryWorkflowEntry(
                org_key=org_key,
                workflow_id=workflow_id,
                control_plane_workflows=tuple(normalized),
            )
        )
    return entries


def build_control_plane_workflow_index(
    config_dir: Path,
) -> dict[str, RegistryWorkflowEntry]:
    """Map control-plane workflow basename -> registry entry (globally unique)."""
    index: dict[str, RegistryWorkflowEntry] = {}
    for org_dir in discover_org_config_dirs(config_dir):
        for entry in parse_registry_entries(org_dir):
            for filename in entry.control_plane_workflows:
                if filename in index:
                    previous = index[filename]
                    raise ValueError(
                        f"ingress route workflow {filename!r} is listed under both "
                        f"{previous.org_key}:{previous.workflow_id} and "
                        f"{entry.org_key}:{entry.workflow_id}"
                    )
                index[filename] = entry
    return index


def validate_registry_against_workflows(
    config_dir: Path,
    workflows_dir: Path,
    subject_workflow_names: set[str],
) -> list[str]:
    """Return human-readable validation errors (empty when valid)."""
    errors: list[str] = []
    try:
        index = build_control_plane_workflow_index(config_dir)
    except ValueError as exc:
        return [str(exc)]

    registered = set(index)
    missing = subject_workflow_names - registered
    if missing:
        for name in sorted(missing):
            errors.append(
                f"{workflows_dir / name}: not listed in any "
                "workflow-registry.json ingress_routes"
            )

    stale = registered - subject_workflow_names
    for name in sorted(stale):
        entry = index[name]
        errors.append(
            f"workflow-registry.json ({entry.org_key}:{entry.workflow_id}) lists "
            f"{name!r} but no matching file exists under {workflows_dir}"
        )

    for path_name in subject_workflow_names:
        path = workflows_dir / path_name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if LEGACY_ENABLED_WORKFLOW_ID.search(text):
            errors.append(
                f"{path}: remove enabled-workflow-id "
                "(dashboard gating is enforced in ingress route jobs)"
            )
        # control-plane-workflow is required on aw-resolve-apm-assets calls; only
        # forbid legacy passes to aw-prelude.
        if re.search(
            r"uses:\s*\./\.github/workflows/aw-prelude\.ya?ml[\s\S]{0,800}?"
            r"control-plane-workflow:",
            text,
        ):
            errors.append(
                f"{path}: remove control-plane-workflow from aw-prelude "
                "(prelude runs in ingress without per-wrapper gating)"
            )
    return errors
