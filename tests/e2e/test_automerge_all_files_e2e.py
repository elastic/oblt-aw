"""
Unit tests for obs:automerge:all-files E2E harness and oracle.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import automerge_all_files_e2e_harness as harness
import oracle_automerge_all_files_e2e as oracle

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "automerge-all-files"
HAPPY_CASE_ID = "all-files-custom-label-live"
NEGATIVE_CASE_ID = "all-files-custom-label-absent-live"


def _case(case_id: str) -> dict:
    return json.loads(
        (TESTDATA_ROOT / "cases" / case_id / "case.json").read_text(encoding="utf-8")
    )


def _happy_outcome(**overrides: object) -> dict:
    base = {
        "workflow_id": "obs:automerge",
        "case_id": HAPPY_CASE_ID,
        "layer": "e2e",
        "mode": "live",
        "agent_invoked": True,
        "pr_number": 42,
        "pr_author": "elastic-vault-github-plugin-prod[bot]",
        "pr_head_branch": "e2e/automerge-all-files/1-all-files-custom-label-live",
        "pr_base_branch": "e2e/automerge-all-files/base/1-all-files-custom-label-live",
        "path_gates": {
            "dashboard_enabled": True,
            "author_matches_allowed": True,
        },
        "fixture": {
            "label": "e2e:automerge-all-files",
            "branch": "e2e/automerge-all-files/1-all-files-custom-label-live",
            "base_branch": "e2e/automerge-all-files/base/1-all-files-custom-label-live",
            "pr_number": 42,
            "cleaned_up": True,
            "head_absent": True,
            "base_absent": True,
        },
        "custom_trigger_label": {
            "name": "e2e:automerge-all-files-ready",
            "applied": True,
        },
        "merge_ready_label": {
            "name": "oblt-aw/ai/merge-ready",
            "applied": False,
        },
        "dependency_collection_gate_comment": None,
        "automerge": {
            "run_seen": True,
            "job_executed": True,
            "approve_job_executed": True,
            "job_conclusion": "success",
            "matched_job_name": "run-obs-aw-pull-request / automerge / automerge",
        },
        "approving_review": {
            "id": 9,
            "user": "github-actions[bot]",
            "state": "APPROVED",
        },
        "merge": {"merged": True},
    }
    base.update(overrides)
    return base


def _negative_outcome(**overrides: object) -> dict:
    base = _happy_outcome(
        case_id=NEGATIVE_CASE_ID,
        pr_head_branch="e2e/automerge-all-files/1-all-files-custom-label-absent-live",
        pr_base_branch=(
            "e2e/automerge-all-files/base/1-all-files-custom-label-absent-live"
        ),
        fixture={
            "label": "e2e:automerge-all-files",
            "branch": "e2e/automerge-all-files/1-all-files-custom-label-absent-live",
            "base_branch": (
                "e2e/automerge-all-files/base/1-all-files-custom-label-absent-live"
            ),
            "pr_number": 42,
            "cleaned_up": True,
            "head_absent": True,
            "base_absent": True,
        },
        custom_trigger_label={
            "name": "e2e:automerge-all-files-ready",
            "applied": False,
        },
        automerge={
            "run_seen": False,
            "job_executed": False,
            "approve_job_executed": False,
            "job_conclusion": None,
            "matched_job_name": None,
        },
        approving_review=None,
        merge={"merged": False},
    )
    base.update(overrides)
    return base


def _evaluate(
    outcome: dict,
    *,
    case_id: str,
    case_expectations: dict | None = None,
    case_trigger: dict | None = None,
) -> dict:
    case = _case(case_id)
    return oracle.evaluate_outcome(
        outcome,
        case_expectations=case_expectations
        if case_expectations is not None
        else case["expectations"],
        case_trigger=case_trigger if case_trigger is not None else case["trigger"],
    )


def test_checked_in_cases_match_oracle_schema() -> None:
    for case_id in (HAPPY_CASE_ID, NEGATIVE_CASE_ID):
        case = _case(case_id)
        assert case["mode"] == "live"
        assert (
            oracle.case_expectations_schema_error("live", case["expectations"]) is None
        )
        assert oracle.case_trigger_schema_error(case["trigger"]) is None


def test_policy_apm_lists_canonical_custom_label() -> None:
    text = (TESTDATA_ROOT / "policy-apm.yml").read_text(encoding="utf-8")
    assert harness.CUSTOM_TRIGGER_LABEL in text
    assert "oblt-aw/ai/merge-ready" not in text


def test_config_required_dashboard_ids_include_all_files() -> None:
    cfg = harness.load_e2e_config(
        ROOT / "config" / "obs" / "e2e-automerge-all-files.json"
    )
    ids = harness.required_dashboard_ids(cfg)
    assert "obs:automerge" in ids
    assert "obs:automerge:all-files" in ids
    assert "obs:automerge:vm-images" not in ids


def test_oracle_happy_path_passes() -> None:
    report = _evaluate(_happy_outcome(), case_id=HAPPY_CASE_ID)
    assert report["pass"] is True


def test_oracle_negative_path_passes() -> None:
    report = _evaluate(_negative_outcome(), case_id=NEGATIVE_CASE_ID)
    assert report["pass"] is True


def test_oracle_rejects_empty_expectations() -> None:
    report = _evaluate(
        _happy_outcome(),
        case_id=HAPPY_CASE_ID,
        case_expectations={},
    )
    assert report["pass"] is False
    assert any(item["id"] == "case_expectations" for item in report["checks"])


def test_oracle_rejects_typo_expectation_map() -> None:
    report = _evaluate(
        _happy_outcome(),
        case_id=HAPPY_CASE_ID,
        case_expectations={"typo": True},
    )
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "case_expectations" in failed


def test_oracle_requires_matched_automerge_leaf_when_expected() -> None:
    outcome = _happy_outcome(
        automerge={
            "run_seen": True,
            "job_executed": True,
            "approve_job_executed": True,
            "job_conclusion": "success",
            "matched_job_name": "run-obs-aw-pull-request / automerge / verify",
        }
    )
    report = _evaluate(outcome, case_id=HAPPY_CASE_ID)
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "automerge_job_executed" in failed


def test_oracle_approve_is_not_merge_substitute() -> None:
    outcome = _happy_outcome(
        automerge={
            "run_seen": True,
            "job_executed": False,
            "approve_job_executed": True,
            "job_conclusion": None,
            "matched_job_name": None,
        },
        merge={"merged": True},
    )
    report = _evaluate(outcome, case_id=HAPPY_CASE_ID)
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "automerge_job_executed" in failed


def test_oracle_happy_requires_approve_job_not_only_review() -> None:
    outcome = _happy_outcome(
        automerge={
            "run_seen": True,
            "job_executed": True,
            "approve_job_executed": False,
            "job_conclusion": "success",
            "matched_job_name": "run-obs-aw-pull-request / automerge / automerge",
        }
    )
    report = _evaluate(outcome, case_id=HAPPY_CASE_ID)
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "approve_review_present" in failed


def test_oracle_negative_rejects_failed_merge_leaf_evidence() -> None:
    outcome = _negative_outcome(
        automerge={
            "run_seen": True,
            "job_executed": False,
            "approve_job_executed": False,
            "job_conclusion": "failure",
            "matched_job_name": "run-obs-aw-pull-request / automerge / automerge",
        }
    )
    report = _evaluate(outcome, case_id=NEGATIVE_CASE_ID)
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "automerge_job_executed" in failed


def test_oracle_requires_explicit_merge_merged_boolean() -> None:
    outcome = _negative_outcome()
    outcome["merge"] = {}
    report = _evaluate(outcome, case_id=NEGATIVE_CASE_ID)
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "pr_merged" in failed


def test_oracle_rejects_wrong_custom_label_name_when_applied() -> None:
    outcome = _happy_outcome(
        custom_trigger_label={"name": "nightshift:risk-low", "applied": True}
    )
    report = _evaluate(outcome, case_id=HAPPY_CASE_ID)
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "custom_trigger_label_applied" in failed


def test_oracle_rejects_cleanup_without_absence_evidence() -> None:
    outcome = _happy_outcome(
        fixture={
            "label": "e2e:automerge-all-files",
            "branch": "e2e/automerge-all-files/1-all-files-custom-label-live",
            "base_branch": "e2e/automerge-all-files/base/1-all-files-custom-label-live",
            "pr_number": 42,
            "cleaned_up": True,
            "head_absent": False,
            "base_absent": True,
        }
    )
    report = _evaluate(outcome, case_id=HAPPY_CASE_ID)
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "fixture_cleaned_up" in failed


def test_oracle_fixture_identity_requires_observed_head_and_base() -> None:
    outcome = _happy_outcome(pr_head_branch="e2e/automerge-all-files/other")
    report = _evaluate(outcome, case_id=HAPPY_CASE_ID)
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "fixture_identity" in failed


def test_oracle_blocked_outcome_fails() -> None:
    report = _evaluate(
        {
            "workflow_id": "obs:automerge",
            "case_id": HAPPY_CASE_ID,
            "layer": "e2e",
            "mode": "live",
            "blocked": True,
            "block_reason": "Dashboard missing required ids",
        },
        case_id=HAPPY_CASE_ID,
    )
    assert report["pass"] is False
    assert report["block_reason"]


def test_oracle_rejects_trigger_false_before_contract() -> None:
    case = _case(HAPPY_CASE_ID)
    trigger = dict(case["trigger"])
    trigger["force_stacked_policy_base"] = False
    report = _evaluate(
        _happy_outcome(),
        case_id=HAPPY_CASE_ID,
        case_trigger=trigger,
    )
    assert report["pass"] is False
    failed = {item["id"] for item in report["checks"] if not item["pass"]}
    assert "case_trigger_enforced" in failed


def test_cleanup_stacked_fixture_retries_until_base_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exists_calls = {"base": 0}

    def _exists(_repo: str, branch: str) -> bool:
        if branch.endswith("/head"):
            return False
        exists_calls["base"] += 1
        # First exists check + first post-delete check still see the branch;
        # second post-delete check reports absent.
        return exists_calls["base"] < 3

    deletes: list[str] = []

    def _delete(_repo: str, branch: str) -> None:
        deletes.append(branch)

    sleeps: list[float] = []

    monkeypatch.setattr(harness.dr_e2e, "fixture_branch_exists", _exists)
    monkeypatch.setattr(harness.dr_e2e, "delete_fixture_branch", _delete)
    monkeypatch.setattr(harness.time, "sleep", sleeps.append)

    result = harness.cleanup_stacked_fixture(
        "elastic/oblt-aw",
        pr_number=1,
        head_branch="e2e/automerge-all-files/head",
        base_branch="e2e/automerge-all-files/base/x",
        merged=True,
    )
    assert result["completed"] is True
    assert result["head_absent"] is True
    assert result["base_absent"] is True
    assert "error" not in result
    assert deletes == ["e2e/automerge-all-files/base/x"]
    assert sleeps == [harness._CLEANUP_ABSENCE_SLEEP_SECONDS]


def test_cleanup_stacked_fixture_records_error_when_base_remains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(harness.dr_e2e, "fixture_branch_exists", lambda *_a, **_k: True)
    monkeypatch.setattr(harness.dr_e2e, "delete_fixture_branch", lambda *_a, **_k: None)
    monkeypatch.setattr(harness.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_CLEANUP_ABSENCE_ATTEMPTS", 2)

    result = harness.cleanup_stacked_fixture(
        "elastic/oblt-aw",
        pr_number=1,
        head_branch="e2e/automerge-all-files/head",
        base_branch="e2e/automerge-all-files/base/x",
        merged=True,
    )
    assert result["completed"] is False
    assert result["base_absent"] is False
    assert "still present after 2 delete attempts" in str(result.get("error") or "")


def test_automerge_matched_job_name_prefers_merge_leaf() -> None:
    detail = {
        "jobs": [
            {
                "name": "run-obs-aw-pull-request / automerge / approve / conclusion",
                "conclusion": "success",
            },
            {
                "name": "run-obs-aw-pull-request / automerge / automerge",
                "conclusion": "success",
            },
        ]
    }
    assert harness.automerge_matched_job_name(detail) == (
        "run-obs-aw-pull-request / automerge / automerge"
    )


def test_negative_case_must_not_expect_merge() -> None:
    case = _case(NEGATIVE_CASE_ID)
    assert case["trigger"]["apply_custom_trigger_label"] is False
    assert case["trigger"]["wait_automerge"] is False
    assert case["trigger"]["expect_merge"] is False
    assert case["expectations"]["automerge_job_executed"] is False
    assert case["expectations"]["pr_merged"] is False


@pytest.mark.parametrize(
    ("key",),
    [
        ("require_open_pr",),
        ("force_stacked_policy_base",),
        ("require_allowed_pr_author",),
    ],
)
def test_case_trigger_schema_requires_bool_keys(key: str) -> None:
    case = _case(HAPPY_CASE_ID)
    trigger = dict(case["trigger"])
    trigger[key] = "true"
    assert oracle.case_trigger_schema_error(trigger) is not None


@pytest.mark.parametrize(
    ("key", "mode"),
    [
        ("require_open_pr", "omit"),
        ("require_open_pr", "false"),
        ("force_stacked_policy_base", "omit"),
        ("force_stacked_policy_base", "false"),
        ("require_allowed_pr_author", "omit"),
        ("require_allowed_pr_author", "false"),
    ],
)
def test_run_live_blocks_required_flag_before_remote_mutation(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    mode: str,
) -> None:
    case = _case(HAPPY_CASE_ID)
    trigger = dict(case["trigger"])
    if mode == "omit":
        trigger.pop(key)
    else:
        trigger[key] = False
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(
        json.dumps({**case, "trigger": trigger}, indent=2) + "\n",
        encoding="utf-8",
    )
    cfg = harness.load_e2e_config(
        ROOT / "config" / "obs" / "e2e-automerge-all-files.json"
    )

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("remote API must not be called")

    monkeypatch.setattr(harness.am_vm, "dashboard_enables_all", _boom)
    monkeypatch.setattr(harness, "create_stacked_policy_fixture", _boom)

    outcome = harness.run_live_case(case_dir, cfg, run_url="https://example.test/run")
    assert outcome["blocked"] is True
    assert key in str(outcome.get("block_reason") or "")
    assert outcome.get("pr_number") is None
