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
Ingress dispatch metadata from per-org workflow-registry.json.

Each ``workflows[]`` entry declares one dashboard ``id`` and an ``ingress_routes``
array of objects. Each object may include ``id``, ``workflow_file``, and
``allowed_bot_users_from``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

AllowedBotUsersFrom = Literal["", "allowed-pr", "allowed-issue"]
ALLOWED_BOT_USERS_FROM_VALUES: frozenset[str] = frozenset(
    {"", "allowed-pr", "allowed-issue"}
)


class RegistryParseError(ValueError):
    """Invalid workflow-registry.json route config metadata."""


@dataclass(frozen=True)
class IngressRouteSpec:
    route_id: str
    workflow_file: str
    allowed_bot_users_from: AllowedBotUsersFrom = ""
    registry_workflow_id: str = ""


ORG_WORKFLOW_PREFIX = {
    "obs": "oblt-aw",
    "docs": "docs-aw",
}


def default_workflow_file(route_id: str, org_key: str = "obs") -> str:
    """Default naming contract when workflow_file is omitted in the registry."""
    prefix = ORG_WORKFLOW_PREFIX.get(org_key, f"{org_key}-aw")
    return f"{prefix}-{route_id}.yml"


def _normalize_route_entry(entry: object, *, context: str) -> dict[str, object]:
    if not isinstance(entry, dict):
        raise RegistryParseError(f"{context} must be an object")
    return entry


def _parse_route_config_entry(
    entry: object,
    *,
    context: str,
    org_key: str,
    registry_workflow_id: str,
) -> IngressRouteSpec:
    normalized = _normalize_route_entry(entry, context=context)

    route_id = normalized.get("id")
    if not isinstance(route_id, str) or not route_id:
        raise RegistryParseError(f"{context} requires string 'id'")

    workflow_file = normalized.get("workflow_file")
    if workflow_file is None:
        workflow_file = default_workflow_file(route_id, org_key)
    elif not isinstance(workflow_file, str) or not workflow_file.strip():
        raise RegistryParseError(f"{context}.workflow_file must be a non-empty string")

    allowed_raw = normalized.get("allowed_bot_users_from", "")
    if allowed_raw is None:
        allowed_raw = ""
    if not isinstance(allowed_raw, str):
        raise RegistryParseError(f"{context}.allowed_bot_users_from must be a string")
    if allowed_raw not in ALLOWED_BOT_USERS_FROM_VALUES:
        raise RegistryParseError(
            f"{context}.allowed_bot_users_from must be one of "
            f"{sorted(ALLOWED_BOT_USERS_FROM_VALUES)!r}, got {allowed_raw!r}"
        )

    return IngressRouteSpec(
        route_id=route_id,
        workflow_file=workflow_file,
        allowed_bot_users_from=allowed_raw,  # type: ignore[arg-type]
    )


def parse_workflow_ingress_routes(
    workflow: dict[str, object],
    *,
    org_key: str,
    context: str,
) -> list[IngressRouteSpec]:
    """Resolve ingress route specs from one ``workflows[]`` registry entry."""
    registry_workflow_id = workflow.get("id")
    if not isinstance(registry_workflow_id, str) or not registry_workflow_id:
        raise RegistryParseError(f"{context} requires string 'id'")

    if workflow.get("control_plane_workflows") is not None:
        raise RegistryParseError(
            f"{context}: remove deprecated 'control_plane_workflows'; "
            "control-plane workflow files are derived from 'ingress_routes'"
        )
    if workflow.get("config") is not None:
        raise RegistryParseError(
            f"{context}: rename deprecated 'config' to 'ingress_routes'"
        )

    routes = workflow.get("ingress_routes")
    if routes is None:
        raise RegistryParseError(f"{context} missing required 'ingress_routes' array")
    if not isinstance(routes, list) or not routes:
        raise RegistryParseError(f"{context}.ingress_routes must be a non-empty array")

    specs: list[IngressRouteSpec] = []
    seen_route_ids: set[str] = set()
    for route_index, entry in enumerate(routes):
        route_context = f"{context}.ingress_routes[{route_index}]"
        spec = _parse_route_config_entry(
            entry,
            context=route_context,
            org_key=org_key,
            registry_workflow_id=registry_workflow_id,
        )
        if spec.route_id in seen_route_ids:
            raise RegistryParseError(
                f"{route_context}: duplicate route id {spec.route_id!r}"
            )
        seen_route_ids.add(spec.route_id)
        specs.append(
            IngressRouteSpec(
                route_id=spec.route_id,
                workflow_file=spec.workflow_file,
                allowed_bot_users_from=spec.allowed_bot_users_from,
                registry_workflow_id=registry_workflow_id,
            )
        )
    return specs


