"""
Unit tests for ESTC PR Buildkite Detective E2E / integration harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import estc_pr_buildkite_detective_e2e_harness as harness  # noqa: E402
import oracle_estc_pr_buildkite_detective_e2e as oracle  # noqa: E402

CASE_DIR = (
    ROOT
    / "testdata"
    / "agentic"
    / "estc-pr-buildkite-detective"
    / "cases"
    / "status-failure-open-pr"
)


class TestHarnessFixtureCase:
    def test_status_failure_open_pr_path_ready(self) -> None:
        outcome = harness.run_fixture_case(CASE_DIR)
        assert outcome["workflow_id"] == "obs:estc-pr-buildkite-detective"
        assert outcome["mode"] == "fixture"
        assert outcome["layer"] == "integration"
        assert outcome["agent_invoked"] is False
        assert outcome["path_gates"]["path_ready"] is True
        assert outcome["buildkite"]["ok"] is True
        assert outcome["buildkite"]["failed_job_count"] == 1
        assert outcome["buildkite"]["event_context"]["pr_number"] == "7"
        assert outcome["buildkite"]["failed_jobs"][0]["log_has_content"] is True

    def test_cli_writes_outcome(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        outcome_path = tmp_path / "outcome.json"
        code = harness.main(
            [
                "--mode",
                "fixture",
                "--case-id",
                "status-failure-open-pr",
                "--outcome-path",
                str(outcome_path),
                "--run-url",
                "https://example.test/run/1",
            ]
        )
        assert code == 0
        data = json.loads(outcome_path.read_text(encoding="utf-8"))
        assert data["run_url"] == "https://example.test/run/1"
        assert data["path_gates"]["path_ready"] is True
        assert data["layer"] == "integration"

    def test_live_mode_blocks_without_buildkite_url(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        monkeypatch.delenv("E2E_ESTC_BUILDKITE_TARGET_URL", raising=False)

        def fake_dashboard(repo: str, workflow_id: str) -> bool:
            return True

        monkeypatch.setattr(harness, "dashboard_enables_workflow", fake_dashboard)
        outcome_path = tmp_path / "outcome.json"
        code = harness.main(
            [
                "--mode",
                "live",
                "--case-id",
                "status-failure-open-pr-live",
                "--outcome-path",
                str(outcome_path),
            ]
        )
        assert code == 2
        data = json.loads(outcome_path.read_text(encoding="utf-8"))
        assert data["blocked"] is True
        assert "E2E_ESTC_BUILDKITE_TARGET_URL" in str(data.get("block_reason"))


class TestOracle:
    def test_fixture_outcome_passes(self) -> None:
        outcome = harness.run_fixture_case(CASE_DIR)
        report = oracle.evaluate_outcome(outcome, {"cases": []})
        assert report["pass"] is True
        assert report["layer"] == "integration"
        assert report["quarantined"] is False
        assert all(item["pass"] for item in report["checks"])

    def test_quarantine_requires_owner_and_reason(self) -> None:
        outcome = harness.run_fixture_case(CASE_DIR)
        incomplete = {
            "default_owner_team": "@elastic/observablt-robots",
            "cases": [
                {
                    "workflow_id": "obs:estc-pr-buildkite-detective",
                    "case_id": "status-failure-open-pr",
                    "reason": "missing owner",
                }
            ],
        }
        report = oracle.evaluate_outcome(outcome, incomplete)
        assert report["quarantined"] is False
        assert report["pass"] is True

    def test_quarantine_skips_with_owner(self) -> None:
        outcome = harness.run_fixture_case(CASE_DIR)
        quarantine = {
            "default_owner_team": "@elastic/observablt-robots",
            "cases": [
                {
                    "workflow_id": "obs:estc-pr-buildkite-detective",
                    "case_id": "status-failure-open-pr",
                    "owner": "@elastic/observablt-robots",
                    "reason": "test quarantine",
                }
            ],
        }
        report = oracle.evaluate_outcome(outcome, quarantine)
        assert report["pass"] is True
        assert report["skipped"] is True
        assert report["quarantined"] is True
        assert report["quarantine_owner"] == "@elastic/observablt-robots"

    def test_missing_failed_jobs_fails(self) -> None:
        outcome = harness.run_fixture_case(CASE_DIR)
        outcome["buildkite"]["failed_job_count"] = 0
        outcome["path_gates"]["path_ready"] = False
        report = oracle.evaluate_outcome(outcome, {"cases": []})
        assert report["pass"] is False
        failed_ids = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "buildkite_failed_jobs" in failed_ids

    def test_live_oracle_requires_comment_markers(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "status_trigger": {"job_executed": True, "url": "https://example.test/run"},
            "agent_comment": {
                "id": 1,
                "url": "https://example.test/comment",
            },
            "expectations": {
                "dashboard_enabled": True,
                "status_job_executed": True,
                "agent_invoked": True,
                "expect_agent_comment": True,
                "agent_comment_markers": ["### TL;DR", "## Remediation"],
            },
        }
        report = oracle.evaluate_outcome(outcome, {"cases": []})
        assert report["pass"] is True
        assert report["layer"] == "e2e"

    def test_live_oracle_rejects_string_bool_coercion(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "status_trigger": {"job_executed": True},
            "agent_comment": {"id": 1},
            "expectations": {
                "dashboard_enabled": "yes",
                "agent_invoked": True,
                "expect_agent_comment": True,
            },
        }
        report = oracle.evaluate_outcome(outcome, {"cases": []})
        assert report["pass"] is False
        failed = {c["id"]: c for c in report["checks"] if not c["pass"]}
        assert "dashboard_enabled" in failed

    def test_cli_writes_report_and_summary(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        outcome_path = tmp_path / "outcome.json"
        report_path = tmp_path / "report.json"
        summary_path = tmp_path / "summary.json"
        harness.main(
            [
                "--mode",
                "fixture",
                "--case-id",
                "status-failure-open-pr",
                "--outcome-path",
                str(outcome_path),
            ]
        )
        code = oracle.main(
            [
                "--outcome-path",
                str(outcome_path),
                "--report-path",
                str(report_path),
                "--summary-path",
                str(summary_path),
                "--quarantine-path",
                str(ROOT / "config" / "obs" / "e2e-quarantine.json"),
            ]
        )
        assert code == 0
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["pass"] is True
        assert summary["workflow_id"] == "obs:estc-pr-buildkite-detective"
        assert summary["layer"] == "integration"
