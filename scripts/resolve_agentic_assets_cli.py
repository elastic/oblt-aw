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
GitHub Actions CLI for agentic asset resolution.

Reads workflow env vars, delegates to :func:`agentic_assets_resolver.resolve_agentic_assets`,
and writes ``GITHUB_OUTPUT``. For importable composition logic, use
``agentic_assets_resolver`` directly.

Environment:
  ENABLED_WORKFLOW_ID  Compound org-key:workflow-id (preferred; from registry resolution)
  WORKFLOW_ID          Registry workflow id when ORG_KEY is set separately
  ORG_KEY              Org key from config/<org-key>/ (default: obs)
  REPO_ROOT            Repository root (default: cwd)
  PLATFORM_ADDITIONAL_INSTRUCTIONS  Multiline platform baseline text
  PLATFORM_INPUTS_JSON JSON object of platform workflow_call inputs
  CONTROL_PLANE_CONFIG_DIR  Optional path to config/ for registry validation
  WORKFLOW_BASENAME         Basename of the calling wrapper (for inner-workflows)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from agentic_assets_resolver import resolve_agentic_assets
from common import append_multiline_github_output, write_outputs


def main() -> int:
    compound = os.environ.get("ENABLED_WORKFLOW_ID", "").strip()
    workflow_id = os.environ.get("WORKFLOW_ID", "").strip()
    org_key = os.environ.get("ORG_KEY", "obs").strip() or "obs"
    workflow_basename = os.environ.get("WORKFLOW_BASENAME", "").strip()

    if compound:
        from apm_agentic_assets import parse_compound_workflow_id

        org_key, workflow_id = parse_compound_workflow_id(compound)

    if not workflow_id:
        print("WORKFLOW_ID or ENABLED_WORKFLOW_ID is required", file=sys.stderr)
        return 1
    repo_root = Path(os.environ.get("REPO_ROOT", ".")).resolve()
    platform_text = os.environ.get("PLATFORM_ADDITIONAL_INSTRUCTIONS", "")

    platform_inputs_raw = os.environ.get("PLATFORM_INPUTS_JSON", "{}").strip()
    try:
        platform_inputs = json.loads(platform_inputs_raw or "{}")
    except json.JSONDecodeError as exc:
        print(f"PLATFORM_INPUTS_JSON is invalid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(platform_inputs, dict):
        print("PLATFORM_INPUTS_JSON must be a JSON object", file=sys.stderr)
        return 1
    if not all(isinstance(k, str) for k in platform_inputs):
        print("PLATFORM_INPUTS_JSON keys must all be strings", file=sys.stderr)
        return 1
    platform_inputs_typed: dict[str, Any] = cast(dict[str, Any], platform_inputs)

    config_dir: Path | None = None
    config_env = os.environ.get("CONTROL_PLANE_CONFIG_DIR", "").strip()
    if config_env:
        config_dir = Path(config_env).resolve()

    try:
        resolved = resolve_agentic_assets(
            repo_root=repo_root,
            workflow_id=workflow_id,
            org_key=org_key,
            platform_additional_instructions=platform_text,
            platform_inputs=platform_inputs_typed,
            config_dir=config_dir,
            workflow_basename=workflow_basename,
        )
    except (OSError, ValueError, TypeError, FileNotFoundError) as exc:
        print(
            f"agentic_assets_resolver.resolve_agentic_assets failed: {exc}",
            file=sys.stderr,
        )
        return 1

    additional = resolved["additional_instructions"]
    inputs_json = json.dumps(resolved["inputs"], ensure_ascii=False)
    setup_json = json.dumps(resolved["setup_commands"], ensure_ascii=False)
    layers_json = json.dumps(
        resolved.get("instruction_layers") or {}, ensure_ascii=False
    )

    write_outputs(
        {
            "apm-manifest-present": "true"
            if resolved["apm_manifest_present"]
            else "false",
            "apm-extension-present": (
                "true" if resolved["apm_extension_present"] else "false"
            ),
            "asset-source": str(resolved["asset_source"]),
            "resolved-inputs-json": inputs_json,
            "resolved-setup-commands-json": setup_json,
            "resolved-instruction-layers-json": layers_json,
        }
    )
    append_multiline_github_output("resolved-additional-instructions", additional)

    print(
        "Resolved agentic assets: "
        f"manifest={resolved['apm_manifest_present']} "
        f"extension={resolved['apm_extension_present']} "
        f"source={resolved['asset_source']} "
        f"workflow-basename={workflow_basename or '(none)'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
