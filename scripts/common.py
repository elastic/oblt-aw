#!/usr/bin/env python3
"""
Shared utilities for workflow scripts.

Provides write_outputs and parse_repositories used by build_repos_matrix
and build_target_operations.
"""

from __future__ import annotations

import json
import os


def write_outputs(values: dict[str, str]) -> None:
    """Write key=value pairs to GITHUB_OUTPUT."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if not github_output:
        raise SystemExit("GITHUB_OUTPUT is not set")

    with open(github_output, "a", encoding="utf-8") as output_file:
        for key, value in values.items():
            output_file.write(f"{key}={value}\n")


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
