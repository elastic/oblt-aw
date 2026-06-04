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
    discover_repo_org_assignments,
    merge_repository_token_policies_from_org_trees,
    parse_repositories,
    write_outputs,
)

REMOTE_TEMPLATE_DIR = pathlib.Path(".github/remote-workflow-template")
ZERO_SHA = "0000000000000000000000000000000000000000"


def list_org_template_files(org_key: str) -> list[dict[str, str]]:
    """
    Return ``[{src, dst}]`` entries for files under
    ``.github/remote-workflow-template/<org_key>/``.

    ``src`` is the path from the source repo root (POSIX separators).
    ``dst`` is the path inside the target repo (relative to repo root).
    """
    org_root = REMOTE_TEMPLATE_DIR / org_key
    if not org_root.is_dir():
        return []
    files: list[dict[str, str]] = []
    for path in sorted(org_root.rglob("*")):
        if not path.is_file():
            continue
        rel_src = path.as_posix()
        files.append(
            {
                "src": rel_src,
                "dst": path.relative_to(org_root).as_posix(),
            }
        )
    return files


def list_org_template_files_at_ref(org_key: str, ref: str) -> list[dict[str, str]]:
    """Return ``[{src, dst}]`` from the template tree at ``ref`` via git."""
    if not ref or ref == ZERO_SHA:
        return []
    org_prefix = f"{REMOTE_TEMPLATE_DIR.as_posix()}/{org_key}/"
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", ref, str(REMOTE_TEMPLATE_DIR)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    files: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.startswith(org_prefix):
            continue
        rel = line[len(org_prefix) :]
        if not rel:
            continue
        files.append({"src": line, "dst": rel})
    return sorted(files, key=lambda f: f["src"])


def read_previous_repo_org_assignments(base_ref: str) -> dict[str, list[str]]:
    """Repo→sorted-org-keys mapping at ``base_ref``, recovered from git history."""
    if not base_ref or base_ref == ZERO_SHA:
        return {}
    assignments: dict[str, set[str]] = {}
    try:
        lst = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", base_ref, "config"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return {}
    for line in lst.stdout.splitlines():
        parts = line.split("/")
        if (
            len(parts) < 3
            or parts[0] != "config"
            or parts[-1] != "active-repositories.json"
        ):
            continue
        org_key = parts[1]
        try:
            content = subprocess.run(
                ["git", "show", f"{base_ref}:{line}"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        except subprocess.CalledProcessError:
            continue
        for repo in parse_repositories(content):
            assignments.setdefault(repo, set()).add(org_key)
    return {repo: sorted(orgs) for repo, orgs in assignments.items()}


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def has_relevant_git_changes(base_ref: str) -> bool:
    """
    True when ``config/`` or the remote template tree differ between ``base_ref`` and HEAD.

    Used as a fallback when the changed-files action reports count 0 (for example git
    renames under ``.github/remote-workflow-template/`` are not counted as added,
    modified, or deleted).
    """
    if not base_ref or base_ref == ZERO_SHA:
        return False
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                base_ref,
                "HEAD",
                "--",
                "config",
                REMOTE_TEMPLATE_DIR.as_posix(),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return False
    return bool(result.stdout.strip())


def should_run_distribution(
    changed_files_count: int, force_distribution: bool, base_ref: str
) -> bool:
    if force_distribution:
        return True
    if changed_files_count > 0:
        return True
    return has_relevant_git_changes(base_ref)


def main() -> int:
    changed_files_count = int(os.getenv("CHANGED_FILES_COUNT", "0"))
    force_distribution = parse_bool(os.getenv("FORCE_DISTRIBUTION", "false"))
    base_ref = os.getenv("BASE_REF", "").strip()
    git_relevant = has_relevant_git_changes(base_ref)

    if not should_run_distribution(changed_files_count, force_distribution, base_ref):
        write_outputs(
            {
                "targets": "[]",
                "has_targets": "false",
                "install_count": "0",
                "remove_count": "0",
                "total_count": "0",
                "relevant_git_changes": "false",
            }
        )
        return 0

    config_dir = pathlib.Path("config")
    current_assignments = discover_repo_org_assignments(config_dir)
    token_policies = merge_repository_token_policies_from_org_trees(config_dir)

    previous_assignments = read_previous_repo_org_assignments(base_ref)

    current_files_by_org: dict[str, list[dict[str, str]]] = {}
    previous_files_by_org: dict[str, list[dict[str, str]]] = {}

    def files_for_orgs(orgs: list[str], at_base_ref: bool) -> list[dict[str, str]]:
        cache = previous_files_by_org if at_base_ref else current_files_by_org
        seen_dst: set[str] = set()
        out: list[dict[str, str]] = []
        for org in orgs:
            if org not in cache:
                cache[org] = (
                    list_org_template_files_at_ref(org, base_ref)
                    if at_base_ref
                    else list_org_template_files(org)
                )
            for entry in cache[org]:
                if entry["dst"] in seen_dst:
                    continue
                seen_dst.add(entry["dst"])
                out.append(entry)
        return out

    def dst_paths(files: list[dict[str, str]]) -> set[str]:
        return {entry["dst"] for entry in files}

    operations: list[dict[str, object]] = []

    for repo in sorted(current_assignments):
        files = files_for_orgs(current_assignments[repo], at_base_ref=False)
        previous_files = files_for_orgs(
            previous_assignments.get(repo, []), at_base_ref=True
        )
        current_dsts = dst_paths(files)
        remove_files = sorted(dst_paths(previous_files) - current_dsts)
        operations.append(
            {
                "repository": repo,
                "operation": "install",
                "files": files,
                "remove_files": remove_files,
                "token-policy": token_policies.get(repo, ""),
            }
        )

    removed_repositories = sorted(set(previous_assignments) - set(current_assignments))
    for repo in removed_repositories:
        files = files_for_orgs(previous_assignments[repo], at_base_ref=True)
        operations.append(
            {
                "repository": repo,
                "operation": "remove",
                "files": files,
                "token-policy": token_policies.get(repo, ""),
            }
        )

    install_count = len(current_assignments)
    remove_count = len(removed_repositories)
    total_count = len(operations)

    write_outputs(
        {
            "targets": json.dumps(operations),
            "has_targets": "true" if total_count > 0 else "false",
            "install_count": str(install_count),
            "remove_count": str(remove_count),
            "total_count": str(total_count),
            "relevant_git_changes": "true" if git_relevant else "false",
        }
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
