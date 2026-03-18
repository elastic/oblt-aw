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
import sys
from pathlib import Path

from common import parse_repositories, write_outputs


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
