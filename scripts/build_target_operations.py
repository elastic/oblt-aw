import json
import os
import pathlib
import subprocess
import sys

from common import parse_repositories, write_outputs


def read_previous_repositories(base_ref: str) -> list[str]:
    if not base_ref or base_ref == "0000000000000000000000000000000000000000":
        return []

    try:
        result = subprocess.run(
            ["git", "show", f"{base_ref}:active-repositories.json"],
            check=True,
            capture_output=True,
            text=True,
        )
        return parse_repositories(result.stdout)
    except subprocess.CalledProcessError:
        return []


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

    config_path = pathlib.Path("active-repositories.json")
    current_content = (
        config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    )
    current_repositories = parse_repositories(current_content)

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
