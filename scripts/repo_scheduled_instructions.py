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

"""Discover and filter consumer repo-scheduled instruction files.

Instruction Markdown lives under ``.github/ai/scheduled/*.md`` with YAML
frontmatter. Consumers pick schedule lanes and optional capability ids; the
framework owns cron, MCP, and secret wiring for those allowlisted ids.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from common import write_outputs

SCHEDULED_INSTRUCTIONS_DIR = Path(".github/ai/scheduled")
KNOWN_SCHEDULE_PROFILES = frozenset({"daily", "frequent", "weekly"})
# capability id -> env var that must be non-empty when the capability is requested
KNOWN_CAPABILITIES: dict[str, str] = {
    "buildkite-logs": "BUILDKITE_API_TOKEN",
}
E2E_BAIT_AUTOMATION_ID = "e2e-repo-scheduled-bait"
E2E_BAIT_PATH = ".github/ai/scheduled/e2e-repo-scheduled-bait.md"

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
    """Return (frontmatter mapping, body). Fail closed on missing frontmatter."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ValueError(f"{path}: missing YAML frontmatter delimited by ---")
    raw = yaml.safe_load(match.group(1))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise TypeError(f"{path}: frontmatter must be a YAML mapping")
    body = match.group(2).strip()
    if not body:
        raise ValueError(f"{path}: instruction body is empty")
    return raw, body


def _as_str_list(value: Any, *, field: str, path: Path) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        raise TypeError(f"{path}: {field} must be a string or list of strings")
    out: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{path}: {field} entries must be non-empty strings")
        out.append(item.strip())
    return out


def load_automation(path: Path) -> ScheduledAutomation:
    """Parse one instruction file into a ScheduledAutomation."""
    meta, _body = parse_instruction_file(path)
    automation_id = meta.get("id")
    if automation_id is None:
        automation_id = _slug_from_stem(path.stem)
    if not isinstance(automation_id, str) or not automation_id.strip():
        raise ValueError(f"{path}: id must be a non-empty string when set")
    automation_id = automation_id.strip()

    profiles = _as_str_list(
        meta.get("schedule-profiles"), field="schedule-profiles", path=path
    )
    if not profiles:
        raise ValueError(f"{path}: schedule-profiles is required and must be non-empty")
    unknown_profiles = sorted(set(profiles) - KNOWN_SCHEDULE_PROFILES)
    if unknown_profiles:
        known = ", ".join(sorted(KNOWN_SCHEDULE_PROFILES))
        raise ValueError(
            f"{path}: unknown schedule-profiles {unknown_profiles}; known: {known}"
        )

    capabilities = _as_str_list(
        meta.get("capabilities"), field="capabilities", path=path
    )
    unknown_caps = sorted(set(capabilities) - set(KNOWN_CAPABILITIES))
    if unknown_caps:
        known = ", ".join(sorted(KNOWN_CAPABILITIES))
        raise ValueError(f"{path}: unknown capabilities {unknown_caps}; known: {known}")

    return ScheduledAutomation(
        automation_id=automation_id,
        path=path.as_posix(),
        schedule_profiles=tuple(profiles),
        capabilities=tuple(capabilities),
    )


def discover_automations(repo_root: Path) -> list[ScheduledAutomation]:
    """Load all ``*.md`` instruction files under the scheduled instructions dir."""
    root = repo_root / SCHEDULED_INSTRUCTIONS_DIR
    if not root.is_dir():
        return []
    paths = sorted(p for p in root.glob("*.md") if p.is_file())
    return [load_automation(path) for path in paths]


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

    env_map = dict(env) if env is not None else dict(__import__("os").environ)
    matching: list[ScheduledAutomation] = []
    blocked: list[dict[str, str]] = []
    errors: list[str] = []

    try:
        automations = discover_automations(repo_root)
    except ValueError as exc:
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


def filter_e2e_bait_only(
    matching: list[ScheduledAutomation],
    *,
    bait_id: str = E2E_BAIT_AUTOMATION_ID,
    bait_path: str = E2E_BAIT_PATH,
) -> list[ScheduledAutomation]:
    """Keep only the canonical E2E bait automation; fail if it is absent."""
    kept = [
        item
        for item in matching
        if item.automation_id == bait_id and item.path == bait_path
    ]
    if not kept:
        raise ValueError(
            "e2e-bait-only: canonical bait automation not discovered "
            f"(id={bait_id!r} path={bait_path!r})"
        )
    return kept


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Discover .github/ai/scheduled instruction files for repo-scheduled "
            "and filter by schedule-profile + capability secrets"
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
    parser.add_argument(
        "--e2e-bait-only",
        action="store_true",
        help=(
            "Keep only the canonical E2E bait automation "
            f"({E2E_BAIT_AUTOMATION_ID} @ {E2E_BAIT_PATH}); fail if absent"
        ),
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

    matching = result.matching
    if args.e2e_bait_only:
        try:
            matching = filter_e2e_bait_only(matching)
        except ValueError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 1

    relevant_blocked = result.blocked
    if args.e2e_bait_only:
        relevant_blocked = [
            item
            for item in result.blocked
            if item.get("id") == E2E_BAIT_AUTOMATION_ID
            or item.get("path") == E2E_BAIT_PATH
        ]

    for blocked in relevant_blocked:
        print(
            f"::error::repo-scheduled automation {blocked['id']} blocked: "
            f"{blocked['reason']}",
            file=sys.stderr,
        )

    payload = matrix_payload(matching)
    write_outputs(
        {
            "has-matches": "true" if matching else "false",
            "has-blocked": "true" if relevant_blocked else "false",
            "automations-matrix-json": json.dumps(payload, separators=(",", ":")),
            "blocked-automations-json": json.dumps(
                relevant_blocked, separators=(",", ":")
            ),
            "match-count": str(len(matching)),
            "blocked-count": str(len(relevant_blocked)),
        }
    )
    print(
        f"repo-scheduled: profile={args.schedule_profile!r} "
        f"matches={len(matching)} blocked={len(relevant_blocked)}"
        + (" e2e-bait-only=true" if args.e2e_bait_only else "")
    )
    # Fail closed when capability secrets are missing for requested automations.
    if relevant_blocked:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
