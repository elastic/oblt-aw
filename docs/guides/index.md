---
navigation_title: Guides by role
description: User, operator, and maintainer stories for OBLT Agentic Workflows.
applies_to: {}
---

# Guides by role

These guides answer **who you are** and **what you want to do**. Each page is a short procedure with links to the authoritative docs — not a second copy of workflow behavior or routing rules.

| Audience | When you are… | Stories |
|----------|---------------|---------|
| **User** | A developer or repo owner using agentic workflows in your repository | [User stories](#user-stories) |
| **Operator** | Responsible for the service (for example, answering in `#observability-robots`) | [Operator stories](#operator-stories) |
| **Maintainer** | Contributing to `elastic/oblt-aw` or `elastic/ai-github-actions` | [Maintainer stories](#maintainer-stories) |

## User stories

- [Onboard a repository](user/onboard-a-repository.md) — Open an issue in `elastic/oblt-aw`, merge agent-opened PRs, then enable workflows from the Control Plane Dashboard.
- [Start from scratch](user/start-from-scratch.md) — Short pointer to the issue-driven onboard path (and technical registration).
- [Enable a new workflow](user/enable-a-new-workflow.md) — Turn on a workflow that already exists in the org registry and client templates.
- [Opt in or opt out](user/opt-in-opt-out.md) — Enable or disable workflows from the dashboard and understand runtime gating.
- [Choose Automerge services](user/automerge-services.md) — Review the dependency-update categories that Automerge can merge for your repository.

## Operator stories

- [Troubleshoot an error](operator/troubleshoot-an-error.md) — Structured checklist from a failed workflow run to the right doc.
- [Configure a GitHub secret](operator/configure-a-github-secret.md) — When repository secrets are required versus ephemeral tokens.

## Maintainer stories

- [Add a new agentic workflow](maintainer/add-a-new-agentic-workflow.md) — Ship a new routed workflow on the control plane.
- [Change maturity level](maintainer/change-maturity-level.md) — Update `workflow-registry.json` and dashboard sync behavior.
- [Use GitHub ephemeral tokens](maintainer/use-gh-ephemeral-tokens.md) — `create-token`, OIDC, and token policy fields.
