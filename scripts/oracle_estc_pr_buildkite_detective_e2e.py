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

Asserts path gates and comment presence/absence only — never full free-text
golden equality of agent prose, and (for now) not comment-section marker
shape. Markers remain harness identity for find/clear; stricter oracle
checks are deferred to follow-ups. Emits a machine-readable report for #1878.
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


# Mode-specific keys that authorize case gates. Non-empty is not enough:
# a typo-only map must fail closed the same way as missing/empty expectations.
_LIVE_REQUIRED_EXPECTATION_KEYS = (
    "dashboard_enabled",
    "status_job_executed",
    "agent_invoked",
    "expect_agent_comment",
)
# Live trigger contract from checked-in case.json (not harness-copied outcome.trigger).
_LIVE_REQUIRED_TRIGGER_BOOL_KEYS = (
    "context_contains_buildkite",
    "require_open_pr",
    "use_buildkite_target_url",
    "clear_prior_detective_comments",
)
_LIVE_OPTIONAL_TRIGGER_BOOL_KEYS = ("create_failed_buildkite_build",)
_FIXTURE_REQUIRED_EXPECTATION_KEYS = (
    "path_gates",
    "buildkite",
    "agent_invoked",
)
_FIXTURE_REQUIRED_PATH_GATE_KEYS = (
    "state_failure",
    "context_contains_buildkite",
    "has_open_pr",
)
_FIXTURE_REQUIRED_BUILDKITE_EVENT_KEYS = (
    "event_name",
    "commit_sha",
    "build_url",
    "pipeline",
    "branch",
    "pr_number",
)


def case_expectations_schema_error(
    mode: str, expectations: dict[str, Any]
) -> str | None:
    """Return a detail string when expectations lack required mode-specific gates.

    Callers must treat any returned string as a failed ``case_expectations``
    check and must not authorize gate assertions from the incomplete map.
    """
    if mode == "live":
        missing = [k for k in _LIVE_REQUIRED_EXPECTATION_KEYS if k not in expectations]
        if missing:
            return f"live expectations missing required keys: {missing}"
        for key in _LIVE_REQUIRED_EXPECTATION_KEYS:
            try:
                _as_bool(expectations[key])
            except TypeError as exc:
                return f"live expectation {key!r} must be bool ({exc})"
        return None

    missing = [k for k in _FIXTURE_REQUIRED_EXPECTATION_KEYS if k not in expectations]
    if missing:
        return f"fixture expectations missing required keys: {missing}"
    path_gates = expectations.get("path_gates")
    if not isinstance(path_gates, dict) or not path_gates:
        return "fixture expectations.path_gates must be a non-empty object"
    path_missing = [k for k in _FIXTURE_REQUIRED_PATH_GATE_KEYS if k not in path_gates]
    if path_missing:
        return f"fixture path_gates missing required keys: {path_missing}"
    for key in _FIXTURE_REQUIRED_PATH_GATE_KEYS:
        try:
            _as_bool(path_gates[key])
        except TypeError as exc:
            return f"fixture path_gates.{key} must be bool ({exc})"
    buildkite = expectations.get("buildkite")
    if not isinstance(buildkite, dict) or not buildkite:
        return "fixture expectations.buildkite must be a non-empty object"
    if "min_failed_jobs" not in buildkite:
        return "fixture expectations.buildkite.min_failed_jobs is required"
    try:
        min_failed = int(buildkite["min_failed_jobs"])
    except (TypeError, ValueError) as exc:
        return f"fixture expectations.buildkite.min_failed_jobs must be int ({exc})"
    if min_failed < 1:
        return (
            "fixture expectations.buildkite.min_failed_jobs must be a positive "
            f"integer, got {min_failed}"
        )
    required_event_keys = buildkite.get("required_event_keys")
    if not isinstance(required_event_keys, list) or not required_event_keys:
        return (
            "fixture expectations.buildkite.required_event_keys must be a "
            "non-empty list"
        )
    if not all(isinstance(key, str) and key for key in required_event_keys):
        return (
            "fixture expectations.buildkite.required_event_keys must contain "
            "only non-empty strings"
        )
    event_missing = [
        key
        for key in _FIXTURE_REQUIRED_BUILDKITE_EVENT_KEYS
        if key not in required_event_keys
    ]
    if event_missing:
        return (
            "fixture expectations.buildkite.required_event_keys missing "
            f"required keys: {event_missing}"
        )
    try:
        agent_invoked = _as_bool(expectations["agent_invoked"])
    except TypeError as exc:
        return f"fixture expectation agent_invoked must be bool ({exc})"
    # Fixture mode is explicitly no-agent; true would skip the evaluator gate.
    if agent_invoked is not False:
        return "fixture expectation agent_invoked must be false"
    return None


