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

"""Discover and filter consumer repo-scheduled automations from apm.yml.

Consumers declare automations under
``x-oblt-aw.obs.workflows.repo-scheduled.automations`` with an
``instructions-file`` path. Optional ``schedule-profiles``, ``capabilities``,
and ``id`` may live in the APM entry and/or the instruction file frontmatter
(APM wins when both set). The framework owns cron, MCP, and secret wiring for
allowlisted capability ids.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from apm_agentic_assets import load_apm_manifest
from common import write_outputs

ORG_KEY = "obs"
WORKFLOW_ID = "repo-scheduled"
KNOWN_SCHEDULE_PROFILES = frozenset({"daily", "frequent", "weekly"})
# capability id -> env var that must be non-empty when the capability is requested
KNOWN_CAPABILITIES: dict[str, str] = {
    "buildkite-logs": "BUILDKITE_API_TOKEN",
}

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z",
    re.DOTALL,
)


@dataclass(frozen=True)
class ScheduledAutomation:
    """One consumer instruction file selected for a schedule wake."""

    automation_id: str
    path: str
    schedule_profiles: tuple[str, ...]
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class DiscoveryResult:
    """Runnable automations plus capability blocks for the current wake."""

    matching: list[ScheduledAutomation]
    blocked: list[dict[str, str]]
    errors: list[str]


def _slug_from_stem(stem: str) -> str:
    return stem.strip().lower().replace("_", "-")


def parse_instruction_file(path: Path) -> tuple[dict[str, Any], str]:
    """Return (frontmatter mapping, body).

    Frontmatter is optional when metadata is supplied from apm.yml. The body
    must be non-empty either way.
    """
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        body = text.strip()
        if not body:
            raise ValueError(f"{path}: instruction body is empty")
        return {}, body
    raw = yaml.safe_load(match.group(1))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise TypeError(f"{path}: frontmatter must be a YAML mapping")
    body = match.group(2).strip()
    if not body:
        raise ValueError(f"{path}: instruction body is empty")
    return raw, body


def _as_str_list(value: Any, *, field: str, source: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        raise TypeError(f"{source}: {field} must be a string or list of strings")
    out: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{source}: {field} entries must be non-empty strings")
        out.append(item.strip())
    return out


def _validate_profiles(profiles: list[str], *, source: str) -> None:
    unknown = sorted(set(profiles) - KNOWN_SCHEDULE_PROFILES)
    if unknown:
        known = ", ".join(sorted(KNOWN_SCHEDULE_PROFILES))
        raise ValueError(
            f"{source}: unknown schedule-profiles {unknown}; known: {known}"
        )


def _validate_capabilities(capabilities: list[str], *, source: str) -> None:
    unknown = sorted(set(capabilities) - set(KNOWN_CAPABILITIES))
    if unknown:
        known = ", ".join(sorted(KNOWN_CAPABILITIES))
        raise ValueError(f"{source}: unknown capabilities {unknown}; known: {known}")


def _reject_path_escape(rel: str, *, source: str) -> Path:
    """Return a normalized relative path; reject absolute / parent escapes."""
    raw = rel.strip()
    if not raw:
        raise ValueError(f"{source}: instructions-file must be a non-empty string")
    path = Path(raw)
    if path.is_absolute():
        raise ValueError(f"{source}: instructions-file must be repo-relative")
    if ".." in path.parts:
        raise ValueError(f"{source}: instructions-file must not contain '..'")
    return path


def _resolve_contained_file(repo_root: Path, rel: Path, *, source: str) -> Path:
    """Resolve ``rel`` under ``repo_root`` and reject symlink/path escapes."""
    candidate = repo_root / rel
    if not candidate.exists():
        raise ValueError(f"{source}: instructions-file not found: {rel.as_posix()}")
    resolved_root = repo_root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(
            f"{source}: instructions-file escapes repository root: {rel.as_posix()}"
        ) from exc
    if not resolved.is_file():
        raise ValueError(
            f"{source}: instructions-file is not a regular file: {rel.as_posix()}"
        )
    return resolved


def load_apm_document(repo_root: Path) -> dict[str, Any] | None:
    """Load consumer ``apm.yml`` / ``apm.yaml`` when present; None when absent.

    Filename precedence matches ``apm_agentic_assets.load_apm_manifest``
    (``.yml`` before ``.yaml``).
    """
    data, present = load_apm_manifest(repo_root)
    if not present:
        return None
    return data


def read_automations_entries(apm: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the ``automations`` list from x-oblt-aw.obs.workflows.repo-scheduled."""
    ext = apm.get("x-oblt-aw")
    if ext is None:
        return []
    if not isinstance(ext, dict):
        raise TypeError("apm.yml: x-oblt-aw must be a mapping")
    org = ext.get(ORG_KEY)
    if org is None:
        return []
    if not isinstance(org, dict):
        raise TypeError(f"apm.yml: x-oblt-aw.{ORG_KEY} must be a mapping")
    workflows = org.get("workflows")
    if workflows is None:
        return []
    if not isinstance(workflows, dict):
        raise TypeError(f"apm.yml: x-oblt-aw.{ORG_KEY}.workflows must be a mapping")
    block = workflows.get(WORKFLOW_ID)
    if block is None:
        return []
    if not isinstance(block, dict):
        raise TypeError(
            f"apm.yml: x-oblt-aw.{ORG_KEY}.workflows.{WORKFLOW_ID} must be a mapping"
        )
    automations = block.get("automations")
    if automations is None:
        return []
    if not isinstance(automations, list):
        raise TypeError(
            f"apm.yml: x-oblt-aw.{ORG_KEY}.workflows.{WORKFLOW_ID}.automations "
            "must be a list"
        )
    out: list[dict[str, Any]] = []
    for index, item in enumerate(automations):
        if not isinstance(item, dict):
            raise TypeError(f"apm.yml: automations[{index}] must be a mapping")
        out.append(item)
    return out


