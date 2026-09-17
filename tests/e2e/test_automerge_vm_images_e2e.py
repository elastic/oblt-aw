"""
Unit tests for obs:automerge:vm-images E2E harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

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
            "author_is_github_actions": True,
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
            "user": "elastic-vault-github-plugin-prod[bot]",
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


def test_case_json_schema_matches_oracle_required_keys() -> None:
    case = _live_case()
    assert oracle.case_expectations_schema_error("live", case["expectations"]) is None
    assert oracle.case_trigger_schema_error(case["trigger"]) is None


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
