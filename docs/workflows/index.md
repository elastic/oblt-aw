---
navigation_title: Workflow documentation index
description: Alphabetical index of every workflow document under docs/workflows.
applies_to: {}
---

# Workflow documentation index

Alphabetical index of every workflow document under `docs/workflows/` (framework sources and client templates). Prefer [Catalog by outcome](../knowledge-base/agentic-workflows/by-outcome.md) if you are choosing what to enable.

## Job naming (Actions UI)

Shared framework jobs use **kebab-case, action-oriented** ids with domain context:

| Pattern | Example job ids |
|---------|-----------------|
| Consumer entrypoint | `run-obs-aw-pull-request`, `run-docs-aw-issues` |
| Event orchestrator prelude | `run-aw-prelude` |
| Control Plane dashboard read | `read-oblt-aw-dashboard` |
| Allow-list load | `load-oblt-aw-bot-allow-lists` |
| Gate evaluation | `evaluate-workflow-gates` |
| Agentic asset resolve (leaf reusable) | `resolve-agentic-assets` |

## Index

- [Agentic maintenance](agentics-maintenance.md)
- [Agent suggestions](obs-aw-agent-suggestions.md)
- [Allow-list loader](load-allowed-authors.md)
- [APM CLI version sync](aw-sync-apm-version.md)
- [Autodoc](obs-aw-autodoc.md)
- [Automerge](obs-aw-automerge.md)
- [Automerge deferred](obs-aw-automerge-deferred.md)
- [CI](ci.md)
- [Codex preview](codex-preview.md)
- [Codex preview cleanup](codex-preview-cleanup.md)
- [Compiler upgrade](compiler-upgrade.md)
- [Compiler upgrade (Observability)](obs-aw-compiler-upgrade.md)
- [Control Plane dashboard audit](aw-dashboard-audit.md)
- [Control Plane dashboard reader](get-enabled-workflows.md)
- [Control Plane dashboard sync](sync-control-plane-dashboard.md)
- [Create PR from issue agentic workflow](gh-aw-create-pr-from-issue.md)
- [Dependency review](obs-aw-dependency-review.md)
- [Dependency review source](gh-aw-dependency-review.md)
- [Distribution](distribute-client-workflow.md)
- [Duplicate Issue Detector](obs-aw-duplicate-issue-detector.md)
- [Docs client templates](docs-aw-client-template.md)
- [Docs issue AI menu](docs-aw-ai-menu.md)
- [Docs issue-comment event router](docs-aw-event-issue-comment.md)
- [Docs issues event router](docs-aw-event-issues.md)
- [Docs patrol source](gh-aw-docs-patrol.md)
- [Docs PR AI menu](docs-aw-pr-ai-menu.md)
- [Docs PR AI menu collector](docs-aw-pr-ai-menu-collect.md)
- [Docs pull-request event router](docs-aw-event-pull-request.md)
- [Docs workflow-run event router](docs-aw-event-workflow-run.md)
- [E2E all-workflow orchestrator](e2e-all.md)
- [E2E autodoc audit](e2e-autodoc.md)
- [E2E automerge VM images](e2e-automerge-vm-images.md)
- [E2E dependency-review Actions fixture](e2e-dependency-review-actions-fixture.md)
- [E2E dependency review](e2e-dependency-review.md)
- [E2E ESTC Buildkite detective](e2e-estc-pr-buildkite-detective.md)
- [E2E Observability schedule dispatcher](e2e-trigger-obs-aw-schedule.md)
- [E2E PR Actions detective](e2e-pr-actions-detective.md)
- [E2E PR Actions detective intentional failure](e2e-pr-actions-detective-fail.md)
- [Issue Fixer](obs-aw-issue-fixer.md)
- [Issue Triage](obs-aw-issue-triage.md)
- [Mention in Issue](obs-aw-mention-in-issue.md)
- [Observability client templates](obs-aw-client-template.md)
- [Observability issue-comment event router](obs-aw-event-issue-comment.md)
- [Observability issues event router](obs-aw-event-issues.md)
- [Observability pull-request event router](obs-aw-event-pull-request.md)
- [Observability schedule event router](obs-aw-event-schedule.md)
- [Observability status event router](obs-aw-event-status.md)
- [Observability workflow-run event router](obs-aw-event-workflow-run.md)
- [Onboard repository (in-repo only)](gh-aw-onboard-repository.md)
- [PR Actions Detective](obs-aw-pr-actions-detective.md)
- [PR Buildkite Detective](obs-aw-estc-pr-buildkite-detective.md)
- [Release promote](aw-release-promote.md)
- [Release rollback](aw-release-rollback.md)
- [Resolve agentic assets](aw-resolve-agentic-assets.md)
- [Resource Not Accessible detector](obs-aw-resource-not-accessible-by-integration-detector.md)
- [Resource Not Accessible fixer](obs-aw-resource-not-accessible-by-integration-fixer.md)
- [Resource Not Accessible triage](obs-aw-resource-not-accessible-by-integration-triage.md)
- [Security detector](obs-aw-security-detector.md)
- [Security fixer](obs-aw-security-fixer.md)
- [Security issue superseder](obs-aw-security-issue-superseder.md)
- [Security scanning ruleset](security-scanning-ruleset.md)
- [Security triage](obs-aw-security-triage.md)
- [Shared prelude](aw-prelude.md)
