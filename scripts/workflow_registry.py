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
workflow files under ``.github/workflows/`` via ``inner_workflows``.
Optional ``sub_features`` expose independently toggleable child capabilities.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from common import (
    compound_subfeature_key,
    compound_workflow_key,
    discover_org_config_dirs,
)

CONTROL_PLANE_WORKFLOW_NAME = re.compile(r"^[a-z0-9-]+-aw-[a-z0-9-]+\.ya?ml$")
WORKFLOW_BASENAME_INPUT = re.compile(
    r"workflow-basename:\s*([^\s#]+)",
    re.MULTILINE,
)
LEGACY_ENABLED_WORKFLOW_ID = re.compile(
    r"enabled-workflow-id:\s*([^\s#]+)",
    re.MULTILINE,
)
AUTOMERGE_COLLECTIONS_PATH = Path("obs") / "automerge-dependency-collections.json"


@dataclass(frozen=True)
class RegistrySubFeatureEntry:
    org_key: str
    workflow_id: str
    sub_feature_id: str
    inner_workflows: tuple[str, ...]

    @property
    def compound_id(self) -> str:
        return compound_subfeature_key(
            self.org_key, self.workflow_id, self.sub_feature_id
        )

    @property
    def parent_compound_id(self) -> str:
        return compound_workflow_key(self.org_key, self.workflow_id)


@dataclass(frozen=True)
class RegistryWorkflowEntry:
    org_key: str
    workflow_id: str
    inner_workflows: tuple[str, ...]
    sub_features: tuple[RegistrySubFeatureEntry, ...] = ()

    @property
    def compound_id(self) -> str:
        return compound_workflow_key(self.org_key, self.workflow_id)


@dataclass(frozen=True)
class ControlPlaneWorkflowIndexEntry:
    """Maps a control-plane workflow basename to its gating compound id."""

    org_key: str
    workflow_id: str
    sub_feature_id: str | None = None

    @property
    def compound_id(self) -> str:
        if self.sub_feature_id is not None:
            return compound_subfeature_key(
                self.org_key, self.workflow_id, self.sub_feature_id
            )
        return compound_workflow_key(self.org_key, self.workflow_id)

    @property
    def parent_compound_id(self) -> str:
        return compound_workflow_key(self.org_key, self.workflow_id)


def load_workflow_registry(org_dir: Path) -> dict[str, object]:
    path = org_dir / "workflow-registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{org_dir}: workflow-registry.json must be a JSON object")
    return data


def _normalize_control_plane_workflow_names(
    org_dir: Path,
    workflow_id: str,
    files: object,
    *,
    context: str,
) -> tuple[str, ...]:
    if not isinstance(files, list):
        raise TypeError(
            f"{org_dir}: {context} ({workflow_id!r}) must define "
            "inner_workflows as an array"
        )
    normalized: list[str] = []
    for file_index, name in enumerate(files):
        if not isinstance(name, str) or not CONTROL_PLANE_WORKFLOW_NAME.match(name):
            raise ValueError(
                f"{org_dir}: {context} ({workflow_id!r}) "
                f"inner_workflows[{file_index}] must match *-aw-*.yml or *-aw-*.yaml, "
                f"got {name!r}"
            )
        normalized.append(name)
    return tuple(normalized)


def _parse_sub_features(
    org_dir: Path,
    org_key: str,
    workflow_id: str,
    raw_sub_features: object,
    parent_files: tuple[str, ...],
) -> tuple[RegistrySubFeatureEntry, ...]:
    if raw_sub_features is None:
        return ()
    if not isinstance(raw_sub_features, list):
        raise TypeError(
            f"{org_dir}: workflows entry {workflow_id!r} sub_features must be an array"
        )

    parent_file_set = set(parent_files)
    seen_sub_ids: set[str] = set()
    entries: list[RegistrySubFeatureEntry] = []
    for index, item in enumerate(raw_sub_features):
        if not isinstance(item, dict):
            raise TypeError(
                f"{org_dir}: workflows entry {workflow_id!r} sub_features[{index}] "
                "must be an object"
            )
        sub_id = item.get("id")
        if not isinstance(sub_id, str) or not sub_id:
            raise ValueError(
                f"{org_dir}: workflows entry {workflow_id!r} "
                f"sub_features[{index}].id must be a non-empty string"
            )
        if sub_id in seen_sub_ids:
            raise ValueError(
                f"{org_dir}: workflows entry {workflow_id!r} has duplicate "
                f"sub_features id {sub_id!r}"
            )
        seen_sub_ids.add(sub_id)

        raw_files = item.get("inner_workflows", [])
        sub_files = _normalize_control_plane_workflow_names(
            org_dir,
            workflow_id,
            raw_files,
            context=f"sub_features[{index}]",
        )
        overlap = parent_file_set.intersection(sub_files)
        if overlap:
            raise ValueError(
                f"{org_dir}: workflows entry {workflow_id!r} sub_features[{index}] "
                f"({sub_id!r}) lists inner_workflows also assigned to the "
                f"parent: {sorted(overlap)}"
            )
        entries.append(
            RegistrySubFeatureEntry(
                org_key=org_key,
                workflow_id=workflow_id,
                sub_feature_id=sub_id,
                inner_workflows=sub_files,
            )
        )
    return tuple(entries)


