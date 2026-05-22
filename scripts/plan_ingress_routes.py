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

"""
Route planning for oblt-aw-ingress dynamic dispatch.

Evaluates the same gates as legacy per-job ``if:`` conditions in oblt-aw-ingress.yml
and returns only workflow routes that should run for the current event.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Literal

from common import write_outputs

ORG_PREFIX = "obs:"

IssueAssociation = Literal["OWNER", "MEMBER", "COLLABORATOR"]

SUPPORTED_EVENT_ACTIONS: dict[str, frozenset[str]] = {
    "issues": frozenset({"opened", "labeled"}),
    "issue_comment": frozenset({"created"}),
    "pull_request": frozenset({"opened", "synchronize", "reopened", "labeled"}),
}

SUPPORTED_TOP_LEVEL_EVENTS = frozenset(
    {
        "schedule",
        "workflow_call",
        "workflow_dispatch",
        "status",
        "issues",
        "issue_comment",
        "pull_request",
    }
)


@dataclass(frozen=True)
class RoutePlanContext:
    """Inputs required to evaluate ingress route eligibility."""

    event_name: str
    event_action: str
    effective_raw: str
    enabled_workflows: list[str]
    allowed_pr_authors: list[str]
    allowed_issue_authors: list[str]
    pull_request_user_login: str
    pull_request_labels: list[str]
    issue_labels: list[str]
    issue_is_pull_request: bool
    comment_body: str
    comment_author_association: str
    status_state: str
    status_context: str
    labeled_label_name: str


@dataclass(frozen=True)
class RoutePlanResult:
    """Planned routes and trigger metadata for ingress."""

    routes: list[str]
    unsupported_trigger: bool
    summary_lines: list[str]

    @property
    def has_routes(self) -> bool:
        return bool(self.routes)


def _dashboard_allows(route_id: str, ctx: RoutePlanContext) -> bool:
    if ctx.effective_raw == "":
        return True
    compound = f"{ORG_PREFIX}{route_id}"
    return compound in ctx.enabled_workflows


def _labels_csv(labels: list[str]) -> str:
    return ",".join(labels)


def _contains_label(labels: list[str], needle: str) -> bool:
    return needle in labels


def _contains_label_prefix(labels: list[str], prefix: str) -> bool:
    joined = _labels_csv(labels)
    return prefix in joined


def _author_in_list(login: str, allowed: list[str]) -> bool:
    return login in allowed


def _comment_starts_with(body: str, prefix: str) -> bool:
    return body.startswith(prefix)


def _association_allowed(association: str) -> bool:
    return association in {"OWNER", "MEMBER", "COLLABORATOR"}


def is_supported_trigger(ctx: RoutePlanContext) -> bool:
    if ctx.event_name not in SUPPORTED_TOP_LEVEL_EVENTS:
        return False
    if ctx.event_name == "issues":
        return ctx.event_action in SUPPORTED_EVENT_ACTIONS["issues"]
    if ctx.event_name == "issue_comment":
        return ctx.event_action in SUPPORTED_EVENT_ACTIONS["issue_comment"]
    if ctx.event_name == "pull_request":
        return ctx.event_action in SUPPORTED_EVENT_ACTIONS["pull_request"]
    return True


def _evaluate_agent_suggestions(ctx: RoutePlanContext) -> bool:
    return ctx.event_name == "schedule" and _dashboard_allows("agent-suggestions", ctx)


def _evaluate_autodoc(ctx: RoutePlanContext) -> bool:
    return ctx.event_name == "schedule" and _dashboard_allows("autodoc", ctx)


def _evaluate_automerge(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "pull_request"
        and ctx.event_action in {"opened", "synchronize", "reopened", "labeled"}
        and _author_in_list(ctx.pull_request_user_login, ctx.allowed_pr_authors)
        and _contains_label(ctx.pull_request_labels, "oblt-aw/ai/merge-ready")
        and _dashboard_allows("automerge", ctx)
    )


def _evaluate_dependency_review(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "pull_request"
        and ctx.event_action in {"opened", "synchronize", "reopened"}
        and _author_in_list(ctx.pull_request_user_login, ctx.allowed_pr_authors)
        and _dashboard_allows("dependency-review", ctx)
    )


def _evaluate_duplicate_issue_detector(ctx: RoutePlanContext) -> bool:
    return (
        (ctx.event_name == "issues" and ctx.event_action == "opened")
        or ctx.event_name == "workflow_dispatch"
    ) and _dashboard_allows("duplicate-issue-detector", ctx)


def _evaluate_issue_triage(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "issues"
        and ctx.event_action == "opened"
        and _dashboard_allows("issue-triage", ctx)
    )


def _evaluate_issue_fixer(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "issue_comment"
        and ctx.event_action == "created"
        and not ctx.issue_is_pull_request
        and _comment_starts_with(ctx.comment_body, "/ai implement")
        and _association_allowed(ctx.comment_author_association)
        and not _contains_label_prefix(ctx.issue_labels, "oblt-aw/triage/security-")
        and not _contains_label_prefix(
            ctx.issue_labels, "oblt-aw/triage/res-not-accessible-by-integration"
        )
        and _dashboard_allows("issue-fixer", ctx)
    )


def _evaluate_mention_in_issue(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "issue_comment"
        and ctx.event_action == "created"
        and not ctx.issue_is_pull_request
        and _comment_starts_with(ctx.comment_body, "/ai")
        and not _comment_starts_with(ctx.comment_body, "/ai implement")
        and _association_allowed(ctx.comment_author_association)
        and _dashboard_allows("mention-in-issue", ctx)
    )


def _evaluate_res_not_accessible_detector(ctx: RoutePlanContext) -> bool:
    return ctx.event_name == "schedule" and _dashboard_allows(
        "resource-not-accessible-by-integration", ctx
    )


def _evaluate_res_not_accessible_fixer(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "issues"
        and ctx.event_action == "labeled"
        and ctx.labeled_label_name == "oblt-aw/ai/fix-ready"
        and _contains_label_prefix(
            ctx.issue_labels, "oblt-aw/triage/res-not-accessible-by-integration"
        )
        and _dashboard_allows("resource-not-accessible-by-integration", ctx)
    )


def _evaluate_res_not_accessible_triage(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "issues"
        and (
            (
                ctx.event_action == "opened"
                and _contains_label(
                    ctx.issue_labels,
                    "oblt-aw/detector/res-not-accessible-by-integration",
                )
            )
            or (
                ctx.event_action == "labeled"
                and ctx.labeled_label_name
                == "oblt-aw/detector/res-not-accessible-by-integration"
            )
        )
        and _dashboard_allows("resource-not-accessible-by-integration", ctx)
    )


def _evaluate_security_detector(ctx: RoutePlanContext) -> bool:
    return ctx.event_name in {"schedule", "workflow_dispatch"} and _dashboard_allows(
        "security", ctx
    )


def _evaluate_security_fixer(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "issues"
        and ctx.event_action == "labeled"
        and (
            (
                ctx.labeled_label_name == "oblt-aw/ai/fix-ready"
                and _contains_label_prefix(ctx.issue_labels, "oblt-aw/triage/security-")
            )
            or (
                ctx.labeled_label_name.startswith("oblt-aw/triage/security-")
                and _contains_label(ctx.issue_labels, "oblt-aw/ai/fix-ready")
            )
        )
        and _dashboard_allows("security", ctx)
    )


def _evaluate_security_triage(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "issues"
        and (
            (
                ctx.event_action == "opened"
                and _contains_label(ctx.issue_labels, "oblt-aw/detector/security")
            )
            or (
                ctx.event_action == "labeled"
                and ctx.labeled_label_name == "oblt-aw/detector/security"
            )
        )
        and _dashboard_allows("security", ctx)
    )


def _evaluate_estc_pr_buildkite_detective(ctx: RoutePlanContext) -> bool:
    return (
        ctx.event_name == "status"
        and ctx.status_state == "failure"
        and "buildkite" in ctx.status_context
        and _dashboard_allows("estc-pr-buildkite-detective", ctx)
    )


# Stable dispatch order (matches workflow-registry.json ordering).
ROUTE_EVALUATORS: tuple[tuple[str, Any], ...] = (
    ("agent-suggestions", _evaluate_agent_suggestions),
    ("autodoc", _evaluate_autodoc),
    ("automerge", _evaluate_automerge),
    ("dependency-review", _evaluate_dependency_review),
    ("duplicate-issue-detector", _evaluate_duplicate_issue_detector),
    ("issue-triage", _evaluate_issue_triage),
    ("issue-fixer", _evaluate_issue_fixer),
    ("mention-in-issue", _evaluate_mention_in_issue),
    (
        "resource-not-accessible-by-integration-detector",
        _evaluate_res_not_accessible_detector,
    ),
    (
        "resource-not-accessible-by-integration-fixer",
        _evaluate_res_not_accessible_fixer,
    ),
    (
        "resource-not-accessible-by-integration-triage",
        _evaluate_res_not_accessible_triage,
    ),
    ("security-detector", _evaluate_security_detector),
    ("security-fixer", _evaluate_security_fixer),
    ("security-triage", _evaluate_security_triage),
    ("estc-pr-buildkite-detective", _evaluate_estc_pr_buildkite_detective),
)


def plan_routes(ctx: RoutePlanContext) -> RoutePlanResult:
    """Return route ids that should run and whether the trigger is unsupported."""
    unsupported = not is_supported_trigger(ctx)
    if unsupported:
        return RoutePlanResult(
            routes=[],
            unsupported_trigger=True,
            summary_lines=[
                f"unsupported trigger: event={ctx.event_name} action={ctx.event_action}",
            ],
        )

    routes: list[str] = []
    summary: list[str] = []
    for route_id, evaluator in ROUTE_EVALUATORS:
        if evaluator(ctx):
            routes.append(route_id)
            summary.append(f"eligible: {route_id}")

    if not routes:
        summary.append("no routes eligible for this event")

    return RoutePlanResult(
        routes=routes,
        unsupported_trigger=False,
        summary_lines=summary,
    )


def parse_enabled_workflows(raw: str) -> list[str]:
    if not raw.strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise SystemExit("enabled-workflows must be a JSON array")
    return [str(item) for item in data]


def parse_author_list(raw: str) -> list[str]:
    if not raw.strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise SystemExit("author list must be a JSON array")
    return [str(item) for item in data]


def parse_labels_csv(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes"}


def context_from_env(environ: dict[str, str]) -> RoutePlanContext:
    """Build planning context from environment variables set by the workflow."""
    return RoutePlanContext(
        event_name=environ.get("EVENT_NAME", ""),
        event_action=environ.get("EVENT_ACTION", ""),
        effective_raw=environ.get("EFFECTIVE_RAW", ""),
        enabled_workflows=parse_enabled_workflows(
            environ.get("ENABLED_WORKFLOWS_JSON", "[]")
        ),
        allowed_pr_authors=parse_author_list(
            environ.get("ALLOWED_PR_AUTHORS_JSON", "[]")
        ),
        allowed_issue_authors=parse_author_list(
            environ.get("ALLOWED_ISSUE_AUTHORS_JSON", "[]")
        ),
        pull_request_user_login=environ.get("PR_USER_LOGIN", ""),
        pull_request_labels=parse_labels_csv(environ.get("PR_LABELS_CSV", "")),
        issue_labels=parse_labels_csv(environ.get("ISSUE_LABELS_CSV", "")),
        issue_is_pull_request=parse_bool(environ.get("ISSUE_IS_PULL_REQUEST", "false")),
        comment_body=environ.get("COMMENT_BODY", ""),
        comment_author_association=environ.get("COMMENT_AUTHOR_ASSOCIATION", ""),
        status_state=environ.get("STATUS_STATE", ""),
        status_context=environ.get("STATUS_CONTEXT", ""),
        labeled_label_name=environ.get("LABELED_LABEL_NAME", ""),
    )


def run_plan_cli() -> None:
    """Write planned routes to GITHUB_OUTPUT (ingress plan-routes job)."""
    ctx = context_from_env({key: value for key, value in os.environ.items()})
    result = plan_routes(ctx)

    write_outputs(
        {
            "routes": json.dumps(result.routes),
            "has-routes": "true" if result.has_routes else "false",
            "unsupported-trigger": "true" if result.unsupported_trigger else "false",
        }
    )

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [
            "## Planned oblt-aw routes",
            "",
            f"- Event: `{ctx.event_name}` / `{ctx.event_action}`",
            f"- Routes: `{json.dumps(result.routes)}`",
            f"- Unsupported trigger: `{result.unsupported_trigger}`",
            "",
        ]
        lines.extend(f"- {line}" for line in result.summary_lines)
        with open(summary_path, "a", encoding="utf-8") as summary_file:
            summary_file.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    try:
        run_plan_cli()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"plan_ingress_routes failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
