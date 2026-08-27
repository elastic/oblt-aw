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
Importable library: compose agentic assets for one workflow invocation.

Combines control-plane instruction fragments, APM manifest assets
(``apm.yml`` / ``x-oblt-aw``), and consumer-side configuration (for example
``.oblt-aw.autodocignore``). Used by unit tests and by
``resolve_agentic_assets_cli.py`` (GitHub Actions entrypoint).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from apm_agentic_assets import resolve_apm_assets
from autodocignore import resolve_autodocignore_instructions
from instruction_fragments import compose_control_plane_fragments


def append_consumer_instructions(
    instructions: str,
    *,
    repo_root: Path,
    workflow_id: str,
) -> tuple[str, list[str]]:
    """
    Append consumer-repo instructions that are not sourced from apm.yml.

    Returns ``(text, auto_sources)`` where ``auto_sources`` lists appenders
    that contributed text (for example ``autodocignore``).
    """
    parts: list[str] = []
    auto_sources: list[str] = []
    if instructions.strip():
        parts.append(instructions.strip())

    autodocignore = resolve_autodocignore_instructions(repo_root, workflow_id)
    if autodocignore:
        parts.append(autodocignore)
        auto_sources.append("autodocignore")

    return "\n\n".join(parts), auto_sources


def resolve_agentic_assets(
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
    Resolve all agentic assets for one workflow run.

    Returns the same structure as :func:`apm_agentic_assets.resolve_apm_assets`,
    with ``additional_instructions`` extended by control-plane fragments and
    consumer-side configuration, plus ``instruction_layers`` metadata.
    """
    cp_text, cp_layers = compose_control_plane_fragments(
        config_dir=config_dir,
        org_key=org_key,
        workflow_id=workflow_id,
        control_plane_workflow=control_plane_workflow,
    )

    resolved = resolve_apm_assets(
        repo_root=repo_root,
        workflow_id=workflow_id,
        org_key=org_key,
        platform_additional_instructions=platform_additional_instructions,
        platform_inputs=platform_inputs,
        config_dir=config_dir,
        control_plane_workflow=control_plane_workflow,
    )

    apm_instructions = resolved["additional_instructions"]
    merged_parts: list[str] = []
    if cp_text.strip():
        merged_parts.append(cp_text.strip())
    if apm_instructions.strip():
        # apm_instructions already starts with platform-inline when present
        merged_parts.append(apm_instructions.strip())
    combined = "\n\n".join(merged_parts)

    combined, auto_sources = append_consumer_instructions(
        combined,
        repo_root=repo_root,
        workflow_id=workflow_id,
    )

    layers: list[dict[str, Any]] = list(cp_layers)
    layers.extend(resolved.get("instruction_layers") or [])
    layers.append(
        {"layer": "consumer-auto", "kind": "auto", "sources": auto_sources}
    )

    resolved["additional_instructions"] = combined
    resolved["instruction_layers"] = {
        "org-key": org_key,
        "workflow-id": workflow_id,
        "control-plane-workflow": control_plane_workflow,
        "layers": layers,
    }
    return resolved
