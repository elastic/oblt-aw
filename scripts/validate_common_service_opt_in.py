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

"""
Validate that orgs which ``include_common`` wire event orchestrators and triggers.

When an org opts into a shared service from ``config/common/services.json``, the
same PR must provide runtime wiring for that org. This check fails closed if:

* an included service's ``inner_workflows`` basename is missing from that org's
  ``*-aw-event-*.yml`` ``control-plane-workflows`` list, or
* no job in those orchestrators ``uses:`` that basename, or
* the remote client template for the event family the orchestrator covers is
  missing under ``.github/remote-workflow-template/<org-key>/``.

Orgs with an empty or absent ``include_common`` are skipped.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

from common import discover_org_config_dirs
from workflow_registry import load_common_services, load_workflow_registry

DEFAULT_WORKFLOWS_DIR = pathlib.Path(".github/workflows")
DEFAULT_REMOTE_TEMPLATE_ROOT = pathlib.Path(".github/remote-workflow-template")
DEFAULT_CONFIG_DIR = pathlib.Path("config")

# event-orchestrator suffix (after ``-aw-event-``) → remote trigger suffix.
_EVENT_TO_TRIGGER_SUFFIX: dict[str, str] = {
    "issue-comment": "issue-comment",
    "issues": "issues",
    "pull-request": "pull-request",
    "schedule": "schedule",
    "status": "status",
    "workflow-run": "workflow-run",
}

_CONTROL_PLANE_LIST = re.compile(
    r"control-plane-workflows:\s*(?:>-\s*)?(?P<body>(?:.|\n)*?)(?=\n\s{0,2}[a-zA-Z_-]+:|\Z)",
    re.MULTILINE,
)
_USES_WORKFLOW = re.compile(
    r"uses:\s*(?:\./)?\.github/workflows/(?P<name>[A-Za-z0-9_.-]+\.ya?ml)\b"
)


def _include_common_ids(org_dir: pathlib.Path) -> list[str]:
    raw = load_workflow_registry(org_dir)
    include_raw = raw.get("include_common", [])
    if include_raw is None:
        return []
    if not isinstance(include_raw, list):
        raise TypeError(f"{org_dir}: include_common must be an array when present")
    ids: list[str] = []
    for index, item in enumerate(include_raw):
        if not isinstance(item, str) or not item:
            raise ValueError(
                f"{org_dir}: include_common[{index}] must be a non-empty string"
            )
        ids.append(item)
    return ids


def _event_orchestrators(
    org_key: str, workflows_dir: pathlib.Path
) -> list[pathlib.Path]:
    if not workflows_dir.is_dir():
        return []
    return sorted(workflows_dir.glob(f"{org_key}-aw-event-*.yml")) + sorted(
        workflows_dir.glob(f"{org_key}-aw-event-*.yaml")
    )


def _basenames_in_control_plane_workflows(text: str) -> set[str]:
    found: set[str] = set()
    for match in _CONTROL_PLANE_LIST.finditer(text):
        body = match.group("body")
        found.update(re.findall(r'["\']([A-Za-z0-9_.-]+\.ya?ml)["\']', body))
    return found


def _basenames_used_by_jobs(text: str) -> set[str]:
    return {match.group("name") for match in _USES_WORKFLOW.finditer(text)}


def _trigger_suffix_for_orchestrator(path: pathlib.Path) -> str | None:
    name = path.name
    marker = "-aw-event-"
    if marker not in name:
        return None
    event_part = name.split(marker, 1)[1]
    event_part = re.sub(r"\.ya?ml$", "", event_part)
    return _EVENT_TO_TRIGGER_SUFFIX.get(event_part, event_part)


def _remote_triggers(org_key: str, remote_root: pathlib.Path) -> list[pathlib.Path]:
    template_dir = remote_root / org_key / ".github" / "workflows"
    if not template_dir.is_dir():
        return []
    return sorted(template_dir.glob(f"trigger-{org_key}-aw-*.yml")) + sorted(
        template_dir.glob(f"trigger-{org_key}-aw-*.yaml")
    )


def _has_trigger_for_suffix(
    org_key: str, trigger_suffix: str, remote_root: pathlib.Path
) -> bool:
    prefix = f"trigger-{org_key}-aw-{trigger_suffix}"
    for path in _remote_triggers(org_key, remote_root):
        stem = path.name.rsplit(".", 1)[0]
        if stem == prefix or stem.startswith(f"{prefix}-"):
            return True
    return False


def validate_org_common_opt_in(
    org_dir: pathlib.Path,
    config_dir: pathlib.Path,
    *,
    workflows_dir: pathlib.Path = DEFAULT_WORKFLOWS_DIR,
    remote_root: pathlib.Path = DEFAULT_REMOTE_TEMPLATE_ROOT,
) -> list[str]:
    """Return human-readable errors for one org (empty when valid)."""
    org_key = org_dir.name
    try:
        include_ids = _include_common_ids(org_dir)
    except (TypeError, ValueError) as exc:
        return [str(exc)]
    if not include_ids:
        return []

    try:
        common = load_common_services(config_dir)
    except (TypeError, ValueError) as exc:
        return [str(exc)]

    errors: list[str] = []
    required_basenames: set[str] = set()
    for service_id in include_ids:
        service = common.get(service_id)
        if service is None:
            known = ", ".join(sorted(common)) or "(none)"
            errors.append(
                f"{org_dir}: include_common lists unknown common service "
                f"{service_id!r} (known: {known})"
            )
            continue
        inner = service.get("inner_workflows")
        if not isinstance(inner, list) or not inner:
            errors.append(
                f"{config_dir / 'common' / 'services.json'}: service "
                f"{service_id!r} must define a non-empty inner_workflows array"
            )
            continue
        for name in inner:
            if isinstance(name, str) and name:
                required_basenames.add(name)

    if not required_basenames:
        return errors

    orchestrators = _event_orchestrators(org_key, workflows_dir)
    if not orchestrators:
        errors.append(
            f"{org_key}: include_common is set but no "
            f"{org_key}-aw-event-*.yml orchestrators exist under {workflows_dir}"
        )
        return errors

    listed: set[str] = set()
    used: set[str] = set()
    orchestrators_touching: list[pathlib.Path] = []
    for path in orchestrators:
        text = path.read_text(encoding="utf-8")
        in_list = _basenames_in_control_plane_workflows(text)
        in_uses = _basenames_used_by_jobs(text)
        listed |= in_list
        used |= in_uses
        if required_basenames & (in_list | in_uses):
            orchestrators_touching.append(path)

    missing_list = sorted(required_basenames - listed)
    if missing_list:
        errors.append(
            f"{org_key}: include_common requires these basenames in some "
            f"{org_key}-aw-event-*.yml control-plane-workflows list: "
            f"{missing_list}"
        )
    missing_uses = sorted(required_basenames - used)
    if missing_uses:
        errors.append(
            f"{org_key}: include_common requires a job uses: "
            f"./.github/workflows/<basename> for: {missing_uses}"
        )

    for path in orchestrators_touching:
        suffix = _trigger_suffix_for_orchestrator(path)
        if suffix is None:
            continue
        if not _has_trigger_for_suffix(org_key, suffix, remote_root):
            errors.append(
                f"{org_key}: orchestrator {path.name} wires included common "
                f"services but remote template is missing "
                f"trigger-{org_key}-aw-{suffix}*.yml under "
                f"{remote_root / org_key}"
            )

    return errors


def validate_all(
    config_dir: pathlib.Path = DEFAULT_CONFIG_DIR,
    *,
    workflows_dir: pathlib.Path = DEFAULT_WORKFLOWS_DIR,
    remote_root: pathlib.Path = DEFAULT_REMOTE_TEMPLATE_ROOT,
) -> list[str]:
    errors: list[str] = []
    for org_dir in discover_org_config_dirs(config_dir):
        errors.extend(
            validate_org_common_opt_in(
                org_dir,
                config_dir,
                workflows_dir=workflows_dir,
                remote_root=remote_root,
            )
        )
    return errors


def main() -> int:
    try:
        errors = validate_all()
    except (TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"common-service opt-in validation failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("common-service opt-in validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(
        "Validated include_common wiring for all orgs "
        "(event orchestrators + remote triggers)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
