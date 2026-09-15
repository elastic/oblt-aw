"""
Unit tests for ESTC PR Buildkite Detective E2E / integration harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import estc_pr_buildkite_detective_e2e_harness as harness
import oracle_estc_pr_buildkite_detective_e2e as oracle

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "estc-pr-buildkite-detective"
LIVE_CASE_ID = "status-success-skipped"


def _synthetic_live_outcome(
    *,
    case_id: str = LIVE_CASE_ID,
    agent_invoked: bool = False,
) -> dict:
    """Minimal live outcome for oracle/quarantine tests (no harness fixture mode)."""
    return {
        "workflow_id": "obs:estc-pr-buildkite-detective",
        "case_id": case_id,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": agent_invoked,
        "path_gates": {"dashboard_enabled": True},
        "status": {
            "state": "success",
            "context": "buildkite/elastic/x",
            "target_url": "https://buildkite.com/elastic/x/builds/1",
            "publisher": "harness",
        },
        "status_trigger": {
            "run_seen": True,
            "job_executed": False,
            "job_conclusion": "skipped",
            "url": "https://example.test/run",
        },
        "agent_comment": None,
    }


def _evaluate(
    outcome: dict,
    quarantine: dict | None = None,
    *,
    case_expectations: dict | None = None,
    case_trigger: dict | None = None,
) -> dict:
    """Oracle helper matching production: load checked-in case.json by default.

    Pass ``case_expectations`` / ``case_trigger`` explicitly for synthetic or
    mutated maps. Never authorize gates from harness-copied
    ``outcome["expectations"]`` or ``outcome["trigger"]`` implicitly — those
    paths are not the production source of truth.
    """
    if quarantine is None:
        quarantine = {"cases": []}
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
        quarantine,
        case_expectations=case_expectations,
        case_trigger=case_trigger,
    )


class TestHarnessLive:
    def test_live_mode_blocks_without_buildkite_token(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        monkeypatch.delenv("E2E_ESTC_BUILDKITE_TARGET_URL", raising=False)
        monkeypatch.delenv("BUILDKITE_TOKEN", raising=False)

        def fake_dashboard(repo: str, workflow_id: str) -> bool:
            return True

        monkeypatch.setattr(harness, "dashboard_enables_workflow", fake_dashboard)
        outcome_path = tmp_path / "outcome.json"
        code = harness.main(
            [
                "--case-id",
                "status-failure-open-pr-live",
                "--outcome-path",
                str(outcome_path),
            ]
        )
        assert code == 2
        data = json.loads(outcome_path.read_text(encoding="utf-8"))
        assert data["blocked"] is True
        reason = str(data.get("block_reason"))
        assert "BUILDKITE_TOKEN" in reason

    def test_ensure_failed_build_uses_override_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "E2E_ESTC_BUILDKITE_TARGET_URL",
            "https://buildkite.com/elastic/oblt-aw-e2e-estc-fail/builds/99",
        )
        url, meta = harness.ensure_failed_buildkite_target_url(
            harness.load_e2e_config(
                ROOT / "config/obs/e2e-estc-pr-buildkite-detective.json"
            ),
            commit="abc",
            branch="e2e/estc-pr-buildkite-detective",
            pr_number=1,
            case_id="status-failure-open-pr-live",
        )
        assert url.endswith("/builds/99")
        assert meta["source"] == "override_env"

    def test_needs_real_failed_buildkite_for_happy_path(self) -> None:
        assert harness.needs_real_failed_buildkite(
            {
                "use_buildkite_target_url": True,
                "status_state": "failure",
                "create_failed_buildkite_build": True,
            },
            {"agent_invoked": True, "expect_agent_comment": True},
        )
        assert not harness.needs_real_failed_buildkite(
            {"use_buildkite_target_url": True, "status_state": "success"},
            {"agent_invoked": False},
        )

    def test_job_names_indicate_agent_ignores_wrapper_job(self) -> None:
        assert not harness._job_names_indicate_agent(
            {
                "jobs": [
                    {
                        "name": "estc-pr-buildkite-detective",
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
        assert found["user"] == "copilot-swe-agent[bot]"

    def test_wait_for_new_run_ignores_head_sha_and_incomplete(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        since = harness._utc_now().replace(microsecond=0)
        listed = [
            {
                "databaseId": 99,
                "status": "in_progress",
                "conclusion": "",
                "createdAt": since.isoformat().replace("+00:00", "Z"),
                "event": "status",
                "displayTitle": "status",
                "url": "https://example.test/run/99",
                "headSha": "default-branch-tip",
            }
        ]
        clock = {"now": since.timestamp()}

        def fake_time() -> float:
            return clock["now"]

        def fake_sleep(_seconds: float) -> None:
            # Expire the poll deadline after the first in-progress observation.
            clock["now"] += 10_000

        monkeypatch.setattr(
            harness, "list_status_trigger_runs", lambda *_a, **_k: listed
        )
        monkeypatch.setattr(
            harness,
            "gh_json",
            lambda *_a, **_k: {
                "databaseId": 99,
                "status": "in_progress",
                "conclusion": "",
                "url": "https://example.test/run/99",
                "jobs": [],
                "createdAt": listed[0]["createdAt"],
                "headSha": "default-branch-tip",
                "event": "status",
            },
        )
        monkeypatch.setattr(harness.time, "time", fake_time)
        monkeypatch.setattr(harness.time, "sleep", fake_sleep)

        result = harness.wait_for_new_run(
            "elastic/oblt-aw",
            "trigger-obs-aw-status.yml",
            since=since,
            timeout_seconds=1,
            interval_seconds=1,
        )
        assert result is None

    def test_agent_job_invoked_ignores_wrapper_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        since = harness._utc_now().replace(microsecond=0)

        monkeypatch.setattr(harness, "list_status_trigger_runs", lambda *_a, **_k: [])
        assert (
            harness.agent_job_invoked(
                "elastic/oblt-aw",
                {
                    "jobs": [
                        {
                            "name": "estc-pr-buildkite-detective",
                            "conclusion": "success",
                        }
                    ]
                },
                since=since,
            )
            is False
        )

    def test_agent_job_invoked_ignores_lock_success_without_agent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        since = harness._utc_now().replace(microsecond=0)
        monkeypatch.setattr(
            harness,
            "list_status_trigger_runs",
            lambda *_a, **_k: [
                {
                    "databaseId": 42,
                    "status": "completed",
                    "conclusion": "success",
                    "createdAt": since.isoformat().replace("+00:00", "Z"),
                }
            ],
        )
        monkeypatch.setattr(
            harness,
            "_view_run_jobs",
            lambda *_a, **_k: {"jobs": [{"name": "agent", "conclusion": "skipped"}]},
        )
        assert (
            harness.agent_job_invoked(
                "elastic/oblt-aw",
                {
                    "jobs": [
                        {
                            "name": "Run obs-aw-status",
                            "conclusion": "success",
                        }
                    ]
                },
                since=since,
            )
            is False
        )

    def test_agent_job_invoked_skips_lock_scan_when_status_job_not_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        since = harness._utc_now().replace(microsecond=0)
        called = {"lock": False}

        def fake_list(*_a: object, **_k: object) -> list[dict[str, object]]:
            called["lock"] = True
            return []

        monkeypatch.setattr(harness, "list_status_trigger_runs", fake_list)
        assert (
            harness.agent_job_invoked(
                "elastic/oblt-aw",
                {
                    "jobs": [
                        {
                            "name": "Run obs-aw-status",
                            "conclusion": "skipped",
                        }
                    ]
                },
                since=since,
            )
            is False
        )
        assert called["lock"] is False

    def test_flatten_slurped_pages_merges_status_pages(self) -> None:
        pages = [
            [{"id": 1, "context": "a"}],
            [{"id": 2, "context": "b"}],
        ]
        flat = harness.flatten_slurped_pages(pages)
        assert [item["id"] for item in flat] == [1, 2]
        assert harness.flatten_slurped_pages([{"id": 1}]) == [{"id": 1}]
        assert harness.flatten_slurped_pages(None) == []

    def test_list_commit_statuses_uses_slurp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, list[str]] = {}

        def fake_gh_json(args: list[str], *, check: bool = True) -> object:
            captured["args"] = args
            return [[{"id": 1}], [{"id": 2}]]

        monkeypatch.setattr(harness, "gh_json", fake_gh_json)
        statuses = harness.list_commit_statuses("elastic/oblt-aw", "abc")
        assert "--slurp" in captured["args"]
        assert "--paginate" in captured["args"]
        assert [s["id"] for s in statuses] == [1, 2]

    def test_infer_status_publisher_from_creator(self) -> None:
        assert (
            harness.infer_status_publisher(
                {"creator": {"login": "buildkite[bot]"}},
                fallback="buildkite",
            )
            == "buildkite"
        )
        assert (
            harness.infer_status_publisher(
                {"creator": {"login": "github-actions[bot]"}},
                fallback="harness",
            )
            == "harness"
        )
        assert (
            harness.infer_status_publisher(
                {"creator": {"login": "someone"}},
                fallback="buildkite",
            )
            == "other"
        )
        # Created-build path must fail closed when creator.login is absent.
        assert (
            harness.infer_status_publisher(
                {"state": "failure", "context": "buildkite/elastic/x"},
                fallback="other",
            )
            == "other"
        )
        assert harness.infer_status_publisher(None, fallback="other") == "other"
        # Call-site seam: created-build path permanently uses fallback=other.
        assert (
            harness.publisher_for_created_build_status(
                {"state": "failure", "context": "buildkite/elastic/x"}
            )
            == "other"
        )
        assert harness.publisher_for_created_build_status(None) == "other"

    def test_status_job_conclusion_fails_closed_without_named_job(self) -> None:
        assert (
            harness.status_job_conclusion(
                {
                    "conclusion": "success",
                    "jobs": [{"name": "unrelated", "conclusion": "success"}],
                }
            )
            is None
        )
        assert (
            harness.status_job_executed({"conclusion": "success", "jobs": []}) is False
        )
        assert (
            harness.status_job_conclusion(
                {
                    "conclusion": "success",
                    "jobs": [
                        {
                            "name": "Run obs-aw-status",
                            "conclusion": "success",
                        }
                    ],
                }
            )
            == "success"
        )
        assert (
            harness.status_job_conclusion(
                {
                    "conclusion": "failure",
                    "jobs": [
                        {
                            "name": "run-obs-aw-status",
                            "conclusion": "skipped",
                        }
                    ],
                }
            )
            == "skipped"
        )

    def test_require_case_mode_rejects_mismatch(self) -> None:
        with pytest.raises(RuntimeError, match="declares mode='fixture'"):
            harness.require_case_mode(
                {"id": "synthetic-case", "mode": "fixture"},
                "live",
                case_id="synthetic-case",
            )

    def test_cli_rejects_unknown_case(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        outcome_path = tmp_path / "outcome.json"
        with pytest.raises(SystemExit, match="Case directory not found"):
            harness.main(
                [
                    "--case-id",
                    "no-such-case",
                    "--outcome-path",
                    str(outcome_path),
                ]
            )

    def test_match_commit_status_requires_context_state_and_url(self) -> None:
        statuses = [
            {
                "context": "buildkite/elastic/oblt-aw-e2e-estc-fail",
                "state": "failure",
                "target_url": "https://buildkite.com/elastic/oblt-aw-e2e-estc-fail/builds/1",
                "created_at": "2026-09-14T10:00:00Z",
            },
            {
                "context": "buildkite/elastic/oblt-aw-e2e-estc-fail",
                "state": "failure",
                "target_url": "https://buildkite.com/elastic/other/builds/9",
                "created_at": "2026-09-14T11:00:00Z",
            },
        ]
        matched = harness.match_commit_status(
            statuses,
            context="buildkite/elastic/oblt-aw-e2e-estc-fail",
            state="failure",
            target_url="https://buildkite.com/elastic/oblt-aw-e2e-estc-fail/builds/1",
        )
        assert matched is not None
        assert matched["target_url"].endswith("/builds/1")
        assert (
            harness.match_commit_status(
                statuses,
                context="buildkite/elastic/oblt-aw-e2e-estc-fail",
                state="success",
                target_url="https://buildkite.com/elastic/oblt-aw-e2e-estc-fail/builds/1",
            )
            is None
        )

    def test_expected_buildkite_status_context_matches_org_pipeline(self) -> None:
        cfg = {
            "buildkite_failure": {
                "org_default": "elastic",
                "pipeline_default": "oblt-aw-e2e-estc-fail",
            }
        }
        assert (
            harness.expected_buildkite_status_context(cfg)
            == "buildkite/elastic/oblt-aw-e2e-estc-fail"
        )
        cfg["expected_status_context"] = "buildkite/custom"
        assert harness.expected_buildkite_status_context(cfg) == "buildkite/custom"

    def test_summarize_and_timeout_block_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        statuses = [
            {
                "context": "CLA",
                "state": "success",
                "target_url": "https://example.test/cla",
                "created_at": "2026-09-15T12:00:00Z",
                "creator": {"login": "cla-bot"},
            }
        ]
        text = harness.summarize_commit_statuses(statuses)
        assert "CLA" in text
        assert "cla-bot" in text
        monkeypatch.setattr(harness, "list_commit_statuses", lambda *_a, **_k: statuses)
        reason = harness.commit_status_timeout_block_reason(
            repo="elastic/oblt-aw",
            sha="abc123",
            context="buildkite/elastic/oblt-aw-e2e-estc-fail",
            state="failure",
            target_url="https://buildkite.com/elastic/oblt-aw-e2e-estc-fail/builds/1",
            timeout_seconds=300,
        )
        assert "Timed out after 300s" in reason
        assert "CLA" in reason
        assert "buildkite/elastic/oblt-aw-e2e-estc-fail" in reason

    def test_sync_fail_pipeline_requires_notify(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pipeline = tmp_path / "pipeline.yml"
        pipeline.write_text("steps: []\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="github_commit_status"):
            harness.sync_fail_pipeline_to_fixture_branch(
                "elastic/oblt-aw",
                branch="e2e/estc-pr-buildkite-detective",
                pipeline_path=pipeline,
            )

    def test_find_open_e2e_pr_strict_branch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            harness,
            "gh_json",
            lambda *_a, **_k: [
                {
                    "number": 3,
                    "url": "https://example.test/pr/3",
                    "headRefName": "other-branch",
                    "headRefOid": "abc",
                    "title": "other",
                    "headRepository": {"nameWithOwner": "elastic/oblt-aw"},
                }
            ],
        )
        with pytest.raises(RuntimeError, match="none use branch"):
            harness.find_open_e2e_pr(
                "elastic/oblt-aw",
                "e2e:estc-pr-buildkite-detective",
                branch="e2e/estc-pr-buildkite-detective",
            )
        assert (
            harness.find_open_e2e_pr(
                "elastic/oblt-aw",
                "e2e:estc-pr-buildkite-detective",
                branch="e2e/estc-pr-buildkite-detective",
                strict_branch=False,
            )
            is None
        )

    def test_find_open_e2e_pr_rejects_fork_head(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            harness,
            "gh_json",
            lambda *_a, **_k: [
                {
                    "number": 9,
                    "url": "https://example.test/pr/9",
                    "headRefName": "e2e/estc-pr-buildkite-detective",
                    "headRefOid": "abc",
                    "title": "fork",
                    "headRepository": {"nameWithOwner": "someone/oblt-aw"},
                }
            ],
        )
        with pytest.raises(RuntimeError, match="same-repo"):
            harness.find_open_e2e_pr(
                "elastic/oblt-aw",
                "e2e:estc-pr-buildkite-detective",
                branch="e2e/estc-pr-buildkite-detective",
            )
        assert (
            harness.find_open_e2e_pr(
                "elastic/oblt-aw",
                "e2e:estc-pr-buildkite-detective",
                branch="e2e/estc-pr-buildkite-detective",
                strict_branch=False,
            )
            is None
        )

    def test_ensure_label_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _Proc:
            returncode = 1
            stdout = ""
            stderr = "HTTP 403: Resource not accessible"

        monkeypatch.setattr(
            harness.subprocess,
            "run",
            lambda *_a, **_k: _Proc(),
        )
        with pytest.raises(RuntimeError, match="Failed to ensure label"):
            harness._ensure_label("elastic/oblt-aw", "e2e:estc-pr-buildkite-detective")


class TestOracle:
    def test_synthetic_live_outcome_passes(self) -> None:
        report = _evaluate(_synthetic_live_outcome())
        assert report["pass"] is True
        assert report["layer"] == "e2e"
        assert report["quarantined"] is False
        assert all(item["pass"] for item in report["checks"])

    def test_quarantine_requires_owner_and_reason(self) -> None:
        outcome = _synthetic_live_outcome()
        incomplete = {
            "default_owner_team": "@elastic/observablt-robots",
            "cases": [
                {
                    "workflow_id": "obs:estc-pr-buildkite-detective",
                    "case_id": LIVE_CASE_ID,
                    "reason": "missing owner",
                }
            ],
        }
        report = _evaluate(outcome, incomplete)
        assert report["quarantined"] is False
        assert report["pass"] is True

    def test_quarantine_skips_with_owner(self) -> None:
        outcome = _synthetic_live_outcome()
        quarantine = {
            "default_owner_team": "@elastic/observablt-robots",
            "cases": [
                {
                    "workflow_id": "obs:estc-pr-buildkite-detective",
                    "case_id": LIVE_CASE_ID,
                    "owner": "@elastic/observablt-robots",
                    "reason": "test quarantine",
                }
            ],
        }
        report = _evaluate(outcome, quarantine)
        assert report["pass"] is False
        assert report["skipped"] is True
        assert report["quarantined"] is True
        assert report["quarantine_owner"] == "@elastic/observablt-robots"
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "quarantine" in failed

    def test_blocked_timeout_notes_mention_commit_status(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": LIVE_CASE_ID,
            "layer": "e2e",
            "mode": "live",
            "blocked": True,
            "block_reason": (
                "Timed out after 300s waiting for GitHub commit status "
                "context='buildkite/elastic/oblt-aw-e2e-estc-fail' "
                "state='failure' target_url='https://buildkite.com/x' on abc."
            ),
            "agent_invoked": False,
            "run_url": "https://example.test/run/1",
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert report["block_reason"]
        assert any(c["id"] == "not_blocked" and not c["pass"] for c in report["checks"])
        assert any("commit status" in n.lower() for n in report["notes"])
        assert any("notify" in n.lower() for n in report["notes"])

    def test_missing_workflow_id_fails_closed(self) -> None:
        outcome = _synthetic_live_outcome()
        del outcome["workflow_id"]
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert report["workflow_id"] == ""
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "workflow_id" in failed

    def test_non_live_mode_fails_closed(self) -> None:
        outcome = _synthetic_live_outcome()
        outcome["mode"] = "fixture"
        outcome["layer"] = "integration"
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "mode_live_only" in failed

    def test_live_oracle_rejects_string_expect_agent_comment(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "trigger": {
                "status_state": "failure",
                "context_contains_buildkite": True,
                "use_buildkite_target_url": True,
                "create_failed_buildkite_build": True,
            },
            "status": {
                "state": "failure",
                "context": "buildkite/elastic/x",
                "target_url": "https://buildkite.com/elastic/x/builds/1",
                "publisher": "buildkite",
            },
            "buildkite": {"source": "created", "fail_log_marker_verified": True},
            "status_trigger": {
                "run_seen": True,
                "job_executed": True,
                "job_conclusion": "success",
                "url": "https://example.test/run",
            },
            "agent_comment": {"id": 1},
        }
        report = _evaluate(
            outcome,
            case_expectations={
                "dashboard_enabled": True,
                "status_job_executed": True,
                "agent_invoked": True,
                "expect_agent_comment": "true",
            },
        )
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_expectations" in failed

    def test_live_oracle_requires_comment_present(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "trigger": {
                "status_state": "failure",
                "context_contains_buildkite": True,
                "use_buildkite_target_url": True,
                "create_failed_buildkite_build": True,
            },
            "status": {
                "state": "failure",
                "context": "buildkite/elastic/x",
                "target_url": "https://buildkite.com/elastic/x/builds/1",
                "publisher": "buildkite",
            },
            "buildkite": {"source": "created", "fail_log_marker_verified": True},
            "status_trigger": {
                "run_seen": True,
                "job_executed": True,
                "job_conclusion": "success",
                "url": "https://example.test/run",
            },
            "agent_comment": {
                "id": 1,
                "url": "https://example.test/comment",
                "markers_present": {"### TL;DR": True, "## Remediation": True},
            },
        }
        report = _evaluate(outcome)
        assert report["pass"] is True
        assert report["layer"] == "e2e"
        check_ids = {c["id"] for c in report["checks"]}
        assert "agent_comment_present" in check_ids
        assert "agent_comment_markers" not in check_ids

    def test_live_oracle_asserts_trigger_status_contract(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "trigger": {
                "status_state": "failure",
                "context_contains_buildkite": True,
                "use_buildkite_target_url": True,
                "create_failed_buildkite_build": True,
            },
            "status": {
                "state": "success",
                "context": "ci/other",
                "publisher": "harness",
            },
            "buildkite": {"source": "created", "fail_log_marker_verified": True},
            "status_trigger": {
                "run_seen": True,
                "job_executed": True,
                "job_conclusion": "success",
            },
            "agent_comment": {
                "id": 1,
                "markers_present": {"### TL;DR": True, "## Remediation": True},
            },
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "status_state" in failed
        assert "status_context_buildkite" in failed
        assert "status_target_url" in failed
        assert "status_publisher_buildkite_path" in failed

    def test_live_oracle_presence_only_ignores_marker_shape(self) -> None:
        """Oracle asserts comment id presence; marker shape is harness identity."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "trigger": {
                "status_state": "failure",
                "context_contains_buildkite": True,
                "use_buildkite_target_url": True,
                "create_failed_buildkite_build": True,
            },
            "status": {
                "state": "failure",
                "context": "buildkite/elastic/x",
                "target_url": "https://buildkite.com/elastic/x/builds/1",
                "publisher": "buildkite",
            },
            "buildkite": {"source": "created", "fail_log_marker_verified": True},
            "status_trigger": {
                "run_seen": True,
                "job_executed": True,
                "job_conclusion": "success",
                "url": "https://example.test/run",
            },
            "agent_comment": {"id": 1, "markers_present": {"### TL;DR": False}},
        }
        report = _evaluate(outcome)
        assert report["pass"] is True
        check_ids = {c["id"] for c in report["checks"]}
        assert "agent_comment_present" in check_ids
        assert "agent_comment_markers" not in check_ids

    def test_live_oracle_requires_run_seen(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/elastic/x"},
            "status_trigger": {"run_seen": False, "job_executed": False},
            "agent_comment": None,
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "status_trigger_run_seen" in failed

    def test_live_oracle_rejects_string_bool_coercion(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "status_trigger": {"run_seen": True, "job_executed": True},
            "agent_comment": {
                "id": 1,
                "markers_present": {"### TL;DR": True, "## Remediation": True},
            },
        }
        report = _evaluate(
            outcome,
            case_expectations={
                "dashboard_enabled": "yes",
                "status_job_executed": True,
                "agent_invoked": True,
                "expect_agent_comment": True,
            },
        )
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_expectations" in failed

    def test_live_oracle_rejects_string_agent_invoked(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": "false",
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "failure", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": True,
                "job_conclusion": "success",
            },
        }
        report = _evaluate(
            outcome,
            case_expectations={
                "dashboard_enabled": True,
                "status_job_executed": True,
                "agent_invoked": True,
                "expect_agent_comment": False,
            },
        )
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "agent_invoked" in failed

    def test_live_oracle_rejects_harness_publisher_on_created_build(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "trigger": {
                "status_state": "failure",
                "context_contains_buildkite": True,
                "use_buildkite_target_url": True,
                "create_failed_buildkite_build": True,
            },
            "status": {
                "state": "failure",
                "context": "buildkite/elastic/x",
                "target_url": "https://buildkite.com/elastic/x/builds/1",
                "publisher": "harness",
            },
            "buildkite": {"source": "created", "fail_log_marker_verified": True},
            "status_trigger": {
                "run_seen": True,
                "job_executed": True,
                "job_conclusion": "success",
            },
            "agent_comment": {
                "id": 1,
                "markers_present": {"### TL;DR": True, "## Remediation": True},
            },
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "status_publisher_buildkite_path" in failed

    def test_live_oracle_fails_closed_on_missing_buildkite_source(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-failure-open-pr-live",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": True,
            "path_gates": {"dashboard_enabled": True},
            "trigger": {
                "status_state": "failure",
                "context_contains_buildkite": True,
                "use_buildkite_target_url": True,
                "create_failed_buildkite_build": True,
            },
            "status": {
                "state": "failure",
                "context": "buildkite/elastic/x",
                "target_url": "https://buildkite.com/elastic/x/builds/1",
                "publisher": "buildkite",
            },
            "buildkite": {},
            "status_trigger": {
                "run_seen": True,
                "job_executed": True,
                "job_conclusion": "success",
            },
            "agent_comment": {
                "id": 1,
                "markers_present": {"### TL;DR": True, "## Remediation": True},
            },
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "buildkite_source_valid" in failed

    def test_oracle_main_rejects_case_id_mismatch(self, tmp_path: pathlib.Path) -> None:
        outcome_path = tmp_path / "outcome.json"
        report_path = tmp_path / "report.json"
        outcome_path.write_text(
            json.dumps(
                {
                    "workflow_id": "obs:estc-pr-buildkite-detective",
                    "case_id": "status-success-skipped",
                    "layer": "e2e",
                    "mode": "live",
                    "agent_invoked": False,
                    "expectations": {"expect_agent_comment": False},
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit, match="does not match"):
            oracle.main(
                [
                    "--outcome-path",
                    str(outcome_path),
                    "--report-path",
                    str(report_path),
                    "--expected-case-id",
                    "status-failure-open-pr-live",
                ]
            )

    def test_live_oracle_requires_skipped_conclusion_for_negative_cases(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "trigger": {
                "status_state": "success",
                "context_contains_buildkite": True,
            },
            "status": {
                "state": "success",
                "context": "buildkite/elastic/x",
                "publisher": "harness",
            },
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "failure",
                "url": "https://example.test/run",
            },
            "agent_comment": None,
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "status_job_skipped" in failed

    def test_live_oracle_rejects_wrong_layer(self) -> None:
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "integration",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "layer_e2e" in failed

    def test_oracle_rejects_missing_case_expectations(self) -> None:
        """Do not authorize gate checks when checked-in expectations are absent."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "no-such-case",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
            # Harness-copied blob must not authorize gates when case file is absent.
            "expectations": {
                "dashboard_enabled": True,
                "status_job_executed": False,
                "agent_invoked": False,
                "expect_agent_comment": False,
            },
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_expectations" in failed

    def test_oracle_rejects_empty_case_expectations_mapping(self) -> None:
        """Empty checked-in expectations must not skip all gate assertions."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
        }
        report = oracle.evaluate_outcome(
            outcome,
            {"cases": []},
            case_expectations={},
            case_trigger=oracle.load_case_trigger(
                TESTDATA_ROOT, "status-success-skipped"
            ),
        )
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_expectations" in failed

    def test_oracle_rejects_typo_only_case_expectations_mapping(self) -> None:
        """Non-empty but schema-incomplete expectations must not skip gates."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
        }
        report = oracle.evaluate_outcome(
            outcome,
            {"cases": []},
            case_expectations={"typo": True},
            case_trigger=oracle.load_case_trigger(
                TESTDATA_ROOT, "status-success-skipped"
            ),
        )
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_expectations" in failed
        assert "status_job_executed" not in {c["id"] for c in report["checks"]}

    def test_oracle_rejects_partial_live_case_expectations(self) -> None:
        """Missing a required live key must fail closed even if others are present."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
        }
        report = oracle.evaluate_outcome(
            outcome,
            {"cases": []},
            case_expectations={
                "dashboard_enabled": True,
                "agent_invoked": False,
                "expect_agent_comment": False,
                # status_job_executed omitted on purpose
            },
            case_trigger=oracle.load_case_trigger(
                TESTDATA_ROOT, "status-success-skipped"
            ),
        )
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_expectations" in failed

    def test_oracle_rejects_missing_or_empty_case_trigger(self) -> None:
        """Live routing gates must not run when checked-in trigger is absent."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
            # Harness-copied trigger must not authorize gates.
            "trigger": {
                "status_state": "success",
                "context_contains_buildkite": True,
                "require_open_pr": True,
                "use_buildkite_target_url": True,
                "clear_prior_detective_comments": False,
            },
        }
        expectations = oracle.load_case_expectations(
            TESTDATA_ROOT, "status-success-skipped"
        )
        report = oracle.evaluate_outcome(
            outcome,
            {"cases": []},
            case_expectations=expectations,
            case_trigger={},
        )
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_trigger" in failed
        assert "status_state" not in {c["id"] for c in report["checks"]}

    def test_oracle_rejects_partial_live_case_trigger(self) -> None:
        """Incomplete trigger must fail closed even when expectations are complete."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
        }
        report = oracle.evaluate_outcome(
            outcome,
            {"cases": []},
            case_expectations=oracle.load_case_expectations(
                TESTDATA_ROOT, "status-success-skipped"
            ),
            case_trigger={"status_state": "success"},
        )
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_trigger" in failed

    def test_oracle_ignores_empty_outcome_trigger_when_case_trigger_present(
        self,
    ) -> None:
        """Checked-in trigger must authorize gates even if outcome.trigger is empty."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "trigger": {},
            "status": {
                "state": "success",
                "context": "buildkite/x",
                "target_url": "u",
                "publisher": "harness",
            },
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
        }
        report = _evaluate(outcome)
        assert report["pass"] is True
        check_ids = {c["id"] for c in report["checks"]}
        assert "status_state" in check_ids
        assert "status_context_buildkite" in check_ids
        assert "status_target_url" in check_ids

    def test_oracle_rejects_run_conclusion_as_job_skipped(self) -> None:
        """Missing named-job conclusion must not inherit overall run conclusion."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": None,
                "conclusion": "skipped",
            },
            "agent_comment": None,
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "status_job_skipped" in failed

    def test_oracle_helper_ignores_outcome_expectations_by_default(self) -> None:
        """Unit helper must not green gates from harness-copied outcome.expectations."""
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "no-such-case",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {"state": "success", "context": "buildkite/x"},
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
            "expectations": {
                "dashboard_enabled": True,
                "status_job_executed": False,
                "agent_invoked": False,
                "expect_agent_comment": False,
            },
        }
        report = _evaluate(outcome)
        assert report["pass"] is False
        failed = {c["id"] for c in report["checks"] if not c["pass"]}
        assert "case_expectations" in failed

    def test_oracle_prefers_case_file_expectations(
        self, tmp_path: pathlib.Path
    ) -> None:
        case_dir = tmp_path / "cases" / "status-success-skipped"
        case_dir.mkdir(parents=True)
        (case_dir / "case.json").write_text(
            json.dumps(
                {
                    "id": "status-success-skipped",
                    "mode": "live",
                    "trigger": {
                        "status_state": "success",
                        "context_contains_buildkite": True,
                        "require_open_pr": True,
                        "use_buildkite_target_url": True,
                        "clear_prior_detective_comments": False,
                    },
                    "expectations": {
                        "dashboard_enabled": True,
                        "status_job_executed": False,
                        "agent_invoked": False,
                        "expect_agent_comment": False,
                    },
                }
            ),
            encoding="utf-8",
        )
        outcome = {
            "workflow_id": "obs:estc-pr-buildkite-detective",
            "case_id": "status-success-skipped",
            "layer": "e2e",
            "mode": "live",
            "agent_invoked": False,
            "path_gates": {"dashboard_enabled": True},
            "status": {
                "state": "success",
                "context": "buildkite/x",
                "target_url": "https://buildkite.com/elastic/x/builds/1",
                "publisher": "harness",
            },
            "status_trigger": {
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": "skipped",
            },
            "agent_comment": None,
            # Maliciously empty harness expectations — case file must win.
            "expectations": {},
            "trigger": {},
        }
        report = oracle.evaluate_outcome(
            outcome,
            {"cases": []},
            case_expectations=oracle.load_case_expectations(
                tmp_path, "status-success-skipped"
            ),
            case_trigger=oracle.load_case_trigger(tmp_path, "status-success-skipped"),
        )
        assert report["pass"] is True

    def test_cli_writes_report_and_summary(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(ROOT)
        outcome_path = tmp_path / "outcome.json"
        report_path = tmp_path / "report.json"
        summary_path = tmp_path / "summary.json"
        outcome_path.write_text(
            json.dumps(_synthetic_live_outcome()),
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
                "--quarantine-path",
                str(ROOT / "config" / "obs" / "e2e-quarantine.json"),
                "--testdata-root",
                str(ROOT / "testdata" / "agentic" / "estc-pr-buildkite-detective"),
            ]
        )
        assert code == 0
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["pass"] is True
        assert summary["workflow_id"] == "obs:estc-pr-buildkite-detective"
        assert summary["layer"] == "e2e"
        assert summary.get("failed_checks") == []
        assert summary.get("failure_detail") is None

    def test_cli_summary_includes_block_reason(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(ROOT)
        outcome_path = tmp_path / "outcome.json"
        report_path = tmp_path / "report.json"
        summary_path = tmp_path / "summary.json"
        outcome_path.write_text(
            json.dumps(
                {
                    "workflow_id": "obs:estc-pr-buildkite-detective",
                    "case_id": LIVE_CASE_ID,
                    "layer": "e2e",
                    "mode": "live",
                    "blocked": True,
                    "block_reason": (
                        "Timed out after 300s waiting for GitHub commit status "
                        "context='buildkite/elastic/oblt-aw-e2e-estc-fail'"
                    ),
                    "agent_invoked": False,
                }
            ),
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
                "--quarantine-path",
                str(ROOT / "config" / "obs" / "e2e-quarantine.json"),
                "--testdata-root",
                str(ROOT / "testdata" / "agentic" / "estc-pr-buildkite-detective"),
            ]
        )
        assert code == 1
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["pass"] is False
        assert "Timed out" in (summary.get("failure_detail") or "")
        assert summary.get("failed_checks")
        captured = capsys.readouterr()
        assert "Oracle failed checks" in captured.out
        assert "not_blocked" in captured.out