def load_ingress_route_specs(registry_path: Path) -> dict[str, IngressRouteSpec]:
    """Flatten ``workflows[].ingress_routes`` from a workflow-registry.json file."""
    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    workflows = raw.get("workflows")
    if not isinstance(workflows, list):
        raise SystemExit(f"{registry_path}: 'workflows' must be a JSON array")

    org_key = registry_path.parent.name
    specs: dict[str, IngressRouteSpec] = {}
    for wf_index, workflow in enumerate(workflows):
        if not isinstance(workflow, dict):
            raise SystemExit(
                f"{registry_path}: workflows[{wf_index}] must be an object"
            )
        context = f"{registry_path}: workflows[{wf_index}]"
        try:
            route_specs = parse_workflow_ingress_routes(
                workflow,
                org_key=org_key,
                context=context,
            )
        except RegistryParseError as exc:
            raise SystemExit(str(exc)) from exc

        for spec in route_specs:
            if spec.route_id in specs:
                raise SystemExit(
                    f"{registry_path}: duplicate ingress route id '{spec.route_id}'"
                )
            specs[spec.route_id] = spec

    if raw.get("ingress_routes") is not None:
        raise SystemExit(
            f"{registry_path}: top-level 'ingress_routes' is deprecated; "
            "use workflows[].ingress_routes instead"
        )

    return specs


def validate_all_org_registries(config_dir: Path) -> None:
    """Ensure each org workflow-registry.json defines workflows[].ingress_routes."""
    for org_key in ORG_WORKFLOW_PREFIX:
        load_ingress_route_specs(config_dir / org_key / "workflow-registry.json")


ROUTE_JOB_PATTERN = re.compile(r"^\s+route-([\w-]+):\s*$", re.MULTILINE)
ROUTE_JOB_BLOCK_PATTERN = re.compile(
    r"^  route-([\w-]+):\n(.*?)(?=^  \S|\Z)",
    re.MULTILINE | re.DOTALL,
)
PERMISSION_SCOPE_PATTERN = re.compile(
    r"^      ([a-z0-9-]+): (read|write|none)\s*$", re.MULTILINE
)

_PERMISSION_LEVELS: dict[str, int] = {"none": 0, "read": 1, "write": 2}


