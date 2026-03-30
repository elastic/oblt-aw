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
