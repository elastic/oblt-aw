#!/usr/bin/env python3
# Copyright 2026-2027 Elasticsearch B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Structured oracle for obs:automerge:all-files live E2E outcomes.

Asserts dashboard gates, custom trigger label identity, automerge merge leaf,
approving review, merge (or absence), and stacked-fixture cleanup — never
free-text golden equality. Approve is not a substitute for merge.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

WORKFLOW_ID = "obs:automerge"
CANONICAL_FIXTURE_LABEL = "e2e:automerge-all-files"
CANONICAL_FIXTURE_BRANCH_PREFIX = "e2e/automerge-all-files/"
CANONICAL_BASE_BRANCH_PREFIX = "e2e/automerge-all-files/base/"
CANONICAL_CUSTOM_TRIGGER_LABEL = "e2e:automerge-all-files-ready"
CANONICAL_MERGE_READY_LABEL = "oblt-aw/ai/merge-ready"
CANONICAL_ALLOWED_PR_AUTHOR = "elastic-vault-github-plugin-prod[bot]"
CANONICAL_AUTOMERGE_JOB_SUFFIX = " / automerge / automerge"

_LIVE_REQUIRED_EXPECTATION_KEYS = (
    "dashboard_enabled",
    "custom_trigger_label_applied",
    "merge_ready_label_applied",
    "approve_review_present",
    "automerge_job_executed",
    "pr_merged",
    "no_dependency_collection_gate",
    "fixture_cleaned_up",
)

