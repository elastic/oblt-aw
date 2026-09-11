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

"""Structured oracle for estc-pr-buildkite-detective E2E / integration outcomes.

Asserts structured path/side-effect markers only — never full free-text
golden equality of agent prose. Emits a machine-readable report for #1878.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKFLOW_ID = "obs:estc-pr-buildkite-detective"
DEFAULT_QUARANTINE = Path("config/obs/e2e-quarantine.json")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_quarantine(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "version": 1,
            "default_owner_team": "@elastic/observablt-robots",
            "cases": [],
        }
    data = _load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"Quarantine file must be a JSON object: {path}")
    return data


def find_quarantine_entry(
    quarantine: dict[str, Any], workflow_id: str, case_id: str
) -> dict[str, Any] | None:
    for entry in quarantine.get("cases") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("workflow_id") != workflow_id or entry.get("case_id") != case_id:
            continue
        owner = entry.get("owner")
        reason = entry.get("reason")
        if not owner or not reason:
            # Invalid quarantine rows are ignored (do not silently skip).
            continue
        return entry
    return None


def _check(
    checks: list[dict[str, Any]], check_id: str, passed: bool, detail: str
) -> None:
    checks.append({"id": check_id, "pass": passed, "detail": detail})


def _as_bool(value: Any) -> bool:
    """Strict boolean: only real bools; reject truthy strings/numbers."""
    if isinstance(value, bool):
        return value
    raise TypeError(f"expected bool, got {type(value).__name__}: {value!r}")


def evaluate_outcome(
    outcome: dict[str, Any],
    quarantine: dict[str, Any],
) -> dict[str, Any]:
    workflow_id = str(outcome.get("workflow_id") or WORKFLOW_ID)
    case_id = str(outcome.get("case_id") or "unknown")
    mode = str(outcome.get("mode") or "fixture")
    layer = str(outcome.get("layer") or ("e2e" if mode == "live" else "integration"))
    checks: list[dict[str, Any]] = []
    quarantined = find_quarantine_entry(quarantine, workflow_id, case_id)

    if quarantined:
        report = {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": mode,
            "pass": True,
            "skipped": True,
            "quarantined": True,
            "quarantine_owner": quarantined["owner"],
            "quarantine_reason": quarantined["reason"],
            "run_url": outcome.get("run_url"),
            "checks": [
                {
                    "id": "quarantine",
                    "pass": True,
                    "detail": (
                        f"Skipped quarantined case; owner={quarantined['owner']}; "
                        f"{quarantined['reason']}"
                    ),
                }
            ],
            "agent_invoked": bool(outcome.get("agent_invoked")),
            "notes": [
                "Quarantined cases must not be silently retried into green.",
                "Remove the quarantine entry when the flake is fixed.",
            ],
        }
        return report

    if outcome.get("blocked"):
        _check(
            checks,
            "not_blocked",
            False,
            str(outcome.get("block_reason") or "blocked"),
        )
        return {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": mode,
            "pass": False,
            "skipped": False,
            "quarantined": False,
            "run_url": outcome.get("run_url"),
            "checks": checks,
            "agent_invoked": bool(outcome.get("agent_invoked")),
            "notes": [
                "Resolve block_reason (dashboard enablement or Buildkite URL var), then re-run.",
            ],
        }

    expectations = outcome.get("expectations") or {}
    path_exp = expectations.get("path_gates") or {}
    bk_exp = expectations.get("buildkite") or {}
    path_gates = outcome.get("path_gates") or {}
    buildkite = outcome.get("buildkite") or {}

    _check(
        checks,
        "workflow_id",
        outcome.get("workflow_id") == WORKFLOW_ID,
        f"workflow_id={outcome.get('workflow_id')!r}",
    )

    # Explicit non-goal: never compare agent free text.
    _check(
        checks,
        "no_free_text_golden",
        "golden_free_text" not in outcome and "agent_prose" not in outcome,
        "outcome has no free-text golden fields",
    )

    if mode == "live":
        return _evaluate_live(outcome, expectations, checks, workflow_id, case_id, layer)

    # Fixture / integration mode.
    _check(
        checks,
        "mode_fixture_no_agent",
        mode == "fixture" and outcome.get("agent_invoked") is False,
        f"mode={mode!r} agent_invoked={outcome.get('agent_invoked')!r}",
    )
    _check(
        checks,
        "layer_integration",
        layer == "integration",
        f"layer={layer!r}",
    )

    for key, check_id in (
        ("state_failure", "path_state_failure"),
        ("context_contains_buildkite", "path_context_buildkite"),
        ("has_open_pr", "path_has_open_pr"),
        ("shared_proceed", "path_shared_proceed"),
    ):
        if key not in path_exp:
            continue
        try:
            actual = _as_bool(path_gates.get(key))
            expected = _as_bool(path_exp[key])
        except TypeError as exc:
            _check(checks, check_id, False, str(exc))
            continue
        _check(
            checks,
            check_id,
            actual == expected,
            f"expected={expected} actual={actual}",
        )

    path_ready = bool(path_gates.get("path_ready"))
    _check(checks, "path_ready", path_ready, f"path_ready={path_ready}")

    bk_ok = bool(buildkite.get("ok"))
    _check(checks, "buildkite_ok", bk_ok, str(buildkite.get("error") or "ok"))

    event_context = buildkite.get("event_context") or {}
    required_keys = bk_exp.get("required_event_keys") or [
        "event_name",
        "commit_sha",
        "build_url",
        "pipeline",
        "branch",
        "pr_number",
    ]
    missing = [key for key in required_keys if not event_context.get(key)]
    _check(
        checks,
        "buildkite_event_keys",
        not missing,
        f"missing={missing}" if missing else "all required keys present",
    )

    min_failed = int(bk_exp.get("min_failed_jobs", 1))
    failed_count = int(buildkite.get("failed_job_count") or 0)
    _check(
        checks,
        "buildkite_failed_jobs",
        failed_count >= min_failed,
        f"failed_job_count={failed_count} min={min_failed}",
    )

    if "log_has_content" in bk_exp or any(
        job.get("log_has_content") is False for job in (buildkite.get("failed_jobs") or [])
    ):
        jobs = buildkite.get("failed_jobs") or []
        logs_ok = bool(jobs) and all(bool(job.get("log_has_content")) for job in jobs)
        _check(
            checks,
            "buildkite_log_content",
            logs_ok,
            f"failed_jobs_with_logs={sum(1 for j in jobs if j.get('log_has_content'))}/{len(jobs)}",
        )

    if expectations.get("agent_invoked") is False:
        _check(
            checks,
            "agent_not_invoked",
            outcome.get("agent_invoked") is False,
            f"agent_invoked={outcome.get('agent_invoked')!r}",
        )

    overall = all(item["pass"] for item in checks)
    return {
        "workflow_id": workflow_id,
        "case_id": case_id,
        "layer": layer,
        "mode": mode,
        "pass": overall,
        "skipped": False,
        "quarantined": False,
        "run_url": outcome.get("run_url"),
        "checks": checks,
        "agent_invoked": bool(outcome.get("agent_invoked")),
        "notes": [
            "Fixture oracle asserts structured gates and Buildkite markers only.",
            "Promote (#1878) should prefer live E2E summary.pass for this workflow.",
        ],
    }


def _evaluate_live(
    outcome: dict[str, Any],
    expectations: dict[str, Any],
    checks: list[dict[str, Any]],
    workflow_id: str,
    case_id: str,
    layer: str,
) -> dict[str, Any]:
    path_gates = outcome.get("path_gates") or {}
    status_trigger = outcome.get("status_trigger") or {}
    comment = outcome.get("agent_comment")

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

    if "status_job_executed" in expectations:
        try:
            expected = _as_bool(expectations["status_job_executed"])
            actual = bool(status_trigger.get("job_executed"))
            _check(
                checks,
                "status_job_executed",
                actual == expected,
                f"expected={expected} actual={actual} run={status_trigger.get('url')}",
            )
        except TypeError as exc:
            _check(checks, "status_job_executed", False, str(exc))

    if "agent_invoked" in expectations:
        try:
            expected = _as_bool(expectations["agent_invoked"])
            actual = bool(outcome.get("agent_invoked"))
            _check(
                checks,
                "agent_invoked",
                actual == expected,
                f"expected={expected} actual={actual}",
            )
        except TypeError as exc:
            _check(checks, "agent_invoked", False, str(exc))

    expect_comment = expectations.get("expect_agent_comment")
    if expect_comment is True:
        markers = expectations.get("agent_comment_markers") or ["### TL;DR", "## Remediation"]
        _check(
            checks,
            "agent_comment_present",
            isinstance(comment, dict) and bool(comment.get("id")),
            f"comment={comment}",
        )
        _check(
            checks,
            "agent_comment_markers_configured",
            bool(markers),
            f"markers={markers}",
        )
    elif expect_comment is False:
        _check(
            checks,
            "agent_comment_absent",
            comment is None,
            f"comment={comment}",
        )

    overall = all(item["pass"] for item in checks)
    return {
        "workflow_id": workflow_id,
        "case_id": case_id,
        "layer": layer,
        "mode": "live",
        "pass": overall,
        "skipped": False,
        "quarantined": False,
        "run_url": outcome.get("run_url"),
        "status_trigger_url": status_trigger.get("url"),
        "pr_url": outcome.get("pr_url"),
        "checks": checks,
        "agent_invoked": bool(outcome.get("agent_invoked")),
        "notes": [
            "Live oracle asserts dashboard gate, status job execution, agent invocation, "
            "and structured PR comment markers — never full agent prose.",
            "Promote (#1878) should consume report.pass / summary.json.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Oracle for estc-pr-buildkite-detective E2E / integration outcomes"
    )
    parser.add_argument(
        "--outcome-path",
        type=Path,
        required=True,
        help="Harness outcome JSON",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        required=True,
        help="Where to write the machine-readable oracle report JSON",
    )
    parser.add_argument(
        "--quarantine-path",
        type=Path,
        default=DEFAULT_QUARANTINE,
        help="Quarantine config JSON",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=None,
        help="Optional compact summary JSON for promote (#1878) consumers",
    )
    args = parser.parse_args(argv)

    outcome = _load_json(args.outcome_path)
    if not isinstance(outcome, dict):
        raise SystemExit(f"Outcome must be a JSON object: {args.outcome_path}")

    quarantine = load_quarantine(args.quarantine_path)
    report = evaluate_outcome(outcome, quarantine)

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "pass": report.get("pass"),
        "skipped": report.get("skipped"),
        "quarantined": report.get("quarantined"),
        "case_id": report.get("case_id"),
        "run_url": report.get("run_url"),
        "status_trigger_url": report.get("status_trigger_url"),
        "pr_url": report.get("pr_url"),
        "workflow_id": report.get("workflow_id"),
        "layer": report.get("layer"),
        "mode": report.get("mode"),
        "agent_invoked": report.get("agent_invoked"),
    }
    if args.summary_path is not None:
        args.summary_path.parent.mkdir(parents=True, exist_ok=True)
        args.summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote promote summary to {args.summary_path}")
    print(f"Wrote oracle report to {args.report_path}")
    print(json.dumps(summary, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
