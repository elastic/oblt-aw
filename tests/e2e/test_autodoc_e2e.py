"""
Unit tests for obs:autodoc E2E harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys

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

    def test_autodoc_fix_agent_leaf(self) -> None:
        detail = {
            "jobs": [
                {
                    "name": "autodoc / fix / agent",
                    "conclusion": "success",
                }
            ]
        }
        assert harness.schedule_fix_job_executed(detail) is True

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


class TestBaitContent:
    def test_bait_is_valid_python(self) -> None:
        compile(harness.bait_content(), "<bait>", "exec")


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
