"""
Unit tests for obs:autodoc E2E harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import autodoc_e2e_harness as harness
import oracle_autodoc_e2e as oracle

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "autodoc"
LIVE_CASE_ID = "schedule-audit-issue-live"
FIX_CASE_ID = "schedule-audit-fix-pr-live"


def _live_case() -> dict:
    return json.loads(
        (TESTDATA_ROOT / "cases" / LIVE_CASE_ID / "case.json").read_text(
            encoding="utf-8"
        )
    )


def _fix_case() -> dict:
    return json.loads(
        (TESTDATA_ROOT / "cases" / FIX_CASE_ID / "case.json").read_text(
            encoding="utf-8"
        )
    )


def _live_expectations(**overrides: object) -> dict:
    case = _live_case()
    expectations = dict(case["expectations"])
    expectations.update(overrides)
    return expectations


def _synthetic_live_outcome(**overrides: object) -> dict:
    base: dict = {
        "workflow_id": "obs:autodoc",
        "case_id": LIVE_CASE_ID,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": True,
        "fix_agent_invoked": False,
        "path_gates": {"dashboard_enabled": True},
        "schedule_trigger": {
            "run_seen": True,
            "job_executed": True,
            "job_conclusion": "success",
            "job_name": "autodoc / audit / agent",
            "url": "https://example.test/schedule",
        },
        "fix_trigger": {
            "job_executed": False,
            "job_conclusion": None,
        },
        "audit_issue": {
            "number": 42,
            "title": "[oblt-aw][autodoc] Document e2e bait",
            "url": "https://example.test/issues/42",
        },
        "fix_pr": None,
        "cleanup": {
            "completed": True,
            "bait_path": "scripts/e2e_autodoc_intentional_undocumented.py",
            "bait_removed": False,
            "bait_present": True,
            "closed_prs": [],
        },
        "bait": {
            "path": "scripts/e2e_autodoc_intentional_undocumented.py",
            "commit_sha": None,
            "created_by_this_run": False,
        },
    }
    base.update(overrides)
    return base


def _synthetic_fix_outcome(**overrides: object) -> dict:
    base = _synthetic_live_outcome(
        case_id=FIX_CASE_ID,
        fix_agent_invoked=True,
        fix_trigger={
            "job_executed": True,
            "job_conclusion": "success",
        },
        fix_pr={
            "number": 99,
            "title": "docs: Documentation analysis and improvement",
            "url": "https://example.test/pull/99",
        },
    )
    base.update(overrides)
    return base


def _evaluate(
    outcome: dict,
    *,
    case_expectations: dict | None = None,
    case_trigger: dict | None = None,
) -> dict:
    case = _live_case()
    return oracle.evaluate_outcome(
        outcome,
        case_expectations=case_expectations
        if case_expectations is not None
        else case["expectations"],
        case_trigger=case_trigger if case_trigger is not None else case["trigger"],
    )


class TestOracleHappyPath:
    def test_live_happy_path_passes(self) -> None:
        report = _evaluate(_synthetic_live_outcome())
        assert report["pass"] is True
        assert report["agent_invoked"] is True

    def test_fix_happy_path_passes(self) -> None:
        case = _fix_case()
        report = oracle.evaluate_outcome(
            _synthetic_fix_outcome(),
            case_expectations=case["expectations"],
            case_trigger=case["trigger"],
        )
        assert report["pass"] is True
        assert report["fix_pr_url"] == "https://example.test/pull/99"

    def test_missing_issue_fails(self) -> None:
        report = _evaluate(_synthetic_live_outcome(audit_issue=None))
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "audit_issue_present" in failed_ids

    def test_missing_fix_pr_fails(self) -> None:
        case = _fix_case()
        report = oracle.evaluate_outcome(
            _synthetic_fix_outcome(fix_pr=None),
            case_expectations=case["expectations"],
            case_trigger=case["trigger"],
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "fix_pr_present" in failed_ids

    def test_fix_job_executed_false_fails_despite_success_conclusion(self) -> None:
        case = _fix_case()
        report = oracle.evaluate_outcome(
            _synthetic_fix_outcome(
                fix_agent_invoked=True,
                fix_trigger={
                    "job_executed": False,
                    "job_conclusion": "success",
                },
            ),
            case_expectations=case["expectations"],
            case_trigger=case["trigger"],
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "fix_job_executed" in failed_ids

    def test_fix_job_executed_true_fails_when_fix_agent_not_expected(self) -> None:
        case = _fix_case()
        expectations = dict(case["expectations"])
        expectations["fix_agent_invoked"] = False
        expectations["expect_fix_pr"] = False
        report = oracle.evaluate_outcome(
            _synthetic_fix_outcome(
                fix_agent_invoked=False,
                fix_trigger={
                    "job_executed": True,
                    "job_conclusion": "success",
                },
                fix_pr=None,
            ),
            case_expectations=expectations,
            case_trigger=case["trigger"],
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "fix_job_executed" in failed_ids

    def test_failed_fix_leaf_fails_negative_expectations(self) -> None:
        """A failed attempt must not green fix_agent_invoked: false."""
        case = _fix_case()
        expectations = dict(case["expectations"])
        expectations["fix_agent_invoked"] = False
        expectations["expect_fix_pr"] = False
        report = oracle.evaluate_outcome(
            _synthetic_fix_outcome(
                fix_agent_invoked=True,
                fix_trigger={
                    "job_executed": True,
                    "job_conclusion": "failure",
                },
                fix_pr=None,
            ),
            case_expectations=expectations,
            case_trigger=case["trigger"],
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "fix_agent_invoked" in failed_ids
        assert "fix_job_executed" in failed_ids

    def test_failed_fix_conclusion_fails_success_check(self) -> None:
        case = _fix_case()
        report = oracle.evaluate_outcome(
            _synthetic_fix_outcome(
                fix_agent_invoked=True,
                fix_trigger={
                    "job_executed": True,
                    "job_conclusion": "failure",
                },
            ),
            case_expectations=case["expectations"],
            case_trigger=case["trigger"],
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "fix_job_success" in failed_ids

    def test_wrong_schedule_leaf_name_fails_even_with_success(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(
                schedule_trigger={
                    "run_seen": True,
                    "job_executed": True,
                    "job_conclusion": "success",
                    "job_name": "autodoc / audit / verify / agent",
                    "url": "https://example.test/schedule",
                }
            )
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "schedule_job_name" in failed_ids

    def test_nested_schedule_leaf_name_matches_canonical_suffix(self) -> None:
        """Caller-prefixed nested names must pass (exact leaf equality false-fails)."""
        report = _evaluate(
            _synthetic_live_outcome(
                schedule_trigger={
                    "run_seen": True,
                    "job_executed": True,
                    "job_conclusion": "success",
                    "job_name": ("run-obs-aw-schedule / autodoc / audit / agent"),
                    "url": "https://example.test/schedule",
                }
            )
        )
        assert report["pass"] is True
        assert oracle.schedule_audit_job_name_matches(
            "run-obs-aw-schedule / autodoc / audit / agent"
        )
        assert oracle.schedule_audit_job_name_matches("autodoc / audit / agent")
        assert not oracle.schedule_audit_job_name_matches(
            "run-obs-aw-schedule / autodoc / audit / verify / agent"
        )
        assert not oracle.schedule_audit_job_name_matches("")

    def test_unexpected_fix_pr_fails_when_expect_absent(self) -> None:
        case = _fix_case()
        expectations = dict(case["expectations"])
        expectations["expect_fix_pr"] = False
        report = oracle.evaluate_outcome(
            _synthetic_fix_outcome(),
            case_expectations=expectations,
            case_trigger=case["trigger"],
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "fix_pr_absent" in failed_ids

    def test_both_false_fix_keys_still_select_fix_contract(self) -> None:
        """Key presence (not truthiness) selects fix mode for negative cases."""
        case = _fix_case()
        expectations = dict(case["expectations"])
        expectations["fix_agent_invoked"] = False
        expectations["expect_fix_pr"] = False
        assert oracle.live_case_selects_fix(expectations) is True
        report = oracle.evaluate_outcome(
            _synthetic_fix_outcome(
                fix_agent_invoked=False,
                fix_trigger={"job_executed": False, "job_conclusion": None},
                fix_pr={
                    "number": 99,
                    "title": "docs: Documentation analysis and improvement",
                    "url": "https://example.test/pull/99",
                },
            ),
            case_expectations=expectations,
            case_trigger=case["trigger"],
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "fix_pr_absent" in failed_ids

    def test_audit_only_expectations_do_not_select_fix(self) -> None:
        assert oracle.live_case_selects_fix(_live_case()["expectations"]) is False

    def test_partial_fix_expectations_fail_closed(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(),
            case_expectations={
                "dashboard_enabled": True,
                "schedule_job_executed": True,
                "audit_agent_invoked": True,
                "expect_audit_issue": True,
                "expect_fix_pr": True,
            },
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "case_expectations" in failed_ids

    def test_issue_without_url_fails(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(
                audit_issue={
                    "number": 42,
                    "title": "[oblt-aw][autodoc] Document e2e bait",
                    "url": "",
                }
            )
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "audit_issue_present" in failed_ids

    def test_empty_expectations_fail_closed(self) -> None:
        report = _evaluate(_synthetic_live_outcome(), case_expectations={})
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "case_expectations" in failed_ids

    def test_typo_expectations_fail_closed(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(),
            case_expectations={"typo": True},
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "case_expectations" in failed_ids

    def test_unknown_expectation_key_with_required_keys_fails(self) -> None:
        expectations = _live_expectations(typo_extra=True)
        report = _evaluate(_synthetic_live_outcome(), case_expectations=expectations)
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "case_expectations" in failed_ids

    def test_unknown_trigger_key_fails(self) -> None:
        case = _live_case()
        trigger = dict(case["trigger"])
        trigger["typo_extra"] = True
        report = _evaluate(_synthetic_live_outcome(), case_trigger=trigger)
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "case_trigger" in failed_ids

    def test_dispatch_false_trigger_fails(self) -> None:
        case = _live_case()
        trigger = dict(case["trigger"])
        trigger["dispatch_schedule_trigger"] = False
        report = _evaluate(_synthetic_live_outcome(), case_trigger=trigger)
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "case_trigger" in failed_ids

    def test_cleanup_after_false_trigger_fails(self) -> None:
        case = _live_case()
        trigger = dict(case["trigger"])
        trigger["cleanup_after"] = False
        report = _evaluate(_synthetic_live_outcome(), case_trigger=trigger)
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "case_trigger" in failed_ids

    def test_cleanup_incomplete_fails_when_required(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(
                cleanup={
                    "completed": False,
                    "bait_path": "x",
                    "bait_removed": False,
                    "bait_present": False,
                }
            )
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "cleanup_completed" in failed_ids

    def test_cleanup_completed_without_bait_present_fails(self) -> None:
        """Producer completed flag alone must not green when bait is missing."""
        report = _evaluate(
            _synthetic_live_outcome(
                cleanup={
                    "completed": True,
                    "bait_path": "scripts/e2e_bait.py",
                    "bait_removed": False,
                    "bait_present": False,
                    "closed_prs": [],
                }
            )
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "cleanup_bait_present" in failed_ids

    def test_cleanup_missing_bait_present_fails_closed(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(
                cleanup={
                    "completed": True,
                    "bait_path": "scripts/e2e_bait.py",
                    "closed_prs": [],
                }
            )
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "cleanup_bait_present" in failed_ids

    def test_live_oracle_rejects_wrong_layer(self) -> None:
        report = _evaluate(_synthetic_live_outcome(layer="integration"))
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "layer_e2e" in failed_ids

    def test_blocked_outcome_fails(self) -> None:
        report = _evaluate(
            {
                "workflow_id": "obs:autodoc",
                "case_id": LIVE_CASE_ID,
                "layer": "e2e",
                "mode": "live",
                "blocked": True,
                "block_reason": "Dashboard does not enable obs:autodoc",
            }
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "not_blocked" in failed_ids


class TestJobNameMatching:
    def test_autodoc_audit_agent_leaf(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / audit / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_audit_job_executed(detail) is True

    def test_unrelated_success_is_not_audit(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "agent-suggestions / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_audit_job_executed(detail) is False

    def test_fix_agent_sibling_is_not_audit(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / fix / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_audit_job_executed(detail) is False
        assert harness.autodoc_audit_job_conclusion(detail) is None
        assert harness.schedule_fix_job_executed(detail) is True

    def test_non_autodoc_docs_patrol_leaf_is_not_audit(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "docs-route / gh-aw-docs-patrol / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_audit_job_executed(detail) is False

    def test_audit_success_is_not_fix(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / audit / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_fix_job_executed(detail) is False

    def test_skipped_audit_agent_fails(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / audit / agent",
                    "conclusion": "skipped",
                }
            ]
        }
        assert harness.schedule_audit_job_executed(detail) is False
        assert harness.audit_agent_succeeded(detail) is False

    def test_failed_fix_leaf_counts_as_executed_not_succeeded(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / fix / agent",
                    "conclusion": "failure",
                }
            ]
        }
        assert harness.schedule_fix_job_executed(detail) is True
        assert harness.fix_agent_invoked(detail) is True
        assert harness.fix_agent_succeeded(detail) is False
        assert harness.autodoc_fix_job_conclusion(detail) == "failure"

    def test_non_autodoc_create_pr_leaf_is_not_fix(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "docs-route / gh-aw-create-pr-from-issue / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_fix_job_executed(detail) is False
        assert harness.autodoc_fix_job_conclusion(detail) is None

    def test_failed_audit_leaf_counts_as_executed_not_succeeded(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / audit / agent",
                    "conclusion": "failure",
                }
            ]
        }
        assert harness.schedule_audit_job_executed(detail) is True
        assert harness.audit_agent_invoked(detail) is True
        assert harness.audit_agent_succeeded(detail) is False

    def test_schedule_audit_job_name_preserves_matched_leaf_identity(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "run-obs-aw-schedule / autodoc / audit / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_audit_job_executed(detail) is True
        assert (
            harness.schedule_audit_job_name(detail)
            == "run-obs-aw-schedule / autodoc / audit / agent"
        )

    def test_audit_verify_sibling_is_not_leaf(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / audit / verify / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_audit_job_executed(detail) is False
        assert harness.schedule_audit_job_name(detail) is None

    def test_fix_verify_sibling_is_not_leaf(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / fix / verify / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_fix_job_executed(detail) is False
        assert harness.autodoc_fix_job_conclusion(detail) is None

    def test_wait_for_schedule_audit_run_returns_failed_audit_leaf(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run = {
            "databaseId": 123,
            "createdAt": "2026-09-24T09:00:00Z",
            "event": "schedule",
        }
        detail = {
            "databaseId": 123,
            "status": "completed",
            "url": "https://example.test/runs/123",
            "jobs": [
                {
                    "name": "autodoc / audit / agent",
                    "conclusion": "failure",
                }
            ],
        }
        monkeypatch.setattr(
            harness, "list_schedule_trigger_runs", lambda *args, **kwargs: [run]
        )
        monkeypatch.setattr(harness.estc, "gh_json", lambda *args, **kwargs: detail)
        result = harness.wait_for_schedule_audit_run(
            "elastic/oblt-aw",
            "trigger-obs-aw-schedule.yml",
            since=datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc),
            timeout_seconds=1,
            interval_seconds=0,
        )
        assert result == detail


class TestIssueAndPrCorrelation:
    def test_issue_body_requires_path_and_run_token(self) -> None:
        run_token = "abcd1234efgh5678"
        bait_path = harness.DEFAULT_BAIT_PATH
        basename = Path(bait_path).name
        marker = harness.run_token_marker(run_token)
        assert harness._issue_body_matches_bait(
            f"Update docs for `{bait_path}` ({marker})",
            bait_path,
            run_token=run_token,
        )
        assert harness._issue_body_matches_bait(
            f"Document {basename} entrypoint {marker}",
            bait_path,
            run_token=run_token,
        )
        # Path without run-token marker is not enough.
        assert not harness._issue_body_matches_bait(
            f"Update docs for `{bait_path}`",
            bait_path,
            run_token=run_token,
        )
        # Static fixture marker alone is not enough.
        assert not harness._issue_body_matches_bait(
            f"Document {harness.E2E_AUTODOC_BAIT_MARKER} entrypoint",
            bait_path,
            run_token=run_token,
        )
        assert not harness._issue_body_matches_bait(
            "Generic documentation drift finding",
            bait_path,
            run_token=run_token,
        )
        # Wrong run token must not match.
        assert not harness._issue_body_matches_bait(
            f"Update docs for `{bait_path}` ({harness.run_token_marker('deadbeefdeadbeef')})",
            bait_path,
            run_token=run_token,
        )

    def test_pr_must_reference_issue_number(self) -> None:
        repo = "elastic/oblt-aw"
        assert harness._pr_references_issue("Closes #42\n\nDone.", 42, repo=repo)
        assert harness._pr_references_issue("Fixes #42", 42, repo=repo)
        assert harness._pr_references_issue("Related issue: #42", 42, repo=repo)
        assert harness._pr_references_issue("See #42 for context", 42, repo=repo)
        assert harness._pr_references_issue(
            "Fixes https://github.com/elastic/oblt-aw/issues/42",
            42,
            repo=repo,
        )
        assert harness._pr_references_issue(
            "Fixes elastic/oblt-aw#42",
            42,
            repo=repo,
        )
        assert not harness._pr_references_issue(
            "docs: Documentation analysis", 42, repo=repo
        )
        assert not harness._pr_references_issue("Closes #43", 42, repo=repo)
        assert not harness._pr_references_issue(
            "Fixes https://github.com/other/repo/issues/42",
            42,
            repo=repo,
        )
        # Cross-repo shorthand must not match bare #N fallback.
        assert not harness._pr_references_issue(
            "Fixes elastic/other-repo#42",
            42,
            repo=repo,
        )
        assert not harness._pr_references_issue(
            "See other/repo#42",
            42,
            repo=repo,
        )


class TestClosePrsForIssue:
    def test_close_failure_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            harness,
            "list_fix_prs_for_issue",
            lambda repo, *, issue_number: [{"number": 7, "body": "Fixes #1"}],
        )

        def _failing_gh_text(args: list[str], *, check: bool = True) -> str:
            assert check is True
            raise RuntimeError("gh pr close failed (1): boom")

        monkeypatch.setattr(harness.estc, "gh_text", _failing_gh_text)
        with pytest.raises(RuntimeError, match="gh pr close failed"):
            harness.close_prs_for_issue("elastic/oblt-aw", issue_number=1)


class TestBaitContent:
    def test_bait_is_valid_python(self) -> None:
        compile(harness.bait_content(), "<bait>", "exec")

    def test_bait_contains_correlation_marker(self) -> None:
        assert harness.E2E_AUTODOC_BAIT_MARKER in harness.bait_content()

    def test_e2e_additional_instructions_embed_run_token(self) -> None:
        token = "abcd1234efgh5678"
        text = harness.e2e_additional_instructions(
            bait_path=harness.DEFAULT_BAIT_PATH, run_token=token
        )
        assert harness.run_token_marker(token) in text
        assert harness.DEFAULT_BAIT_PATH in text
        assert harness.E2E_AUTODOC_BAIT_MARKER in text

    def test_bait_path_for_run_is_unique(self) -> None:
        a = harness.bait_path_for_run("aaaaaaaaaaaaaaaa")
        b = harness.bait_path_for_run("bbbbbbbbbbbbbbbb")
        assert a != b
        assert a.endswith("_aaaaaaaaaaaaaaaa.py")
        with pytest.raises(ValueError):
            harness.bait_path_for_run("../escape")
        with pytest.raises(ValueError):
            harness.bait_path_for_run("")


class TestContentsHelpers:
    def test_contents_absent_detects_404(self) -> None:
        assert harness._contents_get_error_is_absent("HTTP 404: Not Found", "")
        assert harness._contents_get_error_is_absent("", "Not Found")
        assert not harness._contents_get_error_is_absent("HTTP 403: Forbidden", "")


class TestHarnessDashboardGate:
    def test_blocks_when_dashboard_disabled(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        monkeypatch.setattr(
            harness.estc,
            "dashboard_enables_workflow",
            lambda repo, workflow_id: False,
        )
        outcome_path = tmp_path / "outcome.json"
        case = _live_case()
        cfg = harness.load_e2e_config(ROOT / "config" / "obs" / "e2e-autodoc.json")
        outcome = harness.run_live_case(
            case=case,
            cfg=cfg,
            outcome_path=outcome_path,
            run_url="https://example.test/run",
        )
        assert outcome["blocked"] is True
        assert "Dashboard" in str(outcome.get("block_reason") or "")
        assert outcome_path.is_file()
        assert outcome["bait"]["run_token"]
        assert outcome["bait"]["path"] == harness.DEFAULT_BAIT_PATH

    def test_negative_fix_case_serializes_unexpected_pr(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both-false fix keys must still snapshot title-matched PRs."""
        monkeypatch.chdir(ROOT)
        case = _fix_case()
        case = {
            **case,
            "expectations": {
                **case["expectations"],
                "fix_agent_invoked": False,
                "expect_fix_pr": False,
            },
        }
        unexpected_pr = {
            "number": 77,
            "title": "docs: Documentation analysis and improvement",
            "url": "https://example.test/pull/77",
        }
        monkeypatch.setattr(
            harness.estc,
            "dashboard_enables_workflow",
            lambda repo, workflow_id: True,
        )
        monkeypatch.setattr(harness, "default_branch", lambda repo: "main")
        monkeypatch.setattr(
            harness,
            "ensure_checked_in_bait",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            harness, "list_schedule_trigger_runs", lambda *args, **kwargs: []
        )
        monkeypatch.setattr(
            harness, "dispatch_schedule_trigger", lambda *args, **kwargs: None
        )
        monkeypatch.setattr(
            harness,
            "wait_for_schedule_audit_run",
            lambda *args, **kwargs: {
                "url": "https://example.test/schedule",
                "jobs": [
                    {
                        "name": "autodoc / audit / agent",
                        "conclusion": "success",
                    }
                ],
            },
        )
        monkeypatch.setattr(
            harness,
            "find_audit_issue",
            lambda *args, **kwargs: {
                "number": 42,
                "title": "[oblt-aw][autodoc] Document e2e bait",
                "url": "https://example.test/issues/42",
            },
        )
        monkeypatch.setattr(
            harness,
            "list_fix_prs_for_issue",
            lambda *args, **kwargs: [unexpected_pr],
        )
        monkeypatch.setattr(
            harness,
            "schedule_audit_job_executed",
            lambda run: True,
        )
        monkeypatch.setattr(harness, "audit_agent_invoked", lambda run: True)
        monkeypatch.setattr(
            harness, "autodoc_audit_job_conclusion", lambda run: "success"
        )
        monkeypatch.setattr(harness, "schedule_fix_job_executed", lambda run: False)
        monkeypatch.setattr(harness, "fix_agent_invoked", lambda run: False)
        monkeypatch.setattr(harness, "fix_agent_succeeded", lambda run: False)
        monkeypatch.setattr(harness, "autodoc_fix_job_conclusion", lambda run: None)
        monkeypatch.setattr(harness, "close_prs_for_issue", lambda *a, **k: [])
        monkeypatch.setattr(harness, "close_issue", lambda *a, **k: None)
        monkeypatch.setattr(harness, "remote_bait_present", lambda *a, **k: True)

        outcome_path = tmp_path / "outcome.json"
        cfg = harness.load_e2e_config(ROOT / "config" / "obs" / "e2e-autodoc.json")
        outcome = harness.run_live_case(
            case=case,
            cfg=cfg,
            outcome_path=outcome_path,
            run_url="https://example.test/run",
        )
        assert outcome["blocked"] is False
        assert outcome.get("fix_pr") == {
            "number": 77,
            "title": "docs: Documentation analysis and improvement",
            "url": "https://example.test/pull/77",
        }
        report = oracle.evaluate_outcome(
            outcome,
            case_expectations=case["expectations"],
            case_trigger=case["trigger"],
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "fix_pr_absent" in failed_ids

    def test_invalid_trigger_blocks_before_remote_mutation(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        case = _live_case()
        case["trigger"] = {**case["trigger"], "seed_doc_drift_bait": "false"}
        outcome_path = tmp_path / "outcome.json"
        cfg = harness.load_e2e_config(ROOT / "config" / "obs" / "e2e-autodoc.json")
        dashboard_called = False

        def _dashboard(*_args: object, **_kwargs: object) -> bool:
            nonlocal dashboard_called
            dashboard_called = True
            return True

        monkeypatch.setattr(harness.estc, "dashboard_enables_workflow", _dashboard)
        outcome = harness.run_live_case(
            case=case,
            cfg=cfg,
            outcome_path=outcome_path,
            run_url="https://example.test/run",
        )
        assert outcome["blocked"] is True
        assert (
            "case trigger failed schema validation"
            in str(outcome.get("block_reason") or "").lower()
        )
        assert dashboard_called is False

    def test_invalid_fix_expectation_blocks_before_remote_mutation(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        case = _fix_case()
        case["expectations"] = {
            **case["expectations"],
            "fix_agent_invoked": "false",
        }
        outcome_path = tmp_path / "outcome.json"
        cfg = harness.load_e2e_config(ROOT / "config" / "obs" / "e2e-autodoc.json")
        dashboard_called = False

        def _dashboard(*_args: object, **_kwargs: object) -> bool:
            nonlocal dashboard_called
            dashboard_called = True
            return True

        monkeypatch.setattr(harness.estc, "dashboard_enables_workflow", _dashboard)
        outcome = harness.run_live_case(
            case=case,
            cfg=cfg,
            outcome_path=outcome_path,
            run_url="https://example.test/run",
        )
        assert outcome["blocked"] is True
        assert (
            "case expectations failed schema validation"
            in str(outcome.get("block_reason") or "").lower()
        )
        assert dashboard_called is False

    def test_exception_after_dashboard_pass_preserves_dashboard_gate(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        case = _live_case()
        outcome_path = tmp_path / "outcome.json"
        cfg = harness.load_e2e_config(ROOT / "config" / "obs" / "e2e-autodoc.json")
        monkeypatch.setattr(
            harness.estc,
            "dashboard_enables_workflow",
            lambda repo, workflow_id: True,
        )
        monkeypatch.setattr(harness, "default_branch", lambda repo: "main")

        def _boom(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("bait fixture missing")

        monkeypatch.setattr(harness, "ensure_checked_in_bait", _boom)
        outcome = harness.run_live_case(
            case=case,
            cfg=cfg,
            outcome_path=outcome_path,
            run_url="https://example.test/run",
        )
        assert outcome["blocked"] is True
        assert outcome["path_gates"]["dashboard_enabled"] is True
        assert "bait fixture missing" in str(outcome.get("block_reason") or "")


class TestOracleCliSummary:
    def test_summary_includes_fix_pr_url(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        outcome_path = tmp_path / "outcome.json"
        report_path = tmp_path / "report.json"
        summary_path = tmp_path / "summary.json"
        outcome_path.write_text(
            json.dumps(_synthetic_fix_outcome()),
            encoding="utf-8",
        )
        code = oracle.main(
            [
                "--outcome-path",
                str(outcome_path),
                "--report-path",
                str(report_path),
                "--summary-path",
                str(summary_path),
                "--testdata-root",
                str(TESTDATA_ROOT),
            ]
        )
        assert code == 0
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["pass"] is True
        assert summary["fix_pr_url"] == "https://example.test/pull/99"
        assert summary["issue_url"] == "https://example.test/issues/42"
