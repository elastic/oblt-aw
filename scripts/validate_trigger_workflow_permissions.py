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
Validate *-aw-* control-plane workflows and client trigger templates:

1. Jobs calling gh-aw-*.lock.yml declare exactly the upstream lock permissions.
2. Trigger run-aw jobs declare exactly the union of all job permissions in the callee.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

PERM_ORDER = {"read": 1, "write": 2}
PERM_KEY_ORDER = (
    "actions",
    "checks",
    "contents",
    "discussions",
    "id-token",
    "issues",
    "pull-requests",
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = ROOT / ".github/workflows"
LOCK_PERMISSIONS_PATH = (
    pathlib.Path(__file__).resolve().parent / "gh_aw_lock_permissions.json"
)
TEMPLATE_ROOTS = (
    ROOT / ".github/remote-workflow-template/obs/.github/workflows",
    ROOT / ".github/remote-workflow-template/docs/.github/workflows",
)

RUN_AW_JOB = re.compile(r"^\s+run-aw:\s*$", re.MULTILINE)
JOB_PERMISSIONS = re.compile(
    r"^    permissions:\s*\n((?:      [a-z0-9-]+: (?:read|write)\n)+)",
    re.MULTILINE,
)
WORKFLOW_PERMISSIONS = re.compile(
    r"^permissions:\s*\n((?:  [a-z0-9-]+: (?:read|write)\n)+)",
    re.MULTILINE,
)
USES_GH_AW = re.compile(
    r"uses:\s+elastic/(?P<org>ai-github-actions|docs-actions)/\.github/workflows/"
    r"(?P<lock>gh-aw-[^@\s]+\.lock\.yml)@(?P<ref>[^\s#]+)",
)
JOB_BLOCK = re.compile(
    r"^  (?P<id>[a-z0-9-]+):\n(?P<body>(?:    .*\n)*?)(?=^  [a-z0-9-]+:|\Z)",
    re.MULTILINE,
)
AW_SUBJECT = re.compile(r".+-aw-.+\.ya?ml$")


def merge_perms(acc: dict[str, str], block: dict[str, str]) -> dict[str, str]:
    for key, level in block.items():
        if key not in acc or PERM_ORDER.get(level, 0) > PERM_ORDER.get(acc[key], 0):
            acc[key] = level
    return acc


def parse_permission_block(text: str) -> dict[str, str]:
    block: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s+([a-z0-9-]+):\s*(read|write)\s*$", line)
        if match:
            block[match.group(1)] = match.group(2)
    return block


def load_lock_permissions() -> dict[str, dict[str, str]]:
    data = json.loads(LOCK_PERMISSIONS_PATH.read_text(encoding="utf-8"))
    return {key: dict(value) for key, value in data.items()}


def lock_key(org: str, ref: str, lock: str) -> str:
    repo = "ai-github-actions" if org == "ai-github-actions" else "docs-actions"
    return f"elastic/{repo}@{ref}:{lock}"


def collect_reusable_permissions(path: pathlib.Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    acc: dict[str, str] = {}

    jobs_idx = text.find("\njobs:")
    head = text[:jobs_idx] if jobs_idx >= 0 else text
    workflow_match = WORKFLOW_PERMISSIONS.search(head)
    if workflow_match:
        merge_perms(acc, parse_permission_block(workflow_match.group(1)))

    for match in re.finditer(
        r"^    permissions:\s*\n((?:      [a-z0-9-]+: (?:read|write)\n)+)",
        text,
        re.MULTILINE,
    ):
        merge_perms(acc, parse_permission_block(match.group(1)))

    return acc


def list_aw_workflows() -> list[pathlib.Path]:
    paths = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    return [
        p
        for p in paths
        if AW_SUBJECT.match(p.name)
        and p.name
        not in {
            "aw-prelude.yml",
            "get-enabled-workflows.yml",
            "load-allowed-authors.yml",
        }
    ]


def validate_gh_aw_job_permissions(
    path: pathlib.Path, locks: dict[str, dict[str, str]]
) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for match in JOB_BLOCK.finditer(text):
        job_id = match.group("id")
        body = match.group("body")
        uses = USES_GH_AW.search(body)
        if not uses:
            continue
        perm_match = re.search(
            r"^    permissions:\s*\n((?:      [a-z0-9-]+: (?:read|write)\n)+)",
            body,
            re.MULTILINE,
        )
        if not perm_match:
            errors.append(
                f"{path}: job '{job_id}' calls {uses.group('lock')} but has no "
                "permissions block"
            )
            continue
        actual = parse_permission_block(perm_match.group(1))
        key = lock_key(uses.group("org"), uses.group("ref"), uses.group("lock"))
        required = locks.get(key)
        if required is None:
            errors.append(f"{path}: job '{job_id}' uses unknown lock key {key}")
            continue
        errors.extend(
            compare_permissions(
                pathlib.Path(f"{path}:{job_id}"),
                actual,
                required,
            )
        )
    return errors


def format_permissions(perms: dict[str, str]) -> str:
    lines: list[str] = []
    for key in PERM_KEY_ORDER:
        if key in perms:
            lines.append(f"      {key}: {perms[key]}")
    for key in sorted(perms):
        if key not in PERM_KEY_ORDER:
            lines.append(f"      {key}: {perms[key]}")
    return "\n".join(lines) + "\n"


def reusable_name_for_trigger(trigger_path: pathlib.Path) -> str:
    stem = trigger_path.stem
    if stem.startswith("trg-oblt-aw-"):
        return f"oblt-aw-{stem.removeprefix('trg-oblt-aw-')}.yml"
    if stem.startswith("trg-docs-aw-"):
        return f"docs-aw-{stem.removeprefix('trg-docs-aw-')}.yml"
    raise ValueError(f"Unrecognized trigger filename: {trigger_path.name}")


def parse_run_aw_permissions(trigger_path: pathlib.Path) -> dict[str, str]:
    text = trigger_path.read_text(encoding="utf-8")
    if not RUN_AW_JOB.search(text):
        raise ValueError(f"{trigger_path}: missing job id 'run-aw'")
    match = JOB_PERMISSIONS.search(text)
    if not match:
        raise ValueError(f"{trigger_path}: missing run-aw permissions block")
    return parse_permission_block(match.group(1))


def compare_permissions(
    label: pathlib.Path,
    actual: dict[str, str],
    required: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    for scope, level in required.items():
        if scope not in actual:
            errors.append(f"{label}: missing permission {scope}: {level}")
            continue
        actual_level = PERM_ORDER.get(actual[scope], 0)
        required_level = PERM_ORDER.get(level, 0)
        if actual_level < required_level:
            errors.append(f"{label}: {scope} is {actual[scope]} but requires {level}")
        elif actual_level > required_level:
            errors.append(
                f"{label}: {scope} is {actual[scope]} but only requires {level}"
            )
    for scope in actual:
        if scope not in required:
            errors.append(f"{label}: unnecessary permission {scope}: {actual[scope]}")
    return errors


def list_trigger_templates() -> list[pathlib.Path]:
    paths: list[pathlib.Path] = []
    for root in TEMPLATE_ROOTS:
        if not root.is_dir():
            raise SystemExit(f"Missing directory: {root}")
        paths.extend(sorted(root.glob("trg-*-aw-*.yml")))
    return paths


def validate_trigger(trigger_path: pathlib.Path) -> list[str]:
    reusable_name = reusable_name_for_trigger(trigger_path)
    reusable_path = WORKFLOWS_DIR / reusable_name
    if not reusable_path.is_file():
        return [f"{trigger_path}: reusable workflow not found: {reusable_path}"]

    required = collect_reusable_permissions(reusable_path)
    actual = parse_run_aw_permissions(trigger_path)
    return compare_permissions(trigger_path, actual, required)


def main() -> int:
    locks = load_lock_permissions()
    errors: list[str] = []

    aw_workflows = list_aw_workflows()
    for workflow_path in aw_workflows:
        errors.extend(validate_gh_aw_job_permissions(workflow_path, locks))

    triggers = list_trigger_templates()
    for trigger_path in triggers:
        errors.extend(validate_trigger(trigger_path))

    if errors:
        print("Workflow permission validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"Validated gh-aw permissions on {len(aw_workflows)} workflow(s) and "
        f"{len(triggers)} trigger template(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
