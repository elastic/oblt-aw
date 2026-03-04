import json
import os
import sys

from lib.workflow_common import (
    deduplicate_preserve_order,
    normalize_repository,
    read_json_file,
    write_github_outputs,
)


def main() -> int:
    default_owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "").strip()

    config = read_json_file("active-repositories.json")

    repositories = config.get("repositories", [])
    if not isinstance(repositories, list):
        print("repositories=[]", file=sys.stderr)
        print("has_repositories=false")
        print("repositories=[]")
        return 1

    normalized = []
    for entry in repositories:
        repository = normalize_repository(str(entry), default_owner)
        if repository:
            normalized.append(repository)

    deduplicated = deduplicate_preserve_order(normalized)

    write_github_outputs(
        {
            "repositories": json.dumps(deduplicated),
            "has_repositories": "true" if deduplicated else "false",
        }
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
