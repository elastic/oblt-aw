"""Workflow-contract: approval assert gates merge and binds the merge SHA."""

from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "obs-aw-automerge.yml"


def _load_workflow() -> dict:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{WORKFLOW}: expected mapping root"
    jobs = data.get("jobs")
    assert isinstance(jobs, dict), f"{WORKFLOW}: missing jobs"
    return jobs


def test_automerge_needs_successful_assert_approved_review() -> None:
    jobs = _load_workflow()
    automerge = jobs["automerge"]
    needs = automerge.get("needs") or []
    assert "assert-approved-review" in needs
    job_if = automerge.get("if") or ""
    assert "needs.assert-approved-review.result == 'success'" in job_if


def test_assert_approved_review_job_exists() -> None:
    jobs = _load_workflow()
    assert "assert-approved-review" in jobs
    assert_job = jobs["assert-approved-review"]
    needs = assert_job.get("needs") or []
    assert "approve" in needs


def test_primary_merge_is_sha_bound_rest_not_pascalgn() -> None:
    """COMMENT-only / head rewrite must not reach an unbound merge action."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pascalgn/automerge-action" not in text
    assert "UPDATE_LABELS" not in text
    jobs = _load_workflow()
    automerge = jobs["automerge"]
    steps = automerge.get("steps") or []
    merge_steps = [s for s in steps if s.get("id") == "merge-pull-request"]
    assert len(merge_steps) == 1
    merge = merge_steps[0]
    assert "uses" not in merge
    run = merge.get("run") or ""
    assert "automerge_squash_merge_at_sha" in run
    assert '"${PR_AUTHOR}"' in run or "${PR_AUTHOR}" in run
    env = merge.get("env") or {}
    assert env.get("ASSERTED_SHA") == (
        "${{ needs.assert-approved-review.outputs.head_sha }}"
    )
    assert env.get("PR_AUTHOR") == ("${{ github.event.pull_request.user.login }}")


def test_rest_merge_binds_asserted_head_sha() -> None:
    jobs = _load_workflow()
    rest = jobs["rest-merge"]
    steps = rest.get("steps") or []
    merge_steps = [s for s in steps if s.get("id") == "merge"]
    assert len(merge_steps) == 1
    env = merge_steps[0].get("env") or {}
    assert env.get("HEAD_SHA") == (
        "${{ needs.assert-approved-review.outputs.head_sha }}"
    )
    assert env.get("PR_AUTHOR") == ("${{ github.event.pull_request.user.login }}")
    run = merge_steps[0].get("run") or ""
    assert "automerge_squash_merge_at_sha" in run
    assert "${PR_AUTHOR}" in run