_LIVE_REQUIRED_TRIGGER_BOOL_KEYS = (
    "require_open_pr",
    "force_stacked_policy_base",
    "require_allowed_pr_author",
    "apply_custom_trigger_label",
    "wait_automerge",
    "expect_merge",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(
    checks: list[dict[str, Any]], check_id: str, passed: bool, detail: str
) -> None:
    checks.append({"id": check_id, "pass": passed, "detail": detail})


def _failed_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    checks = report.get("checks") or []
    if not isinstance(checks, list):
        return []
    return [item for item in checks if isinstance(item, dict) and not item.get("pass")]


def _primary_failure_detail(report: dict[str, Any]) -> str | None:
    if report.get("block_reason"):
        return str(report["block_reason"])
    failed = _failed_checks(report)
    if not failed:
        return None
    first = failed[0]
    return f"{first.get('id')}: {first.get('detail')}"


def _emit_oracle_failure_logs(report: dict[str, Any]) -> None:
    detail = _primary_failure_detail(report)
    if detail and os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        first = detail.splitlines()[0]
        print(f"::error::E2E oracle failed: {first}", flush=True)
    print("Oracle failed checks:", flush=True)
    for item in _failed_checks(report):
        print(f"  - [{item.get('id')}] {item.get('detail')}", flush=True)
    if detail:
        print(f"Primary failure:\n{detail}", flush=True)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError(f"expected bool, got {type(value).__name__}: {value!r}")


def _trigger_bool(
    trigger: dict[str, Any],
    key: str,
    *,
    default: bool,
) -> bool:
    if key not in trigger:
        return default
    return _as_bool(trigger[key])


def case_expectations_schema_error(
    mode: str, expectations: dict[str, Any]
) -> str | None:
    if mode != "live":
        return f"unsupported outcome mode {mode!r}; only live E2E is supported"
    missing = [k for k in _LIVE_REQUIRED_EXPECTATION_KEYS if k not in expectations]
    if missing:
        return f"live expectations missing required keys: {missing}"
    for key in _LIVE_REQUIRED_EXPECTATION_KEYS:
        try:
            _as_bool(expectations[key])
        except TypeError as exc:
            return f"live expectation {key!r} must be bool ({exc})"
    return None


def case_trigger_schema_error(trigger: dict[str, Any]) -> str | None:
    missing = [k for k in _LIVE_REQUIRED_TRIGGER_BOOL_KEYS if k not in trigger]
    if missing:
        return f"live trigger missing required keys: {missing}"
    for key in _LIVE_REQUIRED_TRIGGER_BOOL_KEYS:
        try:
            _as_bool(trigger[key])
        except TypeError as exc:
            return f"live trigger {key!r} must be bool ({exc})"
    # wait_verify_skip is required only for negative (expect_merge false) paths.
    try:
        expect_merge = _as_bool(trigger["expect_merge"])
    except TypeError as exc:
        return f"live trigger 'expect_merge' must be bool ({exc})"
    if not expect_merge:
        if "wait_verify_skip" not in trigger:
            return "live trigger missing required key: wait_verify_skip"
        try:
            _as_bool(trigger["wait_verify_skip"])
        except TypeError as exc:
            return f"live trigger 'wait_verify_skip' must be bool ({exc})"
    return None


def evaluate_outcome(
    outcome: dict[str, Any],
    *,
    case_expectations: dict[str, Any] | None = None,
    case_trigger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow_id = str(outcome.get("workflow_id") or "")
    case_id = str(outcome.get("case_id") or "unknown")
    mode = str(outcome.get("mode") or "")
    layer = str(outcome.get("layer") or "e2e")
    checks: list[dict[str, Any]] = []

    if outcome.get("blocked"):
        block_reason = str(outcome.get("block_reason") or "blocked")
        _check(checks, "not_blocked", False, block_reason)
        notes = [
            "Harness set blocked=true; see block_reason / not_blocked detail above.",
        ]
        lower = block_reason.lower()
        if "dashboard" in lower:
            notes.append(
                "Enable obs:automerge and obs:automerge:all-files on the "
                "Control Plane Dashboard, then re-run."
            )
        elif "author" in lower:
            notes.append(
                "Run under GitHub Actions with Vault create-token using this "
                "repo's workflow-token-policy so the fixture PR is authored as "
                f"{CANONICAL_ALLOWED_PR_AUTHOR}."
            )
        else:
            notes.append("Resolve block_reason, then re-run.")
        return {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": mode,
            "pass": False,
            "skipped": False,
            "run_url": outcome.get("run_url"),
            "block_reason": block_reason,
            "checks": checks,
            "agent_invoked": bool(outcome.get("agent_invoked")),
            "notes": notes,
        }

    expectations: dict[str, Any] = {}
    if not isinstance(case_expectations, dict) or not case_expectations:
        _check(
            checks,
            "case_expectations",
            False,
            (
                "non-empty checked-in case expectations are required "
                "(do not trust outcome.expectations or empty mappings)"
            ),
        )
    else:
        schema_error = case_expectations_schema_error(mode, case_expectations)
        if schema_error is not None:
            _check(checks, "case_expectations", False, schema_error)
        else:
            expectations = case_expectations

    trigger: dict[str, Any] = {}
    if mode == "live":
        if not isinstance(case_trigger, dict) or not case_trigger:
            _check(
                checks,
                "case_trigger",
                False,
                (
                    "non-empty checked-in case trigger is required "
                    "(do not trust outcome.trigger or empty mappings)"
                ),
            )
        else:
            trigger_error = case_trigger_schema_error(case_trigger)
            if trigger_error is not None:
                _check(checks, "case_trigger", False, trigger_error)
            else:
                trigger = case_trigger

    _check(
        checks,
        "workflow_id",
        workflow_id == WORKFLOW_ID,
        f"workflow_id={workflow_id!r}",
    )
    _check(
        checks,
        "no_free_text_golden",
        "golden_free_text" not in outcome and "agent_prose" not in outcome,
        "outcome has no free-text golden fields",
    )

    if mode != "live":
        _check(
            checks,
            "mode_live_only",
            False,
            f"unsupported outcome mode {mode!r}; only live E2E is supported",
        )
        return {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": mode,
            "pass": all(item["pass"] for item in checks),
            "skipped": False,
            "run_url": outcome.get("run_url"),
            "checks": checks,
            "agent_invoked": bool(outcome.get("agent_invoked")),
            "notes": ["Only live E2E outcomes are supported."],
        }

    return _evaluate_live(
        outcome, expectations, trigger, checks, workflow_id, case_id, layer, mode
    )


def _evaluate_live(
    outcome: dict[str, Any],
    expectations: dict[str, Any],
    trigger: dict[str, Any],
    checks: list[dict[str, Any]],
    workflow_id: str,
    case_id: str,
    layer: str,
    mode: str,
) -> dict[str, Any]:
    path_gates = outcome.get("path_gates") or {}
    am = outcome.get("automerge") or {}
    custom_label = outcome.get("custom_trigger_label") or {}
    merge_ready = outcome.get("merge_ready_label") or {}
    merge = outcome.get("merge") or {}
    review = outcome.get("approving_review")
    gate_comment = outcome.get("dependency_collection_gate_comment")
    raw_fixture = outcome.get("fixture")
    fixture: dict[str, Any] = raw_fixture if isinstance(raw_fixture, dict) else {}

    _check(checks, "layer_e2e", layer == "e2e", f"layer={layer!r}")

    require_open_pr = False
    force_stacked = False
    require_allowed = False
    apply_custom = False
    wait_automerge = False
    expect_merge = False
    try:
        require_open_pr = _trigger_bool(trigger, "require_open_pr", default=False)
        force_stacked = _trigger_bool(
            trigger, "force_stacked_policy_base", default=False
        )
        require_allowed = _trigger_bool(
            trigger, "require_allowed_pr_author", default=False
        )
        apply_custom = _trigger_bool(
            trigger, "apply_custom_trigger_label", default=False
        )
        wait_automerge = _trigger_bool(trigger, "wait_automerge", default=False)
        expect_merge = _trigger_bool(trigger, "expect_merge", default=False)
        trigger_ok = (
            require_open_pr
            and force_stacked
            and require_allowed
            and (apply_custom == expect_merge)
            and (wait_automerge == expect_merge)
        )
        if not expect_merge:
            wait_verify_skip = _trigger_bool(trigger, "wait_verify_skip", default=False)
            trigger_ok = trigger_ok and wait_verify_skip and not apply_custom
        _check(
            checks,
            "case_trigger_enforced",
            trigger_ok,
            (
                f"require_open_pr={require_open_pr} "
                f"force_stacked_policy_base={force_stacked} "
                f"require_allowed_pr_author={require_allowed} "
                f"apply_custom_trigger_label={apply_custom} "
                f"wait_automerge={wait_automerge} expect_merge={expect_merge}"
            ),
        )
    except TypeError as exc:
        _check(checks, "case_trigger_enforced", False, str(exc))

    if require_open_pr and force_stacked:
        pr_number = outcome.get("pr_number")
        fixture_pr = fixture.get("pr_number")
        branch = str(fixture.get("branch") or "")
        base_branch = str(fixture.get("base_branch") or "")
        pr_head = str(outcome.get("pr_head_branch") or "")
        pr_base = str(outcome.get("pr_base_branch") or "")
        label = str(fixture.get("label") or "")
        pr_ok = isinstance(pr_number, int) and pr_number > 0 and fixture_pr == pr_number
        branch_ok = (
            branch.startswith(CANONICAL_FIXTURE_BRANCH_PREFIX)
            and pr_head.startswith(CANONICAL_FIXTURE_BRANCH_PREFIX)
            and pr_head == branch
            and not branch.startswith(CANONICAL_BASE_BRANCH_PREFIX)
        )
        base_ok = (
            base_branch.startswith(CANONICAL_BASE_BRANCH_PREFIX)
            and pr_base.startswith(CANONICAL_BASE_BRANCH_PREFIX)
            and pr_base == base_branch
        )
        label_ok = label == CANONICAL_FIXTURE_LABEL
        _check(
            checks,
            "fixture_identity",
            pr_ok and branch_ok and base_ok and label_ok,
            (
                f"pr_number={pr_number!r} fixture_pr={fixture_pr!r} "
                f"branch={branch!r} pr_head_branch={pr_head!r} "
                f"base_branch={base_branch!r} pr_base_branch={pr_base!r} "
                f"label={label!r}"
            ),
        )

    if expectations:
        try:
            expected = _as_bool(expectations["dashboard_enabled"])
            actual = _as_bool(path_gates.get("dashboard_enabled"))
            _check(
                checks,
                "dashboard_enabled",
                actual == expected,
                f"expected={expected} actual={actual}",
            )
        except TypeError as exc:
            _check(checks, "dashboard_enabled", False, str(exc))

        if require_allowed:
            pr_author = str(outcome.get("pr_author") or "")
            identity_ok = pr_author == CANONICAL_ALLOWED_PR_AUTHOR
            _check(
                checks,
                "author_allowed",
                identity_ok,
                f"pr_author={pr_author!r} canonical={CANONICAL_ALLOWED_PR_AUTHOR!r}",
            )

        try:
            expected = _as_bool(expectations["custom_trigger_label_applied"])
            actual = _as_bool(custom_label.get("applied"))
            label_name = str(custom_label.get("name") or "")
            name_ok = (not expected) or (label_name == CANONICAL_CUSTOM_TRIGGER_LABEL)
            # Fail closed: applied=false must still report the canonical name when
            # the harness knows which label it managed.
            reported_ok = (not label_name) or (
                label_name == CANONICAL_CUSTOM_TRIGGER_LABEL
            )
            _check(
                checks,
                "custom_trigger_label_applied",
                actual == expected and name_ok and reported_ok,
                f"expected={expected} actual={actual} label={label_name!r} "
                f"canonical={CANONICAL_CUSTOM_TRIGGER_LABEL!r}",
            )
        except TypeError as exc:
            _check(checks, "custom_trigger_label_applied", False, str(exc))

        try:
            expected = _as_bool(expectations["merge_ready_label_applied"])
            actual = _as_bool(merge_ready.get("applied"))
            label_name = str(merge_ready.get("name") or "")
            name_ok = (not expected) or (label_name == CANONICAL_MERGE_READY_LABEL)
            reported_ok = (not label_name) or (
                label_name == CANONICAL_MERGE_READY_LABEL
            )
            _check(
                checks,
                "merge_ready_label_applied",
                actual == expected and name_ok and reported_ok,
                f"expected={expected} actual={actual} label={label_name!r} "
                f"canonical={CANONICAL_MERGE_READY_LABEL!r}",
            )
        except TypeError as exc:
            _check(checks, "merge_ready_label_applied", False, str(exc))

        try:
            expected = _as_bool(expectations["no_dependency_collection_gate"])
            gate_present = isinstance(gate_comment, dict) and bool(
                gate_comment.get("id")
            )
            ok = (not gate_present) if expected else gate_present
            _check(
                checks,
                "no_dependency_collection_gate",
                ok,
                f"expected_absent={expected} gate_present={gate_present}",
            )
        except TypeError as exc:
            _check(checks, "no_dependency_collection_gate", False, str(exc))

        try:
            expected = _as_bool(expectations["approve_review_present"])
            present = isinstance(review, dict) and bool(review.get("id"))
            review_state = ""
            if isinstance(review, dict):
                review_state = str(review.get("state") or "")
            state_ok = present and review_state.upper() == "APPROVED"
            _check(
                checks,
                "approve_review_present",
                state_ok == expected,
                f"expected={expected} review={review!r}",
            )
        except TypeError as exc:
            _check(checks, "approve_review_present", False, str(exc))

        try:
            expected = _as_bool(expectations["automerge_job_executed"])
            actual = _as_bool(am.get("job_executed"))
            job_conclusion = am.get("job_conclusion")
            matched_job = str(am.get("matched_job_name") or "")
            leaf_ok = (not expected) or matched_job.lower().endswith(
                CANONICAL_AUTOMERGE_JOB_SUFFIX.lower()
            )
            named_ok = actual and job_conclusion == "success"
            _check(
                checks,
                "automerge_job_executed",
                named_ok == expected and leaf_ok,
                f"expected={expected} job_executed={actual} "
                f"job_conclusion={job_conclusion!r} "
                f"matched_job_name={matched_job!r} "
                f"approve_job={am.get('approve_job_executed')}",
            )
        except TypeError as exc:
            _check(checks, "automerge_job_executed", False, str(exc))

        try:
            expected = _as_bool(expectations["pr_merged"])
            merged = _as_bool(merge.get("merged")) if "merged" in merge else False
            _check(
                checks,
                "pr_merged",
                merged == expected,
                f"expected={expected} merged={merged} merge={merge!r}",
            )
        except TypeError as exc:
            _check(checks, "pr_merged", False, str(exc))

        try:
            expected = _as_bool(expectations["fixture_cleaned_up"])
            cleaned_up = fixture.get("cleaned_up") is True
            cleanup_error = fixture.get("cleanup_error")
            head_absent = fixture.get("head_absent") is True
            base_absent = fixture.get("base_absent") is True
            detail = (
                f"expected={expected} cleaned_up={fixture.get('cleaned_up')!r} "
                f"head_absent={fixture.get('head_absent')!r} "
                f"base_absent={fixture.get('base_absent')!r} "
                f"cleanup_error={cleanup_error!r}"
            )
            if not expected:
                # Live cases must always clean up stacked branches.
                _check(
                    checks,
                    "fixture_cleaned_up",
                    False,
                    (
                        "fixture_cleaned_up expectation false is unsupported; "
                        "live cases must clean up stacked branches"
                    ),
                )
            else:
                # Fail closed: cleaned_up alone is not enough — require absence.
                side_effect_ok = (
                    cleaned_up and not cleanup_error and head_absent and base_absent
                )
                _check(checks, "fixture_cleaned_up", side_effect_ok, detail)
        except TypeError as exc:
            _check(checks, "fixture_cleaned_up", False, str(exc))

    overall = all(item["pass"] for item in checks)
    return {
        "workflow_id": workflow_id,
        "case_id": case_id,
        "layer": layer,
        "mode": mode,
        "pass": overall,
        "skipped": False,
        "run_url": outcome.get("run_url"),
        "checks": checks,
        "agent_invoked": bool(outcome.get("agent_invoked")),
        "notes": [
            (
                "Oracle asserts side effects only (custom label, review, merge, "
                "cleanup); not agent free text."
            ),
        ],
    }


def _summary_from_report(report: dict[str, Any]) -> dict[str, Any]:
    failed = _failed_checks(report)
    return {
        "pass": bool(report.get("pass")),
        "run_url": report.get("run_url"),
        "workflow_id": report.get("workflow_id"),
        "layer": report.get("layer"),
        "mode": report.get("mode"),
        "case_id": report.get("case_id"),
        "agent_invoked": report.get("agent_invoked"),
        "block_reason": report.get("block_reason"),
        "failure_detail": _primary_failure_detail(report),
        "failed_checks": [
            {"id": item.get("id"), "detail": item.get("detail")} for item in failed
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Oracle for obs:automerge:all-files live E2E."
    )
    parser.add_argument("--outcome-path", type=Path, required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/automerge-all-files"),
    )
    parser.add_argument("--expected-case-id", required=True)
    args = parser.parse_args(argv)

    if not args.outcome_path.is_file():
        print(f"Missing outcome file: {args.outcome_path}", file=sys.stderr)
        return 2

    outcome = _load_json(args.outcome_path)
    case_path = args.testdata_root / "cases" / args.expected_case_id / "case.json"
    if not case_path.is_file():
        print(f"Missing case.json: {case_path}", file=sys.stderr)
        return 2
    case = _load_json(case_path)
    case_expectations = case.get("expectations")
    case_trigger = case.get("trigger")
    if not isinstance(case_expectations, dict):
        case_expectations = None
    if not isinstance(case_trigger, dict):
        case_trigger = None

    report = evaluate_outcome(
        outcome,
        case_expectations=case_expectations,
        case_trigger=case_trigger,
    )
    summary = _summary_from_report(report)

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.summary_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if not report.get("pass"):
        _emit_oracle_failure_logs(report)
        return 1
    print(f"Oracle pass for case {args.expected_case_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
