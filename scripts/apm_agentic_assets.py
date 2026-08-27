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

Structure (non-negotiable):
- Top-level ``version`` plus one mapping per org key (e.g. ``obs``, ``docs``).
- Each org block **must** include ``common`` and may include ``workflows``.
- Optional org-level ``fragments`` maps local ids to repo-relative Markdown paths.
- Optional ``inner-workflows.<basename>`` under a workflow block selects assets for one
  control-plane wrapper when several wrappers share a registry workflow id.

Precedence within the org block for the running ``org-key``:
- If ``workflows.<workflow-id>.inner-workflows.<basename>`` exists, use that block only.
- Else if ``workflows.<workflow-id>`` is present, use that block only (ignore ``common``).
  The ``inner-workflows`` key on the parent is structural and is not instruction content.
- Otherwise use ``common``.
- Platform / control-plane inputs are merged per-key on top: APM ``inputs`` override
  platform keys; consumer fragments then inline ``additional-instructions`` append after
  platform text.

``setup-commands`` accepts inline shell (string, list, or multiline block) and optional
``setup-commands-file`` (one command per line). Entries may be script paths or shell.
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
    global KNOWN_REGISTRY_IDS
    if KNOWN_REGISTRY_IDS is None:
        KNOWN_REGISTRY_IDS = {}

    cache_key = f"{config_dir.resolve()}:{org_key}"
    cached = KNOWN_REGISTRY_IDS.get(cache_key)
    if cached is not None:
        return cached

    path = config_dir / org_key / "workflow-registry.json"
    if not path.is_file():
        known: frozenset[str] = frozenset()
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        workflows = data.get("workflows", [])
        if not isinstance(workflows, list):
            known = frozenset()
        else:
            ids: set[str] = set()
            for entry in workflows:
                if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                    ids.add(entry["id"])
            known = frozenset(ids)

    KNOWN_REGISTRY_IDS[cache_key] = known
    return known


def parent_registry_workflow_id(workflow_id: str) -> str:
    """Strip sub-feature suffix from a compound-derived workflow id."""
    return workflow_id.split(":", 1)[0]


def validate_workflow_id(
    workflow_id: str,
    org_key: str,
    *,
    config_dir: Path | None,
) -> None:
    if config_dir is None:
        return
    known = load_registry_workflow_ids(config_dir, org_key)
    registry_id = parent_registry_workflow_id(workflow_id)
    if known and registry_id not in known:
        raise ValueError(
            f"workflow-id {registry_id!r} is not listed in "
            f"{config_dir / org_key / 'workflow-registry.json'}"
        )


def reject_legacy_flat_extension(extension: dict[str, Any]) -> None:
    """Reject pre–multi-org flat ``common`` / ``workflows`` at the extension root."""
    if "common" in extension or "workflows" in extension:
        raise ValueError(
            f"{OBLT_AW_EXTENSION_KEY} must nest assets under org keys (e.g. obs, docs); "
            "top-level common/workflows are no longer supported"
        )


def extract_org_extension(
    extension: dict[str, Any], org_key: str
) -> dict[str, Any] | None:
    """Return the org-scoped block (``common`` + optional ``workflows``) or None."""
    reject_legacy_flat_extension(extension)
    org_block = extension.get(org_key)
    if org_block is None:
        return None
    if not isinstance(org_block, dict):
        raise ValueError(
            f"{OBLT_AW_EXTENSION_KEY}.{org_key} must be a mapping, "
            f"got {type(org_block).__name__}"
        )
    return org_block


