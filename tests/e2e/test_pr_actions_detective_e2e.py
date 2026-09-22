"""Unit tests for PR Actions Detective E2E harness and oracle."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import oracle_pr_actions_detective_e2e as oracle
import pr_actions_detective_e2e_harness as harness

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "pr-actions-detective"
LIVE_CASE_ID = "workflow-run-failure-open-pr-live"

_NEGATIVE_CASE_EXPECTATIONS = {
    "dashboard_enabled": True,
    "workflow_run_job_executed": False,
    "agent_invoked": False,
    "expect_agent_comment": False,
}
_NEGATIVE_CASE_TRIGGER = {
    "require_open_pr": True,
    "create_failed_actions_run": True,
    "clear_prior_detective_comments": False,
    "fail_workflow_conclusion": "failure",
    "fail_workflow_event": "pull_request",
}


def _synthetic_live_outcome(
    *,
    case_id: str = LIVE_CASE_ID,
    agent_invoked: bool = True,
) -> dict:
    return {
        "workflow_id": "obs:pr-actions-detective",
        "case_id": case_id,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": agent_invoked,
        "path_gates": {"dashboard_enabled": True},
        "fail_workflow": {
            "source": "created",
            "conclusion": "failure",
            "event": "pull_request",
            "fail_log_marker_verified": True,
            "url": "https://example.test/fail-run",
        },
        "workflow_run_trigger": {
            "run_seen": True,
            "job_executed": True,
            "job_conclusion": "success",
            "url": "https://example.test/run",
        },
        "agent_comment": {"id": 1} if agent_invoked else None,
    }


def _evaluate(
    outcome: dict,
    *,
    case_expectations: dict | None = None,
    case_trigger: dict | None = None,
) -> dict:
    case_id = str(outcome.get("case_id") or "")
    if case_expectations is None:
        case_expectations = (
            oracle.load_case_expectations(TESTDATA_ROOT, case_id) if case_id else None
        )
    if case_trigger is None and str(outcome.get("mode") or "") == "live":
        case_trigger = (
            oracle.load_case_trigger(TESTDATA_ROOT, case_id) if case_id else None
        )
    return oracle.evaluate_outcome(
        outcome,
        case_expectations=case_expectations,
        case_trigger=case_trigger,
    )


class TestHarnessHelpers:
    def test_job_names_indicate_agent_ignores_wrapper_job(self) -> None:
        assert not harness._job_names_indicate_agent(
            {
                "jobs": [
                    {
                        "name": "pr-actions-detective",
                        "conclusion": "success",
                    }
                ]
            }
        )
        assert harness._job_names_indicate_agent(
            {"jobs": [{"name": "agent", "conclusion": "success"}]}
        )
        assert not harness._job_names_indicate_agent(
            {"jobs": [{"name": "agent", "conclusion": "skipped"}]}
        )
        assert harness._job_names_indicate_agent(
            {
                "jobs": [
                    {
                        "name": "PR Actions Detective / agent",
                        "conclusion": "success",
                    }
                ]
            }
        )

    def test_workflow_run_job_executed_requires_named_job(self) -> None:
        assert not harness.workflow_run_job_executed(
            {
                "jobs": [{"name": "unrelated", "conclusion": "success"}],
                "conclusion": "success",
            }
        )
        assert harness.workflow_run_job_executed(
            {
                "jobs": [
                    {
                        "name": "run-obs-aw-workflow-run",
                        "conclusion": "success",
                    }
                ]
            }
        )
        assert not harness.workflow_run_job_executed(
            {
                "jobs": [
                    {
                        "name": "run-obs-aw-workflow-run",
                        "conclusion": "skipped",
                    }
                ]
            }
        )

    def test_find_agent_comment_requires_bot_author(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        since = harness._utc_now().replace(microsecond=0)
        comments = [
            {
                "id": 1,
                "html_url": "https://example.test/c/1",
                "created_at": since.isoformat().replace("+00:00", "Z"),
                "user": {"login": "human-user"},
                "body": "### TL;DR\n## Remediation\n",
            },
            {
                "id": 2,
                "html_url": "https://example.test/c/2",
                "created_at": since.isoformat().replace("+00:00", "Z"),
                "user": {"login": "copilot-swe-agent[bot]"},
                "body": "### TL;DR\n## Remediation\n",
            },
        ]
        monkeypatch.setattr(harness, "_list_issue_comments", lambda *_a, **_k: comments)
        found = harness.find_agent_comment(
            "elastic/oblt-aw",
            1,
            since=since,
            markers=["### TL;DR", "## Remediation"],
        )
        assert found is not None
        assert found["id"] == 2

    def test_normalize_e2e_pr_config_rejects_wrong_branch(self) -> None:
        with pytest.raises(RuntimeError, match="e2e_pr.branch"):
            harness.normalize_e2e_pr_config(
                {
                    "e2e_pr": {
                        "label": "e2e:pr-actions-detective",
                        "branch": "e2e/wrong",
                    }
                }
            )

    def test_live_mode_blocks_invalid_trigger_before_remote_writes(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        case_dir = tmp_path / "cases" / "bad"
        case_dir.mkdir(parents=True)
        (case_dir / "case.json").write_text(
            json.dumps(
                {
                    "id": "bad",
                    "mode": "live",
                    "workflow_id": "obs:pr-actions-detective",
                    "trigger": {
                        "require_open_pr": True,
                        # Truthy string must not reach ensure_e2e_pr / Contents API.
                        "create_failed_actions_run": "false",
                        "clear_prior_detective_comments": True,
                        "fail_workflow_conclusion": "failure",
                        "fail_workflow_event": "pull_request",
                    },
                    "expectations": {
                        "dashboard_enabled": True,
                        "workflow_run_job_executed": True,
                        "agent_invoked": True,
                        "expect_agent_comment": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        called: list[str] = []

        def _boom(*_a: object, **_k: object) -> None:
            called.append("ensure_e2e_pr")
            raise AssertionError("ensure_e2e_pr must not run before schema validation")

        monkeypatch.setattr(harness, "ensure_e2e_pr", _boom)
        monkeypatch.setattr(
            harness,
            "dashboard_enables_workflow",
            lambda *_a, **_k: (_ for _ in ()).throw(
                AssertionError("dashboard check must not run before schema validation")
            ),
        )
        monkeypatch.chdir(ROOT)
        outcome = harness.run_live_case(
            case_dir,
            harness.load_e2e_config(ROOT / "config/obs/e2e-pr-actions-detective.json"),
        )
        assert outcome["blocked"] is True
        assert "Invalid live trigger contract" in str(outcome.get("block_reason"))
        assert called == []

    def test_sync_fail_workflow_refuses_differing_remote(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workflow = tmp_path / "e2e-pr-actions-detective-fail.yml"
        workflow.write_text("name: local\n", encoding="utf-8")
        monkeypatch.setattr(harness, "FAIL_WORKFLOW_PATH", workflow)

        def _fake_run(cmd: list[str], **_k: object) -> object:
            class _Proc:
                returncode = 0
                stdout = json.dumps(
                    {
                        "sha": "abc",
                        "content": "bm90LW1hdGNoCg==",  # "not-match\n" b64
                    }
                )
                stderr = ""

            assert "contents/" in " ".join(cmd)
            return _Proc()

        monkeypatch.setattr(harness.subprocess, "run", _fake_run)

        def _put_must_not_run(*_a: object, **_k: object) -> None:
            raise AssertionError("put_branch_file must not overwrite differing remote")

        monkeypatch.setattr(harness, "put_branch_file", _put_must_not_run)
        with pytest.raises(RuntimeError, match="refusing to overwrite"):
            harness.sync_fail_workflow_to_fixture_branch(
                "elastic/oblt-aw", branch="e2e/pr-actions-detective"
            )

    def test_agent_job_invoked_ignores_uncorrelated_lock_runs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        since = harness._utc_now().replace(microsecond=0)
        caller = {
            "jobs": [
                {"name": "run-obs-aw-workflow-run", "conclusion": "success"},
            ]
        }
        monkeypatch.setattr(
            harness,
            "list_workflow_runs",
            lambda *_a, **_k: [
                {
                    "databaseId": 99,
                    "createdAt": since.isoformat().replace("+00:00", "Z"),
                    "status": "completed",
                    "conclusion": "success",
                    "headSha": "other-sha",
                    "displayTitle": "unrelated detective run",
                    "url": "https://example.test/runs/99",
                }
            ],
        )
        monkeypatch.setattr(
            harness,
            "_view_run_jobs",
            lambda *_a, **_k: {
                "jobs": [{"name": "agent", "conclusion": "success"}],
                "headSha": "other-sha",
                "displayTitle": "unrelated detective run",
            },
        )
        assert (
            harness.agent_job_invoked(
                "elastic/oblt-aw",
                caller,
                since=since,
                fail_run_id=42,
                fail_head_sha="expected-sha",
            )
            is False
        )

    def test_agent_job_invoked_accepts_head_sha_bound_lock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        since = harness._utc_now().replace(microsecond=0)
        caller = {
            "jobs": [
                {"name": "run-obs-aw-workflow-run", "conclusion": "success"},
            ]
        }
        monkeypatch.setattr(
            harness,
            "list_workflow_runs",
            lambda *_a, **_k: [
                {
                    "databaseId": 99,
                    "createdAt": since.isoformat().replace("+00:00", "Z"),
                    "status": "completed",
                    "conclusion": "success",
                    "headSha": "expected-sha",
                    "displayTitle": "lock run",
                    "url": "https://example.test/runs/99",
                }
            ],
        )
        monkeypatch.setattr(
            harness,
            "_view_run_jobs",
            lambda *_a, **_k: {
                "jobs": [{"name": "agent", "conclusion": "success"}],
                "headSha": "expected-sha",
                "displayTitle": "lock run",
            },
        )
        assert (
            harness.agent_job_invoked(
                "elastic/oblt-aw",
                caller,
                since=since,
                fail_run_id=42,
                fail_head_sha="expected-sha",
            )
            is True
        )


class TestOracleFailClosed:
    def test_happy_path_passes(self) -> None:
        report = _evaluate(_synthetic_live_outcome())
        assert report["pass"] is True
        check_ids = {c["id"] for c in report["checks"]}
        assert "agent_comment_present" in check_ids
        assert "fail_log_marker_verified" in check_ids
        assert "workflow_run_job_executed" in check_ids

    def test_missing_expectations_fail_closed(self) -> None:
        report = oracle.evaluate_outcome(
            _synthetic_live_outcome(),
            case_expectations=None,
            case_trigger=_NEGATIVE_CASE_TRIGGER,
        )
        assert report["pass"] is False
        assert any(
            c["id"] == "case_expectations" and not c["pass"] for c in report["checks"]
        )

    def test_typo_expectations_fail_closed(self) -> None:
        report = _evaluate(
            _synthetic_live_outcome(),
            case_expectations={"typo": True},
            case_trigger=_NEGATIVE_CASE_TRIGGER,
        )
        assert report["pass"] is False
        assert any(
            c["id"] == "case_expectations" and not c["pass"] for c in report["checks"]
        )

    def test_string_expect_agent_comment_rejected(self) -> None:
        expectations = {
            **_NEGATIVE_CASE_EXPECTATIONS,
            "expect_agent_comment": "true",  # type: ignore[dict-item]
            "workflow_run_job_executed": True,
            "agent_invoked": True,
        }
        report = _evaluate(
            _synthetic_live_outcome(),
            case_expectations=expectations,  # type: ignore[arg-type]
            case_trigger=_NEGATIVE_CASE_TRIGGER,
        )
        assert report["pass"] is False

    def test_missing_trigger_fail_closed(self) -> None:
        report = oracle.evaluate_outcome(
            _synthetic_live_outcome(),
            case_expectations=_NEGATIVE_CASE_EXPECTATIONS,
            case_trigger=None,
        )
        assert report["pass"] is False
        assert any(
            c["id"] == "case_trigger" and not c["pass"] for c in report["checks"]
        )

    def test_blocked_outcome_fails(self) -> None:
        outcome = _synthetic_live_outcome()
        outcome["blocked"] = True
        outcome["block_reason"] = "Dashboard does not enable obs:pr-actions-detective"
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert any(c["id"] == "not_blocked" and not c["pass"] for c in report["checks"])

    def test_missing_comment_fails_when_expected(self) -> None:
        outcome = _synthetic_live_outcome(agent_invoked=True)
        outcome["agent_comment"] = None
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert any(
            c["id"] == "agent_comment_present" and not c["pass"]
            for c in report["checks"]
        )

    def test_overall_run_conclusion_not_substitute_for_named_job(self) -> None:
        outcome = _synthetic_live_outcome()
        outcome["workflow_run_trigger"] = {
            "run_seen": True,
            "job_executed": False,
            "job_conclusion": "skipped",
            "conclusion": "success",
            "url": "https://example.test/run",
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert any(
            c["id"] == "workflow_run_job_executed" and not c["pass"]
            for c in report["checks"]
        )

    def test_checked_in_case_json_loads(self) -> None:
        expectations = oracle.load_case_expectations(TESTDATA_ROOT, LIVE_CASE_ID)
        trigger = oracle.load_case_trigger(TESTDATA_ROOT, LIVE_CASE_ID)
        assert expectations is not None
        assert trigger is not None
        assert oracle.case_expectations_schema_error("live", expectations) is None
        assert oracle.case_trigger_schema_error(trigger) is None

    def test_trigger_schema_pins_failure_pull_request_contract(self) -> None:
        trigger = dict(_NEGATIVE_CASE_TRIGGER)
        assert oracle.case_trigger_schema_error(trigger) is None
        bad_conclusion = {**trigger, "fail_workflow_conclusion": "success"}
        err = oracle.case_trigger_schema_error(bad_conclusion)
        assert err is not None
        assert "failure" in err
        bad_event = {**trigger, "fail_workflow_event": "push"}
        err = oracle.case_trigger_schema_error(bad_event)
        assert err is not None
        assert "pull_request" in err
        false_create = {**trigger, "create_failed_actions_run": False}
        err = oracle.case_trigger_schema_error(false_create)
        assert err is not None
        assert "create_failed_actions_run" in err
        string_bool = {**trigger, "require_open_pr": "true"}  # type: ignore[dict-item]
        err = oracle.case_trigger_schema_error(string_bool)  # type: ignore[arg-type]
        assert err is not None

    def test_layer_mismatch_fails(self) -> None:
        outcome = _synthetic_live_outcome()
        outcome["layer"] = "integration"
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert any(c["id"] == "layer_e2e" and not c["pass"] for c in report["checks"])


class TestFailWorkflowArtifacts:
    def test_fail_workflow_yaml_contains_marker(self) -> None:
        path = ROOT / ".github/workflows/e2e-pr-actions-detective-fail.yml"
        text = path.read_text(encoding="utf-8")
        assert "OBLT_AW_E2E_PR_ACTIONS_INTENTIONAL_FAILURE" in text
        assert "e2e:pr-actions-detective" in text
        assert "e2e/pr-actions-detective" in text

    def test_config_matches_fixture_constants(self) -> None:
        cfg = harness.load_e2e_config(ROOT / "config/obs/e2e-pr-actions-detective.json")
        assert cfg["e2e_pr"]["branch"] == harness.FIXTURE_BRANCH
        assert cfg["e2e_pr"]["label"] == harness.FIXTURE_LABEL
        assert cfg["fail_workflow_file"] == "e2e-pr-actions-detective-fail.yml"
