"""
Unit tests for obs:repo-scheduled E2E harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import oracle_repo_scheduled_e2e as oracle
import repo_scheduled_e2e_harness as harness

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "repo-scheduled"
LIVE_CASE_ID = "schedule-issue-live"


def _live_case() -> dict:
    return json.loads(
        (TESTDATA_ROOT / "cases" / LIVE_CASE_ID / "case.json").read_text(
            encoding="utf-8"
        )
    )


def _synthetic_live_outcome(**overrides: object) -> dict:
    base: dict = {
        "workflow_id": "obs:repo-scheduled",
        "case_id": LIVE_CASE_ID,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": True,
        "path_gates": {"dashboard_enabled": True},
        "schedule_trigger": {
            "run_seen": True,
            "job_executed": True,
            "job_conclusion": "success",
            "job_name": (
                "run-obs-aw-schedule / repo-scheduled / "
                "run-automation (e2e-repo-scheduled-bait) / agent"
            ),
            "url": "https://example.test/schedule",
        },
        "issue": {
            "number": 42,
            "title": "[oblt-aw][repo-scheduled] E2E bait",
            "url": "https://example.test/issues/42",
        },
        "cleanup": {
            "completed": True,
            "bait_path": ".github/ai/scheduled/e2e-repo-scheduled-bait.md",
            "bait_removed": False,
            "bait_present": True,
        },
        "bait": {
            "path": ".github/ai/scheduled/e2e-repo-scheduled-bait.md",
            "commit_sha": None,
            "created_by_this_run": False,
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
        report = _evaluate(_synthetic_live_outcome(issue=None))
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "issue_present" in failed_ids

    def test_overall_conclusion_does_not_substitute_for_leaf(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(
                schedule_trigger={
                    "run_seen": True,
                    "job_executed": False,
                    "job_conclusion": "success",
                    "job_name": None,
                    "url": "https://example.test/schedule",
                },
                agent_invoked=False,
            )
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "schedule_job_executed" in failed_ids

    def test_wrong_leaf_job_name_fails(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(
                schedule_trigger={
                    "run_seen": True,
                    "job_executed": True,
                    "job_conclusion": "success",
                    "job_name": "autodoc / audit / agent",
                    "url": "https://example.test/schedule",
                }
            )
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "schedule_job_name" in failed_ids

    def test_cleanup_completed_without_bait_present_fails(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(
                cleanup={
                    "completed": True,
                    "bait_path": ".github/ai/scheduled/e2e-repo-scheduled-bait.md",
                    "bait_removed": False,
                    "bait_present": False,
                }
            )
        )
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "cleanup_bait_present" in failed_ids


class TestOracleSchemaFailClosed:
    def test_empty_expectations_fail(self) -> None:
        err = oracle.case_expectations_schema_error("live", {})
        assert err is not None
        assert "missing" in err

    def test_typo_expectation_key_fails(self) -> None:
        case = _live_case()
        expectations = dict(case["expectations"])
        expectations["typo_key"] = True
        err = oracle.case_expectations_schema_error("live", expectations)
        assert err is not None
        assert "unknown" in err

    def test_trigger_false_required_flag_fails(self) -> None:
        case = _live_case()
        trigger = dict(case["trigger"])
        trigger["dispatch_schedule_trigger"] = False
        err = oracle.case_trigger_schema_error(trigger)
        assert err is not None
        assert "dispatch_schedule_trigger" in err

    def test_blocked_outcome_fails(self) -> None:
        report = _evaluate(
            {
                "workflow_id": "obs:repo-scheduled",
                "case_id": LIVE_CASE_ID,
                "layer": "e2e",
                "mode": "live",
                "blocked": True,
                "block_reason": "Dashboard does not enable obs:repo-scheduled",
            }
        )
        assert report["pass"] is False
        assert report["block_reason"]


class TestLeafMatcher:
    def test_matrix_leaf_matches(self) -> None:
        assert oracle.schedule_agent_job_name_matches(
            "run-obs-aw-schedule / repo-scheduled / "
            "run-automation (e2e-repo-scheduled-bait) / agent"
        )

    def test_plain_run_automation_leaf_matches(self) -> None:
        assert oracle.schedule_agent_job_name_matches(
            "repo-scheduled / run-automation / agent"
        )

    def test_sibling_agent_does_not_match(self) -> None:
        assert not oracle.schedule_agent_job_name_matches("autodoc / audit / agent")

    def test_wrong_matrix_id_does_not_match(self) -> None:
        assert not oracle.schedule_agent_job_name_matches(
            "run-automation (other-id) / agent"
        )


class TestHarnessHelpers:
    def test_bait_content_requires_marker(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "bait.md"
        path.write_text(
            "---\nid: x\nschedule-profiles: [daily]\n---\nbody\n", encoding="utf-8"
        )
        try:
            harness.bait_content(path)
            raise AssertionError("expected RuntimeError")
        except RuntimeError as exc:
            assert "E2E_REPO_SCHEDULED_BAIT_MARKER" in str(exc)

    def test_checked_in_case_loads(self) -> None:
        case = _live_case()
        assert case["id"] == LIVE_CASE_ID
        assert case["mode"] == "live"
        assert case["workflow_id"] == "obs:repo-scheduled"
