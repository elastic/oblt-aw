"""
Unit tests for obs:autodoc E2E harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys
from pathlib import Path

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import autodoc_e2e_harness as harness
import oracle_autodoc_e2e as oracle

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "autodoc"
LIVE_CASE_ID = "schedule-audit-issue-live"


def _live_case() -> dict:
    return json.loads(
        (TESTDATA_ROOT / "cases" / LIVE_CASE_ID / "case.json").read_text(
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
        "path_gates": {"dashboard_enabled": True},
        "schedule_trigger": {
            "run_seen": True,
            "job_executed": True,
            "job_conclusion": "success",
            "url": "https://example.test/schedule",
        },
        "audit_issue": {
            "number": 42,
            "title": "[oblt-aw][autodoc] Document e2e bait",
            "url": "https://example.test/issues/42",
        },
        "cleanup": {
            "completed": True,
            "bait_path": "scripts/e2e_autodoc_intentional_undocumented.py",
            "closed_prs": [],
        },
        "bait": {
            "path": "scripts/e2e_autodoc_intentional_undocumented.py",
            "commit_sha": "abc123",
            "created_by_this_run": True,
        },
    }
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

    def test_missing_issue_fails(self) -> None:
        report = _evaluate(_synthetic_live_outcome(audit_issue=None))
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "audit_issue_present" in failed_ids

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

    def test_cleanup_incomplete_fails_when_required(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(cleanup={"completed": False, "bait_path": "x"})
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "cleanup_completed" in failed_ids

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


class TestIssueAndPrCorrelation:
    def test_issue_body_requires_static_marker_and_per_run_path(self) -> None:
        run_token = "abcd1234efgh5678"
        bait_path = harness.bait_path_for_run(run_token)
        basename = Path(bait_path).name
        assert harness._issue_body_matches_bait(
            f"Document {harness.E2E_AUTODOC_BAIT_MARKER} for `{bait_path}`",
            bait_path,
            run_token=run_token,
        )
        assert harness._issue_body_matches_bait(
            f"Document {harness.E2E_AUTODOC_BAIT_MARKER} in {basename}",
            bait_path,
            run_token=run_token,
        )
        # Static marker alone is not enough (cross-run / production substitute).
        assert not harness._issue_body_matches_bait(
            f"Document {harness.E2E_AUTODOC_BAIT_MARKER} entrypoint",
            bait_path,
            run_token=run_token,
        )
        # Path alone without the static marker is not enough.
        assert not harness._issue_body_matches_bait(
            f"Update docs for `{bait_path}`",
            bait_path,
            run_token=run_token,
        )
        assert not harness._issue_body_matches_bait(
            "Generic documentation drift finding",
            bait_path,
            run_token=run_token,
        )
        # Wrong (other-run) path must not match this run_token.
        other_path = harness.bait_path_for_run("deadbeefdeadbeef")
        assert not harness._issue_body_matches_bait(
            f"Document {harness.E2E_AUTODOC_BAIT_MARKER} for `{other_path}`",
            bait_path,
            run_token=run_token,
        )

    def test_pr_must_reference_issue_number(self) -> None:
        repo = "elastic/oblt-aw"
        assert harness._pr_references_issue("Closes #42\n\nDone.", 42, repo=repo)
        assert harness._pr_references_issue("Fixes #42", 42, repo=repo)
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
        compile(harness.bait_content(run_token="abcd1234efgh5678"), "<bait>", "exec")

    def test_bait_contains_correlation_marker(self) -> None:
        assert harness.E2E_AUTODOC_BAIT_MARKER in harness.bait_content()

    def test_bait_content_embeds_run_token(self) -> None:
        token = "abcd1234efgh5678"
        text = harness.bait_content(run_token=token)
        assert harness.run_token_marker(token) in text
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
        assert outcome["bait"]["path"].endswith(f"_{outcome['bait']['run_token']}.py")
