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

"""Structured oracle for estc-pr-buildkite-detective E2E outcomes.

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
        if entry.get("workflow_id") == workflow_id and entry.get("case_id") == case_id:
            return entry
    return None


def _check(
    checks: list[dict[str, Any]], check_id: str, passed: bool, detail: str
) -> None:
    checks.append({"id": check_id, "pass": passed, "detail": detail})


def evaluate_outcome(
    outcome: dict[str, Any],
    quarantine: dict[str, Any],
) -> dict[str, Any]:
    workflow_id = str(outcome.get("workflow_id") or WORKFLOW_ID)
    case_id = str(outcome.get("case_id") or "unknown")
    mode = str(outcome.get("mode") or "fixture")
    checks: list[dict[str, Any]] = []
    quarantined = find_quarantine_entry(quarantine, workflow_id, case_id)

    if quarantined:
        owner = quarantined.get("owner") or quarantine.get(
            "default_owner_team", "@elastic/observablt-robots"
        )
        reason = quarantined.get("reason") or "quarantined"
        report = {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": "e2e",
            "mode": mode,
            "pass": True,
            "skipped": True,
            "quarantined": True,
            "quarantine_owner": owner,
            "quarantine_reason": reason,
            "run_url": outcome.get("run_url"),
            "checks": [
                {
                    "id": "quarantine",
                    "pass": True,
                    "detail": f"Skipped quarantined case; owner={owner}; {reason}",
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
            "live_not_blocked_unexpectedly",
            False,
            str(outcome.get("block_reason") or "blocked"),
        )
        return {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": "e2e",
            "mode": mode,
            "pass": False,
            "skipped": False,
            "quarantined": False,
            "run_url": outcome.get("run_url"),
            "checks": checks,
            "agent_invoked": bool(outcome.get("agent_invoked")),
            "notes": [
                "Live mode remains blocked until a sandbox consumer exists.",
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
    _check(
        checks,
        "mode_fixture_no_agent",
        mode == "fixture" and outcome.get("agent_invoked") is False,
        f"mode={mode!r} agent_invoked={outcome.get('agent_invoked')!r}",
    )

    if "state_failure" in path_exp:
        actual = bool(path_gates.get("state_failure"))
        expected = bool(path_exp["state_failure"])
        _check(
            checks,
            "path_state_failure",
            actual == expected,
            f"expected={expected} actual={actual}",
        )
    if "context_contains_buildkite" in path_exp:
        actual = bool(path_gates.get("context_contains_buildkite"))
        expected = bool(path_exp["context_contains_buildkite"])
        _check(
            checks,
            "path_context_buildkite",
            actual == expected,
            f"expected={expected} actual={actual}",
        )
    if "has_open_pr" in path_exp:
        actual = bool(path_gates.get("has_open_pr"))
        expected = bool(path_exp["has_open_pr"])
        _check(
            checks,
            "path_has_open_pr",
            actual == expected,
            f"expected={expected} actual={actual}",
        )
    if "shared_proceed" in path_exp:
        actual = bool(path_gates.get("shared_proceed"))
        expected = bool(path_exp["shared_proceed"])
        _check(
            checks,
            "path_shared_proceed",
            actual == expected,
            f"expected={expected} actual={actual}",
        )

    path_ready = bool(path_gates.get("path_ready"))
    _check(
        checks,
        "path_ready",
        path_ready,
        f"path_ready={path_ready}",
    )

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

    if expectations.get("agent_invoked") is False:
        _check(
            checks,
            "agent_not_invoked",
            outcome.get("agent_invoked") is False,
            f"agent_invoked={outcome.get('agent_invoked')!r}",
        )

    # Explicit non-goal: never compare agent free text.
    _check(
        checks,
        "no_free_text_golden",
        "golden_free_text" not in outcome and "agent_prose" not in outcome,
        "outcome has no free-text golden fields",
    )

    overall = all(item["pass"] for item in checks)
    return {
        "workflow_id": workflow_id,
        "case_id": case_id,
        "layer": "e2e",
        "mode": mode,
        "pass": overall,
        "skipped": False,
        "quarantined": False,
        "run_url": outcome.get("run_url"),
        "checks": checks,
        "agent_invoked": bool(outcome.get("agent_invoked")),
        "notes": [
            "Oracle asserts structured gates and Buildkite markers only.",
            "Promote (#1878) should consume report.pass / report.run_url / checks.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Oracle for estc-pr-buildkite-detective E2E outcomes"
    )
    parser.add_argument(
        "--outcome-path",
        type=Path,
        required=True,
        help="Harness outcome JSON from estc_pr_buildkite_detective_e2e_harness.py",
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
        "--allow-live-blocked",
        action="store_true",
        help=(
            "Treat live-mode blocked outcomes as a non-failing informational "
            "report (exit 0). Default fails live blocked runs."
        ),
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

    if (
        args.allow_live_blocked
        and outcome.get("blocked")
        and outcome.get("mode") == "live"
    ):
        report["pass"] = True
        report["skipped"] = True
        report["notes"] = list(report.get("notes") or []) + [
            "Live blocked outcome accepted via --allow-live-blocked.",
        ]
        for item in report["checks"]:
            if item["id"] == "live_not_blocked_unexpectedly":
                item["pass"] = True
                item["detail"] = "accepted as blocked (sandbox Unknown)"

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
        "workflow_id": report.get("workflow_id"),
        "layer": report.get("layer"),
        "mode": report.get("mode"),
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
