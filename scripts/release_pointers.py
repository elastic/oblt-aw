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

"""Release pointer store and tag helpers for the agentic release train.

See docs/operations/agentic-release-model.md.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)

ReleaseType = Literal["major", "minor", "patch"]
RELEASE_TYPES: tuple[ReleaseType, ...] = ("major", "minor", "patch")

DEFAULT_POINTERS_PATH = Path("config/release-pointers.json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_full_sha(sha: str, *, label: str = "sha") -> str:
    value = sha.strip().lower()
    if not FULL_SHA_RE.fullmatch(value):
        raise ValueError(f"{label} must be a 40-char lowercase hex SHA, got {sha!r}")
    return value


def normalize_semver(tag: str) -> str:
    """Return canonical ``vMAJOR.MINOR.PATCH`` or raise."""
    raw = tag.strip()
    match = SEMVER_RE.fullmatch(raw)
    if match is None:
        raise ValueError(f"semver must look like v1.2.3 or 1.2.3, got {tag!r}")
    return f"v{match.group('major')}.{match.group('minor')}.{match.group('patch')}"


def normalize_release_type(value: str) -> ReleaseType:
    cleaned = value.strip().lower()
    for release_type in RELEASE_TYPES:
        if cleaned == release_type:
            return release_type
    raise ValueError(
        f"release_type must be one of {', '.join(RELEASE_TYPES)}, got {value!r}"
    )


def next_semver(current: str, release_type: ReleaseType) -> str:
    """Bump ``current`` by ``release_type``. Empty current → ``v{major}.0.0`` floor."""
    release_type = normalize_release_type(release_type)
    if not (current or "").strip():
        return "v1.0.0"
    match = SEMVER_RE.fullmatch(normalize_semver(current))
    if match is None:
        raise ValueError(f"internal error: semver not normalized: {current!r}")
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))
    if release_type == "major":
        return f"v{major + 1}.0.0"
    if release_type == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def load_pointers(path: Path = DEFAULT_POINTERS_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported schema_version: {data.get('schema_version')!r}")
    pointers = data.get("pointers")
    if not isinstance(pointers, dict):
        raise TypeError("pointers must be an object")
    for key in ("prod", "candidate", "previous_prod"):
        entry = pointers.get(key)
        if not isinstance(entry, dict):
            raise TypeError(f"pointers.{key} must be an object")
    return data


def save_pointers(data: dict[str, Any], path: Path = DEFAULT_POINTERS_PATH) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def pointer_sha(data: dict[str, Any], name: str) -> str:
    entry = data["pointers"][name]
    sha = entry.get("sha") or ""
    if not isinstance(sha, str):
        raise TypeError(f"pointers.{name}.sha must be a string")
    return sha.strip().lower()


def set_pointer(
    data: dict[str, Any],
    name: str,
    *,
    sha: str,
    semver: str,
    updated_at: str | None = None,
) -> None:
    data["pointers"][name] = {
        "sha": validate_full_sha(sha, label=f"pointers.{name}.sha"),
        "semver": normalize_semver(semver) if semver else "",
        "updated_at": updated_at or utc_now_iso(),
    }


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def resolve_sha(ref: str) -> str:
    result = run_git(["rev-parse", f"{ref}^{{commit}}"])
    return validate_full_sha(result.stdout.strip(), label=ref)


def tag_points_at(tag: str, sha: str) -> bool:
    try:
        return resolve_sha(tag) == validate_full_sha(sha)
    except (subprocess.CalledProcessError, ValueError):
        return False


def move_tag(tag: str, sha: str, *, message: str) -> None:
    """Create or force-update an annotated tag at ``sha`` (local only)."""
    sha = validate_full_sha(sha)
    run_git(["tag", "-f", "-a", tag, sha, "-m", message])


def create_immutable_semver_tag(semver: str, sha: str, *, message: str) -> None:
    """Create an immutable annotated semver tag; fail if it already exists."""
    semver = normalize_semver(semver)
    sha = validate_full_sha(sha)
    existing = run_git(["tag", "-l", semver], check=False)
    if existing.stdout.strip():
        raise ValueError(f"immutable tag {semver} already exists")
    run_git(["tag", "-a", semver, sha, "-m", message])


def push_tags(tags: list[str], *, remote: str = "origin") -> None:
    if not tags:
        return
    run_git(["push", remote, *tags, "--force"])


def plan_promote(
    data: dict[str, Any],
    *,
    sha: str,
    release_type: str,
) -> dict[str, Any]:
    """Compute tag/pointer updates for a production promote (no git side effects).

    Always promotes ``sha`` (expected: tip of default branch). First promote
    (empty prod pointer) creates ``v1.0.0`` regardless of ``release_type``.
    """
    sha = validate_full_sha(sha, label="sha")
    release_type = normalize_release_type(release_type)
    current_prod = pointer_sha(data, "prod")
    bootstrap = not bool(current_prod)
    current_semver = str(data["pointers"]["prod"].get("semver") or "")
    if bootstrap:
        semver = "v1.0.0"
    else:
        if not current_semver:
            raise ValueError("prod.semver is empty while prod.sha is set")
        semver = next_semver(current_semver, release_type)

    match = SEMVER_RE.fullmatch(semver)
    if match is None:
        raise ValueError(f"internal error: semver not normalized: {semver!r}")
    new_major = int(match.group("major"))
    prod_tag = f"v{new_major}"
    candidate_tag = str(data["tags"]["candidate"])
    previous_tag = str(data["tags"]["previous_prod"])
    previous_sha = current_prod if current_prod else sha
    previous_semver = current_semver if current_semver else semver

    return {
        "bootstrap": bootstrap,
        "candidate_tag": candidate_tag,
        "immutable_tag": semver,
        "previous_semver": previous_semver,
        "previous_sha": previous_sha,
        "previous_tag": previous_tag,
        "prod_tag": prod_tag,
        "release_type": release_type,
        "semver": semver,
        "sha": sha,
    }


def apply_promote_pointer_updates(
    data: dict[str, Any],
    plan: dict[str, Any],
    *,
    updated_at: str | None = None,
) -> None:
    """Mutate ``data`` pointers/tags/major to match a promote plan."""
    now = updated_at or utc_now_iso()
    match = SEMVER_RE.fullmatch(str(plan["semver"]))
    if match is None:
        raise ValueError(f"plan semver invalid: {plan['semver']!r}")
    data["major"] = int(match.group("major"))
    data["tags"]["prod"] = str(plan["prod_tag"])
    set_pointer(
        data,
        "previous_prod",
        sha=str(plan["previous_sha"]),
        semver=str(plan["previous_semver"]),
        updated_at=now,
    )
    set_pointer(
        data,
        "prod",
        sha=str(plan["sha"]),
        semver=str(plan["semver"]),
        updated_at=now,
    )
    set_pointer(
        data,
        "candidate",
        sha=str(plan["sha"]),
        semver=str(plan["semver"]),
        updated_at=now,
    )


def plan_rollback(data: dict[str, Any]) -> dict[str, Any]:
    """Compute tag/pointer updates for rollback to previous-prod."""
    previous_sha = pointer_sha(data, "previous_prod")
    current_prod = pointer_sha(data, "prod")
    if not previous_sha:
        raise ValueError("previous_prod pointer is empty; cannot rollback")
    if not current_prod:
        raise ValueError("prod pointer is empty; cannot rollback")
    if previous_sha == current_prod:
        raise ValueError("previous_prod equals prod; nothing to rollback")
    previous_semver = str(data["pointers"]["previous_prod"].get("semver") or "")
    if not previous_semver:
        raise ValueError("previous_prod.semver is empty; cannot rollback safely")
    rollback_semver = normalize_semver(previous_semver)
    match = SEMVER_RE.fullmatch(rollback_semver)
    if match is None:
        raise ValueError(f"internal error: semver not normalized: {rollback_semver!r}")
    return {
        "candidate_tag": str(data["tags"]["candidate"]),
        "displaced_prod_semver": str(data["pointers"]["prod"].get("semver") or ""),
        "displaced_prod_sha": current_prod,
        "previous_tag": str(data["tags"]["previous_prod"]),
        "prod_tag": f"v{int(match.group('major'))}",
        "rollback_semver": rollback_semver,
        "rollback_sha": previous_sha,
    }
