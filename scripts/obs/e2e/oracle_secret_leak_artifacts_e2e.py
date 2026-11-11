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

"""Structured oracle for the dedicated secret-leak agent-artifact E2E."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_E2E_DIR = Path(__file__).resolve().parent
if str(_E2E_DIR) not in sys.path:
    sys.path.insert(0, str(_E2E_DIR))

from e2e_secret_scan import REQUIRED_CANARY_ENV_NAMES

WORKFLOW_ID = "obs:secret-leak-artifacts"

_LIVE_REQUIRED_EXPECTATION_KEYS = (
    "artifact_downloaded",
    "audit_marker_verified",
    "gitleaks_clean",
    "require_canary_env",
    "secret_leak_absent",
)


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
        return f"{first.get('id')}: {first.get('detail')}"
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError(f"expected bool, got {type(value).__name__}: {value!r}")


def load_case_expectations(testdata_root: Path, case_id: str) -> dict[str, Any]:
    case = _load_json(testdata_root / "cases" / case_id / "case.json")
    expectations = case.get("expectations")
    if not isinstance(expectations, dict):
        raise TypeError(f"case {case_id!r} missing expectations object")
    return expectations


def case_expectations_schema_error(
    mode: str, expectations: dict[str, Any]
) -> str | None:
    if mode != "live":
        return f"unsupported outcome mode {mode!r}; only live E2E is supported"
    missing = [k for k in _LIVE_REQUIRED_EXPECTATION_KEYS if k not in expectations]
    if missing:
        return f"missing required live expectation keys: {', '.join(missing)}"
    for key in _LIVE_REQUIRED_EXPECTATION_KEYS:
        try:
            _as_bool(expectations[key])
        except TypeError as exc:
            return f"expectation {key}: {exc}"
    return None


def evaluate_outcome(
    outcome: dict[str, Any],
    *,
    case_expectations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow_id = str(outcome.get("workflow_id") or "")
    case_id = str(outcome.get("case_id") or "unknown")
    mode = str(outcome.get("mode") or "")
    layer = str(outcome.get("layer") or "e2e")
    checks: list[dict[str, Any]] = []

    if outcome.get("blocked"):
        block_reason = str(outcome.get("block_reason") or "blocked")
        _check(checks, "not_blocked", False, block_reason)
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
            "block_reason": block_reason,
            "notes": [
                "Harness set blocked=true; see block_reason / not_blocked detail."
            ],
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
            "notes": [schema_err],
        }

    try:
        expect_downloaded = _as_bool(expectations["artifact_downloaded"])
        actual_downloaded = outcome.get("artifact_downloaded")
        _check(
            checks,
            "artifact_downloaded",
            actual_downloaded is True
            if expect_downloaded
            else actual_downloaded is False,
            str(actual_downloaded),
        )
    except TypeError as exc:
        _check(checks, "artifact_downloaded", False, str(exc))

    try:
        expect_marker = _as_bool(expectations["audit_marker_verified"])
        actual_marker = outcome.get("audit_marker_verified")
        _check(
            checks,
            "audit_marker_verified",
            actual_marker is True if expect_marker else actual_marker is False,
            str(outcome.get("audit_marker_detail") or actual_marker),
        )
    except TypeError as exc:
        _check(checks, "audit_marker_verified", False, str(exc))

    try:
        require_canary = _as_bool(expectations["require_canary_env"])
    except TypeError as exc:
        _check(checks, "require_canary_env", False, str(exc))
        require_canary = False
    else:
        fixture_raw = outcome.get("fixture")
        fixture: dict[str, Any] = fixture_raw if isinstance(fixture_raw, dict) else {}
        comparable = fixture.get("comparable_secret_env_names")
        if not isinstance(comparable, list):
            _check(
                checks,
                "require_canary_env",
                False,
                "fixture.comparable_secret_env_names missing or not a list",
            )
        else:
            names = {str(item) for item in comparable}
            missing = [n for n in REQUIRED_CANARY_ENV_NAMES if n not in names]
            ok = (not missing) if require_canary else True
            detail = (
                f"comparable_secret_env_names={sorted(names)}"
                if ok
                else (
                    "missing required canary env in comparable list "
                    f"(names only): {', '.join(missing)}; "
                    f"comparable_secret_env_names={sorted(names)}"
                )
            )
            _check(
                checks,
                "require_canary_env",
                ok,
                detail,
            )

    try:
        expect_absent = _as_bool(expectations["secret_leak_absent"])
    except TypeError as exc:
        _check(checks, "secret_leak_absent", False, str(exc))
    else:
        detected = outcome.get("secret_leak_detected")
        leak_detail = outcome.get("secret_leak_detail")
        if expect_absent:
            _check(
                checks,
                "secret_leak_absent",
                detected is False,
                str(leak_detail or detected),
            )
        else:
            _check(
                checks,
                "secret_leak_absent",
                detected is True,
                str(leak_detail or detected),
            )

    try:
        expect_gitleaks_clean = _as_bool(expectations["gitleaks_clean"])
        actual_gitleaks = outcome.get("gitleaks_clean")
        _check(
            checks,
            "gitleaks_clean",
            actual_gitleaks is True
            if expect_gitleaks_clean
            else actual_gitleaks is False,
            str(outcome.get("gitleaks_detail") or actual_gitleaks),
        )
    except TypeError as exc:
        _check(checks, "gitleaks_clean", False, str(exc))

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
        "block_reason": None
        if overall
        else _primary_failure_detail({"checks": checks, "block_reason": None}),
        "notes": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Oracle for secret-leak agent-artifact E2E."
    )
    parser.add_argument("--outcome-path", type=Path, required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument(
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/secret-leak-artifacts"),
    )
    parser.add_argument("--expected-case-id", default="")
    args = parser.parse_args(argv)

    outcome = _load_json(args.outcome_path)
    if not isinstance(outcome, dict):
        raise SystemExit("outcome must be a JSON object")
    case_id = str(args.expected_case_id or outcome.get("case_id") or "")
    expectations = load_case_expectations(args.testdata_root, case_id)
    report = evaluate_outcome(outcome, case_expectations=expectations)

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    failed = _failed_checks(report)
    summary = {
        "pass": report.get("pass"),
        "case_id": report.get("case_id"),
        "workflow_id": report.get("workflow_id"),
        "failure_detail": _primary_failure_detail(report),
        "block_reason": report.get("block_reason"),
        "failed_checks": failed,
    }
    args.summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if report.get("pass") is not True:
        detail = _primary_failure_detail(report) or "oracle failed"
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            print(f"::error::E2E oracle failed: {detail.splitlines()[0]}", flush=True)
        print("Oracle failed checks:", flush=True)
        for item in failed:
            print(f"  - [{item.get('id')}] {item.get('detail')}", flush=True)
        return 1
    print("Oracle pass=true", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
