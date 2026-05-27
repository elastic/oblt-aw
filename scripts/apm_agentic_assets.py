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
Resolve agentic-workflow assets from a consumer repository ``apm.yml``.

Extension block: ``x-oblt-aw`` (see ``config/schema/apm-agentic-workflows.schema.json``).

Precedence (non-negotiable):
- If ``workflows.<workflow-id>`` is present in ``x-oblt-aw``, use that block only
  (ignore ``common`` entirely).
- Otherwise use ``common`` when present.
- Platform / control-plane inputs are merged per-key on top: APM ``inputs`` override
  platform keys; ``additional-instructions`` from APM are appended after platform text.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

OBLT_AW_EXTENSION_KEY = "x-oblt-aw"
APM_MANIFEST_NAMES = ("apm.yml", "apm.yaml")

# Keys whose values are repo-relative file paths to load as UTF-8 text.
FILE_INPUT_SUFFIX = "-file"

KNOWN_REGISTRY_IDS: dict[str, frozenset[str]] | None = None


def parse_compound_workflow_id(compound: str) -> tuple[str, str]:
    """Split ``org-key:workflow-id`` into components."""
    compound = compound.strip()
    if ":" not in compound:
        raise ValueError(
            f"enabled-workflow-id must be org-key:workflow-id, got {compound!r}"
        )
    org_key, workflow_id = compound.split(":", 1)
    if not org_key or not workflow_id:
        raise ValueError(
            f"enabled-workflow-id must be org-key:workflow-id, got {compound!r}"
        )
    return org_key, workflow_id


def load_apm_manifest(repo_root: Path) -> tuple[dict[str, Any] | None, bool]:
    """Return (parsed manifest, manifest_file_present)."""
    for name in APM_MANIFEST_NAMES:
        path = repo_root / name
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if data is None:
                return {}, True
            if not isinstance(data, dict):
                raise ValueError(f"{name} must be a YAML mapping at the top level")
            return data, True
    return None, False


def load_registry_workflow_ids(config_dir: Path, org_key: str) -> frozenset[str]:
    """Load workflow ids from ``config/<org-key>/workflow-registry.json``."""
    path = config_dir / org_key / "workflow-registry.json"
    if not path.is_file():
        return frozenset()
    data = json.loads(path.read_text(encoding="utf-8"))
    workflows = data.get("workflows", [])
    if not isinstance(workflows, list):
        return frozenset()
    ids: set[str] = set()
    for entry in workflows:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            ids.add(entry["id"])
    return frozenset(ids)


def validate_workflow_id(
    workflow_id: str,
    org_key: str,
    *,
    config_dir: Path | None,
) -> None:
    if config_dir is None:
        return
    known = load_registry_workflow_ids(config_dir, org_key)
    if known and workflow_id not in known:
        raise ValueError(
            f"workflow-id {workflow_id!r} is not listed in "
            f"{config_dir / org_key / 'workflow-registry.json'}"
        )


def select_asset_block(
    extension: dict[str, Any], workflow_id: str
) -> dict[str, Any] | None:
    """
    Pick common or workflow-specific assets.

    Workflow block wins entirely when the key exists (override semantics).
    """
    workflows = extension.get("workflows")
    if isinstance(workflows, dict) and workflow_id in workflows:
        block = workflows[workflow_id]
        if block is None:
            return {}
        if not isinstance(block, dict):
            raise ValueError(
                f"x-oblt-aw.workflows.{workflow_id} must be a mapping, "
                f"got {type(block).__name__}"
            )
        return block

    common = extension.get("common")
    if common is None:
        return None
    if not isinstance(common, dict):
        raise ValueError("x-oblt-aw.common must be a mapping")
    return common


def read_file_input(repo_root: Path, relative_path: str) -> str:
    path = (repo_root / relative_path).resolve()
    root = repo_root.resolve()
    if root not in path.parents and path != root:
        raise ValueError(f"Refusing path outside repository: {relative_path}")
    if not path.is_file():
        raise FileNotFoundError(f"Asset file not found: {relative_path}")
    return path.read_text(encoding="utf-8")


