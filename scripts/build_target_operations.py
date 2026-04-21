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

import json
import os
import pathlib
import subprocess
import sys

from common import (
    merge_active_repositories_from_org_trees,
    parse_repositories,
    write_outputs,
)


def read_previous_repositories(base_ref: str) -> list[str]:
    """Load union of repository lists from ``base_ref`` (legacy paths + per-org files)."""
    if not base_ref or base_ref == "0000000000000000000000000000000000000000":
        return []

    merged: set[str] = set()
    for path in ("config/active-repositories.json", "active-repositories.json"):
        try:
            result = subprocess.run(
                ["git", "show", f"{base_ref}:{path}"],
                check=True,
                capture_output=True,
                text=True,
            )
            merged.update(parse_repositories(result.stdout))
        except subprocess.CalledProcessError:
            continue

    try:
        lst = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", base_ref, "config"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return sorted(merged)

    for line in lst.stdout.splitlines():
        parts = line.split("/")
        if len(parts) < 3:
            continue
        if parts[-1] != "active-repositories.json":
            continue
        if parts[0] != "config":
            continue
        try:
            result = subprocess.run(
                ["git", "show", f"{base_ref}:{line}"],
                check=True,
                capture_output=True,
                text=True,
            )
            merged.update(parse_repositories(result.stdout))
        except subprocess.CalledProcessError:
            continue
    return sorted(merged)


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    changed_files_count = int(os.getenv("CHANGED_FILES_COUNT", "0"))
    force_distribution = parse_bool(os.getenv("FORCE_DISTRIBUTION", "false"))

    if changed_files_count == 0 and not force_distribution:
        write_outputs(
            {
                "targets": "[]",
                "has_targets": "false",
                "install_count": "0",
                "remove_count": "0",
                "total_count": "0",
            }
        )
        return 0

    config_dir = pathlib.Path("config")
    current_repositories = merge_active_repositories_from_org_trees(config_dir)

    base_ref = os.getenv("BASE_REF", "").strip()
    previous_repositories = read_previous_repositories(base_ref)

    operations = [
        {"repository": repo, "operation": "install"} for repo in current_repositories
    ]

    removed_repositories = sorted(
        set(previous_repositories) - set(current_repositories)
    )
    operations.extend(
        {"repository": repo, "operation": "remove"} for repo in removed_repositories
    )

    install_count = len(current_repositories)
    remove_count = len(removed_repositories)
    total_count = len(operations)

    write_outputs(
        {
            "targets": json.dumps(operations),
            "has_targets": "true" if total_count > 0 else "false",
            "install_count": str(install_count),
            "remove_count": str(remove_count),
            "total_count": str(total_count),
        }
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
