"""Tests for explicit issue-fixer workflow model selection."""

from __future__ import annotations

import pathlib

import yaml


WORKFLOWS_DIR = pathlib.Path(__file__).parent.parent / ".github" / "workflows"
EXPECTED_MODEL = "gpt-5-mini"


def test_issue_fixer_wrappers_set_supported_model() -> None:
    workflow_paths = sorted(WORKFLOWS_DIR.glob("*.yml"))
    matching = []

    for path in workflow_paths:
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        jobs = workflow.get("jobs", {})
        for job in jobs.values():
            if (
                job.get("uses")
                == "elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main"
            ):
                matching.append(path.name)
                assert job.get("with", {}).get("model") == EXPECTED_MODEL

    assert matching == [
        "oblt-aw-issue-fixer.yml",
        "oblt-aw-resource-not-accessible-by-integration-fixer.yml",
        "oblt-aw-security-fixer.yml",
    ]