def case_trigger_schema_error(trigger: dict[str, Any]) -> str | None:
    """Return a detail string when live case trigger lacks the routing contract.

    Live gates for status state/context/publisher/target URL are authorized only
    from this checked-in map — never from a missing or empty harness copy.
    """
    if "status_state" not in trigger:
        return "live trigger missing required key: status_state"
    status_state = trigger.get("status_state")
    if not isinstance(status_state, str) or not status_state.strip():
        return f"live trigger status_state must be a non-empty string, got {status_state!r}"
    missing = [k for k in _LIVE_REQUIRED_TRIGGER_BOOL_KEYS if k not in trigger]
    if missing:
        return f"live trigger missing required keys: {missing}"
    for key in _LIVE_REQUIRED_TRIGGER_BOOL_KEYS:
        try:
            _as_bool(trigger[key])
        except TypeError as exc:
            return f"live trigger {key!r} must be bool ({exc})"
    for key in _LIVE_OPTIONAL_TRIGGER_BOOL_KEYS:
        if key not in trigger:
            continue
        try:
            _as_bool(trigger[key])
        except TypeError as exc:
            return f"live trigger {key!r} must be bool ({exc})"
    return None


def evaluate_outcome(
    outcome: dict[str, Any],
    quarantine: dict[str, Any],
    *,
    case_expectations: dict[str, Any] | None = None,
    case_trigger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Do not default a missing workflow_id to WORKFLOW_ID: report and check
    # must stay consistent, and a missing id must fail closed.
    workflow_id = str(outcome.get("workflow_id") or "")
    case_id = str(outcome.get("case_id") or "unknown")
    mode = str(outcome.get("mode") or "fixture")
    layer = str(outcome.get("layer") or ("e2e" if mode == "live" else "integration"))
    checks: list[dict[str, Any]] = []
    quarantined = find_quarantine_entry(quarantine, workflow_id, case_id)

    if quarantined:
        # Fail closed: skipped + pass=false so matrix/outputs.pass cannot
        # green-promote while a required case is quarantined (#1878 contract).
        report = {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "layer": layer,
            "mode": mode,
            "pass": False,
            "skipped": True,
            "quarantined": True,
            "quarantine_owner": quarantined["owner"],
            "quarantine_reason": quarantined["reason"],
            "run_url": outcome.get("run_url"),
            "checks": [
                {
                    "id": "quarantine",
                    "pass": False,
                    "detail": (
                        f"Quarantined case blocks gate; owner={quarantined['owner']}; "
                        f"{quarantined['reason']}"
                    ),
                }
            ],
            "agent_invoked": bool(outcome.get("agent_invoked")),
            "notes": [
                "Quarantined cases fail the E2E gate (pass=false); do not retry into green.",
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

    # Fail closed: never authorize gate checks from harness-copied
    # outcome.expectations alone. Callers (CLI + tests) must pass checked-in
    # case expectations explicitly. Empty, typo-only, or schema-incomplete
    # mappings are rejected so malformed case.json cannot skip case gates.
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

    # Live routing gates (state/context/publisher/URL) require checked-in
    # case.trigger — never authorize from missing/empty outcome.trigger alone.
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

    path_exp = expectations.get("path_gates") or {}
    bk_exp = expectations.get("buildkite") or {}
    path_gates = outcome.get("path_gates") or {}
    buildkite = outcome.get("buildkite") or {}

    _check(
        checks,
        "workflow_id",
        workflow_id == WORKFLOW_ID,
        f"workflow_id={workflow_id!r}",
    )

    # Explicit non-goal: never compare agent free text.
    _check(
        checks,
        "no_free_text_golden",
        "golden_free_text" not in outcome and "agent_prose" not in outcome,
        "outcome has no free-text golden fields",
    )

    if mode == "live":
        return _evaluate_live(
            outcome, expectations, trigger, checks, workflow_id, case_id, layer
        )

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

    try:
        path_ready = _as_bool(path_gates.get("path_ready"))
        _check(checks, "path_ready", path_ready, f"path_ready={path_ready}")
    except TypeError as exc:
        _check(checks, "path_ready", False, str(exc))

    try:
        bk_ok = _as_bool(buildkite.get("ok"))
        _check(checks, "buildkite_ok", bk_ok, str(buildkite.get("error") or "ok"))
    except TypeError as exc:
        _check(checks, "buildkite_ok", False, str(exc))

    event_context = buildkite.get("event_context") or {}
    # Schema already requires the floor set; still union so supersets apply.
    required_keys = list(_FIXTURE_REQUIRED_BUILDKITE_EVENT_KEYS)
    extra_keys = bk_exp.get("required_event_keys")
    if isinstance(extra_keys, list):
        for key in extra_keys:
            if isinstance(key, str) and key and key not in required_keys:
                required_keys.append(key)
    missing = [key for key in required_keys if not event_context.get(key)]
    _check(
        checks,
        "buildkite_event_keys",
        not missing,
        f"missing={missing}" if missing else "all required keys present",
    )

    try:
        min_failed = int(bk_exp["min_failed_jobs"])
    except (KeyError, TypeError, ValueError):
        # Schema should have rejected this; fail closed if we still got here.
        min_failed = 1
        _check(
            checks,
            "buildkite_failed_jobs",
            False,
            "fixture expectations.buildkite.min_failed_jobs missing or invalid",
        )
    else:
        if min_failed < 1:
            _check(
                checks,
                "buildkite_failed_jobs",
                False,
                f"min_failed_jobs must be >= 1, got {min_failed}",
            )
        else:
            failed_count = int(buildkite.get("failed_job_count") or 0)
            _check(
                checks,
                "buildkite_failed_jobs",
                failed_count >= min_failed,
                f"failed_job_count={failed_count} min={min_failed}",
            )

    if "log_has_content" in bk_exp or any(
        job.get("log_has_content") is False
        for job in (buildkite.get("failed_jobs") or [])
    ):
        jobs = buildkite.get("failed_jobs") or []
        logs_ok = bool(jobs) and all(bool(job.get("log_has_content")) for job in jobs)
        _check(
            checks,
            "buildkite_log_content",
            logs_ok,
            f"failed_jobs_with_logs={sum(1 for j in jobs if j.get('log_has_content'))}/{len(jobs)}",
        )

    if "agent_invoked" in expectations:
        try:
            expected = _as_bool(expectations["agent_invoked"])
            actual = outcome.get("agent_invoked")
            _check(
                checks,
                "agent_not_invoked" if expected is False else "agent_invoked",
                actual is expected,
                f"expected={expected!r} actual={actual!r}",
            )
        except TypeError as exc:
            _check(checks, "agent_invoked", False, str(exc))

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
    trigger: dict[str, Any],
    checks: list[dict[str, Any]],
    workflow_id: str,
    case_id: str,
    layer: str,
) -> dict[str, Any]:
    path_gates = outcome.get("path_gates") or {}
    status_trigger = outcome.get("status_trigger") or {}
    status = outcome.get("status") or {}
    buildkite = outcome.get("buildkite") or {}
    comment = outcome.get("agent_comment")

    _check(
        checks,
        "layer_e2e",
        layer == "e2e",
        f"layer={layer!r}",
    )

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

    # Checked-in case.trigger is the sole source of truth for routing gates.
    # Do not fall back to harness-copied outcome.trigger (may be missing/{}).
    _check(
        checks,
        "status_present",
        isinstance(status, dict) and bool(status),
        f"status={status!r}",
    )
    if status and trigger:
        _check(
            checks,
            "status_emitted",
            bool(status.get("state") and status.get("context")),
            f"status={status}",
        )
        expected_state = trigger.get("status_state")
        _check(
            checks,
            "status_state",
            status.get("state") == expected_state,
            f"expected={expected_state!r} actual={status.get('state')!r}",
        )
        expect_bk = bool(trigger.get("context_contains_buildkite"))
        actual_bk = "buildkite" in str(status.get("context") or "").lower()
        _check(
            checks,
            "status_context_buildkite",
            actual_bk is expect_bk,
            f"expected_contains_buildkite={expect_bk} context={status.get('context')!r}",
        )
        if trigger.get("use_buildkite_target_url") or trigger.get(
            "create_failed_buildkite_build"
        ):
            publisher = status.get("publisher")
            _check(
                checks,
                "status_publisher",
                publisher in {"buildkite", "harness"},
                f"publisher={publisher!r}",
            )
            if trigger.get("create_failed_buildkite_build") and not outcome.get(
                "blocked"
            ):
                # Created intentional-failure builds must be Buildkite-published.
                # Harness publisher is allowed only for the explicit URL override.
                bk = outcome.get("buildkite") or {}
                source = bk.get("source") if isinstance(bk, dict) else None
                if source == "override_env":
                    ok_publisher = publisher in {"buildkite", "harness"}
                else:
                    ok_publisher = publisher == "buildkite"
                _check(
                    checks,
                    "status_publisher_buildkite_path",
                    bool(ok_publisher),
                    f"publisher={publisher!r} buildkite_source={source!r}",
                )
        if trigger.get("use_buildkite_target_url"):
            _check(
                checks,
                "status_target_url",
                bool(status.get("target_url")),
                f"target_url={status.get('target_url')!r}",
            )

    if "status_job_executed" in expectations:
        try:
            run_seen = _as_bool(status_trigger.get("run_seen"))
        except TypeError as exc:
            run_seen = False
            _check(checks, "status_trigger_run_seen", False, str(exc))
        else:
            _check(
                checks,
                "status_trigger_run_seen",
                run_seen is True,
                f"run_seen={run_seen} url={status_trigger.get('url')}",
            )
        try:
            expected = _as_bool(expectations["status_job_executed"])
            actual = _as_bool(status_trigger.get("job_executed"))
            _check(
                checks,
                "status_job_executed",
                actual == expected,
                f"expected={expected} actual={actual} run={status_trigger.get('url')}",
            )
            if expected is False and run_seen is True:
                # Named-job conclusion only — never the overall run conclusion.
                job_conclusion = str(status_trigger.get("job_conclusion") or "").lower()
                _check(
                    checks,
                    "status_job_skipped",
                    job_conclusion == "skipped",
                    (
                        f"negative cases require job_conclusion=skipped, "
                        f"got {job_conclusion!r}"
                    ),
                )
            if expected is True and run_seen is True:
                job_conclusion = str(status_trigger.get("job_conclusion") or "").lower()
                _check(
                    checks,
                    "status_job_success",
                    job_conclusion == "success",
                    f"job_conclusion={job_conclusion!r}",
                )
        except TypeError as exc:
            _check(checks, "status_job_executed", False, str(exc))

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

    # Intentional Buildkite failure path: require a known source and fail closed.
    if trigger.get("create_failed_buildkite_build") and not outcome.get("blocked"):
        source = buildkite.get("source") if isinstance(buildkite, dict) else None
        if source == "created":
            verified = (
                buildkite.get("fail_log_marker_verified")
                if isinstance(buildkite, dict)
                else None
            )
            detail = (
                buildkite.get("fail_log_marker_detail")
                if isinstance(buildkite, dict)
                else None
            )
            _check(
                checks,
                "fail_log_marker_verified",
                verified is True,
                str(detail or verified),
            )
        elif source == "override_env":
            _check(
                checks,
                "buildkite_source_override",
                True,
                "source=override_env",
            )
        else:
            _check(
                checks,
                "buildkite_source_valid",
                False,
                f"expected source in {{'created','override_env'}}, got {source!r}",
            )

    if "expect_agent_comment" in expectations:
        try:
            expect_comment = _as_bool(expectations["expect_agent_comment"])
        except TypeError as exc:
            _check(checks, "expect_agent_comment", False, str(exc))
        else:
            if expect_comment is True:
                # Markers (### TL;DR / ## Remediation) identify the comment in
                # the harness only. Oracle pass/fail is presence of a located
                # comment; asserting marker shape is deferred to a follow-up.
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
        "quarantined": False,
        "run_url": outcome.get("run_url"),
        "status_trigger_url": status_trigger.get("url"),
        "pr_url": outcome.get("pr_url"),
        "checks": checks,
        "agent_invoked": agent_flag,
        "notes": [
            (
                "Live oracle asserts dashboard gate, trigger status contract, observed "
                "status trigger, job execution, agent invocation, and PR comment "
                "presence/absence. Comment-section markers are harness identity only "
                "until a follow-up; never full agent prose."
            ),
            "Promote (#1878) should consume report.pass / summary.json.",
        ],
    }


def load_case_json(testdata_root: Path, case_id: str) -> dict[str, Any] | None:
    """Load checked-in case.json when available."""
    case_path = testdata_root / "cases" / case_id / "case.json"
    if not case_path.is_file():
        return None
    case = _load_json(case_path)
    return case if isinstance(case, dict) else None


def load_case_expectations(testdata_root: Path, case_id: str) -> dict[str, Any] | None:
    """Load expectations from checked-in case.json when available."""
    case = load_case_json(testdata_root, case_id)
    if case is None:
        return None
    expectations = case.get("expectations")
    return expectations if isinstance(expectations, dict) else None


def load_case_trigger(testdata_root: Path, case_id: str) -> dict[str, Any] | None:
    """Load trigger routing contract from checked-in case.json when available."""
    case = load_case_json(testdata_root, case_id)
    if case is None:
        return None
    trigger = case.get("trigger")
    return trigger if isinstance(trigger, dict) else None


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
        "--testdata-root",
        type=Path,
        default=Path("testdata/agentic/estc-pr-buildkite-detective"),
        help="Fixture/case root used to reload checked-in expectations",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=None,
        help="Optional compact summary JSON for promote (#1878) consumers",
    )
    parser.add_argument(
        "--expected-case-id",
        default=None,
        help=(
            "Independent case id from the workflow matrix; must match "
            "outcome.case_id before expectations are loaded"
        ),
    )
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

    quarantine = load_quarantine(args.quarantine_path)
    report = evaluate_outcome(
        outcome,
        quarantine,
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
