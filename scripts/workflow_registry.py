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

Orgs may opt into shared definitions from ``config/common/services.json`` via
``include_common`` (see :func:`expand_org_workflow_dicts`). Shared services keep
implementation under the owning org prefix (for example ``obs-aw-*``) and appear
in each opting org's catalog as ``org:workflow-id`` — not as a Common dashboard
section.
"""

from __future__ import annotations

import copy
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
COMMON_SERVICES_PATH = Path("common") / "services.json"


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


def load_common_services(config_dir: Path) -> dict[str, dict[str, object]]:
    """
    Load ``config/common/services.json`` as ``service_id -> workflow dict``.

    Missing file yields an empty map (orgs must not use ``include_common`` then).
    """
    path = config_dir / COMMON_SERVICES_PATH
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path}: must be a JSON object")
    services = data.get("services")
    if not isinstance(services, list):
        raise TypeError(f"{path}: must contain a services array")
    by_id: dict[str, dict[str, object]] = {}
    for index, item in enumerate(services):
        if not isinstance(item, dict):
            raise TypeError(f"{path}: services[{index}] must be an object")
        service_id = item.get("id")
        if not isinstance(service_id, str) or not service_id:
            raise ValueError(f"{path}: services[{index}].id must be a non-empty string")
        if service_id in by_id:
            raise ValueError(f"{path}: duplicate service id {service_id!r}")
        by_id[service_id] = item
    return by_id


def expand_org_workflow_dicts(
    org_dir: Path, config_dir: Path
) -> list[dict[str, object]]:
    """
    Resolve ``include_common`` then local ``workflows`` for one org.

    Included common services are deep-copied into this org's catalog. Local
    ``workflows`` entries must not reuse an included id.
    """
    raw = load_workflow_registry(org_dir)
    include_raw = raw.get("include_common", [])
    if include_raw is None:
        include_raw = []
    if not isinstance(include_raw, list):
        raise TypeError(f"{org_dir}: include_common must be an array when present")
    include_ids: list[str] = []
    for index, item in enumerate(include_raw):
        if not isinstance(item, str) or not item:
            raise ValueError(
                f"{org_dir}: include_common[{index}] must be a non-empty string"
            )
        if item in include_ids:
            raise ValueError(f"{org_dir}: duplicate include_common id {item!r}")
        include_ids.append(item)

    common = load_common_services(config_dir)
    expanded: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for service_id in include_ids:
        if service_id not in common:
            known = ", ".join(sorted(common)) or "(none)"
            raise ValueError(
                f"{org_dir}: include_common lists unknown common service "
                f"{service_id!r} (known: {known})"
            )
        cloned = copy.deepcopy(common[service_id])
        expanded.append(cloned)
        seen_ids.add(service_id)

    workflows = raw.get("workflows")
    if not isinstance(workflows, list):
        raise TypeError(
            f"{org_dir}: workflow-registry.json must contain a workflows array"
        )
    for index, item in enumerate(workflows):
        if not isinstance(item, dict):
            raise TypeError(f"{org_dir}: workflows[{index}] must be an object")
        workflow_id = item.get("id")
        if not isinstance(workflow_id, str) or not workflow_id:
            raise ValueError(
                f"{org_dir}: workflows[{index}].id must be a non-empty string"
            )
        if workflow_id in seen_ids:
            raise ValueError(
                f"{org_dir}: workflows[{index}] id {workflow_id!r} conflicts with "
                "include_common (move the definition to config/common/services.json "
                "or drop the include)"
            )
        expanded.append(item)
        seen_ids.add(workflow_id)
    return expanded


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


def parse_registry_entries(
    org_dir: Path, config_dir: Path | None = None
) -> list[RegistryWorkflowEntry]:
    """Parse one org registry, expanding ``include_common`` when ``config_dir`` is set."""
    root = config_dir if config_dir is not None else org_dir.parent
    workflows = expand_org_workflow_dicts(org_dir, root)

    org_key = org_dir.name
    entries: list[RegistryWorkflowEntry] = []
    for index, item in enumerate(workflows):
        workflow_id = item.get("id")
        if not isinstance(workflow_id, str) or not workflow_id:
            raise ValueError(
                f"{org_dir}: expanded workflows[{index}].id must be a non-empty string"
            )

        files = item.get("inner_workflows")
        if not isinstance(files, list) or not files:
            raise ValueError(
                f"{org_dir}: workflows entry ({workflow_id!r}) must define a "
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


def _index_label(entry: ControlPlaneWorkflowIndexEntry) -> str:
    if entry.sub_feature_id is not None:
        return f"{entry.org_key}:{entry.workflow_id}:{entry.sub_feature_id}"
    return f"{entry.org_key}:{entry.workflow_id}"


def _register_index_filename(
    index: dict[str, list[ControlPlaneWorkflowIndexEntry]],
    filename: str,
    entry: ControlPlaneWorkflowIndexEntry,
) -> None:
    """
    Register ``filename`` under ``entry``.

    The same basename may appear under multiple orgs only when ``workflow_id`` and
    ``sub_feature_id`` match (intentional common-service share). Conflicting
    mappings still fail closed.
    """
    existing = index.get(filename)
    if existing is None:
        index[filename] = [entry]
        return
    for previous in existing:
        if (
            previous.workflow_id != entry.workflow_id
            or previous.sub_feature_id != entry.sub_feature_id
        ):
            raise ValueError(
                f"inner_workflows[{filename!r}] is listed under both "
                f"{_index_label(previous)} and {_index_label(entry)}"
            )
        if previous.org_key == entry.org_key:
            raise ValueError(
                f"inner_workflows[{filename!r}] is listed twice under "
                f"{_index_label(entry)}"
            )
    existing.append(entry)


def build_control_plane_workflow_index(
    config_dir: Path,
) -> dict[str, tuple[ControlPlaneWorkflowIndexEntry, ...]]:
    """Map control-plane workflow basename -> one or more gating index entries."""
    index: dict[str, list[ControlPlaneWorkflowIndexEntry]] = {}
    for org_dir in discover_org_config_dirs(config_dir):
        entries = parse_registry_entries(org_dir, config_dir)
        validate_automerge_sub_features(config_dir, entries)
        for entry in entries:
            for filename in entry.inner_workflows:
                _register_index_filename(
                    index,
                    filename,
                    ControlPlaneWorkflowIndexEntry(
                        org_key=entry.org_key,
                        workflow_id=entry.workflow_id,
                    ),
                )
            for sub_feature in entry.sub_features:
                for filename in sub_feature.inner_workflows:
                    _register_index_filename(
                        index,
                        filename,
                        ControlPlaneWorkflowIndexEntry(
                            org_key=entry.org_key,
                            workflow_id=entry.workflow_id,
                            sub_feature_id=sub_feature.sub_feature_id,
                        ),
                    )
    return {name: tuple(entries) for name, entries in index.items()}


def implementation_org_key_from_basename(workflow_basename: str) -> str | None:
    """Return the org prefix before ``-aw-`` in a control-plane basename."""
    match = re.match(r"^([a-z0-9-]+)-aw-", workflow_basename)
    if match is None:
        return None
    return match.group(1)


def prefer_index_entry(
    entries: tuple[ControlPlaneWorkflowIndexEntry, ...],
    workflow_basename: str,
) -> ControlPlaneWorkflowIndexEntry:
    """Pick the implementation-org entry when present; else lowest org_key.

    Prefer :func:`resolve_compound_id` with an explicit ``org_key`` when the
    invoking (consuming) org is known — shared common basenames must not
    silently resolve to the implementation org.
    """
    if not entries:
        raise ValueError(f"no index entries for {workflow_basename!r}")
    impl = implementation_org_key_from_basename(workflow_basename)
    if impl is not None:
        for entry in entries:
            if entry.org_key == impl:
                return entry
    return min(entries, key=lambda item: item.org_key)


def resolve_compound_id(
    config_dir: Path,
    workflow_basename: str,
    *,
    org_key: str | None = None,
) -> str:
    index = build_control_plane_workflow_index(config_dir)
    entries = index.get(workflow_basename)
    if entries is None:
        known = ", ".join(sorted(index))
        raise ValueError(
            f"workflow basename {workflow_basename!r} is not listed in any "
            f"workflow-registry.json inner_workflows (known: {known})"
        )
    if org_key is not None:
        for entry in entries:
            if entry.org_key == org_key:
                return entry.compound_id
        labeled = ", ".join(sorted({entry.org_key for entry in entries})) or "(none)"
        raise ValueError(
            f"workflow basename {workflow_basename!r} is not listed for org "
            f"{org_key!r} (present under: {labeled})"
        )
    return prefer_index_entry(entries, workflow_basename).compound_id


def validate_registry_against_workflows(
    config_dir: Path,
    workflows_dir: Path,
    subject_workflow_names: set[str],
) -> list[str]:
    """Return human-readable validation errors (empty when valid)."""
    errors: list[str] = []
    try:
        index = build_control_plane_workflow_index(config_dir)
    except (ValueError, TypeError) as exc:
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
        labels = ", ".join(_index_label(entry) for entry in index[name])
        errors.append(
            f"workflow-registry.json ({labels}) lists "
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
            errors.append(f"{path}: must pass workflow-basename matching this file")
            continue
        declared = match.group(1)
        if declared != path_name:
            errors.append(
                f"{path}: workflow-basename is {declared!r}, expected {path_name!r}"
            )
            continue
    return errors
