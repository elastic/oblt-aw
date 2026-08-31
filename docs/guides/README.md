# Guides by role

## Overview

These guides answer **who you are** and **what you want to do** with OBLT Agentic Workflows (`oblt-aw`). Each page is a short procedure with links to the authoritative docs — not a second copy of workflow behavior or routing rules.

Pick your audience:

| Audience | When you are… | Stories |
|----------|---------------|---------|
| **User** | A developer or repo owner using agentic workflows in your repository | [User stories](user/) |
| **Operator** | Responsible for the service (for example, answering in `#observability-robots`) | [Operator stories](operator/) |
| **Maintainer** | Contributing to `elastic/oblt-aw` or `elastic/ai-github-actions` | [Maintainer stories](maintainer/) |

## User stories

- [Start from scratch](user/start-from-scratch.md) — Register a repository, receive client templates, and enable workflows from the Control Plane Dashboard.
- [Enable a new workflow](user/enable-a-new-workflow.md) — Turn on a workflow that already exists in the org registry and client templates.
- [Opt in or opt out](user/opt-in-opt-out.md) — Enable or disable workflows from the dashboard and understand runtime gating.

## Operator stories

- [Troubleshoot an error](operator/troubleshoot-an-error.md) — Structured checklist from a failed workflow run to the right doc.
- [Configure a GitHub secret](operator/configure-a-github-secret.md) — When repository secrets are required versus ephemeral tokens.

## Maintainer stories

- [Add a new agentic workflow](maintainer/add-a-new-agentic-workflow.md) — Ship a new routed workflow on the control plane.
- [Change maturity level](maintainer/change-maturity-level.md) — Update `workflow-registry.json` and dashboard sync behavior.
- [Use GitHub ephemeral tokens](maintainer/use-gh-ephemeral-tokens.md) — `create-token`, OIDC, and token policy fields.
- [Test mint ephemeral lock tokens](maintainer/test-mint-ephemeral-lock-tokens.md) — Throwaway PR workflow to validate in-lock minting before merge.

## References

- [Documentation index](../README.md)
- [Onboarding (long-form guides)](../onboarding/README.md)
- [Contributing to oblt-aw](../development/contributing.md)
