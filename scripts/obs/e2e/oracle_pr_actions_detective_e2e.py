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

"""Oracle for obs:pr-actions-detective live E2E outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKFLOW_ID = "obs:pr-actions-detective"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(
    checks: list[dict[str, Any]], check_id: str, passed: bool, detail: str
) -> None:
    checks.append({"id": check_id, "pass": passed, "detail": detail})


def _failed_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in (report.get("checks") or []) if not item.get("pass")]


def _primary_failure_detail(report: dict[str, Any]) -> str | None:
    if report.get("block_reason"):
        return str(report["block_reason"])
    failed = _failed_checks(report)
    if failed:
        first = failed[0]
        return f"[{first.get('id')}] {first.get('detail')}"
    return None


def _emit_oracle_failure_logs(report: dict[str, Any]) -> None:
    detail = _primary_failure_detail(report) or "(no failure detail)"
    print(f"::error::E2E oracle failed: {detail}", flush=True)
    for item in _failed_checks(report):
        print(f"  - [{item.get('id')}] {item.get('detail')}", flush=True)


def _as_bool(value: Any) -> bool:
    """Strict boolean: only real bools; reject truthy strings/numbers."""
    if isinstance(value, bool):
        return value
    raise TypeError(f"expected bool, got {type(value).__name__}: {value!r}")


_LIVE_REQUIRED_EXPECTATION_KEYS = (
    "dashboard_enabled",
    "workflow_run_job_executed",
    "agent_invoked",
    "expect_agent_comment",
    "agent_comment_markers",
)
# Happy-path live E2E requires the dashboard gate on.
_LIVE_REQUIRED_EXPECTATION_BOOL_TRUE_KEYS = ("dashboard_enabled",)
_LIVE_REQUIRED_TRIGGER_BOOL_KEYS = (
    "require_open_pr",
    "create_failed_actions_run",
    "clear_prior_detective_comments",
)
# Happy-path live E2E must drive an intentional pull_request failure.
_LIVE_REQUIRED_TRIGGER_BOOL_TRUE_KEYS = (
    "require_open_pr",
    "create_failed_actions_run",
)
_LIVE_PINNED_TRIGGER_STRS = {
    "fail_workflow_conclusion": "failure",
    "fail_workflow_event": "pull_request",
}


def agent_comment_markers_schema_error(markers: Any) -> str | None:
    """Require a non-empty list of non-empty strings (find/clear identity)."""
    if not isinstance(markers, list) or not markers:
        return "agent_comment_markers must be a non-empty list"
    for idx, item in enumerate(markers):
        if not isinstance(item, str) or not item.strip():
            return (
                f"agent_comment_markers[{idx}] must be a non-empty string, got {item!r}"
            )
    return None


def case_expectations_schema_error(
    mode: str, expectations: dict[str, Any]
) -> str | None:
    if mode != "live":
        return f"unsupported outcome mode {mode!r}; only live E2E is supported"

    missing = [k for k in _LIVE_REQUIRED_EXPECTATION_KEYS if k not in expectations]
    if missing:
        return f"live expectations missing required keys: {missing}"
    for key in _LIVE_REQUIRED_EXPECTATION_KEYS:
        if key == "agent_comment_markers":
            continue
        try:
            _as_bool(expectations[key])
        except TypeError as exc:
            return f"live expectation {key!r} must be bool ({exc})"
    for key in _LIVE_REQUIRED_EXPECTATION_BOOL_TRUE_KEYS:
        if expectations.get(key) is not True:
            return f"live expectation {key!r} must be true for happy-path E2E"
    markers_err = agent_comment_markers_schema_error(
        expectations.get("agent_comment_markers")
    )
    if markers_err:
        return f"live expectation {markers_err}"
    return None


def case_trigger_schema_error(trigger: dict[str, Any]) -> str | None:
    """Validate the checked-in live trigger contract (fail closed).

    Pins the intentional ``pull_request`` / ``failure`` path so a typo or
    alternate event/conclusion cannot redefine what the oracle proves.
    """
    missing_bool = [k for k in _LIVE_REQUIRED_TRIGGER_BOOL_KEYS if k not in trigger]
    if missing_bool:
        return f"live trigger missing required keys: {missing_bool}"
    for key in _LIVE_REQUIRED_TRIGGER_BOOL_KEYS:
        try:
            _as_bool(trigger[key])
        except TypeError as exc:
            return f"live trigger {key!r} must be bool ({exc})"
    for key in _LIVE_REQUIRED_TRIGGER_BOOL_TRUE_KEYS:
        if trigger.get(key) is not True:
            return f"live trigger {key!r} must be true for happy-path E2E"
    for key, expected in _LIVE_PINNED_TRIGGER_STRS.items():
        if key not in trigger:
            return f"live trigger missing required key: {key}"
        value = trigger.get(key)
        if not isinstance(value, str) or not value.strip():
            return f"live trigger {key!r} must be a non-empty string, got {value!r}"
        if value.strip().lower() != expected:
            return (
                f"live trigger {key!r} must be {expected!r} "
                f"(intentional Actions failure path), got {value!r}"
            )
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
                "Enable the workflow checkbox on the Control Plane Dashboard, then re-run."
            )
        overall = all(item["pass"] for item in checks)
        return {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": mode or "live",
            "pass": overall,
            "skipped": False,
            "run_url": outcome.get("run_url"),
            "checks": checks,
            "agent_invoked": bool(outcome.get("agent_invoked")),
            "block_reason": block_reason,
            "notes": notes,
        }

    _check(
        checks,
        "workflow_id",
        bool(workflow_id) and workflow_id == WORKFLOW_ID,
        f"workflow_id={workflow_id!r} expected={WORKFLOW_ID!r}",
    )

    expectations = case_expectations
    if expectations is None:
        _check(
            checks,
            "case_expectations",
            False,
            "missing checked-in case expectations; refuse harness-copied outcome.expectations",
        )
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
            "notes": ["Checked-in case.json expectations are required."],
        }

    schema_err = case_expectations_schema_error(mode, expectations)
    if schema_err:
        _check(checks, "case_expectations", False, schema_err)
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
            "notes": ["Incomplete or invalid expectations fail closed."],
        }
    _check(checks, "case_expectations", True, "live expectations schema ok")

    trigger = case_trigger
    if trigger is None:
        _check(
            checks,
            "case_trigger",
            False,
            "missing checked-in case trigger; refuse harness-copied outcome.trigger",
        )
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
            "notes": ["Checked-in case.json trigger is required."],
        }

    trigger_err = case_trigger_schema_error(trigger)
    if trigger_err:
        _check(checks, "case_trigger", False, trigger_err)
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
            "notes": ["Incomplete or invalid trigger contract fails closed."],
        }
    _check(checks, "case_trigger", True, "live trigger schema ok")

    if mode != "live":
        _check(
            checks,
            "mode_live",
            False,
            f"unsupported outcome mode {mode!r}; only live E2E is supported",
        )
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
                "Only live E2E outcomes are supported; integration wiring is #2055.",
            ],
        }

    return _evaluate_live(
        outcome, expectations, trigger, checks, workflow_id, case_id, layer
    )


def _evaluate_live(
    outcome: dict[str, Any],
    expectations: dict[str, Any],
    trigger: dict[str, Any],
    checks: list[dict[str, Any]],
    workflow_id: str,
    case_id: str,
    layer: str,
) -> dict[str, Any]:
    path_gates = outcome.get("path_gates") or {}
    workflow_run_trigger = outcome.get("workflow_run_trigger") or {}
    fail_workflow = outcome.get("fail_workflow") or {}
    comment = outcome.get("agent_comment")

    _check(checks, "layer_e2e", layer == "e2e", f"layer={layer!r}")

    if "dashboard_enabled" in expectations:
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

    if trigger.get("create_failed_actions_run") and not outcome.get("blocked"):
        source = (
            fail_workflow.get("source") if isinstance(fail_workflow, dict) else None
        )
        if source == "created":
            verified = (
                fail_workflow.get("fail_log_marker_verified")
                if isinstance(fail_workflow, dict)
                else None
            )
            detail = (
                fail_workflow.get("fail_log_marker_detail")
                if isinstance(fail_workflow, dict)
                else None
            )
            _check(
                checks,
                "fail_log_marker_verified",
                verified is True,
                str(detail or verified),
            )
            expected_conclusion = str(trigger.get("fail_workflow_conclusion") or "")
            actual_conclusion = str(fail_workflow.get("conclusion") or "").lower()
            _check(
                checks,
                "fail_workflow_conclusion",
                actual_conclusion == expected_conclusion.lower(),
                f"expected={expected_conclusion!r} actual={actual_conclusion!r}",
            )
            expected_event = str(trigger.get("fail_workflow_event") or "")
            actual_event = str(fail_workflow.get("event") or "").lower()
            _check(
                checks,
                "fail_workflow_event",
                actual_event == expected_event.lower(),
                f"expected={expected_event!r} actual={actual_event!r}",
            )
        else:
            _check(
                checks,
                "fail_workflow_source_valid",
                False,
                f"expected source 'created', got {source!r}",
            )

    if "workflow_run_job_executed" in expectations:
        try:
            run_seen = _as_bool(workflow_run_trigger.get("run_seen"))
        except TypeError as exc:
            run_seen = False
            _check(checks, "workflow_run_trigger_run_seen", False, str(exc))
        else:
            _check(
                checks,
                "workflow_run_trigger_run_seen",
                run_seen is True,
                f"run_seen={run_seen} url={workflow_run_trigger.get('url')}",
            )
        try:
            expected = _as_bool(expectations["workflow_run_job_executed"])
            actual = _as_bool(workflow_run_trigger.get("job_executed"))
            _check(
                checks,
                "workflow_run_job_executed",
                actual == expected,
                (
                    f"expected={expected} actual={actual} "
                    f"run={workflow_run_trigger.get('url')}"
                ),
            )
            if expected is True and run_seen is True:
                job_conclusion = str(
                    workflow_run_trigger.get("job_conclusion") or ""
                ).lower()
                _check(
                    checks,
                    "workflow_run_job_success",
                    job_conclusion == "success",
                    f"job_conclusion={job_conclusion!r}",
                )
        except TypeError as exc:
            _check(checks, "workflow_run_job_executed", False, str(exc))

    if "agent_invoked" in expectations:
        try:
            expected = _as_bool(expectations["agent_invoked"])
            actual = _as_bool(outcome.get("agent_invoked"))
            _check(
                checks,
                "agent_invoked",
                actual == expected,
                f"expected={expected} actual={actual}",
            )
        except TypeError as exc:
            _check(checks, "agent_invoked", False, str(exc))

    if "expect_agent_comment" in expectations:
        try:
            expect_comment = _as_bool(expectations["expect_agent_comment"])
        except TypeError as exc:
            _check(checks, "expect_agent_comment", False, str(exc))
        else:
            if expect_comment is True:
                present = isinstance(comment, dict) and bool(comment.get("id"))
                _check(
                    checks,
                    "agent_comment_present",
                    present,
                    f"comment={comment}",
                )
            else:
                _check(
                    checks,
                    "agent_comment_absent",
                    comment is None,
                    f"comment={comment}",
                )

    overall = all(item["pass"] for item in checks)
    agent_flag = False
    try:
        agent_flag = (
            _as_bool(outcome.get("agent_invoked"))
            if "agent_invoked" in outcome
            else False
        )
    except TypeError:
        agent_flag = False
    return {
        "workflow_id": workflow_id,
        "case_id": case_id,
        "layer": layer,
        "mode": "live",
        "pass": overall,
        "skipped": False,
        "run_url": outcome.get("run_url"),
        "workflow_run_trigger_url": workflow_run_trigger.get("url"),
        "pr_url": outcome.get("pr_url"),
        "checks": checks,
        "agent_invoked": agent_flag,
        "notes": [
            (
                "Live oracle asserts dashboard gate, intentional Actions failure, "
                "workflow_run trigger job execution, agent invocation, and PR "
                "comment presence/absence. Comment-section markers are harness "
                "identity only; never full agent prose."
            ),
            "Promote (#1878) should consume report.pass / summary.json.",
        ],
    }


def load_case_json(testdata_root: Path, case_id: str) -> dict[str, Any] | None:
    case_path = testdata_root / "cases" / case_id / "case.json"
    if not case_path.is_file():
        return None
    case = _load_json(case_path)
    return case if isinstance(case, dict) else None


def load_case_expectations(testdata_root: Path, case_id: str) -> dict[str, Any] | None:
    case = load_case_json(testdata_root, case_id)
    if case is None:
        return None
    expectations = case.get("expectations")
    return expectations if isinstance(expectations, dict) else None


def load_case_trigger(testdata_root: Path, case_id: str) -> dict[str, Any] | None:
    case = load_case_json(testdata_root, case_id)
    if case is None:
        return None
    trigger = case.get("trigger")
    return trigger if isinstance(trigger, dict) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Oracle for pr-actions-detective E2E outcomes"
    )
    parser.add_argument("--outcome-path", type=Path, required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/pr-actions-detective"),
    )
    parser.add_argument("--summary-path", type=Path, default=None)
    parser.add_argument("--expected-case-id", default=None)
    args = parser.parse_args(argv)

    outcome = _load_json(args.outcome_path)
    if not isinstance(outcome, dict):
        raise SystemExit(f"Outcome must be a JSON object: {args.outcome_path}")

    outcome_case_id = str(outcome.get("case_id") or "")
    if args.expected_case_id is not None:
        expected_case_id = str(args.expected_case_id).strip()
        if not expected_case_id:
            raise SystemExit("--expected-case-id must be a non-empty string")
        if outcome_case_id != expected_case_id:
            raise SystemExit(
                f"Outcome case_id {outcome_case_id!r} does not match "
                f"--expected-case-id {expected_case_id!r}"
            )
        case_id = expected_case_id
    else:
        case_id = outcome_case_id

    case_expectations = (
        load_case_expectations(args.testdata_root, case_id) if case_id else None
    )
    case_trigger = load_case_trigger(args.testdata_root, case_id) if case_id else None

    report = evaluate_outcome(
        outcome,
        case_expectations=case_expectations,
        case_trigger=case_trigger,
    )

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "pass": report.get("pass"),
        "skipped": report.get("skipped"),
        "case_id": report.get("case_id"),
        "run_url": report.get("run_url"),
        "workflow_run_trigger_url": report.get("workflow_run_trigger_url"),
        "pr_url": report.get("pr_url"),
        "workflow_id": report.get("workflow_id"),
        "layer": report.get("layer"),
        "mode": report.get("mode"),
        "agent_invoked": report.get("agent_invoked"),
        "block_reason": report.get("block_reason"),
        "failure_detail": _primary_failure_detail(report),
        "failed_checks": [
            {"id": item.get("id"), "detail": item.get("detail")}
            for item in _failed_checks(report)
        ],
    }
    if args.summary_path is not None:
        args.summary_path.parent.mkdir(parents=True, exist_ok=True)
        args.summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote promote summary to {args.summary_path}")
    print(f"Wrote oracle report to {args.report_path}")
    print(json.dumps(summary, indent=2), flush=True)
    if not report.get("pass"):
        _emit_oracle_failure_logs(report)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
