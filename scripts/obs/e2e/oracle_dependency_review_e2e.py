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

"""Structured oracle for obs:dependency-review live E2E outcomes.

Asserts dashboard gates, dependency-review job execution, merge-ready label,
and analysis comment — never free-text golden equality of agent prose, and
never automerge/approve/merge.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

WORKFLOW_ID = "obs:dependency-review"
CANONICAL_MERGE_READY_LABEL = "oblt-aw/ai/merge-ready"

_LIVE_REQUIRED_EXPECTATION_KEYS = (
    "dashboard_enabled",
    "dependency_review_job_executed",
    "merge_ready_label_applied",
    "dependency_review_comment",
)

_LIVE_REQUIRED_TRIGGER_BOOL_KEYS = (
    "require_open_pr",
    "force_actions_pin_bump",
    "wait_dependency_review",
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
    if "require_allowed_pr_author" not in trigger:
        missing.append("require_allowed_pr_author")
    if missing:
        return f"live trigger missing required keys: {missing}"
    for key in _LIVE_REQUIRED_TRIGGER_BOOL_KEYS:
        try:
            _as_bool(trigger[key])
        except TypeError as exc:
            return f"live trigger {key!r} must be bool ({exc})"
    try:
        _as_bool(trigger["require_allowed_pr_author"])
    except TypeError as exc:
        return f"live trigger 'require_allowed_pr_author' must be bool ({exc})"
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
                "Enable obs:dependency-review on the Control Plane Dashboard, "
                "then re-run."
            )
        elif "author" in lower:
            notes.append(
                "Run under GitHub Actions with Vault create-token using this "
                "repo's workflow-token-policy from config/e2e.json so "
                "the fixture PR is authored as "
                "elastic-vault-github-plugin-prod[bot]."
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
    dr = outcome.get("dependency_review") or {}
    merge_ready = outcome.get("merge_ready_label") or {}
    dr_comment = outcome.get("dependency_review_comment")

    _check(checks, "layer_e2e", layer == "e2e", f"layer={layer!r}")

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

        if _trigger_bool(trigger, "require_allowed_pr_author", default=True):
            try:
                author_ok = _as_bool(path_gates.get("author_matches_allowed"))
                _check(
                    checks,
                    "author_allowed",
                    author_ok,
                    f"author_matches_allowed={author_ok}",
                )
            except TypeError as exc:
                _check(checks, "author_allowed", False, str(exc))

        try:
            expected = _as_bool(expectations["dependency_review_job_executed"])
            actual = _as_bool(dr.get("job_executed"))
            # Fail closed: overall run conclusion is not a substitute.
            job_conclusion = dr.get("job_conclusion")
            named_ok = actual and job_conclusion == "success"
            _check(
                checks,
                "dependency_review_job_executed",
                named_ok == expected,
                f"expected={expected} job_executed={actual} "
                f"job_conclusion={job_conclusion!r}",
            )
        except TypeError as exc:
            _check(checks, "dependency_review_job_executed", False, str(exc))

        try:
            expected = _as_bool(expectations["merge_ready_label_applied"])
            actual = _as_bool(merge_ready.get("applied"))
            label_name = str(merge_ready.get("name") or "")
            # Fail closed: applied=true with a wrong name must not green the gate.
            name_ok = (not expected) or (label_name == CANONICAL_MERGE_READY_LABEL)
            _check(
                checks,
                "merge_ready_label_applied",
                actual == expected and name_ok,
                f"expected={expected} actual={actual} label={label_name!r} "
                f"canonical={CANONICAL_MERGE_READY_LABEL!r}",
            )
        except TypeError as exc:
            _check(checks, "merge_ready_label_applied", False, str(exc))

        fixture = outcome.get("fixture") or {}
        if isinstance(fixture, dict) and (
            outcome.get("pr_number") is not None or fixture.get("pr_number") is not None
        ):
            cleanup_error = fixture.get("cleanup_error")
            cleaned_up = fixture.get("cleaned_up") is True
            _check(
                checks,
                "fixture_cleaned_up",
                cleaned_up and not cleanup_error,
                f"cleaned_up={fixture.get('cleaned_up')!r} "
                f"cleanup_error={cleanup_error!r}",
            )

        try:
            expected = _as_bool(expectations["dependency_review_comment"])
            present = isinstance(dr_comment, dict) and bool(dr_comment.get("id"))
            _check(
                checks,
                "dependency_review_comment",
                present == expected,
                f"expected={expected} present={present}",
            )
        except TypeError as exc:
            _check(checks, "dependency_review_comment", False, str(exc))

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
                "Oracle asserts side effects only (named DR job, label, comment); "
                "not dependency-review free text; not automerge."
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
        description="Oracle for obs:dependency-review live E2E."
    )
    parser.add_argument("--outcome-path", type=Path, required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/dependency-review"),
    )
    parser.add_argument("--expected-case-id", required=True)
    args = parser.parse_args(argv)

    if not args.outcome_path.is_file():
        print(f"Missing outcome file: {args.outcome_path}", file=sys.stderr)
        return 2

    outcome = _load_json(args.outcome_path)
    if not isinstance(outcome, dict):
        print(f"Outcome must be a JSON object: {args.outcome_path}", file=sys.stderr)
        return 2

    expected_case_id = str(args.expected_case_id).strip()
    if not expected_case_id:
        print("--expected-case-id must be a non-empty string", file=sys.stderr)
        return 2
    outcome_case_id = str(outcome.get("case_id") or "")
    if outcome_case_id != expected_case_id:
        print(
            f"Outcome case_id {outcome_case_id!r} does not match "
            f"--expected-case-id {expected_case_id!r}",
            file=sys.stderr,
        )
        return 2

    case_path = args.testdata_root / "cases" / expected_case_id / "case.json"
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
    print(f"Oracle pass for case {expected_case_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
