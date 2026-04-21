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

Unions ``config/<org-key>/active-repositories.json`` and deprecated top-level
``config/active-repositories.json``, then writes to GITHUB_OUTPUT:

- repos: JSON array of {"repository": "owner/repo"} for matrix strategy
- has_repos: "true" or "false"
- repos_count: number of repositories

Related issue: https://github.com/elastic/observability-robots/issues/3732
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from common import (
    merge_active_repositories_from_org_trees,
    parse_repositories,  # noqa: F401 — re-export for tests
    write_outputs,
)


def main() -> int:
    """Entry point."""
    root = Path(__file__).resolve().parent.parent
    config_dir = root / "config"
    repos = merge_active_repositories_from_org_trees(
        config_dir, include_legacy_root_files=True
    )
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
