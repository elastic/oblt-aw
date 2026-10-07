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
MOVING_MAJOR_TAG_RE = re.compile(r"^v(?:0|[1-9]\d*)$")
SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)
POINTER_KEYS: tuple[str, ...] = ("current", "next", "previous")

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


def configured_major(data: dict[str, Any]) -> int:
    """Return the configured production major from ``release-pointers.json``."""
    major = data.get("major")
    if not isinstance(major, int) or isinstance(major, bool) or major < 0:
        raise ValueError(f"major must be a non-negative int, got {major!r}")
    return major


def bootstrap_semver(data: dict[str, Any]) -> str:
    """First-promote floor: ``v{configured_major}.0.0`` (currently ``v0.0.0``)."""
    return f"v{configured_major(data)}.0.0"


def pointer_string_field(entry: dict[str, Any], field: str, *, label: str) -> str:
    """Return a pointer ``sha``/``semver`` string; reject non-string types.

    Only the empty string (after strip) counts as empty. ``null``, ``false``,
    ``0``, and other JSON scalars must not be coerced into the empty-string
    bootstrap state.
    """
    value = entry.get(field)
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string, got {value!r}")
    return value.strip()


def assert_pointers_empty_for_bootstrap(data: dict[str, Any]) -> None:
    """Refuse bootstrap when any pointer still carries sha/semver residue."""
    residues: list[str] = []
    for key in POINTER_KEYS:
        entry = data["pointers"][key]
        for field in ("sha", "semver"):
            value = pointer_string_field(entry, field, label=f"pointers.{key}.{field}")
            if value:
                residues.append(f"pointers.{key}.{field}={value!r}")
    if residues:
        raise ValueError(
            "partial pointer state; refuse bootstrap until all sha/semver "
            f"are empty: {', '.join(residues)}"
        )


def validate_moving_tag_name(tag: str, *, role: str) -> str:
    """Validate a moving ops tag name before force-push.

    ``current`` must be ``vN``. ``next`` / ``previous`` must be non-empty and
    must not look like an immutable semver or a moving major (``vN``).
    """
    cleaned = tag.strip()
    if not cleaned:
        raise ValueError(f"tags.{role} is empty")
    if role == "current":
        if not MOVING_MAJOR_TAG_RE.fullmatch(cleaned):
            raise ValueError(
                f"tags.current must be a moving major like v0 or v1, got {cleaned!r}"
            )
        return cleaned
    if role not in ("next", "previous"):
        raise ValueError(f"unknown moving tag role: {role!r}")
    if SEMVER_RE.fullmatch(cleaned):
        raise ValueError(
            f"tags.{role} must not be semver-shaped (immutable tags are never "
            f"force-pushed), got {cleaned!r}"
        )
    if MOVING_MAJOR_TAG_RE.fullmatch(cleaned):
        raise ValueError(
            f"tags.{role} must not be a moving major like vN (reserved for "
            f"tags.current), got {cleaned!r}"
        )
    return cleaned


def validate_plan_moving_tags(plan: dict[str, Any]) -> None:
    """Validate moving tag names on a promote/rollback plan before mutation."""
    current = validate_moving_tag_name(str(plan["current_tag"]), role="current")
    next_tag = validate_moving_tag_name(str(plan["next_tag"]), role="next")
    previous = validate_moving_tag_name(str(plan["previous_tag"]), role="previous")
    immutable = str(plan.get("semver") or plan.get("immutable_tag") or "").strip()
    if immutable:
        for role, name in (("next", next_tag), ("previous", previous)):
            if name == immutable or name == normalize_semver(immutable):
                raise ValueError(
                    f"tags.{role} {name!r} collides with immutable semver {immutable!r}"
                )
    if current in {next_tag, previous}:
        raise ValueError(
            f"moving tag collision: current={current!r} next={next_tag!r} "
            f"previous={previous!r}"
        )
    if next_tag == previous:
        raise ValueError(f"tags.next and tags.previous must differ, got {next_tag!r}")


