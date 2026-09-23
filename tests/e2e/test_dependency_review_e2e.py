"""
Unit tests for obs:dependency-review E2E harness and oracle.
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import dependency_review_e2e_harness as harness
import oracle_dependency_review_e2e as oracle

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "dependency-review"
LIVE_CASE_ID = "actions-pin-bump-live"


def _live_case() -> dict:
    """Load checked-in case.json — production evidence source for oracle tests."""
    return json.loads(
        (TESTDATA_ROOT / "cases" / LIVE_CASE_ID / "case.json").read_text(
            encoding="utf-8"
        )
    )


def _synthetic_live_outcome(**overrides: object) -> dict:
    base = {
        "workflow_id": "obs:dependency-review",
        "case_id": LIVE_CASE_ID,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": True,
        "path_gates": {
            "dashboard_enabled": True,
            "author_matches_allowed": True,
        },
        "dependency_review": {
            "run_seen": True,
            "job_executed": True,
            "job_conclusion": "success",
            "url": "https://example.test/dr",
        },
        "merge_ready_label": {
            "name": "oblt-aw/ai/merge-ready",
            "applied": True,
        },
        "dependency_review_comment": {"id": 1},
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


def test_bump_checkout_pin_updates_sha_and_version() -> None:
    src = (
        "uses: actions/checkout@"
        f"{harness.SEED_CHECKOUT_SHA} # {harness.SEED_CHECKOUT_VERSION}\n"
    )
    out = harness.bump_checkout_pin(
        src, sha=harness.BUMP_CHECKOUT_SHA, version=harness.BUMP_CHECKOUT_VERSION
    )
    assert harness.BUMP_CHECKOUT_SHA in out
    assert harness.BUMP_CHECKOUT_VERSION in out
    assert harness.SEED_CHECKOUT_SHA not in out


def test_bump_checkout_pin_fails_closed_without_pin() -> None:
    with pytest.raises(RuntimeError, match="no actions/checkout"):
        harness.bump_checkout_pin(
            "uses: actions/checkout@v4\n",
            sha=harness.BUMP_CHECKOUT_SHA,
            version=harness.BUMP_CHECKOUT_VERSION,
        )


def test_bump_checkout_pin_rejects_non_hex_sha() -> None:
    with pytest.raises(RuntimeError, match="40-char hex"):
        harness.bump_checkout_pin(
            f"uses: actions/checkout@{harness.SEED_CHECKOUT_SHA} # v4.2.2\n",
            sha="not-a-sha",
            version="v4.3.0",
        )


def test_author_login_from_rest_pull_uses_webhook_form() -> None:
    login = harness.author_login_from_rest_pull(
        {
            "user": {
                "login": "elastic-vault-github-plugin-prod[bot]",
                "type": "Bot",
            }
        }
    )
    assert login == "elastic-vault-github-plugin-prod[bot]"


def test_dependency_review_job_matches_nested_conclusion_leaf() -> None:
    """GH-AW terminal leaf authorizes; skipped wrapper / siblings do not."""
    success = {
        "jobs": [
            {
                "name": "run-obs-aw-pull-request / dependency-review",
                "conclusion": "skipped",
            },
            {
                "name": (
                    "run-obs-aw-pull-request / dependency-review / "
                    "dependency-review / agent"
                ),
                "conclusion": "success",
            },
            {
                "name": (
                    "run-obs-aw-pull-request / dependency-review / "
                    "dependency-review / conclusion"
                ),
                "conclusion": "success",
            },
        ]
    }
    assert harness.dependency_review_job_executed(success) is True
    assert harness.dependency_review_job_conclusion(success) == "success"


def test_dependency_review_job_ignores_broad_suffix() -> None:
    """Broad `` / dependency-review`` (wrapper) must not green the gate."""
    broad_only = {
        "jobs": [
            {
                "name": "run-obs-aw-pull-request / dependency-review",
                "conclusion": "success",
            },
            {
                "name": (
                    "run-obs-aw-pull-request / dependency-review / "
                    "dependency-review / agent"
                ),
                "conclusion": "success",
            },
            {
                "name": "run-obs-aw-pull-request / dependency-review / notify-no-comment",
                "conclusion": "success",
            },
        ]
    }
    assert harness.dependency_review_job_executed(broad_only) is False
    assert harness.dependency_review_job_conclusion(broad_only) is None


def test_oracle_happy_path_passes() -> None:
    report = _evaluate(_synthetic_live_outcome())
    assert report["pass"] is True
    assert not any(not c["pass"] for c in report["checks"])


def test_oracle_rejects_empty_expectations() -> None:
    report = _evaluate(_synthetic_live_outcome(), case_expectations={})
    assert report["pass"] is False
    ids = {c["id"] for c in report["checks"] if not c["pass"]}
    assert "case_expectations" in ids


def test_oracle_rejects_typo_only_expectations() -> None:
    report = _evaluate(
        _synthetic_live_outcome(),
        case_expectations={"typo": True},
    )
    assert report["pass"] is False
    failed = [c for c in report["checks"] if c["id"] == "case_expectations"]
    assert failed and failed[0]["pass"] is False


def test_oracle_rejects_partial_expectations() -> None:
    """Missing a required mode key must fail closed (not skip if-key-in gates)."""
    partial = {
        "dashboard_enabled": True,
        "dependency_review_job_executed": True,
        # missing merge_ready_label_applied + dependency_review_comment
    }
    report = _evaluate(_synthetic_live_outcome(), case_expectations=partial)
    assert report["pass"] is False
    failed = [c for c in report["checks"] if c["id"] == "case_expectations"]
    assert failed and "missing required keys" in str(failed[0]["detail"])


def test_oracle_rejects_empty_trigger() -> None:
    report = _evaluate(_synthetic_live_outcome(), case_trigger={})
    assert report["pass"] is False
    ids = {c["id"] for c in report["checks"] if not c["pass"]}
    assert "case_trigger" in ids


def test_oracle_blocked_outcome_fails() -> None:
    report = _evaluate(
        {
            "workflow_id": "obs:dependency-review",
            "case_id": LIVE_CASE_ID,
            "layer": "e2e",
            "mode": "live",
            "blocked": True,
            "block_reason": "Dashboard missing required ids",
            "agent_invoked": False,
        }
    )
    assert report["pass"] is False
    assert report["block_reason"]


def test_oracle_fails_closed_on_overall_conclusion_without_named_job() -> None:
    """Named job_conclusion must authorize dependency-review — not run conclusion."""
    report = _evaluate(
        _synthetic_live_outcome(
            dependency_review={
                "run_seen": True,
                "job_executed": False,
                "job_conclusion": None,
                "conclusion": "success",
            }
        )
    )
    assert report["pass"] is False
    assert any(
        c["id"] == "dependency_review_job_executed" and not c["pass"]
        for c in report["checks"]
    )


def test_oracle_fails_when_merge_ready_missing() -> None:
    report = _evaluate(
        _synthetic_live_outcome(
            merge_ready_label={"name": "oblt-aw/ai/merge-ready", "applied": False}
        )
    )
    assert report["pass"] is False
    assert any(
        c["id"] == "merge_ready_label_applied" and not c["pass"]
        for c in report["checks"]
    )


def test_oracle_fails_when_comment_missing() -> None:
    report = _evaluate(_synthetic_live_outcome(dependency_review_comment=None))
    assert report["pass"] is False
    assert any(
        c["id"] == "dependency_review_comment" and not c["pass"]
        for c in report["checks"]
    )


def test_oracle_fails_closed_on_non_bool_author_gate() -> None:
    report = _evaluate(
        _synthetic_live_outcome(
            path_gates={
                "dashboard_enabled": True,
                "author_matches_allowed": "yes",
            }
        )
    )
    assert report["pass"] is False
    assert any(c["id"] == "author_allowed" and not c["pass"] for c in report["checks"])


def test_config_allowed_author_is_vault_bot() -> None:
    assert harness.ALLOWED_AUTHOR == "elastic-vault-github-plugin-prod[bot]"
    cfg = json.loads(
        (ROOT / "config" / "obs" / "e2e-dependency-review.json").read_text(
            encoding="utf-8"
        )
    )
    assert cfg["allowed_pr_author"] == harness.ALLOWED_AUTHOR


def test_seed_fixture_workflow_noop_when_remote_matches(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = tmp_path / "fixture.yml"
    workflow.write_text("name: fixture\n", encoding="utf-8")
    encoded = base64.b64encode(b"name: fixture\n").decode("ascii")

    def fake_run(cmd: list[str], **_kwargs: object) -> object:
        class Proc:
            returncode = 0
            stdout = json.dumps({"content": encoded, "sha": "abc"})
            stderr = ""

        assert "contents/" in cmd[-1]
        return Proc()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    assert (
        harness.seed_fixture_workflow_on_default_branch(
            "elastic/oblt-aw",
            default_branch="main",
            workflow_path=workflow,
        )
        is None
    )


def test_seed_fixture_workflow_refuses_overwrite(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = tmp_path / "fixture.yml"
    workflow.write_text("name: fixture\n", encoding="utf-8")
    other = base64.b64encode(b"name: other\n").decode("ascii")

    def fake_run(cmd: list[str], **_kwargs: object) -> object:
        class Proc:
            returncode = 0
            stdout = json.dumps({"content": other, "sha": "abc"})
            stderr = ""

        return Proc()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        harness.seed_fixture_workflow_on_default_branch(
            "elastic/oblt-aw",
            default_branch="main",
            workflow_path=workflow,
        )


def test_case_json_schema_matches_oracle_required_keys() -> None:
    case = _live_case()
    assert oracle.case_expectations_schema_error("live", case["expectations"]) is None
    assert oracle.case_trigger_schema_error(case["trigger"]) is None


def test_required_dashboard_ids_from_config() -> None:
    cfg = json.loads(
        (ROOT / "config" / "obs" / "e2e-dependency-review.json").read_text(
            encoding="utf-8"
        )
    )
    ids = harness.required_dashboard_ids(cfg)
    assert ids == ["obs:dependency-review"]


def test_fixture_workflow_seeds_known_checkout_pin() -> None:
    path = ROOT / ".github" / "workflows" / "e2e-dependency-review-actions-fixture.yml"
    text = path.read_text(encoding="utf-8")
    assert harness.SEED_CHECKOUT_SHA in text
    assert f"# {harness.SEED_CHECKOUT_VERSION}" in text
    assert "actions/checkout@" in text


def test_evaluate_defaults_to_checked_in_case_not_outcome_expectations() -> None:
    """Unit helpers must load case.json; harness-copied outcome.expectations ignored."""
    outcome = _synthetic_live_outcome(
        expectations={"typo": True},
        trigger={},
    )
    report = _evaluate(outcome)
    assert report["pass"] is True
