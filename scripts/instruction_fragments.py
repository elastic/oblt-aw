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
Control-plane instruction fragment loading and composition.

Manifest: ``config/<org-key>/instruction-fragment-map.json``
Files: ``config/<org-key>/instruction-fragments/<fragment-id>.md``

Compose order (append):
1. ``common`` fragment ids
2. ``workflows.<workflow-id>.fragments``
3. ``workflows.<workflow-id>.inner-workflows.<basename>.fragments``
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

FRAGMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAP_FILENAME = "instruction-fragment-map.json"
FRAGMENTS_DIRNAME = "instruction-fragments"


def _require_fragment_id(fragment_id: str, *, context: str) -> str:
    if not isinstance(fragment_id, str) or not FRAGMENT_ID_PATTERN.match(fragment_id):
        raise ValueError(
            f"{context}: fragment id must be kebab-case "
            f"(^[a-z0-9]+(?:-[a-z0-9]+)*$), got {fragment_id!r}"
        )
    return fragment_id


def _normalize_fragment_id_list(raw: Any, *, context: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise TypeError(f"{context}: fragments must be a JSON array of ids")
    out: list[str] = []
    for index, item in enumerate(raw):
        out.append(_require_fragment_id(item, context=f"{context}[{index}]"))
    return out


def _normalize_workflow_entry(raw: Any, *, context: str) -> dict[str, Any]:
    """
    Accept either a bare fragment-id array (shorthand) or an object with
    ``fragments`` and optional ``inner-workflows``.
    """
    if isinstance(raw, list):
        return {
            "fragments": _normalize_fragment_id_list(
                raw, context=f"{context}.fragments"
            ),
            "inner-workflows": {},
        }
    if not isinstance(raw, dict):
        raise TypeError(
            f"{context}: must be a fragment-id array or an object with fragments"
        )
    unknown = set(raw) - {"fragments", "inner-workflows"}
    if unknown:
        raise ValueError(f"{context}: unknown keys {sorted(unknown)}")

    inner_raw = raw.get("inner-workflows")
    inner: dict[str, list[str]] = {}
    if inner_raw is not None:
        if not isinstance(inner_raw, dict):
            raise TypeError(f"{context}.inner-workflows must be a mapping")
        for basename, entry in inner_raw.items():
            if not isinstance(basename, str) or not basename.strip():
                raise ValueError(
                    f"{context}.inner-workflows keys must be non-empty basenames"
                )
            if isinstance(entry, list):
                inner[basename] = _normalize_fragment_id_list(
                    entry, context=f"{context}.inner-workflows.{basename}"
                )
            elif isinstance(entry, dict):
                unknown_inner = set(entry) - {"fragments"}
                if unknown_inner:
                    raise ValueError(
                        f"{context}.inner-workflows.{basename}: "
                        f"unknown keys {sorted(unknown_inner)}"
                    )
                inner[basename] = _normalize_fragment_id_list(
                    entry.get("fragments"),
                    context=f"{context}.inner-workflows.{basename}.fragments",
                )
            else:
                raise TypeError(
                    f"{context}.inner-workflows.{basename}: "
                    "must be a fragment-id array or {fragments: [...]}"
                )

    return {
        "fragments": _normalize_fragment_id_list(
            raw.get("fragments"), context=f"{context}.fragments"
        ),
        "inner-workflows": inner,
    }


def load_instruction_fragment_map(
    config_dir: Path, org_key: str
) -> dict[str, Any] | None:
    """Load and validate the org fragment map, or None when the file is absent."""
    path = config_dir / org_key / MAP_FILENAME
    if not path.is_file():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path}: must be a JSON object")

    unknown = set(data) - {"common", "workflows"}
    if unknown:
        raise ValueError(f"{path}: unknown keys {sorted(unknown)}")

    common = _normalize_fragment_id_list(data.get("common"), context=f"{path}: common")

    workflows_raw = data.get("workflows")
    workflows: dict[str, dict[str, Any]] = {}
    if workflows_raw is not None:
        if not isinstance(workflows_raw, dict):
            raise TypeError(f"{path}: workflows must be a mapping")
        for workflow_id, entry in workflows_raw.items():
            if not isinstance(workflow_id, str) or not FRAGMENT_ID_PATTERN.match(
                workflow_id
            ):
                raise ValueError(
                    f"{path}: workflows keys must be kebab-case workflow ids, "
                    f"got {workflow_id!r}"
                )
            workflows[workflow_id] = _normalize_workflow_entry(
                entry, context=f"{path}: workflows.{workflow_id}"
            )

    return {"common": common, "workflows": workflows}