def semver_tuple(semver: str) -> tuple[int, int, int]:
    """Return ``(major, minor, patch)`` for ordering comparisons."""
    match = SEMVER_RE.fullmatch(normalize_semver(semver))
    if match is None:
        raise ValueError(f"internal error: semver not normalized: {semver!r}")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def next_semver(current: str, release_type: ReleaseType) -> str:
    """Bump ``current`` by ``release_type``. Empty current is not allowed."""
    release_type = normalize_release_type(release_type)
    if not (current or "").strip():
        raise ValueError(
            "empty current semver; use bootstrap_semver(data) for first promote"
        )
    major, minor, patch = semver_tuple(current)
    if release_type == "major":
        return f"v{major + 1}.0.0"
    if release_type == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def highest_pointer_semver(data: dict[str, Any]) -> str:
    """Highest non-empty semver among current / next / previous.

    Used as the promote bump base so rollback cannot rewind immutable numbering.
    """
    versions: list[str] = []
    for key in ("current", "next", "previous"):
        raw = pointer_string_field(
            data["pointers"][key], "semver", label=f"pointers.{key}.semver"
        )
        if raw:
            versions.append(normalize_semver(raw))
    if not versions:
        raise ValueError("no pointer semver values; cannot compute promote base")
    return max(versions, key=semver_tuple)


