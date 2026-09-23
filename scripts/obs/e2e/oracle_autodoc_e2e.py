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

"""Structured oracle for obs:autodoc live E2E outcomes.

Asserts dashboard gate, schedule audit/fix job execution, agent invocation,
and issue/PR presence — never free-text golden equality of agent prose.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

WORKFLOW_ID = "obs:autodoc"

_LIVE_AUDIT_EXPECTATION_KEYS = (
    "dashboard_enabled",
    "schedule_job_executed",
    "audit_agent_invoked",
    "expect_audit_issue",
)
_LIVE_FIX_EXPECTATION_KEYS = (
    "fix_agent_invoked",
    "expect_fix_pr",
)
_LIVE_REQUIRED_TRIGGER_BOOL_KEYS = (
    "dispatch_schedule_trigger",
    "seed_doc_drift_bait",
    "cleanup_after",
)


def _live_required_expectation_keys(
    expectations: dict[str, Any],
) -> tuple[str, ...]:
    """Return the required expectation key set for this case (fail closed).

    Audit-only cases use the audit key set. Any presence of a fix-path key
    requires the full audit+fix set (partial maps fail).
    """
    if any(key in expectations for key in _LIVE_FIX_EXPECTATION_KEYS):
        return _LIVE_AUDIT_EXPECTATION_KEYS + _LIVE_FIX_EXPECTATION_KEYS
    return _LIVE_AUDIT_EXPECTATION_KEYS


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


def case_expectations_schema_error(
    mode: str, expectations: dict[str, Any]
) -> str | None:
    if mode != "live":
        return f"unsupported outcome mode {mode!r}; only live E2E is supported"
    required = _live_required_expectation_keys(expectations)
    missing = [k for k in required if k not in expectations]
    if missing:
        return f"live expectations missing required keys: {missing}"
    for key in required:
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
        if "dashboard" in block_reason.lower():
            notes.append(
                "Enable obs:autodoc on the Control Plane Dashboard, then re-run."
            )
        report = {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": "live",
            "pass": False,
            "skipped": False,
            "block_reason": block_reason,
            "run_url": outcome.get("run_url"),
            "checks": checks,
            "agent_invoked": False,
            "notes": notes,
        }
        return report

    expectations = case_expectations if isinstance(case_expectations, dict) else {}
    trigger = case_trigger if isinstance(case_trigger, dict) else {}

    schema_err = case_expectations_schema_error(mode, expectations)
    if schema_err:
        _check(checks, "case_expectations", False, schema_err)
        return {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": "live",
            "pass": False,
            "skipped": False,
            "run_url": outcome.get("run_url"),
            "checks": checks,
            "agent_invoked": False,
            "notes": ["Checked-in case expectations failed schema validation."],
        }

    trigger_err = case_trigger_schema_error(trigger)
    if trigger_err:
        _check(checks, "case_trigger", False, trigger_err)
        return {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": "live",
            "pass": False,
            "skipped": False,
            "run_url": outcome.get("run_url"),
            "checks": checks,
            "agent_invoked": False,
            "notes": ["Checked-in case trigger failed schema validation."],
        }

    _check(
        checks,
        "workflow_id",
        workflow_id == WORKFLOW_ID,
        f"expected={WORKFLOW_ID!r} actual={workflow_id!r}",
    )

    raw_gates = outcome.get("path_gates")
    path_gates: dict[str, Any] = raw_gates if isinstance(raw_gates, dict) else {}
    raw_schedule = outcome.get("schedule_trigger")
    schedule: dict[str, Any] = raw_schedule if isinstance(raw_schedule, dict) else {}
    raw_fix = outcome.get("fix_trigger")
    fix_trigger: dict[str, Any] = raw_fix if isinstance(raw_fix, dict) else {}
    issue = outcome.get("audit_issue")
    fix_pr = outcome.get("fix_pr")
    required_keys = _live_required_expectation_keys(expectations)
    want_fix = "expect_fix_pr" in required_keys

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

    try:
        run_seen = _as_bool(schedule.get("run_seen"))
        _check(
            checks,
            "schedule_trigger_run_seen",
            run_seen is True,
            f"run_seen={run_seen} url={schedule.get('url')}",
        )
    except TypeError as exc:
        _check(checks, "schedule_trigger_run_seen", False, str(exc))

    try:
        expected = _as_bool(expectations["schedule_job_executed"])
        actual = _as_bool(schedule.get("job_executed"))
        _check(
            checks,
            "schedule_job_executed",
            actual == expected,
            f"expected={expected} actual={actual} run={schedule.get('url')}",
        )
        if expected is True:
            job_conclusion = str(schedule.get("job_conclusion") or "").lower()
            _check(
                checks,
                "schedule_job_success",
                job_conclusion == "success",
                f"job_conclusion={job_conclusion!r}",
            )
    except TypeError as exc:
        _check(checks, "schedule_job_executed", False, str(exc))

    try:
        expected = _as_bool(expectations["audit_agent_invoked"])
        actual = _as_bool(outcome.get("agent_invoked"))
        _check(
            checks,
            "audit_agent_invoked",
            actual == expected,
            f"expected={expected} actual={actual}",
        )
    except TypeError as exc:
        _check(checks, "audit_agent_invoked", False, str(exc))

    try:
        expect_issue = _as_bool(expectations["expect_audit_issue"])
    except TypeError as exc:
        _check(checks, "expect_audit_issue", False, str(exc))
    else:
        if expect_issue is True:
            present = isinstance(issue, dict) and bool(issue.get("number"))
            _check(
                checks,
                "audit_issue_present",
                present,
                f"issue={issue}",
            )
        else:
            _check(
                checks,
                "audit_issue_absent",
                issue is None,
                f"issue={issue}",
            )

    if want_fix:
        try:
            expected = _as_bool(expectations["fix_agent_invoked"])
            actual = _as_bool(outcome.get("fix_agent_invoked"))
            _check(
                checks,
                "fix_agent_invoked",
                actual == expected,
                f"expected={expected} actual={actual}",
            )
            if expected is True:
                job_conclusion = str(fix_trigger.get("job_conclusion") or "").lower()
                _check(
                    checks,
                    "fix_job_success",
                    job_conclusion == "success",
                    f"job_conclusion={job_conclusion!r}",
                )
        except TypeError as exc:
            _check(checks, "fix_agent_invoked", False, str(exc))

        try:
            expect_pr = _as_bool(expectations["expect_fix_pr"])
        except TypeError as exc:
            _check(checks, "expect_fix_pr", False, str(exc))
        else:
            if expect_pr is True:
                present = isinstance(fix_pr, dict) and bool(fix_pr.get("number"))
                _check(
                    checks,
                    "fix_pr_present",
                    present,
                    f"fix_pr={fix_pr}",
                )
            else:
                _check(
                    checks,
                    "fix_pr_absent",
                    fix_pr is None,
                    f"fix_pr={fix_pr}",
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
    notes = [
        (
            "Live oracle asserts dashboard gate, schedule audit/fix job execution, "
            "agent invocation, and issue/PR presence — never agent prose."
        ),
        "Promote (#1878) should consume report.pass / summary.json.",
    ]
    return {
        "workflow_id": workflow_id,
        "case_id": case_id,
        "layer": layer,
        "mode": "live",
        "pass": overall,
        "skipped": False,
        "run_url": outcome.get("run_url"),
        "schedule_trigger_url": schedule.get("url"),
        "issue_url": issue.get("url") if isinstance(issue, dict) else None,
        "fix_pr_url": fix_pr.get("url") if isinstance(fix_pr, dict) else None,
        "checks": checks,
        "agent_invoked": agent_flag,
        "notes": notes,
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
    parser = argparse.ArgumentParser(description="Oracle for obs:autodoc E2E outcomes")
    parser.add_argument("--outcome-path", type=Path, required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/autodoc"),
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
        "schedule_trigger_url": report.get("schedule_trigger_url"),
        "issue_url": report.get("issue_url"),
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
