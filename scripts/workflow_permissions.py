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

"""Helpers for comparing GitHub Actions workflow permission scopes."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

PERMISSION_LEVELS = {"read": 1, "write": 2}

REUSABLE_WORKFLOW_USES = re.compile(
    r"^\.?/?\.github/workflows/.+\.ya?ml$|"
    r"^[^/]+/[^/]+/\.github/workflows/.+\.ya?ml$",
    re.IGNORECASE,
)

REUSABLE_WORKFLOW_REF = re.compile(
    r"^(?P<location>\.?/?\.github/workflows/[^@]+\.ya?ml|"
    r"(?P<owner>[^/]+)/(?P<repo>[^/]+)/\.github/workflows/[^@]+\.ya?ml)"
    r"(?:@(?P<ref>.+))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReusableWorkflowRef:
    owner: str | None
    repo: str | None
    workflow_path: str
    ref: str | None
    raw: str


def parse_reusable_workflow_uses(uses: str) -> ReusableWorkflowRef | None:
    uses = uses.strip().split("#", 1)[0].strip()
    if not REUSABLE_WORKFLOW_USES.match(uses.split("@", 1)[0]):
        return None

    match = REUSABLE_WORKFLOW_REF.match(uses)
    if not match:
        return None

    location = match.group("location")
    if location.startswith("./.github/workflows/") or location.startswith(
        ".github/workflows/"
    ):
        workflow_path = location.removeprefix("./")
        return ReusableWorkflowRef(
            owner=None,
            repo=None,
            workflow_path=workflow_path,
            ref=match.group("ref"),
            raw=uses,
        )

    owner = match.group("owner")
    repo = match.group("repo")
    workflow_path = location.split(f"{owner}/{repo}/", 1)[1]
    return ReusableWorkflowRef(
        owner=owner,
        repo=repo,
        workflow_path=workflow_path,
        ref=match.group("ref"),
        raw=uses,
    )


def parse_permissions_block(permissions: Any) -> dict[str, str]:
    if permissions is None:
        return {}
    if permissions == {}:
        return {}
    if not isinstance(permissions, dict):
        raise ValueError(f"unsupported permissions block: {permissions!r}")
    return {str(scope): str(level).lower() for scope, level in permissions.items()}


def effective_job_permissions(
    workflow_permissions: Any,
    job: dict[str, Any],
) -> dict[str, str]:
    root = parse_permissions_block(workflow_permissions)
    job_permissions = job.get("permissions", "__unset__")
    if job_permissions == "__unset__":
        return dict(root)
    if job_permissions == {}:
        return dict(root)
    return parse_permissions_block(job_permissions)


def merge_max_permissions(
    left: dict[str, str],
    right: dict[str, str],
) -> dict[str, str]:
    merged = dict(left)
    for scope, level in right.items():
        if scope not in merged:
            merged[scope] = level
            continue
        if PERMISSION_LEVELS[level] > PERMISSION_LEVELS[merged[scope]]:
            merged[scope] = level
    return merged


def permission_deficits(
    caller: dict[str, str],
    required: dict[str, str],
) -> list[tuple[str, str, str]]:
    deficits: list[tuple[str, str, str]] = []
    for scope, required_level in sorted(required.items()):
        caller_level = caller.get(scope, "none")
        if PERMISSION_LEVELS.get(caller_level, 0) < PERMISSION_LEVELS.get(
            required_level, 0
        ):
            deficits.append((scope, caller_level, required_level))
    return deficits


def is_reusable_workflow_job(job: dict[str, Any]) -> bool:
    uses = job.get("uses")
    return isinstance(uses, str) and parse_reusable_workflow_uses(uses) is not None


class WorkflowPermissionResolver:
    """Resolve reusable workflow YAML and compute permission ceilings."""

    def __init__(
        self,
        workflows_dir: Path,
        *,
        local_owner: str = "elastic",
        local_repo: str = "oblt-aw",
        fetch_remote_workflow: Any | None = None,
    ) -> None:
        self.workflows_dir = workflows_dir
        self.local_owner = local_owner
        self.local_repo = local_repo
        self._cache: dict[str, dict[str, Any]] = {}
        self._requirements_cache: dict[str, dict[str, str]] = {}
        self._fetch_remote_workflow = fetch_remote_workflow or self._default_fetch

    def resolve(self, workflow_ref: ReusableWorkflowRef) -> dict[str, Any]:
        cache_key = self._cache_key(workflow_ref)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._is_local_ref(workflow_ref):
            path = self.workflows_dir.parent.parent / workflow_ref.workflow_path
            if not path.is_file():
                raise FileNotFoundError(f"missing local workflow: {path}")
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            owner = workflow_ref.owner or ""
            repo = workflow_ref.repo or ""
            ref = workflow_ref.ref or "main"
            text = self._fetch_remote_workflow(
                owner, repo, workflow_ref.workflow_path, ref
            )
            data = yaml.safe_load(text)

        if not isinstance(data, dict):
            raise ValueError(f"workflow is not a mapping: {workflow_ref.raw}")

        self._cache[cache_key] = data
        return data

    def callee_requirements(self, workflow_ref: ReusableWorkflowRef) -> dict[str, str]:
        cache_key = self._cache_key(workflow_ref)
        if cache_key in self._requirements_cache:
            return self._requirements_cache[cache_key]

        workflow = self.resolve(workflow_ref)
        required = self._workflow_requirements(workflow)
        self._requirements_cache[cache_key] = required
        return required

    def _workflow_requirements(self, workflow: dict[str, Any]) -> dict[str, str]:
        required: dict[str, str] = {}
        jobs = workflow.get("jobs")
        if not isinstance(jobs, dict):
            return required

        root_permissions = workflow.get("permissions")
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            effective = effective_job_permissions(root_permissions, job)
            required = merge_max_permissions(required, effective)

            uses = job.get("uses")
            if isinstance(uses, str):
                nested_ref = parse_reusable_workflow_uses(uses)
                if nested_ref is not None:
                    nested_required = self.callee_requirements(nested_ref)
                    required = merge_max_permissions(required, nested_required)

        return required

    def _is_local_ref(self, workflow_ref: ReusableWorkflowRef) -> bool:
        if workflow_ref.owner is None:
            return True
        return (
            workflow_ref.owner == self.local_owner
            and workflow_ref.repo == self.local_repo
        )

    def _cache_key(self, workflow_ref: ReusableWorkflowRef) -> str:
        if self._is_local_ref(workflow_ref):
            return f"local:{workflow_ref.workflow_path}"
        return (
            f"remote:{workflow_ref.owner}/{workflow_ref.repo}/"
            f"{workflow_ref.workflow_path}@{workflow_ref.ref or 'main'}"
        )

    def _default_fetch(
        self, owner: str, repo: str, workflow_path: str, ref: str
    ) -> str:
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{workflow_path}?ref={ref}"
        request = urllib.request.Request(url)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        if token:
            request.add_header("Authorization", f"Bearer {token}")

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"failed to fetch {owner}/{repo}/{workflow_path}@{ref}: HTTP {exc.code}"
            ) from exc

        content = payload.get("content")
        if not isinstance(content, str):
            raise RuntimeError(
                f"unexpected GitHub API response for {owner}/{repo}/{workflow_path}@{ref}"
            )
        return base64.b64decode(content).decode("utf-8")