def load_pointers(path: Path = DEFAULT_POINTERS_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported schema_version: {data.get('schema_version')!r}")
    configured_major(data)
    pointers = data.get("pointers")
    if not isinstance(pointers, dict):
        raise TypeError("pointers must be an object")
    for key in ("current", "next", "previous"):
        entry = pointers.get(key)
        if not isinstance(entry, dict):
            raise TypeError(f"pointers.{key} must be an object")
    return data


def save_pointers(data: dict[str, Any], path: Path = DEFAULT_POINTERS_PATH) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_release_plan(path: Path) -> dict[str, Any]:
    """Load a ``{plan: ...}`` JSON artifact written by promote/rollback CLIs."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    plan = payload.get("plan")
    if not isinstance(plan, dict):
        raise TypeError(f"{path}: expected object with 'plan' object")
    return plan


def pointer_sha(data: dict[str, Any], name: str) -> str:
    entry = data["pointers"][name]
    return pointer_string_field(entry, "sha", label=f"pointers.{name}.sha").lower()


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


def require_remote_tip(sha: str, *, tip_ref: str) -> None:
    """Fail unless ``tip_ref`` currently resolves to ``sha`` (strict tip CAS)."""
    sha = validate_full_sha(sha, label="sha")
    tip = resolve_sha(tip_ref)
    if tip != sha:
        raise ValueError(
            f"ref {tip_ref!r} is {tip}, expected promote SHA {sha}; "
            "default branch advanced during the gate — abort and re-run promote"
        )


def require_ancestor_of(sha: str, *, tip_ref: str) -> None:
    """Fail unless ``sha`` is ``tip_ref`` or an ancestor of it.

    Allows promoting the E2E-gated SHA after default branch advanced during
    the gate, while still refusing commits not on that branch history.
    """
    sha = validate_full_sha(sha, label="sha")
    tip = resolve_sha(tip_ref)
    if tip == sha:
        return
    result = run_git(["merge-base", "--is-ancestor", sha, tip], check=False)
    if result.returncode != 0:
        raise ValueError(
            f"promote SHA {sha} is not an ancestor of {tip_ref!r} ({tip}); "
            "refusing to promote a commit not on the default branch history"
        )


def create_github_release(
    *,
    semver: str,
    sha: str,
    previous_semver: str = "",
    bootstrap: bool = False,
) -> None:
    """Create a GitHub Release for an existing immutable semver tag.

    Uses ``gh release create --generate-notes``. When ``previous_semver`` is set
    and this is not a bootstrap promote, pass ``--notes-start-tag`` so notes
    cover the range since the prior production release.
    """
    semver = normalize_semver(semver)
    sha = validate_full_sha(sha, label="sha")
    cmd = [
        "gh",
        "release",
        "create",
        semver,
        "--generate-notes",
        "--title",
        semver,
        "--target",
        sha,
    ]
    previous = (previous_semver or "").strip()
    if previous and not bootstrap:
        previous = normalize_semver(previous)
        if previous != semver:
            cmd.extend(["--notes-start-tag", previous])
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"gh release create {semver} failed: {detail}")


def tag_points_at(tag: str, sha: str) -> bool:
    try:
        return resolve_sha(tag) == validate_full_sha(sha)
    except (subprocess.CalledProcessError, ValueError):
        return False


def remote_tag_commit_sha(tag: str, *, remote: str = "origin") -> str | None:
    """Peeled commit SHA of ``refs/tags/<tag>`` on ``remote``, or None.

    Query the tag and ``^{}`` together. An exact ``refs/tags/<tag>`` pattern
    does not match the peeled ref, so annotated tags would otherwise return
    the tag-object SHA instead of the commit.
    """
    prefix = f"refs/tags/{tag}"
    result = run_git(["ls-remote", remote, prefix, f"{prefix}^{{}}"], check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    peeled: str | None = None
    direct: str | None = None
    for line in result.stdout.splitlines():
        sha, sep, name = line.partition("\t")
        if not sep:
            continue
        name = name.strip()
        sha = sha.strip().lower()
        if name == f"{prefix}^{{}}":
            peeled = sha
        elif name == prefix:
            direct = sha
    chosen = peeled or direct
    if chosen is None:
        return None
    return validate_full_sha(chosen, label=tag)


def require_remote_current_allows_in_flight(
    data: dict[str, Any], *, in_flight_sha: str, remote: str = "origin"
) -> None:
    """Refuse a new promote/rollback when origin's moving tag disagrees.

    After tags-before-pointers, a failed pointers merge leaves ``tags.current``
    on origin at the in-flight SHA while ``main`` still has the old pointers.
    Retrying that same SHA is allowed. Any other mismatch is refused so a later
    promote cannot treat stale ``pointers.current`` as ``previous``.
    """
    pointer_current = pointer_sha(data, "current")
    if not pointer_current:
        return
    in_flight_sha = validate_full_sha(in_flight_sha, label="in_flight_sha")
    current_tag = validate_moving_tag_name(
        str(data["tags"].get("current") or ""), role="current"
    )
    remote_current = remote_tag_commit_sha(current_tag, remote=remote)
    if remote_current is None:
        raise ValueError(
            f"pointers.current is {pointer_current} but {current_tag} is not "
            f"on {remote}; land tags or fix pointers before another release"
        )
    if remote_current in {pointer_current, in_flight_sha}:
        return
    raise ValueError(
        f"remote {current_tag} is {remote_current}, pointers.current is "
        f"{pointer_current}; refuse until they agree or retry the in-flight "
        f"plan at {in_flight_sha}"
    )


def move_tag(tag: str, sha: str, *, message: str) -> None:
    """Create or force-update a lightweight tag at ``sha`` (local only).

    Lightweight (not annotated): GitHub Actions fails nested relative
    ``uses: ./.github/workflows/...`` when the outer reusable workflow is
    pinned to an annotated tag. ``message`` is accepted for caller
    compatibility and ignored.
    """
    del message
    sha = validate_full_sha(sha)
    run_git(["tag", "-f", tag, sha])


def create_immutable_semver_tag(
    semver: str, sha: str, *, message: str, remote: str = "origin"
) -> bool:
    """Create an immutable lightweight semver tag.

    Lightweight (not annotated): same nested reusable-workflow constraint as
    ``move_tag``. ``message`` is accepted for caller compatibility and ignored.

    Returns True when the tag is created. Returns False when it already
    points at ``sha`` (local or ``remote``) so a promote retry can resume
    pointer landing. Fails closed when the tag exists at a different SHA.
    """
    del message
    semver = normalize_semver(semver)
    sha = validate_full_sha(sha)
    existing = run_git(["tag", "-l", semver], check=False)
    if existing.stdout.strip():
        existing_sha = resolve_sha(semver)
        if existing_sha == sha:
            return False
        raise ValueError(
            f"immutable tag {semver} already exists at {existing_sha}, refuse {sha}"
        )
    remote_sha = remote_tag_commit_sha(semver, remote=remote)
    if remote_sha is not None:
        if remote_sha == sha:
            run_git(["fetch", remote, f"refs/tags/{semver}:refs/tags/{semver}"])
            return False
        raise ValueError(
            f"immutable tag {semver} already exists on {remote} at "
            f"{remote_sha}, refuse {sha}"
        )
    run_git(["tag", semver, sha])
    return True


def push_immutable_tags(tags: list[str], *, remote: str = "origin") -> None:
    """Push immutable semver tags without ``--force``.

    Skip a tag that already exists on ``remote`` at the local peeled SHA so
    GitHub's reject-existing-tag does not block a promote retry.
    """
    if not tags:
        return
    pending: list[str] = []
    for raw in tags:
        tag = normalize_semver(raw)
        local_sha = resolve_sha(tag)
        remote_sha = remote_tag_commit_sha(tag, remote=remote)
        if remote_sha is None:
            pending.append(tag)
            continue
        if remote_sha == local_sha:
            continue
        raise ValueError(
            f"immutable tag {tag} already exists on {remote} at "
            f"{remote_sha}, local is {local_sha}"
        )
    if pending:
        run_git(["push", remote, *pending])


def push_moving_tags(tags: list[str], *, remote: str = "origin") -> None:
    """Force-push moving ops tags (``vN``, ``next``, ``previous``)."""
    if not tags:
        return
    if len(tags) != 3:
        raise ValueError(
            "push_moving_tags expects [current, next, previous], "
            f"got {len(tags)} tag(s)"
        )
    validated = [
        validate_moving_tag_name(tags[0], role="current"),
        validate_moving_tag_name(tags[1], role="next"),
        validate_moving_tag_name(tags[2], role="previous"),
    ]
    run_git(["push", remote, *validated, "--force"])


def push_promote_tags(plan: dict[str, Any], *, remote: str = "origin") -> None:
    """Publish immutable semver first, then force-update moving tags."""
    validate_plan_moving_tags(plan)
    # Always publish the canonical vMAJOR.MINOR.PATCH form (plans may carry
    # unprefixed input that normalize_semver accepts).
    push_immutable_tags([normalize_semver(str(plan["semver"]))], remote=remote)
    push_moving_tags(
        [
            str(plan["current_tag"]),
            str(plan["next_tag"]),
            str(plan["previous_tag"]),
        ],
        remote=remote,
    )


def push_rollback_tags(plan: dict[str, Any], *, remote: str = "origin") -> None:
    """Force-update moving tags after rollback (no immutable tags created)."""
    validate_plan_moving_tags(plan)
    push_moving_tags(
        [
            str(plan["current_tag"]),
            str(plan["next_tag"]),
            str(plan["previous_tag"]),
        ],
        remote=remote,
    )


def plan_promote(
    data: dict[str, Any],
    *,
    sha: str,
    release_type: str,
) -> dict[str, Any]:
    """Compute tag/pointer updates for a production promote (no git side effects).

    Always promotes ``sha`` (must be on default-branch history). First promote
    (empty current pointer) creates ``v{major}.0.0`` from ``data["major"]``
    regardless of ``release_type``.
    """
    sha = validate_full_sha(sha, label="sha")
    release_type = normalize_release_type(release_type)
    current_sha = pointer_sha(data, "current")
    bootstrap = not bool(current_sha)
    current_semver = pointer_string_field(
        data["pointers"]["current"], "semver", label="pointers.current.semver"
    )
    if bootstrap:
        assert_pointers_empty_for_bootstrap(data)
        semver = bootstrap_semver(data)
    else:
        if not current_semver:
            raise ValueError("current.semver is empty while current.sha is set")
        # Bump from the highest pointer semver so a rollback cannot rewind
        # immutable tag numbering (v0.0.1 → rollback → next patch must be v0.0.2).
        semver = next_semver(highest_pointer_semver(data), release_type)

    match = SEMVER_RE.fullmatch(semver)
    if match is None:
        raise ValueError(f"internal error: semver not normalized: {semver!r}")
    new_major = int(match.group("major"))
    current_tag = f"v{new_major}"
    next_tag = str(data["tags"]["next"])
    previous_tag = str(data["tags"]["previous"])
    previous_sha = current_sha if current_sha else sha
    previous_semver = current_semver if current_semver else semver

    plan = {
        "bootstrap": bootstrap,
        "current_tag": current_tag,
        "immutable_tag": semver,
        "next_tag": next_tag,
        "previous_semver": previous_semver,
        "previous_sha": previous_sha,
        "previous_tag": previous_tag,
        "release_type": release_type,
        "semver": semver,
        "sha": sha,
    }
    validate_plan_moving_tags(plan)
    return plan


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
    data["tags"]["current"] = str(plan["current_tag"])
    set_pointer(
        data,
        "previous",
        sha=str(plan["previous_sha"]),
        semver=str(plan["previous_semver"]),
        updated_at=now,
    )
    set_pointer(
        data,
        "current",
        sha=str(plan["sha"]),
        semver=str(plan["semver"]),
        updated_at=now,
    )
    set_pointer(
        data,
        "next",
        sha=str(plan["sha"]),
        semver=str(plan["semver"]),
        updated_at=now,
    )


def plan_rollback(data: dict[str, Any]) -> dict[str, Any]:
    """Compute tag/pointer updates for rollback to previous.

    Retargets the **current** production major tag (``tags.current``, e.g. ``v1``),
    not the major derived from ``previous.semver``. After a major promote,
    consumers pin the new major; rollback must move that tag.
    """
    previous_sha = pointer_sha(data, "previous")
    current_sha = pointer_sha(data, "current")
    if not previous_sha:
        raise ValueError("previous pointer is empty; cannot rollback")
    if not current_sha:
        raise ValueError("current pointer is empty; cannot rollback")
    if previous_sha == current_sha:
        raise ValueError("previous equals current; nothing to rollback")
    previous_semver = pointer_string_field(
        data["pointers"]["previous"],
        "semver",
        label="pointers.previous.semver",
    )
    if not previous_semver:
        raise ValueError("previous.semver is empty; cannot rollback safely")
    displaced_current_semver = pointer_string_field(
        data["pointers"]["current"],
        "semver",
        label="pointers.current.semver",
    )
    if not displaced_current_semver:
        raise ValueError("current.semver is empty; cannot rollback safely")
    rollback_semver = normalize_semver(previous_semver)
    displaced_current_semver = normalize_semver(displaced_current_semver)
    current_tag = str(data["tags"].get("current") or "").strip()
    next_tag = str(data["tags"]["next"])
    previous_tag = str(data["tags"]["previous"])
    plan = {
        "current_tag": current_tag,
        "displaced_current_semver": displaced_current_semver,
        "displaced_current_sha": current_sha,
        "next_tag": next_tag,
        "previous_tag": previous_tag,
        "rollback_semver": rollback_semver,
        "rollback_sha": previous_sha,
    }
    validate_plan_moving_tags(plan)
    return plan


def apply_rollback_pointer_updates(
    data: dict[str, Any],
    plan: dict[str, Any],
    *,
    updated_at: str | None = None,
) -> None:
    """Mutate ``data`` pointers/tags/major to match a rollback plan."""
    now = updated_at or utc_now_iso()
    current_tag = str(plan["current_tag"])
    data["tags"]["current"] = current_tag
    data["major"] = int(current_tag.removeprefix("v"))
    # Keep previous pointing at the displaced current so a second rollback
    # can undo the undo (swap).
    set_pointer(
        data,
        "previous",
        sha=str(plan["displaced_current_sha"]),
        semver=str(plan["displaced_current_semver"]),
        updated_at=now,
    )
    set_pointer(
        data,
        "current",
        sha=str(plan["rollback_sha"]),
        semver=str(plan["rollback_semver"]),
        updated_at=now,
    )
    set_pointer(
        data,
        "next",
        sha=str(plan["rollback_sha"]),
        semver=str(plan["rollback_semver"]),
        updated_at=now,
    )
