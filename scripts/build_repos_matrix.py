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
Build a matrix of repositories from org ``active-repositories.json`` files for workflow use.

Unions ``config/<org-key>/active-repositories.json`` for each discovered org tree, then writes
to GITHUB_OUTPUT:

- repos: JSON array of {"repository": "owner/repo", "workflow-token-policy": "..."} for matrix strategy
  (``workflow-token-policy`` is empty when not configured in active-repositories.json)
- has_repos: "true" or "false"
- repos_count: number of repositories

When ``--org-key`` (or ``ORG_KEY``) is set, only that org tree is included, plus any temporary
alias org keys folded into that entrypoint (see ``CONTROL_PLANE_ORG_KEY_ALIASES``).

Related issue: https://github.com/elastic/observability-robots/issues/3732
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from common import (
    CONTROL_PLANE_ORG_KEY_ALIASES,
    discover_org_keys_sorted,
    merge_active_repositories_from_org_trees,
    merge_repository_workflow_token_policies_from_org_trees,
    parse_repositories,
    write_outputs,
)


def resolve_org_keys_for_entrypoint(org_key: str, config_dir: Path) -> list[str]:
    """Return sorted config org-keys handled by a control-plane entrypoint."""
    known = set(discover_org_keys_sorted(config_dir))
    if org_key not in known and org_key not in CONTROL_PLANE_ORG_KEY_ALIASES:
        raise SystemExit(
            f"Unknown org-key {org_key!r}; known: {sorted(known) or '(none)'}"
        )
    keys = {org_key}
    keys.update(
        alias
        for alias in CONTROL_PLANE_ORG_KEY_ALIASES.get(org_key, ())
        if alias in known
    )
    return sorted(keys)


def repositories_for_org_keys(config_dir: Path, org_keys: list[str]) -> list[str]:
    """Union of active repositories for the given org-keys only."""
    merged: set[str] = set()
    for key in org_keys:
        path = config_dir / key / "active-repositories.json"
        if not path.is_file():
            raise SystemExit(f"Missing active-repositories.json for org-key {key!r}")
        merged.update(parse_repositories(path.read_text(encoding="utf-8")))
    return sorted(merged)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Build active-repositories matrix for sync workflows"
    )
    parser.add_argument(
        "--org-key",
        default=os.environ.get("ORG_KEY", "").strip(),
        help="Limit matrix to this control-plane org entrypoint (and aliases)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    config_dir = root / "config"
    token_policies = merge_repository_workflow_token_policies_from_org_trees(config_dir)

    if args.org_key:
        org_keys = resolve_org_keys_for_entrypoint(args.org_key, config_dir)
        repos = repositories_for_org_keys(config_dir, org_keys)
    else:
        repos = merge_active_repositories_from_org_trees(config_dir)

    matrix = [
        {
            "repository": repo,
            "workflow-token-policy": token_policies.get(repo, ""),
        }
        for repo in repos
    ]

    write_outputs(
        {
            "repos": json.dumps(matrix),
            "has_repos": "true" if repos else "false",
            "repos_count": str(len(repos)),
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