def materialize_inputs(
    repo_root: Path,
    raw_inputs: Any,
) -> dict[str, Any]:
    if raw_inputs is None:
        return {}
    if not isinstance(raw_inputs, dict):
        raise ValueError("inputs must be a mapping of workflow input names to values")

    out: dict[str, Any] = {}
    for key, value in raw_inputs.items():
        if not isinstance(key, str):
            raise ValueError("input keys must be strings")
        if key.endswith(FILE_INPUT_SUFFIX) and isinstance(value, str):
            text_key = key[: -len(FILE_INPUT_SUFFIX)]
            out[text_key] = read_file_input(repo_root, value)
        else:
            out[key] = value
    return out


def extract_setup_commands(block: dict[str, Any]) -> list[str]:
    commands = block.get("setup-commands")
    if commands is None:
        return []
    if not isinstance(commands, list):
        raise ValueError("setup-commands must be a list of strings")
    normalized: list[str] = []
    for item in commands:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("setup-commands entries must be non-empty strings")
        normalized.append(item)
    return normalized


def compose_additional_instructions(
    platform_text: str,
    apm_inputs: dict[str, Any],
) -> str:
    parts: list[str] = []
    platform = platform_text.strip()
    if platform:
        parts.append(platform)

    apm_text = apm_inputs.get("additional-instructions")
    if isinstance(apm_text, str) and apm_text.strip():
        parts.append(apm_text.strip())

    return "\n\n".join(parts)


def merge_platform_and_apm_inputs(
    platform_inputs: dict[str, Any],
    apm_inputs: dict[str, Any],
) -> dict[str, Any]:
    """Per-key override: APM inputs replace platform keys."""
    merged = dict(platform_inputs)
    for key, value in apm_inputs.items():
        if key == "additional-instructions":
            continue
        merged[key] = value
    return merged


def resolve_agentic_assets(
    *,
    repo_root: Path,
    workflow_id: str,
    org_key: str,
    platform_additional_instructions: str = "",
    platform_inputs: dict[str, Any] | None = None,
    config_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Resolve assets for one agentic workflow run.

    Returns a dict with keys:
    - apm_manifest_present (bool)
    - apm_extension_present (bool)
    - asset_source (str): none | common | workflow
    - additional_instructions (str)
    - inputs (dict)
    - setup_commands (list[str])
    """
    validate_workflow_id(workflow_id, org_key, config_dir=config_dir)
    platform_inputs = platform_inputs or {}

    manifest, manifest_present = load_apm_manifest(repo_root)
    if not manifest_present or manifest is None:
        return {
            "apm_manifest_present": False,
            "apm_extension_present": False,
            "asset_source": "none",
            "additional_instructions": compose_additional_instructions(
                platform_additional_instructions, {}
            ),
            "inputs": dict(platform_inputs),
            "setup_commands": [],
        }

    extension = manifest.get(OBLT_AW_EXTENSION_KEY)
    if extension is None:
        return {
            "apm_manifest_present": True,
            "apm_extension_present": False,
            "asset_source": "none",
            "additional_instructions": compose_additional_instructions(
                platform_additional_instructions, {}
            ),
            "inputs": dict(platform_inputs),
            "setup_commands": [],
        }

    if not isinstance(extension, dict):
        raise ValueError(f"{OBLT_AW_EXTENSION_KEY} must be a mapping")

    block = select_asset_block(extension, workflow_id)
    if block is None:
        return {
            "apm_manifest_present": True,
            "apm_extension_present": True,
            "asset_source": "none",
            "additional_instructions": compose_additional_instructions(
                platform_additional_instructions, {}
            ),
            "inputs": dict(platform_inputs),
            "setup_commands": [],
        }

    asset_source = (
        "workflow"
        if isinstance(extension.get("workflows"), dict)
        and workflow_id in extension["workflows"]
        else "common"
    )

    apm_inputs = materialize_inputs(repo_root, block.get("inputs"))
    setup_commands = extract_setup_commands(block)

    merged_inputs = merge_platform_and_apm_inputs(platform_inputs, apm_inputs)
    additional = compose_additional_instructions(
        platform_additional_instructions, apm_inputs
    )

    return {
        "apm_manifest_present": True,
        "apm_extension_present": True,
        "asset_source": asset_source,
        "additional_instructions": additional,
        "inputs": merged_inputs,
        "setup_commands": setup_commands,
    }
