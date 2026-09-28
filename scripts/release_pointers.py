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
from typing import Any

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)

DEFAULT_POINTERS_PATH = Path("config/release-pointers.json")

REQUIRED_E2E_WORKFLOW_IDS = (
    "obs:autodoc",
    "obs:automerge",
    "obs:dependency-review",
    "obs:estc-pr-buildkite-detective",
)


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


def classify_run_class(*, candidate_ref: str, github_sha: str) -> str:
    """Return ``gating`` when candidate_ref is a full SHA matching github_sha."""
    candidate = (candidate_ref or "").strip().lower()
    head = (github_sha or "").strip().lower()
    if not candidate:
        return "smoke"
    if not FULL_SHA_RE.fullmatch(candidate):
        return "smoke"
    if not FULL_SHA_RE.fullmatch(head):
        return "smoke"
    if candidate != head:
        return "smoke"
    return "gating"


def enrich_summary(
    summary: dict[str, Any],
    *,
    candidate_ref: str,
    github_sha: str,
) -> dict[str, Any]:
    """Stamp promote metadata onto an oracle summary object."""
    out = dict(summary)
    candidate = (candidate_ref or "").strip().lower()
    head = (
        validate_full_sha(github_sha, label="github_sha") if github_sha.strip() else ""
    )
    run_class = classify_run_class(candidate_ref=candidate, github_sha=head)
    out["candidate_ref"] = candidate if FULL_SHA_RE.fullmatch(candidate) else ""
    out["github_sha"] = head
    out["run_class"] = run_class
    out["eligible_for_promote"] = bool(
        run_class == "gating"
        and out.get("pass") is True
        and out.get("skipped") is not True
    )
    return out


def validate_e2e_gate_summaries(
    summaries: list[dict[str, Any]],
    *,
    expected_candidate_sha: str,
    required_workflow_ids: tuple[str, ...] = REQUIRED_E2E_WORKFLOW_IDS,
) -> None:
    """Fail closed unless every required workflow has a gating pass for the SHA."""
    expected = validate_full_sha(expected_candidate_sha, label="expected_candidate_sha")
    by_id: dict[str, dict[str, Any]] = {}
    for item in summaries:
        if not isinstance(item, dict):
            raise TypeError("each summary must be a JSON object")
        workflow_id = item.get("workflow_id")
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise ValueError(f"summary missing workflow_id: {item!r}")
        by_id[workflow_id.strip()] = item

    missing = [wid for wid in required_workflow_ids if wid not in by_id]
    if missing:
        raise ValueError(f"missing E2E summaries for workflow ids: {missing}")

    errors: list[str] = []
    for wid in required_workflow_ids:
        item = by_id[wid]
        if item.get("run_class") != "gating":
            errors.append(f"{wid}: run_class={item.get('run_class')!r} (need gating)")
        if item.get("eligible_for_promote") is not True:
            errors.append(f"{wid}: eligible_for_promote is not true")
        if item.get("pass") is not True:
            errors.append(f"{wid}: pass is not true")
        if item.get("skipped") is True:
            errors.append(f"{wid}: skipped=true blocks promote")
        cand = str(item.get("candidate_ref") or "").lower()
        if cand != expected:
            errors.append(
                f"{wid}: candidate_ref={cand!r} does not match expected {expected!r}"
            )
    if errors:
        raise ValueError("E2E gate failed:\n- " + "\n- ".join(errors))


def plan_promote(
    data: dict[str, Any],
    *,
    candidate_sha: str,
    semver: str,
    bootstrap: bool,
) -> dict[str, Any]:
    """Compute tag/pointer updates for a production promote (no git side effects)."""
    candidate_sha = validate_full_sha(candidate_sha, label="candidate_sha")
    semver = normalize_semver(semver)
    major = int(data.get("major", 1))
    semver_match = SEMVER_RE.fullmatch(semver)
    if semver_match is None:
        raise ValueError(f"internal error: semver not normalized: {semver!r}")
    parsed_major = int(semver_match.group("major"))
    if parsed_major != major:
        raise ValueError(
            f"semver major {parsed_major} does not match release-pointers major {major}"
        )

    prod_tag = str(data["tags"]["prod"])
    candidate_tag = str(data["tags"]["candidate"])
    previous_tag = str(data["tags"]["previous_prod"])
    current_prod = pointer_sha(data, "prod")

    if not bootstrap and not current_prod:
        raise ValueError(
            "prod pointer is empty; use --bootstrap for the first production promote"
        )
    if bootstrap and current_prod:
        raise ValueError("prod pointer already set; refuse --bootstrap")

    previous_sha = current_prod if current_prod else candidate_sha
    return {
        "candidate_sha": candidate_sha,
        "semver": semver,
        "prod_tag": prod_tag,
        "candidate_tag": candidate_tag,
        "previous_tag": previous_tag,
        "previous_sha": previous_sha,
        "bootstrap": bootstrap,
        "immutable_tag": semver,
    }


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
    return {
        "prod_tag": str(data["tags"]["prod"]),
        "previous_tag": str(data["tags"]["previous_prod"]),
        "candidate_tag": str(data["tags"]["candidate"]),
        "rollback_sha": previous_sha,
        "rollback_semver": normalize_semver(previous_semver),
        "displaced_prod_sha": current_prod,
        "displaced_prod_semver": str(data["pointers"]["prod"].get("semver") or ""),
    }
