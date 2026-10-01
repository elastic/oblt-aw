"""Tests for scripts/validate_aw_workflow_permissions.py."""

from __future__ import annotations

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_aw_workflow_permissions as validator
from workflow_permissions import WorkflowPermissionResolver


def _write_workflow(path: pathlib.Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_validate_workflow_rejects_missing_discussions_for_gh_aw_callee(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    callee = workflows / "obs-aw-duplicate-issue-detector.yml"
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

    caller = workflows / "obs-aw-event-issues.yml"
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
                    "uses": "./.github/workflows/obs-aw-duplicate-issue-detector.yml",
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

    callee = workflows / "obs-aw-duplicate-issue-detector.yml"
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

    caller = workflows / "obs-aw-event-issues.yml"
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
                    "uses": "./.github/workflows/obs-aw-duplicate-issue-detector.yml",
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

    event = workflows / "obs-aw-event-issues.yml"
    _write_workflow(
        event,
        {
            "name": "Issues Event",
            "on": {"workflow_call": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "issue-triage": {
                    "permissions": {"contents": "read", "issues": "write"},
                    "uses": "./.github/workflows/obs-aw-issue-triage.yml",
                }
            },
        },
    )

    route = workflows / "obs-aw-issue-triage.yml"
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

    trigger = workflows / "trigger-obs-aw-issues.yml"
    _write_workflow(
        trigger,
        {
            "name": "Trigger",
            "on": {"issues": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "run-obs-aw-issues": {
                    "permissions": {"contents": "read", "issues": "write"},
                    "uses": (
                        "elastic/oblt-aw/.github/workflows/obs-aw-event-issues.yml@main"
                    ),
                }
            },
        },
    )

    resolver = WorkflowPermissionResolver(workflows)
    assert validator.validate_workflow_file(trigger, resolver) == []


def test_list_workflow_files_includes_remote_workflow_templates(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    control_plane = workflows / "obs-aw-event-schedule.yml"
    control_plane.write_text("name: cp\n", encoding="utf-8")

    remote = (
        tmp_path
        / ".github"
        / "remote-workflow-template"
        / "obs"
        / ".github"
        / "workflows"
    )
    remote.mkdir(parents=True)
    client = remote / "trigger-obs-aw-schedule-frequent.yml"
    client.write_text("name: client\n", encoding="utf-8")

    listed = validator.list_workflow_files(
        workflows_dir=workflows,
        remote_template_dir=tmp_path / ".github" / "remote-workflow-template",
    )
    assert control_plane in listed
    assert client in listed


def test_validate_remote_frequent_caller_rejects_narrow_permissions(
    tmp_path: pathlib.Path,
) -> None:
    """Regression: GitHub startup_failure when frequent caller omits daily union."""
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    _write_workflow(
        workflows / "obs-aw-event-schedule.yml",
        {
            "name": "Schedule Event",
            "on": {"workflow_call": None},
            "permissions": {"contents": "read"},
            "jobs": {
                "autodoc": {
                    "permissions": {
                        "actions": "read",
                        "contents": "write",
                        "copilot-requests": "write",
                        "id-token": "write",
                        "issues": "write",
                        "pull-requests": "write",
                    },
                    "runs-on": "ubuntu-latest",
                    "steps": [{"run": "echo daily"}],
                },
                "automerge-deferred": {
                    "permissions": {
                        "actions": "read",
                        "contents": "write",
                        "id-token": "write",
                        "pull-requests": "write",
                    },
                    "runs-on": "ubuntu-latest",
                    "steps": [{"run": "echo frequent"}],
                },
            },
        },
    )

    remote = (
        tmp_path
        / ".github"
        / "remote-workflow-template"
        / "obs"
        / ".github"
        / "workflows"
    )
    remote.mkdir(parents=True)
    frequent = remote / "trigger-obs-aw-schedule-frequent.yml"
    _write_workflow(
        frequent,
        {
            "name": "Schedule frequent",
            "on": {"schedule": [{"cron": "*/15 * * * *"}]},
            "permissions": {"contents": "read"},
            "jobs": {
                "run-obs-aw-schedule-frequent": {
                    "permissions": {
                        "actions": "read",
                        "contents": "write",
                        "id-token": "write",
                        "issues": "read",
                        "pull-requests": "write",
                    },
                    "uses": (
                        "elastic/oblt-aw/.github/workflows/"
                        "obs-aw-event-schedule.yml@main"
                    ),
                }
            },
        },
    )

    resolver = WorkflowPermissionResolver(workflows)
    errors = validator.validate_workflow_file(frequent, resolver)
    assert any("copilot-requests" in err for err in errors)
    assert any("issues" in err and "write" in err for err in errors)

    listed = validator.list_workflow_files(
        workflows_dir=workflows,
        remote_template_dir=tmp_path / ".github" / "remote-workflow-template",
    )
    assert frequent in listed
