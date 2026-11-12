"""
Unit tests for obs:repo-scheduled E2E harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))
sys.path.insert(0, str(ROOT / "scripts"))

import oracle_repo_scheduled_e2e as oracle
import repo_scheduled_e2e_harness as harness
import repo_scheduled_instructions as discovery

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "repo-scheduled"
LIVE_CASE_ID = "schedule-issue-live"
NOOP_CASE_ID = "schedule-noop-live"


def _live_case(case_id: str = LIVE_CASE_ID) -> dict:
    return json.loads(
        (TESTDATA_ROOT / "cases" / case_id / "case.json").read_text(encoding="utf-8")
    )


def _synthetic_live_outcome(**overrides: object) -> dict:
    base: dict = {
        "workflow_id": "obs:repo-scheduled",
        "case_id": LIVE_CASE_ID,
        "layer": "e2e",
        "mode": "live",
        "invocation_id": "abc123deadbe",
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
    case_id: str = LIVE_CASE_ID,
    case_expectations: dict | None = None,
    case_trigger: dict | None = None,
) -> dict:
    case = _live_case(case_id)
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

    def test_noop_case_happy_path_passes(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(
                case_id=NOOP_CASE_ID,
                issue=None,
                invocation_id="noopinvocat1",
                agent_invoked=False,
                schedule_trigger={
                    "run_seen": True,
                    "job_executed": False,
                    "job_conclusion": None,
                    "job_name": None,
                    "url": "https://example.test/schedule",
                },
            ),
            case_id=NOOP_CASE_ID,
        )
        assert report["pass"] is True

    def test_missing_issue_fails(self) -> None:
        report = _evaluate(_synthetic_live_outcome(issue=None))
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "issue_present" in failed_ids

    def test_missing_invocation_id_fails_issue_case(self) -> None:
        report = _evaluate(_synthetic_live_outcome(invocation_id=""))
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "invocation_id_present" in failed_ids

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

    def test_e2e_mode_mismatch_fails(self) -> None:
        case = _live_case()
        trigger = dict(case["trigger"])
        trigger["e2e_repo_scheduled_mode"] = False
        report = _evaluate(_synthetic_live_outcome(), case_trigger=trigger)
        assert report["pass"] is False
        failed_ids = {item["id"] for item in report["checks"] if not item["pass"]}
        assert "e2e_mode_matches_expect_issue" in failed_ids

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

    def test_plain_run_automation_leaf_does_not_match(self) -> None:
        assert not oracle.schedule_agent_job_name_matches(
            "repo-scheduled / run-automation / agent"
        )

    def test_sibling_agent_does_not_match(self) -> None:
        assert not oracle.schedule_agent_job_name_matches("autodoc / audit / agent")

    def test_wrong_matrix_id_does_not_match(self) -> None:
        assert not oracle.schedule_agent_job_name_matches(
            "run-automation (other-id) / agent"
        )

    def test_matrix_with_path_suffix_does_not_match(self) -> None:
        assert not oracle.schedule_agent_job_name_matches(
            "run-automation (e2e-repo-scheduled-bait, "
            ".github/ai/scheduled/e2e-repo-scheduled-bait.md) / agent"
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

    def test_checked_in_cases_load(self) -> None:
        issue_case = _live_case(LIVE_CASE_ID)
        assert issue_case["trigger"]["e2e_repo_scheduled_mode"] is True
        assert issue_case["expectations"]["schedule_job_executed"] is True
        noop_case = _live_case(NOOP_CASE_ID)
        assert noop_case["trigger"]["e2e_repo_scheduled_mode"] is False
        assert noop_case["expectations"]["expect_issue"] is False
        assert noop_case["expectations"]["schedule_job_executed"] is False
        assert noop_case["expectations"]["agent_invoked"] is False

    def test_run_matches_invocation(self) -> None:
        assert harness._run_matches_invocation(
            {"displayTitle": "E2E schedule [abc123deadbe]"}, "abc123deadbe"
        )
        assert not harness._run_matches_invocation(
            {"displayTitle": "E2E schedule [other]"}, "abc123deadbe"
        )
        assert harness._run_matches_invocation({"displayTitle": "anything"}, "")

    def test_wait_fail_closed_when_correlated_run_lacks_agent_leaf(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        completed = {
            "databaseId": 99,
            "status": "completed",
            "conclusion": "failure",
            "url": "https://example.test/runs/99",
            "createdAt": "2026-11-12T12:00:00Z",
            "event": "workflow_dispatch",
            "displayTitle": "E2E schedule [abc123deadbe]",
            "name": "E2E schedule [abc123deadbe]",
            "jobs": [
                {
                    "name": "repo-scheduled / discover-automations",
                    "conclusion": "failure",
                }
            ],
        }

        def _fake_list(*_a: object, **_k: object) -> list:
            return [
                {
                    "databaseId": 99,
                    "status": "completed",
                    "conclusion": "failure",
                    "createdAt": "2026-11-12T12:00:00Z",
                    "event": "workflow_dispatch",
                    "displayTitle": "E2E schedule [abc123deadbe]",
                    "name": "E2E schedule [abc123deadbe]",
                    "url": "https://example.test/runs/99",
                    "headSha": "abc",
                }
            ]

        def _fake_gh_json(args: list[str]) -> dict:
            assert args[:2] == ["run", "view"]
            return completed

        monkeypatch.setattr(harness, "list_schedule_trigger_runs", _fake_list)
        monkeypatch.setattr(harness.estc, "gh_json", _fake_gh_json)
        monkeypatch.setattr(harness.time, "sleep", lambda *_a, **_k: None)

        detail, reason = harness.wait_for_correlated_schedule_run(
            "elastic/oblt-aw",
            "e2e-trigger-obs-aw-schedule.yml",
            since=datetime(2026, 11, 12, 11, 0, tzinfo=timezone.utc),  # noqa: UP017
            timeout_seconds=30,
            interval_seconds=1,
            invocation_id="abc123deadbe",
            require_agent_leaf=True,
        )
        assert detail is not None
        assert reason is not None
        assert "without repo-scheduled agent leaf" in reason
        assert "Failing closed" in reason


class TestE2EBaitDiscoveryFilter:
    def test_filter_keeps_bait_only(self) -> None:
        bait = discovery.ScheduledAutomation(
            automation_id=discovery.E2E_BAIT_AUTOMATION_ID,
            path=discovery.E2E_BAIT_PATH,
            schedule_profiles=("daily",),
            capabilities=(),
        )
        other = discovery.ScheduledAutomation(
            automation_id="other-job",
            path=".github/ai/scheduled/other.md",
            schedule_profiles=("daily",),
            capabilities=(),
        )
        kept = discovery.filter_e2e_bait_only([bait, other])
        assert [item.automation_id for item in kept] == [
            discovery.E2E_BAIT_AUTOMATION_ID
        ]

    def test_filter_empty_when_bait_absent(self) -> None:
        other = discovery.ScheduledAutomation(
            automation_id="other-job",
            path=".github/ai/scheduled/other.md",
            schedule_profiles=("daily",),
            capabilities=(),
        )
        assert discovery.filter_e2e_bait_only([other]) == []

    def test_resolve_injects_checked_in_bait_when_apm_empty(
        self, tmp_path: pathlib.Path
    ) -> None:
        bait_rel = discovery.E2E_BAIT_PATH
        bait_path = tmp_path / bait_rel
        bait_path.parent.mkdir(parents=True, exist_ok=True)
        bait_path.write_text(
            (
                "---\n"
                f"id: {discovery.E2E_BAIT_AUTOMATION_ID}\n"
                "schedule-profiles: [daily]\n"
                "---\n\n"
                "<!-- E2E_REPO_SCHEDULED_BAIT_MARKER -->\n\n"
                "body\n"
            ),
            encoding="utf-8",
        )
        resolved = discovery.resolve_e2e_bait_only(
            tmp_path, [], schedule_profile="daily"
        )
        assert len(resolved) == 1
        assert resolved[0].automation_id == discovery.E2E_BAIT_AUTOMATION_ID
        assert resolved[0].path == bait_rel

    def test_resolve_prefers_apm_match_over_inject(
        self, tmp_path: pathlib.Path
    ) -> None:
        bait = discovery.ScheduledAutomation(
            automation_id=discovery.E2E_BAIT_AUTOMATION_ID,
            path=discovery.E2E_BAIT_PATH,
            schedule_profiles=("daily",),
            capabilities=(),
            instructions="",
        )
        resolved = discovery.resolve_e2e_bait_only(
            tmp_path, [bait], schedule_profile="daily"
        )
        assert resolved == [bait]