def select_asset_block(
    org_extension: dict[str, Any],
    workflow_id: str,
    *,
    org_key: str,
    control_plane_workflow: str = "",
) -> tuple[dict[str, Any] | None, str]:
    """
    Pick common, workflow, or inner-workflow assets for one org.

    Returns ``(block, asset_source)`` where ``asset_source`` is one of
    ``none``, ``common``, ``workflow``, or ``inner-workflow``.
    Override semantics: the selected grain replaces coarser grains entirely.
    """
    prefix = f"{OBLT_AW_EXTENSION_KEY}.{org_key}"
    registry_workflow_id = parent_registry_workflow_id(workflow_id)
    basename = control_plane_workflow.strip()
    workflows = org_extension.get("workflows")

    if isinstance(workflows, dict) and registry_workflow_id in workflows:
        block = workflows[registry_workflow_id]
        if block is None:
            return {}, "workflow"
        if not isinstance(block, dict):
            raise ValueError(
                f"{prefix}.workflows.{registry_workflow_id} must be a mapping, "
                f"got {type(block).__name__}"
            )

        inner = block.get("inner-workflows")
        if basename and isinstance(inner, dict) and basename in inner:
            inner_block = inner[basename]
            if inner_block is None:
                return {}, "inner-workflow"
            if not isinstance(inner_block, dict):
                raise ValueError(
                    f"{prefix}.workflows.{registry_workflow_id}."
                    f"inner-workflows.{basename} must be a mapping, "
                    f"got {type(inner_block).__name__}"
                )
            return inner_block, "inner-workflow"

        return block, "workflow"

    common = org_extension.get("common")
    if common is None:
        return None, "none"
    if not isinstance(common, dict):
        raise ValueError(f"{prefix}.common must be a mapping")
    return common, "common"


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