def load_automation_from_apm_entry(
    repo_root: Path, entry: dict[str, Any], *, index: int
) -> ScheduledAutomation:
    """Build one ScheduledAutomation from an APM automations[] entry + file."""
    source = f"apm.yml automations[{index}]"
    instructions = entry.get("instructions-file")
    if instructions is None:
        raise ValueError(f"{source}: instructions-file is required (string)")
    if not isinstance(instructions, str):
        raise TypeError(f"{source}: instructions-file must be a string")
    rel = _reject_path_escape(instructions, source=source)
    resolved = _resolve_contained_file(repo_root, rel, source=source)

    meta, _body = parse_instruction_file(resolved)
    file_source = rel.as_posix()

    automation_id = entry.get("id")
    if automation_id is None:
        automation_id = meta.get("id")
    if automation_id is None:
        automation_id = _slug_from_stem(rel.stem)
    if not isinstance(automation_id, str) or not automation_id.strip():
        raise ValueError(f"{source}: id must be a non-empty string when set")
    automation_id = automation_id.strip()

    if "schedule-profiles" in entry:
        profiles = _as_str_list(
            entry.get("schedule-profiles"),
            field="schedule-profiles",
            source=source,
        )
    else:
        profiles = _as_str_list(
            meta.get("schedule-profiles"),
            field="schedule-profiles",
            source=file_source,
        )
    if not profiles:
        raise ValueError(
            f"{source}: schedule-profiles is required on the APM entry or "
            f"in {file_source} frontmatter"
        )
    _validate_profiles(profiles, source=source)

    if "capabilities" in entry:
        capabilities = _as_str_list(
            entry.get("capabilities"),
            field="capabilities",
            source=source,
        )
    else:
        capabilities = _as_str_list(
            meta.get("capabilities"),
            field="capabilities",
            source=file_source,
        )
    _validate_capabilities(capabilities, source=source)

    return ScheduledAutomation(
        automation_id=automation_id,
        path=rel.as_posix(),
        schedule_profiles=tuple(profiles),
        capabilities=tuple(capabilities),
    )


