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
Sync Control Plane Dashboard issue for a single repository.

1. Search for open issue with label oblt-aw/dashboard (by label only, any title)
2. Build body from workflow-registry.json (header, maturity badges, checkboxes)
3. Create (POST) or update (PATCH) issue with title "[oblt-aw] Control Plane Dashboard"
4. Pin issue via gh issue pin; if pin fails (e.g. 3 already pinned), log and continue

On every run: title and table format are updated to current spec; user's enabled
state is preserved. Checkboxes use task list syntax (- [ ] / - [x]) in a list
section so they render as interactive (clickable) in GitHub.

Invoked per-repo by the sync-control-plane-dashboard workflow matrix.

Related issue: https://github.com/elastic/observability-robots/issues/3732
"""

from __future__ import annotations

import argparse
from typing import Any, cast
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

DASHBOARD_LABEL = "oblt-aw/dashboard"
DASHBOARD_TITLE = "[oblt-aw] Control Plane Dashboard"
# Task list - [x] / - [ ] in list context = interactive checkboxes
CHECKBOX_ENABLED = re.compile(r"^- \[x\] <!-- oblt-aw:([a-z0-9-]+) -->")
CHECKBOX_DISABLED = re.compile(r"^- \[ \] <!-- oblt-aw:([a-z0-9-]+) -->")

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging to stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def parse_checkbox_state(body: str | None) -> dict[str, bool]:
    """Extract workflow-id -> enabled from issue body using task list (- [x] / - [ ])."""
    state: dict[str, bool] = {}
    if not body:
        return state
    for line in body.splitlines():
        m = CHECKBOX_ENABLED.search(line)
        if m:
            state[m.group(1)] = True
            continue
        m = CHECKBOX_DISABLED.search(line)
        if m:
            state[m.group(1)] = False
    return state


def maturity_badge(maturity: str) -> str:
    """Return a short maturity badge for display."""
    badges = {
        "stable": "🟢 stable",
        "early-adoption": "🟡 early-adoption",
        "experimental": "🟠 experimental",
    }
    return badges.get(maturity, maturity)


def build_dashboard_body(
    workflows: list[dict[str, Any]],
    existing_body: str | None,
) -> str:
    """Build dashboard issue body from workflow registry.

    Preserves user's enabled/disabled state from existing_body; uses
    default_enabled from registry for workflows not yet present in the body.
    """
    parsed = parse_checkbox_state(existing_body)
    lines = [
        "## Control Plane Dashboard",
        "",
        "Use this dashboard to enable or disable agentic workflows for this repository. ",
        "Click the checkboxes below to toggle workflows on or off.",
        "",
        "### Workflows",
        "",
        "| Workflow | Maturity | Description |",
        "|----------|----------|-------------|",
    ]
    for wf in workflows:
        wf_id = wf["id"]
        name = wf.get("name", wf_id)
        maturity = wf.get("maturity", "experimental")
        desc = wf.get("description", "")
        badge = maturity_badge(maturity)
        lines.append(f"| {name} | {badge} | {desc} |")
    lines.extend(
        [
            "",
            "### Enable / Disable",
            "",
            "Click a checkbox to enable or disable a workflow:",
            "",
        ]
    )
    for wf in workflows:
        wf_id = wf["id"]
        name = wf.get("name", wf_id)
        default = wf.get("default_enabled", True)
        enabled = parsed.get(wf_id, default)
        checkbox = "- [x]" if enabled else "- [ ]"
        lines.append(f"{checkbox} <!-- oblt-aw:{wf_id} --> {name}")
    lines.extend(
        [
            "",
            "### Instructions",
            "",
            "- **Enable a workflow:** Check the checkbox next to the workflow.",
            "- **Disable a workflow:** Uncheck the checkbox.",
            "- Changes are applied at runtime when the client runs.",
        ]
    )
    return "\n".join(lines)


def gh_api(
    method: str,
    path: str,
    token: str,
    *,
    data: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    """Call GitHub REST API via gh CLI."""
    cmd = ["gh", "api", "-X", method, path, "-H", "Accept: application/vnd.github+json"]
    env = {**os.environ, "GH_TOKEN": token}
    if data is not None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            cmd.extend(["--input", f.name])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if result.returncode != 0:
                logger.error("gh api failed: %s", result.stderr)
                raise RuntimeError(f"gh api failed: {result.stderr}")
            result_data: dict[str, Any] = (
                json.loads(result.stdout) if result.stdout.strip() else {}
            )
            return result_data
        finally:
            Path(f.name).unlink(missing_ok=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            logger.error("gh api failed: %s", result.stderr)
            raise RuntimeError(f"gh api failed: {result.stderr}")
        raw: dict[str, Any] | list[Any] = (
            json.loads(result.stdout) if result.stdout.strip() else []
        )
        return raw


def find_dashboard_issue(owner: str, repo: str, token: str) -> dict[str, Any] | None:
    """Find open issue with label oblt-aw/dashboard. Returns first match or None.

    Matches by label only (not title) so existing dashboards are always found and
    updated with current title and table format, preserving user's enabled state.
    """
    labels_param = quote(DASHBOARD_LABEL, safe="")
    path = f"/repos/{owner}/{repo}/issues?labels={labels_param}&state=open&per_page=5"
    issues = gh_api("GET", path, token)
    if not isinstance(issues, list):
        return None
    for issue in issues:
        if issue.get("pull_request") is None:
            return dict(issue)
    return None


def create_issue(owner: str, repo: str, token: str, body: str) -> dict[str, Any]:
    """Create dashboard issue."""
    path = f"/repos/{owner}/{repo}/issues"
    data: dict[str, Any] = {
        "title": DASHBOARD_TITLE,
        "body": body,
        "labels": [DASHBOARD_LABEL],
    }
    return cast(dict[str, Any], gh_api("POST", path, token, data=data))


def update_issue(
    owner: str, repo: str, issue_number: int, token: str, body: str
) -> dict[str, Any]:
    """Update dashboard issue body and title."""
    path = f"/repos/{owner}/{repo}/issues/{issue_number}"
    data: dict[str, Any] = {"body": body, "title": DASHBOARD_TITLE}
    return cast(dict[str, Any], gh_api("PATCH", path, token, data=data))


def pin_issue(owner: str, repo: str, issue_number: int, token: str) -> bool:
    """Pin issue via gh CLI. Returns True on success, False on failure (e.g. 3 already pinned)."""
    result = subprocess.run(
        ["gh", "issue", "pin", str(issue_number), "--repo", f"{owner}/{repo}"],
        capture_output=True,
        text=True,
        env={**os.environ, "GH_TOKEN": token},
    )
    if result.returncode == 0:
        return True
    logger.warning(
        "Failed to pin issue #%s in %s/%s: %s",
        issue_number,
        owner,
        repo,
        result.stderr or result.stdout,
    )
    return False


def sync_repo(
    repo: str,
    token: str,
    workflows: list[dict[str, Any]],
) -> None:
    """Sync dashboard issue for one repository."""
    owner, _, repo_name = repo.partition("/")
    if not repo_name:
        logger.error("Invalid repo format: %s", repo)
        return
    existing = find_dashboard_issue(owner, repo_name, token)
    body = build_dashboard_body(workflows, existing["body"] if existing else None)
    if existing:
        issue_number = existing["number"]
        update_issue(owner, repo_name, issue_number, token, body)
        logger.info("Updated dashboard issue #%s in %s", issue_number, repo)
    else:
        created = create_issue(owner, repo_name, token, body)
        issue_number = created["number"]
        logger.info("Created dashboard issue #%s in %s", issue_number, repo)
    pin_issue(owner, repo_name, issue_number, token)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Sync Control Plane Dashboard issue for a single repository"
    )
    parser.add_argument(
        "--repo",
        metavar="OWNER/REPO",
        required=True,
        help="Repository to sync (e.g. elastic/oblt-aw)",
    )
    args = parser.parse_args()

    setup_logging()
    if "/" not in args.repo:
        logger.error("Invalid repo format: %s. Expected owner/repo", args.repo)
        return 1
    root = Path(__file__).resolve().parent.parent
    registry_path = root / "workflow-registry.json"
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("GH_TOKEN or GITHUB_TOKEN must be set")
        return 1
    if not registry_path.exists():
        logger.error("workflow-registry.json not found at %s", registry_path)
        return 1
    registry = json.loads(registry_path.read_text())
    workflows = registry.get("workflows", [])
    if not workflows:
        logger.warning("No workflows in registry")

    try:
        sync_repo(args.repo, token, workflows)
    except Exception as e:
        logger.exception("Failed to sync %s: %s", args.repo, e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