def _parse_permissions_blocks(workflow_text: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    in_block = False
    current: dict[str, str] = {}
    for line in workflow_text.splitlines():
        if re.match(r"^\s+permissions:\s*$", line):
            in_block = True
            current = {}
            continue
        if in_block:
            match = re.match(r"^\s+([a-z0-9-]+):\s*(read|write|none)\s*$", line)
            if match:
                current[match.group(1)] = match.group(2)
                continue
            if line.strip() and not re.match(r"^\s{6,}", line):
                in_block = False
                if current:
                    blocks.append(current)
                current = {}
    if in_block and current:
        blocks.append(current)
    return blocks


def max_job_permissions(workflow_path: Path) -> dict[str, str]:
    """Union of the highest scope per key across all job permissions blocks."""
    merged: dict[str, str] = {}
    for block in _parse_permissions_blocks(workflow_path.read_text(encoding="utf-8")):
        for scope, level in block.items():
            if (
                scope not in merged
                or _PERMISSION_LEVELS[level] > _PERMISSION_LEVELS[merged[scope]]
            ):
                merged[scope] = level
    return merged


def parse_route_job_permissions(
    ingress_text: str, route_id: str
) -> dict[str, str] | None:
    """Return permissions for route-{route_id}, or None when the block omits it."""
    for match in ROUTE_JOB_BLOCK_PATTERN.finditer(ingress_text):
        if match.group(1) != route_id:
            continue
        scopes = PERMISSION_SCOPE_PATTERN.findall(match.group(2))
        if not scopes:
            return None
        return dict(scopes)
    raise RegistryParseError(f"route-{route_id} job not found in ingress workflow")


def format_route_job_permissions(permissions: dict[str, str]) -> str:
    lines = ["    permissions:"]
    for scope in sorted(permissions):
        lines.append(f"      {scope}: {permissions[scope]}")
    return "\n".join(lines)


def union_permissions(
    permission_maps: list[dict[str, str]],
) -> dict[str, str]:
    merged: dict[str, str] = {}
    for permission_map in permission_maps:
        for scope, level in permission_map.items():
            if (
                scope not in merged
                or _PERMISSION_LEVELS[level] > _PERMISSION_LEVELS[merged[scope]]
            ):
                merged[scope] = level
    return merged


def _permissions_cover(
    actual: dict[str, str] | None, required: dict[str, str]
) -> list[str]:
    if actual is None:
        return [f"missing job permissions (need {required})"]
    errors: list[str] = []
    for scope, required_level in sorted(required.items()):
        actual_level = actual.get(scope)
        if actual_level is None:
            errors.append(f"missing scope {scope!r} (need {required_level})")
            continue
        if _PERMISSION_LEVELS[actual_level] < _PERMISSION_LEVELS[required_level]:
            errors.append(f"{scope}: {actual_level} is below required {required_level}")
    return errors


def validate_ingress_route_job_permissions(
    ingress_path: Path,
    *,
    specs: dict[str, IngressRouteSpec],
    workflows_dir: Path,
) -> None:
    """Route jobs must declare permissions covering each routed workflow."""
    ingress_text = ingress_path.read_text(encoding="utf-8")
    for route_id, spec in sorted(specs.items()):
        required = max_job_permissions(workflows_dir / spec.workflow_file)
        if not required:
            continue
        actual = parse_route_job_permissions(ingress_text, route_id)
        errors = _permissions_cover(actual, required)
        if errors:
            raise SystemExit(
                f"{ingress_path.name} route-{route_id}: " + "; ".join(errors)
            )


def load_ingress_route_job_ids(ingress_path: Path) -> list[str]:
    """Extract route ids from oblt-aw-ingress.yml route-* reusable jobs."""
    text = ingress_path.read_text(encoding="utf-8")
    return ROUTE_JOB_PATTERN.findall(text)


def validate_org_ingress_registry(
    org_key: str,
    *,
    config_dir: Path,
    workflows_dir: Path,
    ingress_path: Path,
) -> None:
    """Org registry ingress_routes must match ingress route-* jobs and workflow files."""
    registry_path = config_dir / org_key / "workflow-registry.json"
    specs = load_ingress_route_specs(registry_path)
    ingress_route_ids = load_ingress_route_job_ids(ingress_path)

    missing_specs = [rid for rid in ingress_route_ids if rid not in specs]
    if missing_specs:
        raise SystemExit(
            f"config/{org_key}/workflow-registry.json ingress_routes missing ids: "
            + ", ".join(missing_specs)
        )

    extra_specs = [rid for rid in specs if rid not in ingress_route_ids]
    if extra_specs:
        raise SystemExit(
            f"ingress_routes ids without route-* job in {ingress_path.name}: "
            + ", ".join(extra_specs)
        )

    missing_files = [
        spec.workflow_file
        for spec in specs.values()
        if not (workflows_dir / spec.workflow_file).is_file()
    ]
    if missing_files:
        raise SystemExit(
            "Missing .github/workflows file(s) referenced by ingress_routes: "
            + ", ".join(sorted(set(missing_files)))
        )

    validate_ingress_route_job_permissions(
        ingress_path,
        specs=specs,
        workflows_dir=workflows_dir,
    )


def validate_obs_ingress_registry(
    *,
    config_dir: Path,
    workflows_dir: Path,
    ingress_path: Path,
) -> None:
    """Obs registry ingress_routes must match ingress route-* jobs and workflow files."""
    validate_org_ingress_registry(
        "obs",
        config_dir=config_dir,
        workflows_dir=workflows_dir,
        ingress_path=ingress_path,
    )


def validate_docs_ingress_registry(
    *,
    config_dir: Path,
    workflows_dir: Path,
    ingress_path: Path,
) -> None:
    """Docs registry ingress_routes must match ingress route-* jobs and workflow files."""
    validate_org_ingress_registry(
        "docs",
        config_dir=config_dir,
        workflows_dir=workflows_dir,
        ingress_path=ingress_path,
    )