def discover_automations(repo_root: Path) -> list[ScheduledAutomation]:
    """Load automations declared in consumer ``apm.yml`` / ``apm.yaml``."""
    apm = load_apm_document(repo_root)
    if apm is None:
        return []
    entries = read_automations_entries(apm)
    return [
        load_automation_from_apm_entry(repo_root, entry, index=index)
        for index, entry in enumerate(entries)
    ]


def _secret_present(env: dict[str, str], capability: str) -> bool:
    env_name = KNOWN_CAPABILITIES[capability]
    return bool(env.get(env_name, "").strip())


def evaluate_for_profile(
    repo_root: Path,
    schedule_profile: str,
    *,
    env: dict[str, str] | None = None,
) -> DiscoveryResult:
    """Select automations for ``schedule_profile`` and apply capability secret gates."""
    profile = schedule_profile.strip()
    if profile not in KNOWN_SCHEDULE_PROFILES:
        known = ", ".join(sorted(KNOWN_SCHEDULE_PROFILES))
        raise ValueError(f"unknown schedule-profile {profile!r}; known: {known}")

    env_map = dict(env) if env is not None else dict(os.environ)
    matching: list[ScheduledAutomation] = []
    blocked: list[dict[str, str]] = []
    errors: list[str] = []

    try:
        automations = discover_automations(repo_root)
    except (ValueError, TypeError) as exc:
        return DiscoveryResult(matching=[], blocked=[], errors=[str(exc)])

    seen_ids: set[str] = set()
    for automation in automations:
        if automation.automation_id in seen_ids:
            errors.append(
                f"duplicate automation id {automation.automation_id!r} "
                f"({automation.path})"
            )
            continue
        seen_ids.add(automation.automation_id)
        if profile not in automation.schedule_profiles:
            continue
        missing = [
            cap for cap in automation.capabilities if not _secret_present(env_map, cap)
        ]
        if missing:
            blocked.append(
                {
                    "id": automation.automation_id,
                    "path": automation.path,
                    "missing-capabilities": ",".join(missing),
                    "reason": (
                        "requested capabilities require secrets that are not "
                        "configured on this schedule path: "
                        + ", ".join(
                            f"{cap} ({KNOWN_CAPABILITIES[cap]})" for cap in missing
                        )
                    ),
                }
            )
            continue
        matching.append(automation)

    return DiscoveryResult(matching=matching, blocked=blocked, errors=errors)


def matrix_payload(automations: list[ScheduledAutomation]) -> dict[str, Any]:
    """GitHub Actions matrix.include payload for runnable automations."""
    return {
        "include": [
            {
                "id": item.automation_id,
                "path": item.path,
                "capabilities": ",".join(item.capabilities),
            }
            for item in automations
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Discover repo-scheduled automations from apm.yml and filter by "
            "schedule-profile + capability secrets"
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Consumer repository root (default: .)",
    )
    parser.add_argument(
        "--schedule-profile",
        required=True,
        help="Current wake profile: daily, frequent, or weekly",
    )
    args = parser.parse_args()

    try:
        result = evaluate_for_profile(args.repo_root, args.schedule_profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if result.errors:
        for err in result.errors:
            print(f"::error::{err}", file=sys.stderr)
        return 1

    for blocked in result.blocked:
        print(
            f"::error::repo-scheduled automation {blocked['id']} blocked: "
            f"{blocked['reason']}",
            file=sys.stderr,
        )

    payload = matrix_payload(result.matching)
    has_matches = "true" if result.matching else "false"
    has_blocked = "true" if result.blocked else "false"
    write_outputs(
        {
            "has-matches": has_matches,
            "has-blocked": has_blocked,
            "automations-matrix-json": json.dumps(payload, separators=(",", ":")),
            "blocked-automations-json": json.dumps(
                result.blocked, separators=(",", ":")
            ),
            "match-count": str(len(result.matching)),
            "blocked-count": str(len(result.blocked)),
        }
    )
    print(
        f"repo-scheduled: profile={args.schedule_profile!r} "
        f"matches={len(result.matching)} blocked={len(result.blocked)}"
    )
    # Fail closed when capability secrets are missing for requested automations.
    if result.blocked:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
