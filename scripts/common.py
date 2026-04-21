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
Shared utilities for workflow scripts.

Provides write_outputs and parse_repositories used by build_repos_matrix
and build_target_operations.

Multi-org control plane: org keys are directory names under ``config/<org-key>/``;
dashboard markers use ``<!-- oblt-aw:<org-key>:<workflow-id> -->``; ingress and
``enabled-workflows`` use compound ids ``org-key:workflow-id``.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path

# Default org for legacy two-part markers ``<!-- oblt-aw:<workflow-id> -->``.
LEGACY_DEFAULT_ORG_KEY = "obs"

# Subdirectories of ``config/`` that are never org roots (JSON Schema, etc.).
RESERVED_CONFIG_DIR_NAMES: frozenset[str] = frozenset({"schema"})


def write_outputs(values: dict[str, str]) -> None:
    """Write key=value pairs to GITHUB_OUTPUT."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if not github_output:
        raise SystemExit("GITHUB_OUTPUT is not set")

    with open(github_output, "a", encoding="utf-8") as output_file:
        for key, value in values.items():
            output_file.write(f"{key}={value}\n")


def append_multiline_github_output(name: str, value: str) -> None:
    """Write a multiline value to GITHUB_OUTPUT using a random delimiter."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if not github_output:
        raise SystemExit("GITHUB_OUTPUT is not set")
    delimiter = secrets.token_urlsafe(24)
    with open(github_output, "a", encoding="utf-8") as output_file:
        output_file.write(f"{name}<<{delimiter}\n")
        output_file.write(value)
        if not value.endswith("\n"):
            output_file.write("\n")
        output_file.write(f"{delimiter}\n")


def parse_repositories(content: str) -> list[str]:
    """Parse active-repositories.json content into a list of owner/repo strings."""
    data = json.loads(content) if content else {"repositories": []}
    if isinstance(data, dict):
        repositories = data.get("repositories", [])
    elif isinstance(data, list):
        repositories = data
    else:
        raise SystemExit(
            "active-repositories.json must be a list or object with 'repositories'"
        )
    if not isinstance(repositories, list):
        raise SystemExit("`repositories` must be a list")
    normalized = []
    for item in repositories:
        if not isinstance(item, str) or "/" not in item:
            raise SystemExit(
                f"Invalid repository entry: {item!r}. Expected 'owner/repo'"
            )
        normalized.append(item.strip())
    return sorted(set(normalized))


def discover_org_config_dirs(config_dir: Path) -> list[Path]:
    """
    Return sorted org root directories under ``config_dir`` (direct children only).

    An org root contains both ``workflow-registry.json`` and
    ``active-repositories.json``. Names in :data:`RESERVED_CONFIG_DIR_NAMES` are
    skipped.
    """
    if not config_dir.is_dir():
        return []
    roots: list[Path] = []
    for child in sorted(config_dir.iterdir()):
        if child.name in RESERVED_CONFIG_DIR_NAMES:
            continue
        if not child.is_dir():
            continue
        if (child / "workflow-registry.json").is_file() and (
            child / "active-repositories.json"
        ).is_file():
            roots.append(child)
    return roots


def discover_org_keys_sorted(config_dir: Path) -> list[str]:
    """Sorted org keys (directory names) under ``config_dir``."""
    return [p.name for p in discover_org_config_dirs(config_dir)]


def format_oblt_aw_marker(org_key: str, workflow_id: str) -> str:
    """HTML comment marker for a task-list checkbox line (no surrounding whitespace)."""
    return f"<!-- oblt-aw:{org_key}:{workflow_id} -->"


def compound_workflow_key(org_key: str, workflow_id: str) -> str:
    """Canonical ``org:workflow-id`` string for ingress and ``enabled-workflows``."""
    return f"{org_key}:{workflow_id}"


def enabled_compound_ids_from_dashboard_body(body: str) -> list[str]:
    """
    Collect enabled workflow compound ids from dashboard issue body.

    Parses ``- [x]`` lines with ``<!-- oblt-aw:<org>:<workflow-id> -->`` or legacy
    ``<!-- oblt-aw:<workflow-id> -->`` (treated as ``obs:<workflow-id>``).
    Order is first-seen; duplicates are skipped.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for line in body.splitlines():
        m3 = re.match(r"^- \[x\] <!-- oblt-aw:([a-z0-9-]+):([a-z0-9-]+) -->", line)
        if m3:
            key = compound_workflow_key(m3.group(1), m3.group(2))
            if key not in seen:
                seen.add(key)
                ordered.append(key)
            continue
        m2 = re.match(r"^- \[x\] <!-- oblt-aw:([a-z0-9-]+) -->", line)
        if m2:
            key = compound_workflow_key(LEGACY_DEFAULT_ORG_KEY, m2.group(1))
            if key not in seen:
                seen.add(key)
                ordered.append(key)
    return ordered


def merge_active_repositories_from_org_trees(config_dir: Path) -> list[str]:
    """
    Union of repositories listed in each org's ``active-repositories.json`` under
    ``config_dir`` (see :func:`discover_org_config_dirs`).
    """
    merged: set[str] = set()
    for org_dir in discover_org_config_dirs(config_dir):
        path = org_dir / "active-repositories.json"
        merged.update(parse_repositories(path.read_text(encoding="utf-8")))
    return sorted(merged)
