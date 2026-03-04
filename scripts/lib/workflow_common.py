import json
import os
from pathlib import Path
from typing import Any


def write_github_outputs(values: dict[str, str]) -> None:
    github_output = os.getenv("GITHUB_OUTPUT", "").strip()
    if not github_output:
        raise SystemExit("GITHUB_OUTPUT is not set")

    with open(github_output, "a", encoding="utf-8") as output_file:
        for key, value in values.items():
            output_file.write(f"{key}={value}\n")


def read_json_file(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json_file(path: str | Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def normalize_repository(value: str, default_owner: str = "") -> str:
    repository = (value or "").strip()
    if not repository:
        return ""

    if "/" in repository:
        owner, repo = repository.split("/", 1)
        owner = owner.strip()
        repo = repo.strip()
        if not owner or not repo:
            return ""
        return f"{owner}/{repo}"

    if not default_owner:
        return ""

    return f"{default_owner}/{repository}"


def split_repository(value: str, default_owner: str = "") -> tuple[str, str]:
    normalized = normalize_repository(value, default_owner)
    if not normalized:
        return "", ""

    owner, repo = normalized.split("/", 1)
    return owner, repo


def deduplicate_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    deduplicated: list[str] = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduplicated.append(value)

    return deduplicated
