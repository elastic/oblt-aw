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