def resolve_control_plane_fragment_ids(
    fragment_map: dict[str, Any],
    *,
    workflow_id: str,
    control_plane_workflow: str,
) -> tuple[list[str], list[str], list[str]]:
    """
    Return (common_ids, workflow_ids, inner_ids) in compose order.

    Parent registry ``workflow_id`` may include a sub-feature suffix
    (``security:injection``); fragment lookup uses the parent id before the
    first ``:``.
    """
    parent_workflow_id = workflow_id.split(":", 1)[0]
    common_ids: list[str] = list(fragment_map.get("common") or [])
    workflow_ids: list[str] = []
    inner_ids: list[str] = []

    workflows = fragment_map.get("workflows") or {}
    entry = workflows.get(parent_workflow_id)
    if entry is None:
        return common_ids, workflow_ids, inner_ids

    workflow_ids = list(entry.get("fragments") or [])
    basename = control_plane_workflow.strip()
    if basename:
        inner_map = entry.get("inner-workflows") or {}
        inner_ids = list(inner_map.get(basename) or [])
    return common_ids, workflow_ids, inner_ids


def read_fragment_file(config_dir: Path, org_key: str, fragment_id: str) -> str:
    """Read one fragment file; refuse path traversal and unknown ids."""
    _require_fragment_id(fragment_id, context="fragment")
    fragments_root = (config_dir / org_key / FRAGMENTS_DIRNAME).resolve()
    path = (fragments_root / f"{fragment_id}.md").resolve()
    if fragments_root not in path.parents and path != fragments_root:
        raise ValueError(
            f"Refusing fragment path outside org fragments dir: {fragment_id}"
        )
    if not path.is_file():
        raise FileNotFoundError(
            f"Instruction fragment not found: "
            f"{org_key}/{FRAGMENTS_DIRNAME}/{fragment_id}.md"
        )
    return path.read_text(encoding="utf-8").strip()


def compose_control_plane_fragments(
    *,
    config_dir: Path | None,
    org_key: str,
    workflow_id: str,
    control_plane_workflow: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    """
    Compose control-plane fragment text and layer metadata.

    When ``config_dir`` is None or the map file is absent, returns empty text
    and empty-id layers (no behavior change for existing callers).
    """
    layers: list[dict[str, Any]] = [
        {"layer": "control-plane-common", "kind": "fragment", "ids": []},
        {"layer": "control-plane-workflow", "kind": "fragment", "ids": []},
        {
            "layer": "control-plane-inner-workflow",
            "kind": "fragment",
            "ids": [],
        },
    ]
    if config_dir is None:
        return "", layers

    fragment_map = load_instruction_fragment_map(config_dir, org_key)
    if fragment_map is None:
        return "", layers

    common_ids, workflow_ids, inner_ids = resolve_control_plane_fragment_ids(
        fragment_map,
        workflow_id=workflow_id,
        control_plane_workflow=control_plane_workflow,
    )
    layers[0]["ids"] = common_ids
    layers[1]["ids"] = workflow_ids
    layers[2]["ids"] = inner_ids

    parts: list[str] = []
    for fragment_id in common_ids + workflow_ids + inner_ids:
        text = read_fragment_file(config_dir, org_key, fragment_id)
        if text:
            parts.append(text)
    return "\n\n".join(parts), layers
