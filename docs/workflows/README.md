# Workflow Catalog

## Overview

This section provides documentation for each workflow source in [.github/workflows/](../../.github/workflows/) and the distributed client template source file.

## Usage

- CI workflow: [docs/workflows/ci.md](ci.md)

### Job naming (Actions UI readability)

Shared control-plane jobs use **kebab-case, action-oriented** ids with domain context:

| Pattern | Example job ids |
|---------|-----------------|
| Consumer entrypoint | `run-obs-aw-pull-request`, `run-docs-aw-issues` |
| Event orchestrator prelude | `run-aw-prelude` |
| Dashboard read | `read-oblt-aw-dashboard` |
| Allow-list load | `load-oblt-aw-bot-allow-lists` |
| Gate evaluation | `evaluate-workflow-gates` |
| Agentic asset resolve (leaf reusable) | `resolve-agentic-assets` |

Route wrappers keep descriptive ids such as `resolve-apm-assets` and `automerge`. Upstream `gh-aw-*` agent lifecycle jobs (`pre_activation`, `activation`, `agent`) are owned by `elastic/ai-github-actions`.

- Shared prelude (dashboard + allow lists): [docs/workflows/aw-prelude.md](aw-prelude.md)
- Dashboard reader (reusable workflow): [docs/workflows/get-enabled-workflows.md](get-enabled-workflows.md)
- PR and issue allow-list loader (reusable workflow): [docs/workflows/load-allowed-authors.md](load-allowed-authors.md)
- Observability client templates (`trigger-obs-aw-*.yml` under remote-workflow-template): [docs/workflows/obs-aw-client-template.md](obs-aw-client-template.md)
- Docs client templates (`trigger-docs-aw-*.yml` under remote-workflow-template): [docs/workflows/docs-aw-client-template.md](docs-aw-client-template.md)
- Docs issue AI menu reusable workflow: [docs/workflows/docs-aw-ai-menu.md](docs-aw-ai-menu.md)
- Docs PR AI menu reusable workflow: [docs/workflows/docs-aw-pr-ai-menu.md](docs-aw-pr-ai-menu.md)
- Agent suggestions workflow: [docs/workflows/obs-aw-agent-suggestions.md](obs-aw-agent-suggestions.md)
- Autodoc workflow: [docs/workflows/obs-aw-autodoc.md](obs-aw-autodoc.md)
- Automerge workflow: [docs/workflows/obs-aw-automerge.md](obs-aw-automerge.md)
- Dependency review workflow: [docs/workflows/obs-aw-dependency-review.md](obs-aw-dependency-review.md)
- Duplicate Issue Detector workflow: [docs/workflows/obs-aw-duplicate-issue-detector.md](obs-aw-duplicate-issue-detector.md)
- Issue Fixer workflow (generic fix-ready path): [docs/workflows/obs-aw-issue-fixer.md](obs-aw-issue-fixer.md)
- Issue Triage workflow (issue opened): [docs/workflows/obs-aw-issue-triage.md](obs-aw-issue-triage.md)
- Mention in Issue workflow: [docs/workflows/obs-aw-mention-in-issue.md](obs-aw-mention-in-issue.md)
- Resource Not Accessible by Integration detector workflow: [docs/workflows/obs-aw-resource-not-accessible-by-integration-detector.md](obs-aw-resource-not-accessible-by-integration-detector.md)
- Resource Not Accessible by Integration triage workflow: [docs/workflows/obs-aw-resource-not-accessible-by-integration-triage.md](obs-aw-resource-not-accessible-by-integration-triage.md)
- Resource Not Accessible by Integration fixer workflow: [docs/workflows/obs-aw-resource-not-accessible-by-integration-fixer.md](obs-aw-resource-not-accessible-by-integration-fixer.md)
- Security scanning ruleset: [docs/workflows/security-scanning-ruleset.md](security-scanning-ruleset.md)
- Security detector workflow: [docs/workflows/obs-aw-security-detector.md](obs-aw-security-detector.md)
- Security issue superseder workflow: [docs/workflows/obs-aw-security-issue-superseder.md](obs-aw-security-issue-superseder.md)
- Security triage workflow: [docs/workflows/obs-aw-security-triage.md](obs-aw-security-triage.md)
- Security fixer workflow: [docs/workflows/obs-aw-security-fixer.md](obs-aw-security-fixer.md)
- Security routing: [docs/routing/security-routing.md](../routing/security-routing.md)
- Security architecture: [docs/architecture/security-agent-architecture.md](../architecture/security-agent-architecture.md)
- Distribution workflow: [docs/workflows/distribute-client-workflow.md](distribute-client-workflow.md)
- Dashboard sync workflow: [docs/workflows/sync-control-plane-dashboard.md](sync-control-plane-dashboard.md)

## References

- Workflow source files: [.github/workflows/](../../.github/workflows/)
- Remote template source: [.github/remote-workflow-template/](../../.github/remote-workflow-template/)
