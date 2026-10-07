---
navigation_title: Filename index
description: Filename-oriented index of every workflow source documented under docs/workflows.
applies_to: {}
---

# Workflow catalog (filename index)

Documentation for each workflow source in [.github/workflows/](https://github.com/elastic/oblt-aw/tree/main/.github/workflows) and the distributed client template source.

**Prefer the outcome view first:** [Catalog by outcome](by-outcome.md).

## Job naming (Actions UI)

Shared control-plane jobs use **kebab-case, action-oriented** ids with domain context:

| Pattern | Example job ids |
|---------|-----------------|
| Consumer entrypoint | `run-obs-aw-pull-request`, `run-docs-aw-issues` |
| Event orchestrator prelude | `run-aw-prelude` |
| Dashboard read | `read-oblt-aw-dashboard` |
| Allow-list load | `load-oblt-aw-bot-allow-lists` |
| Gate evaluation | `evaluate-workflow-gates` |
| Agentic asset resolve (leaf reusable) | `resolve-agentic-assets` |

## All workflow docs

- [Agent suggestions](obs-aw-agent-suggestions.md)
- [Allow-list loader](load-allowed-authors.md)
- [Autodoc](obs-aw-autodoc.md)
- [Automerge](obs-aw-automerge.md)
- [Automerge deferred](obs-aw-automerge-deferred.md)
- [CI](ci.md)
- [Compiler upgrade](compiler-upgrade.md)
- [Compiler upgrade (Observability)](obs-aw-compiler-upgrade.md)
- [Dashboard audit](aw-dashboard-audit.md)
- [Dashboard reader](get-enabled-workflows.md)
- [Dashboard sync](sync-control-plane-dashboard.md)
- [Dependency review](obs-aw-dependency-review.md)
- [Distribution](distribute-client-workflow.md)
- [Docs client templates](docs-aw-client-template.md)
- [Docs issue AI menu](docs-aw-ai-menu.md)
- [Docs PR AI menu](docs-aw-pr-ai-menu.md)
- [Duplicate Issue Detector](obs-aw-duplicate-issue-detector.md)
- [Issue Fixer](obs-aw-issue-fixer.md)
- [Issue Triage](obs-aw-issue-triage.md)
- [Mention in Issue](obs-aw-mention-in-issue.md)
- [Observability client templates](obs-aw-client-template.md)
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
