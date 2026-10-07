---
navigation_title: Home
description: Developer docs for OBLT Agentic Workflows (oblt-aw) — onboard a repo, enable workflows, and operate the fleet.
applies_to: {}
---

# OBLT Agentic Workflows (`oblt-aw`)

**oblt-aw** is the shared control plane for [GitHub Agentic Workflows](https://github.github.com/gh-aw/) across Elastic repositories. Client triggers are distributed for you; you turn workflows on or off from a Control Plane Dashboard in your repo — not by curl-installing agents one by one.

Upstream agent behavior (what the agent does on an issue or PR) lives in [AI GitHub Actions](https://elastic.github.io/ai-github-actions/). This portal covers how Elastic developers **adopt and operate** those agents through `oblt-aw`.

## Get started

1. [Onboard your repository](guides/user/onboard-a-repository.md) — open one issue in `elastic/oblt-aw`, merge the agent-opened PRs, then use the dashboard.
2. [Enable a workflow](guides/user/enable-a-new-workflow.md) — check the box on the Control Plane Dashboard.
3. [Opt in or opt out](guides/user/opt-in-opt-out.md) — change enablement any time; gating applies on the next matching event.

Full path: [Get started](get-started.md).

## I want to…

| Goal | Guide |
|------|--------|
| Onboard a repository that is not registered yet | [Onboard a repository](guides/user/onboard-a-repository.md) |
| Turn on a workflow that already exists for my org | [Enable a new workflow](guides/user/enable-a-new-workflow.md) |
| Enable or disable workflows from the dashboard | [Opt in or opt out](guides/user/opt-in-opt-out.md) |
| Choose which dependency-update bots Automerge can merge | [Choose Automerge services](guides/user/automerge-services.md) |
| See what workflows do and when they run | [Workflow catalog by outcome](workflows/by-outcome.md) |

## When something fails

| Goal | Guide |
|------|--------|
| Debug a failed workflow run | [Troubleshoot an error](guides/operator/troubleshoot-an-error.md) |
| Decide if a repository secret is required | [Configure a GitHub secret](guides/operator/configure-a-github-secret.md) |

## Maintain the platform

| Goal | Guide |
|------|--------|
| Ship a new routed workflow on the control plane | [Add a new agentic workflow](guides/maintainer/add-a-new-agentic-workflow.md) |
| Change maturity or dashboard sync behavior | [Change maturity level](guides/maintainer/change-maturity-level.md) |
| Use ephemeral tokens and token policies | [Use GitHub ephemeral tokens](guides/maintainer/use-gh-ephemeral-tokens.md) |
| Contribute to `elastic/oblt-aw` | [Contributing](development/contributing.md) |

## Reference

Deep dives for architecture, routing, operations, and testing:

- [Architecture overview](architecture/overview.md)
- [Multi-organization design](architecture/multi-org-agentic-workflows.md)
- [Routing](routing/index.md)
- [Distribution](operations/distribute-client-workflow.md)
- [Control Plane Dashboard](operations/control-plane-dashboard.md)
- [Workflow maturity](operations/workflow-maturity.md)
- [Onboarding (long-form)](onboarding/index.md)
- [How docs publish to Codex](development/codex-publish.md)
