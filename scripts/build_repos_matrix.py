#!/usr/bin/env python3
"""
Build a matrix of repositories from active-repositories.json for workflow use.

Reads active-repositories.json and writes to GITHUB_OUTPUT:
- repos: JSON array of {"repository": "owner/repo"} for matrix strategy
- has_repos: "true" or "false"
- repos_count: number of repositories

Related issue: https://github.com/elastic/observability-robots/issues/3732
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


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
        raise SystemExit("'repositories' must be a list")
    normalized = []
    for item in repositories:
        if not isinstance(item, str) or "/" not in item:
            raise SystemExit(
                f"Invalid repository entry: {item!r}. Expected 'owner/repo'"
            )
        normalized.append(item.strip())
    return sorted(set(normalized))


def main() -> int:
    """Entry point."""
    root = Path(__file__).resolve().parent.parent
    active_path = root / "active-repositories.json"
    if not active_path.exists():
        write_outputs({"repos": "[]", "has_repos": "false", "repos_count": "0"})
        return 0

    content = active_path.read_text()
    repos = parse_repositories(content)
    matrix = [{"repository": repo} for repo in repos]

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
