"""Tests for scripts/validate_aw_workflow_permissions.py."""

from __future__ import annotations

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_aw_workflow_permissions as validator  # noqa: E402
from workflow_permissions import WorkflowPermissionResolver  # noqa: E402


def _write_workflow(path: pathlib.Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_validate_workflow_rejects_missing_discussions_for_gh_aw_callee(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    callee = workflows / "oblt-aw-duplicate-issue-detector.yml"
    _write_workflow(
        callee,
        {
            "name": "Duplicate Issue Detector",
            "on": {"workflow_call": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "duplicate-issue-detector": {
                    "permissions": {
                        "actions": "read",
                        "contents": "read",
                        "issues": "write",
                        "pull-requests": "read",
                        "copilot-requests": "write",
                    },
                    "uses": (
                        "elastic/ai-github-actions/.github/workflows/"
                        "gh-aw-duplicate-issue-detector.lock.yml@main"
                    ),
                }
            },
        },
    )

    caller = workflows / "oblt-aw-event-issues.yml"
    _write_workflow(
        caller,
        {
            "name": "Issues Event",
            "on": {"workflow_call": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "duplicate-issue-detector": {
                    "permissions": {
                        "actions": "read",
                        "contents": "read",
                        "issues": "write",
                        "pull-requests": "read",
                        "copilot-requests": "write",
                    },
                    "uses": "./.github/workflows/oblt-aw-duplicate-issue-detector.yml",
                }
            },
        },
    )

    lock_text = """
name: gh-aw duplicate issue detector
on:
  workflow_call: {}
permissions: {}
jobs:
  conclusion:
    permissions:
      contents: read
      discussions: write
      issues: write
  safe_outputs:
    permissions:
      contents: read
      discussions: write
      issues: write
"""

    def fetch_remote(owner: str, repo: str, workflow_path: str, ref: str) -> str:
        assert owner == "elastic"
        assert repo == "ai-github-actions"
        assert workflow_path.endswith("gh-aw-duplicate-issue-detector.lock.yml")
        return lock_text

    resolver = WorkflowPermissionResolver(workflows, fetch_remote_workflow=fetch_remote)
    errors = validator.validate_workflow_file(caller, resolver)
    assert any("discussions" in err for err in errors)


def test_validate_workflow_accepts_aligned_local_and_remote_chain(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    callee = workflows / "oblt-aw-duplicate-issue-detector.yml"
    _write_workflow(
        callee,
        {
            "name": "Duplicate Issue Detector",
            "on": {"workflow_call": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "duplicate-issue-detector": {
                    "permissions": {
                        "actions": "read",
                        "contents": "read",
                        "discussions": "write",
                        "issues": "write",
                        "pull-requests": "read",
                        "copilot-requests": "write",
                    },
                    "uses": (
                        "elastic/ai-github-actions/.github/workflows/"
                        "gh-aw-duplicate-issue-detector.lock.yml@main"
                    ),
                }
            },
        },
    )

    caller = workflows / "oblt-aw-event-issues.yml"
    _write_workflow(
        caller,
        {
            "name": "Issues Event",
            "on": {"workflow_call": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "duplicate-issue-detector": {
                    "permissions": {
                        "actions": "read",
                        "contents": "read",
                        "discussions": "write",
                        "issues": "write",
                        "pull-requests": "read",
                        "copilot-requests": "write",
                    },
                    "uses": "./.github/workflows/oblt-aw-duplicate-issue-detector.yml",
                }
            },
        },
    )

    lock_text = """
name: gh-aw duplicate issue detector
on:
  workflow_call: {}
permissions: {}
jobs:
  conclusion:
    permissions:
      contents: read
      discussions: write
      issues: write
"""

    resolver = WorkflowPermissionResolver(
        workflows,
        fetch_remote_workflow=lambda *_args, **_kwargs: lock_text,
    )
    assert validator.validate_workflow_file(caller, resolver) == []
    assert validator.validate_workflow_file(callee, resolver) == []


def test_validate_workflow_maps_elastic_oblt_aw_ref_to_local_file(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    event = workflows / "oblt-aw-event-issues.yml"
    _write_workflow(
        event,
        {
            "name": "Issues Event",
            "on": {"workflow_call": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "issue-triage": {
                    "permissions": {"contents": "read", "issues": "write"},
                    "uses": "./.github/workflows/oblt-aw-issue-triage.yml",
                }
            },
        },
    )

    route = workflows / "oblt-aw-issue-triage.yml"
    _write_workflow(
        route,
        {
            "name": "Issue Triage",
            "on": {"workflow_call": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "noop": {
                    "runs-on": "ubuntu-latest",
                    "steps": [{"run": "echo ok"}],
                }
            },
        },
    )

    trigger = workflows / "trigger-oblt-aw-issues.yml"
    _write_workflow(
        trigger,
        {
            "name": "Trigger",
            "on": {"issues": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "run-oblt-aw-issues": {
                    "permissions": {"contents": "read", "issues": "write"},
                    "uses": (
                        "elastic/oblt-aw/.github/workflows/"
                        "oblt-aw-event-issues.yml@main"
                    ),
                }
            },
        },
    )

    resolver = WorkflowPermissionResolver(workflows)
    assert validator.validate_workflow_file(trigger, resolver) == []
