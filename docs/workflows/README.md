# Workflow Catalog

## Overview

This section provides documentation for each workflow source in [.github/workflows/](../../.github/workflows/) and the distributed client template source file.

## Usage

- CI workflow: [docs/workflows/ci.md](ci.md)
- Shared prelude (dashboard + allow lists): [docs/workflows/aw-prelude.md](aw-prelude.md)
- Dashboard reader (reusable workflow): [docs/workflows/get-enabled-workflows.md](get-enabled-workflows.md)
- PR and issue allow-list loader (reusable workflow): [docs/workflows/load-allowed-authors.md](load-allowed-authors.md)
- Observability client templates (`trigger-oblt-aw-*.yml` under remote-workflow-template): [docs/workflows/oblt-aw-client-template.md](oblt-aw-client-template.md)
- Docs client templates (`trigger-docs-aw-*.yml` under remote-workflow-template): [docs/workflows/docs-aw-client-template.md](docs-aw-client-template.md)
- Docs issue AI menu reusable workflow: [docs/workflows/docs-aw-ai-menu.md](docs-aw-ai-menu.md)
- Docs PR AI menu reusable workflow: [docs/workflows/docs-aw-pr-ai-menu.md](docs-aw-pr-ai-menu.md)
- Agent suggestions workflow: [docs/workflows/oblt-aw-agent-suggestions.md](oblt-aw-agent-suggestions.md)
- Autodoc workflow: [docs/workflows/oblt-aw-autodoc.md](oblt-aw-autodoc.md)
- Automerge workflow: [docs/workflows/oblt-aw-automerge.md](oblt-aw-automerge.md)
- Dependency review workflow: [docs/workflows/oblt-aw-dependency-review.md](oblt-aw-dependency-review.md)
- Duplicate Issue Detector workflow: [docs/workflows/oblt-aw-duplicate-issue-detector.md](oblt-aw-duplicate-issue-detector.md)
- Issue Fixer workflow (generic fix-ready path): [docs/workflows/oblt-aw-issue-fixer.md](oblt-aw-issue-fixer.md)
- Issue Triage workflow (issue opened): [docs/workflows/oblt-aw-issue-triage.md](oblt-aw-issue-triage.md)
- Mention in Issue workflow: [docs/workflows/oblt-aw-mention-in-issue.md](oblt-aw-mention-in-issue.md)
- Resource Not Accessible by Integration detector workflow: [docs/workflows/oblt-aw-resource-not-accessible-by-integration-detector.md](oblt-aw-resource-not-accessible-by-integration-detector.md)
- Resource Not Accessible by Integration triage workflow: [docs/workflows/oblt-aw-resource-not-accessible-by-integration-triage.md](oblt-aw-resource-not-accessible-by-integration-triage.md)
- Resource Not Accessible by Integration fixer workflow: [docs/workflows/oblt-aw-resource-not-accessible-by-integration-fixer.md](oblt-aw-resource-not-accessible-by-integration-fixer.md)
- Security scanning ruleset: [docs/workflows/security-scanning-ruleset.md](security-scanning-ruleset.md)
- Security detector workflow: [docs/workflows/oblt-aw-security-detector.md](oblt-aw-security-detector.md)
- Security triage workflow: [docs/workflows/oblt-aw-security-triage.md](oblt-aw-security-triage.md)
- Security fixer workflow: [docs/workflows/oblt-aw-security-fixer.md](oblt-aw-security-fixer.md)
- Security routing: [docs/routing/security-routing.md](../routing/security-routing.md)
- Security architecture: [docs/architecture/security-agent-architecture.md](../architecture/security-agent-architecture.md)
- Distribution workflow: [docs/workflows/distribute-client-workflow.md](distribute-client-workflow.md)
- Dashboard sync workflow: [docs/workflows/sync-control-plane-dashboard.md](sync-control-plane-dashboard.md)

## References

- Workflow source files: [.github/workflows/](../../.github/workflows/)
- Remote template source: [.github/remote-workflow-template/](../../.github/remote-workflow-template/)
