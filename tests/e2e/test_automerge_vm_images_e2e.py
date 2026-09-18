"""
Unit tests for obs:automerge:vm-images E2E harness and oracle.
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import automerge_vm_images_e2e_harness as harness
import oracle_automerge_vm_images_e2e as oracle

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "automerge-vm-images"
LIVE_CASE_ID = "vm-images-bump-live"


def _live_case() -> dict:
    return json.loads(
        (TESTDATA_ROOT / "cases" / LIVE_CASE_ID / "case.json").read_text(
            encoding="utf-8"
        )
    )


def _synthetic_live_outcome(**overrides: object) -> dict:
    base = {
        "workflow_id": "obs:automerge",
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
        "dependency_collection_gate_comment": None,
        "automerge": {
            "run_seen": True,
            "job_executed": True,
            "approve_job_executed": True,
            "job_conclusion": "success",
        },
        "approving_review": {
            "id": 9,
            "user": "github-actions[bot]",
            "state": "APPROVED",
        },
        "merge": {"merged": True, "auto_merge_enabled": False},
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


def test_bump_image_pins_updates_playground_shaped_lines() -> None:
    src = (
        'IMAGE_UBUNTU: "platform-ingest-elastic-agent-ubuntu-111"\n'
        'IMAGE_UBUNTU_ARM: "platform-ingest-elastic-agent-ubuntu_arm-111"\n'
    )
    out = harness.bump_image_pins(src, "999")
    assert "ubuntu-999" in out
    assert "ubuntu_arm-999" in out
    assert "111" not in out


def test_bump_image_pins_fails_closed_without_pins() -> None:
    with pytest.raises(RuntimeError, match="no IMAGE_"):
        harness.bump_image_pins("steps: []\n", "1")


def test_author_login_from_rest_pull_uses_webhook_form() -> None:
    """REST user.login is …[bot]; GraphQL app/… must not authorize."""
    login = harness.author_login_from_rest_pull(
        {
            "user": {
                "login": "elastic-vault-github-plugin-prod[bot]",
                "type": "Bot",
            }
        }
    )
    assert login == "elastic-vault-github-plugin-prod[bot]"
    assert login != "app/elastic-vault-github-plugin-prod"


def test_author_login_from_rest_pull_fails_closed_without_login() -> None:
    with pytest.raises(RuntimeError, match="user.login"):
        harness.author_login_from_rest_pull({"user": {"login": ""}})
    with pytest.raises(TypeError, match="missing object user"):
        harness.author_login_from_rest_pull({"user": None})  # type: ignore[dict-item]
    with pytest.raises(TypeError, match="missing object user"):
        harness.author_login_from_rest_pull({})


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
            {
                "name": "run-obs-aw-pull-request / dependency-review / notify-no-comment",
                "conclusion": "skipped",
            },
        ]
    }
    assert harness.dependency_review_job_executed(success) is True
    assert harness.dependency_review_job_conclusion(success) == "success"


def test_dependency_review_job_ignores_skipped_wrapper_only() -> None:
    skipped_only = {
        "jobs": [
            {
                "name": "run-obs-aw-pull-request / dependency-review",
                "conclusion": "skipped",
            }
        ]
    }
    assert harness.dependency_review_job_executed(skipped_only) is False
    assert harness.dependency_review_job_conclusion(skipped_only) is None


def test_dependency_review_job_ignores_agent_without_conclusion() -> None:
    """Broad `` / dependency-review`` and agent-only must not green the gate."""
    agent_only = {
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
            {
                "name": "run-obs-aw-pull-request / automerge / approve / conclusion",
                "conclusion": "success",
            },
        ]
    }
    assert harness.dependency_review_job_executed(agent_only) is False
    assert harness.dependency_review_job_conclusion(agent_only) is None


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


def test_oracle_rejects_empty_trigger() -> None:
    report = _evaluate(_synthetic_live_outcome(), case_trigger={})
    assert report["pass"] is False
    ids = {c["id"] for c in report["checks"] if not c["pass"]}
    assert "case_trigger" in ids


def test_oracle_fails_when_dependency_collection_gate_comment_present() -> None:
    report = _evaluate(
        _synthetic_live_outcome(
            dependency_collection_gate_comment={"id": 42, "marker": "gate"}
        )
    )
    assert report["pass"] is False
    failed = {c["id"]: c for c in report["checks"] if not c["pass"]}
    assert "no_dependency_collection_gate" in failed


def test_oracle_fails_when_not_merged() -> None:
    report = _evaluate(
        _synthetic_live_outcome(
            merge={"merged": False, "auto_merge_enabled": False, "timed_out": True}
        )
    )
    assert report["pass"] is False
    assert any(
        c["id"] == "pr_merged_or_auto_merge" and not c["pass"] for c in report["checks"]
    )


def test_oracle_accepts_auto_merge_enabled() -> None:
    report = _evaluate(
        _synthetic_live_outcome(merge={"merged": False, "auto_merge_enabled": True})
    )
    assert report["pass"] is True


def test_oracle_blocked_outcome_fails() -> None:
    report = _evaluate(
        {
            "workflow_id": "obs:automerge",
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


def test_oracle_fails_closed_when_only_approve_job_executed() -> None:
    """Approve must not authorize the automerge merge-job expectation."""
    report = _evaluate(
        _synthetic_live_outcome(
            automerge={
                "run_seen": True,
                "job_executed": False,
                "approve_job_executed": True,
                "job_conclusion": None,
            }
        )
    )
    assert report["pass"] is False
    assert any(
        c["id"] == "automerge_job_executed" and not c["pass"] for c in report["checks"]
    )


def test_oracle_fails_closed_on_automerge_without_named_conclusion() -> None:
    report = _evaluate(
        _synthetic_live_outcome(
            automerge={
                "run_seen": True,
                "job_executed": True,
                "approve_job_executed": True,
                "job_conclusion": None,
            }
        )
    )
    assert report["pass"] is False
    assert any(
        c["id"] == "automerge_job_executed" and not c["pass"] for c in report["checks"]
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


def test_oracle_fails_when_author_gate_false() -> None:
    report = _evaluate(
        _synthetic_live_outcome(
            path_gates={
                "dashboard_enabled": True,
                "author_matches_allowed": False,
            }
        )
    )
    assert report["pass"] is False
    assert any(c["id"] == "author_allowed" and not c["pass"] for c in report["checks"])


def test_config_allowed_author_is_vault_bot() -> None:
    assert harness.ALLOWED_AUTHOR == "elastic-vault-github-plugin-prod[bot]"
    cfg = json.loads(
        (ROOT / "config" / "obs" / "e2e-automerge-vm-images.json").read_text(
            encoding="utf-8"
        )
    )
    assert cfg["allowed_pr_author"] == harness.ALLOWED_AUTHOR


def _run_with_jobs(*jobs: dict) -> dict:
    return {"jobs": list(jobs)}


def test_automerge_job_executed_ignores_verify_sibling() -> None:
    detail = _run_with_jobs(
        {
            "name": "run-obs-aw-pull-request / automerge / verify",
            "conclusion": "success",
        },
        {
            "name": "run-obs-aw-pull-request / automerge / approve",
            "conclusion": "success",
        },
    )
    assert harness.automerge_job_executed(detail) is False
    assert harness.approve_job_executed(detail) is True


def test_automerge_job_executed_requires_merge_leaf() -> None:
    detail = _run_with_jobs(
        {
            "name": "run-obs-aw-pull-request / automerge / verify",
            "conclusion": "success",
        },
        {
            "name": "run-obs-aw-pull-request / automerge / automerge",
            "conclusion": "success",
        },
    )
    assert harness.automerge_job_executed(detail) is True


def test_automerge_job_executed_ignores_broad_automerge_substring() -> None:
    """Wrapper path ending in / automerge must not authorize the merge leaf."""
    detail = _run_with_jobs(
        {
            "name": "run-obs-aw-pull-request / automerge",
            "conclusion": "success",
        }
    )
    assert harness.automerge_job_executed(detail) is False


def test_seed_fixture_pipeline_noop_when_remote_matches(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline = tmp_path / "pipeline.yml"
    pipeline.write_text("steps: []\n", encoding="utf-8")
    encoded = base64.b64encode(b"steps: []\n").decode("ascii")

    def fake_run(cmd: list[str], **_kwargs: object) -> object:
        class Proc:
            returncode = 0
            stdout = json.dumps({"content": encoded, "sha": "abc"})
            stderr = ""

        assert "contents/" in cmd[-1]
        return Proc()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    assert (
        harness.seed_fixture_pipeline_on_default_branch(
            "elastic/oblt-aw",
            default_branch="main",
            pipeline_path=pipeline,
        )
        is None
    )


def test_seed_fixture_pipeline_refuses_overwrite(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline = tmp_path / "pipeline.yml"
    pipeline.write_text("steps: []\n", encoding="utf-8")
    other = base64.b64encode(b"steps: [different]\n").decode("ascii")

    def fake_run(cmd: list[str], **_kwargs: object) -> object:
        class Proc:
            returncode = 0
            stdout = json.dumps({"content": other, "sha": "abc"})
            stderr = ""

        return Proc()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        harness.seed_fixture_pipeline_on_default_branch(
            "elastic/oblt-aw",
            default_branch="main",
            pipeline_path=pipeline,
        )


def test_case_json_schema_matches_oracle_required_keys() -> None:
    case = _live_case()
    assert oracle.case_expectations_schema_error("live", case["expectations"]) is None
    assert oracle.case_trigger_schema_error(case["trigger"]) is None


def test_harness_trigger_bool_accepts_legacy_author_key() -> None:
    assert (
        harness._trigger_bool(  # type: ignore[attr-defined]
            {"require_github_actions_author": False},
            "require_allowed_pr_author",
            default=True,
            aliases=("require_github_actions_author",),
        )
        is False
    )


def test_oracle_trigger_schema_accepts_legacy_author_key() -> None:
    trigger = dict(_live_case()["trigger"])
    trigger["require_github_actions_author"] = trigger.pop("require_allowed_pr_author")
    assert oracle.case_trigger_schema_error(trigger) is None


def test_required_dashboard_ids_from_config() -> None:
    cfg = json.loads(
        (ROOT / "config" / "obs" / "e2e-automerge-vm-images.json").read_text(
            encoding="utf-8"
        )
    )
    ids = harness.required_dashboard_ids(cfg)
    assert "obs:automerge:vm-images" in ids
    assert "obs:dependency-review" in ids
    assert "obs:automerge" in ids


def test_shared_e2e_token_policy_matches_documented_role() -> None:
    cfg = json.loads((ROOT / "config" / "e2e.json").read_text(encoding="utf-8"))
    doc_path = ROOT / cfg["workflow-token-policy-doc"].split("#", 1)[0]
    doc_text = doc_path.read_text(encoding="utf-8")
    assert cfg["workflow-token-policy"] in doc_text
