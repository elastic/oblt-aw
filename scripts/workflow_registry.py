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
workflow files under ``.github/workflows/`` via ``control_plane_workflows``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from common import compound_workflow_key, discover_org_config_dirs

CONTROL_PLANE_WORKFLOW_NAME = re.compile(r"^[a-z0-9-]+-aw-[a-z0-9-]+\.ya?ml$")
PRELUDE_CONTROL_PLANE_WORKFLOW = re.compile(
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

        files = item.get("control_plane_workflows")
        if not isinstance(files, list) or not files:
            raise ValueError(
                f"{org_dir}: workflows[{index}] ({workflow_id!r}) must define a "
                "non-empty control_plane_workflows array"
            )
        normalized: list[str] = []
        for file_index, name in enumerate(files):
            if not isinstance(name, str) or not CONTROL_PLANE_WORKFLOW_NAME.match(name):
                raise ValueError(
                    f"{org_dir}: workflows[{index}].control_plane_workflows[{file_index}] "
                    f"must match *-aw-*.yml, got {name!r}"
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
                        f"control_plane_workflows[{filename!r}] is listed under both "
                        f"{previous.org_key}:{previous.workflow_id} and "
                        f"{entry.org_key}:{entry.workflow_id}"
                    )
                index[filename] = entry
    return index


def resolve_compound_id(config_dir: Path, control_plane_workflow: str) -> str:
    index = build_control_plane_workflow_index(config_dir)
    entry = index.get(control_plane_workflow)
    if entry is None:
        known = ", ".join(sorted(index))
        raise ValueError(
            f"control-plane workflow {control_plane_workflow!r} is not listed in any "
            f"workflow-registry.json control_plane_workflows (known: {known})"
        )
    return entry.compound_id


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
                "workflow-registry.json control_plane_workflows"
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
                f"{path}: use control-plane-workflow instead of enabled-workflow-id "
                "(compound id is resolved from workflow-registry.json)"
            )
            continue
        match = PRELUDE_CONTROL_PLANE_WORKFLOW.search(text)
        if not match:
            errors.append(
                f"{path}: prelude must pass control-plane-workflow matching this file"
            )
            continue
        declared = match.group(1)
        if declared != path_name:
            errors.append(
                f"{path}: control-plane-workflow is {declared!r}, expected {path_name!r}"
            )
            continue
    return errors
