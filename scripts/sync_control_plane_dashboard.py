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
2. Build body from every org under ``config/<org-key>/`` that lists this repo in
   ``active-repositories.json`` (merged sections, three-part checkbox markers)
3. Create (POST) or update (PATCH) issue with title "[oblt-aw] Control Plane Dashboard"
4. Pin issue via gh issue pin; if pin fails (e.g. 3 already pinned), log and continue

On every run: title and table format are updated to current spec; user's enabled
state is preserved per compound ``org:workflow-id``. Legacy two-part markers map
to the ``obs`` org.

Invoked per-repo by the sync-control-plane-dashboard workflow matrix.

Related issues: https://github.com/elastic/observability-robots/issues/3732,
https://github.com/elastic/observability-robots/issues/4189
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

from common import (
    LEGACY_DEFAULT_ORG_KEY,
    compound_workflow_key,
    discover_org_config_dirs,
    format_oblt_aw_marker,
    parse_repositories,
)

DASHBOARD_LABEL = "oblt-aw/dashboard"
DASHBOARD_TITLE = "[oblt-aw] Control Plane Dashboard"

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging to stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def parse_checkbox_state(body: str | None) -> dict[str, bool]:
    """Extract ``org:workflow-id`` -> enabled from task list lines."""
    state: dict[str, bool] = {}
    if not body:
        return state
    for line in body.splitlines():
        m3 = re.match(r"^- \[x\] <!-- oblt-aw:([a-z0-9-]+):([a-z0-9-]+) -->", line)
        if m3:
            state[compound_workflow_key(m3.group(1), m3.group(2))] = True
            continue
        m3d = re.match(r"^- \[ \] <!-- oblt-aw:([a-z0-9-]+):([a-z0-9-]+) -->", line)
        if m3d:
            state[compound_workflow_key(m3d.group(1), m3d.group(2))] = False
            continue
        m2 = re.match(r"^- \[x\] <!-- oblt-aw:([a-z0-9-]+) -->", line)
        if m2:
            state[compound_workflow_key(LEGACY_DEFAULT_ORG_KEY, m2.group(1))] = True
            continue
        m2d = re.match(r"^- \[ \] <!-- oblt-aw:([a-z0-9-]+) -->", line)
        if m2d:
            state[compound_workflow_key(LEGACY_DEFAULT_ORG_KEY, m2d.group(1))] = False
            continue
    return state


def maturity_badge(maturity: str) -> str:
    """Return a short maturity badge for display."""
    badges = {
        "stable": "🟢 stable",
        "early-adoption": "🟡 early-adoption",
        "experimental": "🟠 experimental",
    }
    return badges.get(maturity, maturity)


def default_section_heading(org_key: str) -> str:
    """Fallback section title when ``workflow-registry.json`` omits ``section_title``."""
    if org_key == "obs":
        return "Observability"
    return org_key.replace("-", " ").title()


def load_org_registry_section(org_dir: Path) -> tuple[str, str, list[dict[str, Any]]]:
    """Return (org_key, section_heading, workflows) from one org directory."""
    org_key = org_dir.name
    raw = json.loads((org_dir / "workflow-registry.json").read_text(encoding="utf-8"))
    heading = (raw.get("section_title") or "").strip() or default_section_heading(
        org_key
    )
    workflows = raw.get("workflows", [])
    return org_key, heading, workflows


def org_config_dirs_for_target_repo(config_dir: Path, target_repo: str) -> list[Path]:
    """Org directories under ``config`` whose active repository list includes ``target_repo``."""
    roots: list[Path] = []
    for od in discover_org_config_dirs(config_dir):
        repos = parse_repositories(
            (od / "active-repositories.json").read_text(encoding="utf-8")
        )
        if target_repo in repos:
            roots.append(od)
    return sorted(roots, key=lambda p: p.name)


def build_dashboard_body(
    org_sections: list[tuple[str, str, list[dict[str, Any]]]],
    existing_body: str | None,
) -> str:
    """Build one dashboard body with a Markdown section per org.

    Each ``org_sections`` item is ``(org_key, section_heading, workflows)``.
    Preserves enabled/disabled state from ``existing_body`` for compound ids and
    legacy two-part ``obs`` markers.
    """
    parsed = parse_checkbox_state(existing_body)
    lines = [
        "## Control Plane Dashboard",
        "",
        "Use this dashboard to enable or disable agentic workflows for this repository. ",
        "Click the checkboxes below to toggle workflows on or off.",
        "",
    ]
    for org_key, section_heading, workflows in org_sections:
        lines.extend(
            [
                f"### {section_heading} ({org_key})",
                "",
                "| Workflow | Maturity | Description |",
                "|----------|----------|-------------|",
            ]
        )
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
                "#### Enable / Disable",
                "",
                "Click a checkbox to enable or disable a workflow:",
                "",
            ]
        )
        for wf in workflows:
            wf_id = wf["id"]
            name = wf.get("name", wf_id)
            default = wf.get("default_enabled", True)
            cmp_key = compound_workflow_key(org_key, wf_id)
            enabled = parsed.get(cmp_key, default)
            checkbox = "- [x]" if enabled else "- [ ]"
            marker = format_oblt_aw_marker(org_key, wf_id)
            lines.append(f"{checkbox} {marker} {name}")
        lines.append("")
    lines.extend(
        [
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
    org_sections: list[tuple[str, str, list[dict[str, Any]]]],
) -> None:
    """Sync dashboard issue for one repository."""
    owner, _, repo_name = repo.partition("/")
    if not repo_name:
        logger.error("Invalid repo format: %s", repo)
        return
    existing = find_dashboard_issue(owner, repo_name, token)
    body = build_dashboard_body(org_sections, existing["body"] if existing else None)
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
    config_dir = root / "config"
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("GH_TOKEN or GITHUB_TOKEN must be set")
        return 1

    org_dirs = org_config_dirs_for_target_repo(config_dir, args.repo)
    if not org_dirs:
        logger.error(
            "Repository %s is not listed in any config/<org-key>/active-repositories.json",
            args.repo,
        )
        return 1

    org_sections: list[tuple[str, str, list[dict[str, Any]]]] = []
    for od in org_dirs:
        org_sections.append(load_org_registry_section(od))
    if not any(wfs for _, _, wfs in org_sections):
        logger.warning("No workflows in org registries for %s", args.repo)

    try:
        sync_repo(args.repo, token, org_sections)
    except Exception as e:
        logger.exception("Failed to sync %s: %s", args.repo, e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