def parse_registry_entries(org_dir: Path) -> list[RegistryWorkflowEntry]:
    raw = load_workflow_registry(org_dir)
    workflows = raw.get("workflows")
    if not isinstance(workflows, list):
        raise TypeError(
            f"{org_dir}: workflow-registry.json must contain a workflows array"
        )

    org_key = org_dir.name
    entries: list[RegistryWorkflowEntry] = []
    for index, item in enumerate(workflows):
        if not isinstance(item, dict):
            raise TypeError(f"{org_dir}: workflows[{index}] must be an object")
        workflow_id = item.get("id")
        if not isinstance(workflow_id, str) or not workflow_id:
            raise ValueError(
                f"{org_dir}: workflows[{index}].id must be a non-empty string"
            )

        files = item.get("inner_workflows")
        if not isinstance(files, list) or not files:
            raise ValueError(
                f"{org_dir}: workflows[{index}] ({workflow_id!r}) must define a "
                "non-empty inner_workflows array"
            )
        normalized = list(
            _normalize_control_plane_workflow_names(
                org_dir,
                workflow_id,
                files,
                context=f"workflows[{index}]",
            )
        )
        sub_features = _parse_sub_features(
            org_dir,
            org_key,
            workflow_id,
            item.get("sub_features"),
            tuple(normalized),
        )
        entries.append(
            RegistryWorkflowEntry(
                org_key=org_key,
                workflow_id=workflow_id,
                inner_workflows=tuple(normalized),
                sub_features=sub_features,
            )
        )
    return entries


def _load_automerge_collection_ids(config_dir: Path) -> set[str]:
    path = config_dir / AUTOMERGE_COLLECTIONS_PATH
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    collections = data.get("collections", [])
    if not isinstance(collections, list):
        return set()
    ids: set[str] = set()
    for item in collections:
        if isinstance(item, dict):
            coll_id = item.get("id")
            if isinstance(coll_id, str) and coll_id:
                ids.add(coll_id)
    return ids


def validate_automerge_sub_features(
    config_dir: Path, entries: list[RegistryWorkflowEntry]
) -> None:
    """Ensure automerge sub_features match automerge-dependency-collections.json ids."""
    collection_ids = _load_automerge_collection_ids(config_dir)
    if not collection_ids:
        return
    for entry in entries:
        if entry.workflow_id != "automerge" or not entry.sub_features:
            continue
        registry_ids = {sf.sub_feature_id for sf in entry.sub_features}
        missing = collection_ids - registry_ids
        extra = registry_ids - collection_ids
        if missing or extra:
            parts: list[str] = []
            if missing:
                parts.append(f"missing sub_features for collections: {sorted(missing)}")
            if extra:
                parts.append(
                    f"unknown sub_features not in collections: {sorted(extra)}"
                )
            raise ValueError(
                f"{entry.org_key}: automerge sub_features must match "
                f"{AUTOMERGE_COLLECTIONS_PATH}: {'; '.join(parts)}"
            )


def build_control_plane_workflow_index(
    config_dir: Path,
) -> dict[str, ControlPlaneWorkflowIndexEntry]:
    """Map control-plane workflow basename -> gating index entry (globally unique)."""
    index: dict[str, ControlPlaneWorkflowIndexEntry] = {}
    for org_dir in discover_org_config_dirs(config_dir):
        entries = parse_registry_entries(org_dir)
        validate_automerge_sub_features(config_dir, entries)
        for entry in entries:
            for filename in entry.inner_workflows:
                if filename in index:
                    previous = index[filename]
                    raise ValueError(
                        f"inner_workflows[{filename!r}] is listed under both "
                        f"{previous.org_key}:{previous.workflow_id}"
                        f"{':' + previous.sub_feature_id if previous.sub_feature_id else ''} "
                        f"and {entry.org_key}:{entry.workflow_id}"
                    )
                index[filename] = ControlPlaneWorkflowIndexEntry(
                    org_key=entry.org_key,
                    workflow_id=entry.workflow_id,
                )
            for sub_feature in entry.sub_features:
                for filename in sub_feature.inner_workflows:
                    if filename in index:
                        previous = index[filename]
                        raise ValueError(
                            f"inner_workflows[{filename!r}] is listed under both "
                            f"{previous.org_key}:{previous.workflow_id}"
                            f"{':' + previous.sub_feature_id if previous.sub_feature_id else ''} "
                            f"and {entry.org_key}:{entry.workflow_id}:{sub_feature.sub_feature_id}"
                        )
                    index[filename] = ControlPlaneWorkflowIndexEntry(
                        org_key=entry.org_key,
                        workflow_id=entry.workflow_id,
                        sub_feature_id=sub_feature.sub_feature_id,
                    )
    return index


def resolve_compound_id(config_dir: Path, workflow_basename: str) -> str:
    index = build_control_plane_workflow_index(config_dir)
    entry = index.get(workflow_basename)
    if entry is None:
        known = ", ".join(sorted(index))
        raise ValueError(
            f"workflow basename {workflow_basename!r} is not listed in any "
            f"workflow-registry.json inner_workflows (known: {known})"
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
                "workflow-registry.json inner_workflows"
            )

    stale = registered - subject_workflow_names
    for name in sorted(stale):
        entry = index[name]
        label = entry.compound_id
        errors.append(
            f"workflow-registry.json ({label}) lists "
            f"{name!r} but no matching file exists under {workflows_dir}"
        )

    for path_name in subject_workflow_names:
        path = workflows_dir / path_name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if LEGACY_ENABLED_WORKFLOW_ID.search(text):
            errors.append(
                f"{path}: use workflow-basename instead of enabled-workflow-id "
                "(compound id is resolved from workflow-registry.json)"
            )
            continue
        match = WORKFLOW_BASENAME_INPUT.search(text)
        if not match:
            errors.append(
                f"{path}: must pass workflow-basename matching this file"
            )
            continue
        declared = match.group(1)
        if declared != path_name:
            errors.append(
                f"{path}: workflow-basename is {declared!r}, expected {path_name!r}"
            )
            continue
    return errors