def _expand_setup_command_lines(text: str) -> list[str]:
    """Split multiline inline setup text into individual shell commands."""
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def _normalize_setup_commands_value(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return _expand_setup_command_lines(value)
    if isinstance(value, list):
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{field} entries must be non-empty strings")
            normalized.extend(_expand_setup_command_lines(item))
        return normalized
    raise ValueError(f"{field} must be a string or a list of strings")


def extract_setup_commands(block: dict[str, Any], *, repo_root: Path) -> list[str]:
    """
    Resolve setup shell commands from an asset block.

    Supports:
    - ``setup-commands``: inline shell (string or list of strings; multiline strings
      split into one command per non-empty, non-comment line)
    - ``setup-commands-file``: repo-relative path to a file with one command per line
    """
    commands = _normalize_setup_commands_value(
        block.get("setup-commands"), field="setup-commands"
    )

    commands_file = block.get("setup-commands-file")
    if commands_file is None:
        return commands
    if not isinstance(commands_file, str) or not commands_file.strip():
        raise ValueError("setup-commands-file must be a non-empty string path")
    file_text = read_file_input(repo_root, commands_file.strip())
    commands.extend(_expand_setup_command_lines(file_text))
    return commands


def _normalize_fragment_id_list(raw: Any, *, field: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{field} must be an array of fragment ids")
    out: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field}[{index}] must be a non-empty string")
        out.append(item.strip())
    return out


def materialize_consumer_fragments(
    *,
    repo_root: Path,
    org_extension: dict[str, Any],
    fragment_ids: list[str],
    org_key: str,
) -> str:
    """Resolve ``additional-instructions-fragments`` via the org ``fragments`` map."""
    if not fragment_ids:
        return ""
    fragments_map = org_extension.get("fragments")
    if fragments_map is None:
        raise ValueError(
            f"{OBLT_AW_EXTENSION_KEY}.{org_key}.fragments is required when "
            "additional-instructions-fragments is set"
        )
    if not isinstance(fragments_map, dict):
        raise ValueError(
            f"{OBLT_AW_EXTENSION_KEY}.{org_key}.fragments must be a mapping"
        )

    parts: list[str] = []
    for fragment_id in fragment_ids:
        if fragment_id not in fragments_map:
            raise ValueError(
                f"Unknown fragment id {fragment_id!r} in "
                f"{OBLT_AW_EXTENSION_KEY}.{org_key}.fragments"
            )
        rel = fragments_map[fragment_id]
        if not isinstance(rel, str) or not rel.strip():
            raise ValueError(
                f"{OBLT_AW_EXTENSION_KEY}.{org_key}.fragments.{fragment_id} "
                "must be a non-empty repo-relative path"
            )
        text = read_file_input(repo_root, rel.strip()).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def compose_additional_instructions(
    platform_text: str,
    *,
    consumer_fragments_text: str = "",
    apm_inputs: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Join platform text, consumer fragments, then consumer inline instructions.

    Returns ``(text, consumer_instruction_layers)``.
    """
    apm_inputs = apm_inputs or {}
    parts: list[str] = []
    layers: list[dict[str, Any]] = []

    platform = platform_text.strip()
    layers.append(
        {"layer": "platform-inline", "kind": "inline", "present": bool(platform)}
    )
    if platform:
        parts.append(platform)

    fragment_text = consumer_fragments_text.strip()
    # ids are recorded by the caller; here we only note whether text was present
    layers.append(
        {
            "layer": "consumer-fragments",
            "kind": "fragment",
            "ids": [],
            "present": bool(fragment_text),
        }
    )
    if fragment_text:
        parts.append(fragment_text)

    apm_text = apm_inputs.get("additional-instructions")
    inline = apm_text.strip() if isinstance(apm_text, str) else ""
    layers.append(
        {"layer": "consumer-inline", "kind": "inline", "present": bool(inline)}
    )
    if inline:
        parts.append(inline)

    return "\n\n".join(parts), layers


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


def resolve_apm_assets(
    *,
    repo_root: Path,
    workflow_id: str,
    org_key: str,
    platform_additional_instructions: str = "",
    platform_inputs: dict[str, Any] | None = None,
    config_dir: Path | None = None,
    control_plane_workflow: str = "",
) -> dict[str, Any]:
    """
    Resolve APM assets from ``apm.yml`` for one agentic workflow run.

    Returns a dict with keys:
    - apm_manifest_present (bool)
    - apm_extension_present (bool)
    - asset_source (str): none | common | workflow | inner-workflow
    - additional_instructions (str)
    - inputs (dict)
    - setup_commands (list[str])
    - instruction_layers (list[dict]): consumer fragment/inline layers
    """
    validate_workflow_id(workflow_id, org_key, config_dir=config_dir)
    platform_inputs = platform_inputs or {}

    def _platform_only(*, manifest_present: bool, extension_present: bool) -> dict[str, Any]:
        additional, layers = compose_additional_instructions(
            platform_additional_instructions
        )
        return {
            "apm_manifest_present": manifest_present,
            "apm_extension_present": extension_present,
            "asset_source": "none",
            "additional_instructions": additional,
            "inputs": dict(platform_inputs),
            "setup_commands": [],
            "instruction_layers": layers,
        }

    manifest, manifest_present = load_apm_manifest(repo_root)
    if not manifest_present or manifest is None:
        return _platform_only(manifest_present=False, extension_present=False)

    extension = manifest.get(OBLT_AW_EXTENSION_KEY)
    if extension is None:
        return _platform_only(manifest_present=True, extension_present=False)

    if not isinstance(extension, dict):
        raise ValueError(f"{OBLT_AW_EXTENSION_KEY} must be a mapping")

    org_extension = extract_org_extension(extension, org_key)
    if org_extension is None:
        return _platform_only(manifest_present=True, extension_present=True)

    block, asset_source = select_asset_block(
        org_extension,
        workflow_id,
        org_key=org_key,
        control_plane_workflow=control_plane_workflow,
    )
    if block is None:
        return _platform_only(manifest_present=True, extension_present=True)

    fragment_ids = _normalize_fragment_id_list(
        block.get("additional-instructions-fragments"),
        field="additional-instructions-fragments",
    )
    consumer_fragments = materialize_consumer_fragments(
        repo_root=repo_root,
        org_extension=org_extension,
        fragment_ids=fragment_ids,
        org_key=org_key,
    )

    apm_inputs = materialize_inputs(repo_root, block.get("inputs"))
    setup_commands = extract_setup_commands(block, repo_root=repo_root)

    merged_inputs = merge_platform_and_apm_inputs(platform_inputs, apm_inputs)
    additional, layers = compose_additional_instructions(
        platform_additional_instructions,
        consumer_fragments_text=consumer_fragments,
        apm_inputs=apm_inputs,
    )
    # Attach resolved consumer fragment ids to the fragments layer entry.
    for layer in layers:
        if layer.get("layer") == "consumer-fragments":
            layer["ids"] = fragment_ids

    return {
        "apm_manifest_present": True,
        "apm_extension_present": True,
        "asset_source": asset_source,
        "additional_instructions": additional,
        "inputs": merged_inputs,
        "setup_commands": setup_commands,
        "instruction_layers": layers,
    }
