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


def test_merge_jobs_propagate_merge_time_assert_reason() -> None:
    """Approval lost after the initial assert must not be reported as a rules failure."""
    jobs = _load_workflow()
    automerge = jobs["automerge"]
    outputs = automerge.get("outputs") or {}
    assert outputs.get("merge_assert_reason") == (
        "${{ steps.merge-pull-request.outputs.assertReason }}"
    )
    merge_run = next(
        s.get("run") or ""
        for s in (automerge.get("steps") or [])
        if s.get("id") == "merge-pull-request"
    )
    assert "assertReason=${assert_reason}" in merge_run

    rest = jobs["rest-merge"]
    rest_if = rest.get("if") or ""
    assert "merge_assert_reason != 'missing_approval'" in rest_if
    assert "merge_assert_reason != 'verify_failed'" in rest_if
    rest_outputs = rest.get("outputs") or {}
    assert rest_outputs.get("merge_assert_reason") == (
        "${{ steps.merge.outputs.assertReason }}"
    )

    report = jobs["report-automerge-outcome"]
    report_env = next(
        (s.get("env") or {})
        for s in (report.get("steps") or [])
        if "Report outcome" in (s.get("name") or "")
    )
    assert "MERGE_ASSERT_REASON" in report_env
    merge_assert_expr = report_env["MERGE_ASSERT_REASON"]
    assert "merge_assert_reason" in merge_assert_expr
    # Fallback reason must win when present (primary ok must not mask it).
    rest_pos = merge_assert_expr.find("needs.rest-merge.outputs.merge_assert_reason")
    auto_pos = merge_assert_expr.find("needs.automerge.outputs.merge_assert_reason")
    assert rest_pos != -1 and auto_pos != -1 and rest_pos < auto_pos
    report_run = next(
        s.get("run") or ""
        for s in (report.get("steps") or [])
        if "Report outcome" in (s.get("name") or "")
    )
    assert "fail_on_assert_reason" in report_run
    assert "MERGE_ASSERT_REASON" in report_run
