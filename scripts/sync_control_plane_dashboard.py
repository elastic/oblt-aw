#!/usr/bin/env python3
"""
Sync Control Plane Dashboard issues across repositories in active-repositories.json.

For each repository:
1. Search for open issue with label oblt-aw/dashboard
2. Build body from workflow-registry.json (header, maturity badges, checkboxes)
3. Create (POST) or update (PATCH) issue with title "[OBLT AW] Control Plane Dashboard"
4. Pin issue via gh issue pin; if pin fails (e.g. 3 already pinned), log and continue

Related issue: https://github.com/elastic/observability-robots/issues/3732
"""

from __future__ import annotations

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
DASHBOARD_TITLE = "[OBLT AW] Control Plane Dashboard"
CHECKBOX_PATTERN = re.compile(r"^- \[([ x])\] <!-- oblt-aw:([a-z0-9-]+) -->")

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging to stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def parse_repositories(content: str) -> list[str]:
    """Parse active-repositories.json content into a list of owner/repo strings."""
    data = json.loads(content) if content else {"repositories": []}
    if isinstance(data, dict):
        repositories = data.get("repositories", [])
    elif isinstance(data, list):
        repositories = data
    else:
        raise SystemExit(
            "active-repositories.json must be a list or object with 'repositories'"
        )
    if not isinstance(repositories, list):
        raise SystemExit("'repositories' must be a list")
    normalized = []
    for item in repositories:
        if not isinstance(item, str) or "/" not in item:
            raise SystemExit(
                f"Invalid repository entry: {item!r}. Expected 'owner/repo'"
            )
        normalized.append(item.strip())
    return sorted(set(normalized))


def parse_checkbox_state(body: str | None) -> dict[str, bool]:
    """Extract workflow-id -> enabled from issue body using checkbox pattern."""
    state: dict[str, bool] = {}
    if not body:
        return state
    for line in body.splitlines():
        m = CHECKBOX_PATTERN.match(line.strip())
        if m:
            checked, workflow_id = m.groups()
            state[workflow_id] = checked.strip().lower() == "x"
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
    workflows: list[dict],
    existing_body: str | None,
) -> str:
    """Build dashboard issue body from workflow registry, preserving user checkbox state."""
    parsed = parse_checkbox_state(existing_body)
    lines = [
        "## Control Plane Dashboard",
        "",
        "Use this dashboard to enable or disable agentic workflows for this repository. "
        "Check a workflow to enable it; uncheck to disable.",
        "",
        "### Workflows",
        "",
        "| Workflow | Maturity | Opt-in | Description |",
        "|----------|----------|--------|-------------|",
    ]
    for wf in workflows:
        wf_id = wf["id"]
        name = wf.get("name", wf_id)
        maturity = wf.get("maturity", "experimental")
        desc = wf.get("description", "")
        default = wf.get("default_enabled", True)
        enabled = parsed.get(wf_id, default)
        checkbox = "- [x]" if enabled else "- [ ]"
        badge = maturity_badge(maturity)
        lines.append(
            f"| {name} | {badge} | {checkbox} <!-- oblt-aw:{wf_id} --> | {desc} |"
        )
    lines.extend(
        [
            "",
            "### Instructions",
            "",
            "- **Enable a workflow:** Check the checkbox next to the workflow.",
            "- **Disable a workflow:** Uncheck the checkbox.",
            "- Changes are applied when the config sync workflow runs (triggered by editing this issue).",
        ]
    )
    return "\n".join(lines)


def gh_api(
    method: str,
    path: str,
    token: str,
    *,
    data: dict | None = None,
) -> dict | list:
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
            return json.loads(result.stdout) if result.stdout.strip() else {}
        finally:
            Path(f.name).unlink(missing_ok=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            logger.error("gh api failed: %s", result.stderr)
            raise RuntimeError(f"gh api failed: {result.stderr}")
        return json.loads(result.stdout) if result.stdout.strip() else []


def find_dashboard_issue(owner: str, repo: str, token: str) -> dict | None:
    """Find open issue with label oblt-aw/dashboard. Returns first match or None."""
    labels_param = quote(DASHBOARD_LABEL, safe="")
    path = f"/repos/{owner}/{repo}/issues?labels={labels_param}&state=open&per_page=5"
    issues = gh_api("GET", path, token)
    if not isinstance(issues, list):
        return None
    for issue in issues:
        if issue.get("pull_request") is None and issue.get("title") == DASHBOARD_TITLE:
            return issue
    return None


def create_issue(owner: str, repo: str, token: str, body: str) -> dict:
    """Create dashboard issue."""
    path = f"/repos/{owner}/{repo}/issues"
    data = {
        "title": DASHBOARD_TITLE,
        "body": body,
        "labels": [DASHBOARD_LABEL],
    }
    return gh_api("POST", path, token, data=data)


def update_issue(
    owner: str, repo: str, issue_number: int, token: str, body: str
) -> dict:
    """Update dashboard issue body."""
    path = f"/repos/{owner}/{repo}/issues/{issue_number}"
    data = {"body": body}
    return gh_api("PATCH", path, token, data=data)


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
    workflows: list[dict],
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
    setup_logging()
    root = Path(__file__).resolve().parent.parent
    registry_path = root / "workflow-registry.json"
    active_path = root / "active-repositories.json"
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("GH_TOKEN or GITHUB_TOKEN must be set")
        return 1
    if not registry_path.exists():
        logger.error("workflow-registry.json not found at %s", registry_path)
        return 1
    if not active_path.exists():
        logger.error("active-repositories.json not found at %s", active_path)
        return 1
    registry = json.loads(registry_path.read_text())
    workflows = registry.get("workflows", [])
    if not workflows:
        logger.warning("No workflows in registry")
    repos = parse_repositories(active_path.read_text())
    if not repos:
        logger.warning("No repositories in active-repositories.json")
        return 0
    for repo in repos:
        try:
            sync_repo(repo, token, workflows)
        except Exception as e:
            logger.exception("Failed to sync %s: %s", repo, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
