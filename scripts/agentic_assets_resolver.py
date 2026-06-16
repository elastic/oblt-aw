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
Orchestrate agentic asset resolution for one workflow invocation.

Composes APM manifest assets (``apm.yml`` / ``x-oblt-aw``) with workflow-specific
consumer configuration files (for example ``.oblt-aw.autodocignore``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from apm_agentic_assets import resolve_apm_assets
from autodocignore import resolve_autodocignore_instructions


def append_consumer_instructions(
    instructions: str,
    *,
    repo_root: Path,
    workflow_id: str,
) -> str:
    """Append consumer-repo instructions that are not sourced from apm.yml."""
    parts: list[str] = []
    if instructions.strip():
        parts.append(instructions.strip())

    autodocignore = resolve_autodocignore_instructions(repo_root, workflow_id)
    if autodocignore:
        parts.append(autodocignore)

    return "\n\n".join(parts)


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
    Resolve all agentic assets for one workflow run.

    Returns the same structure as :func:`apm_agentic_assets.resolve_apm_assets`,
    with ``additional_instructions`` extended by consumer-side configuration.
    """
    resolved = resolve_apm_assets(
        repo_root=repo_root,
        workflow_id=workflow_id,
        org_key=org_key,
        platform_additional_instructions=platform_additional_instructions,
        platform_inputs=platform_inputs,
        config_dir=config_dir,
    )
    resolved["additional_instructions"] = append_consumer_instructions(
        resolved["additional_instructions"],
        repo_root=repo_root,
        workflow_id=workflow_id,
    )
    return resolved
