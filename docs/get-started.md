---
navigation_title: Get started
description: Onboard a repository and enable OBLT Agentic Workflows from the Control Plane Dashboard.
applies_to: {}
---

# Get started

Use this path if you are an Elastic developer and want agentic workflows in a repository through **oblt-aw** (not a per-repo curl install of upstream agents).

## 1. Onboard the repository

If the repository is **not** listed in `config/<org-key>/active-repositories.json` yet:

1. Open an **Onboard a repository** issue in [elastic/oblt-aw](https://github.com/elastic/oblt-aw/issues).
2. Wait for the agent checklist and merge the opened PRs in the documented order (catalog TokenPolicy before `oblt-aw` registration).
3. After registration merges, merge the client-template install PR in your repository and confirm the Control Plane Dashboard issue exists.

Details: [Onboard a repository](guides/user/onboard-a-repository.md).

If the repository is **already** registered, skip to step 2. Short pointer: [Start from scratch](guides/user/start-from-scratch.md).

## 2. Enable workflows

1. Open the `[oblt-aw] Control Plane Dashboard` issue in your repository (label `oblt-aw/dashboard`).
2. Confirm the event-scoped client for the workflow’s trigger family is installed under `.github/workflows/` (for example `trigger-obs-aw-pull-request.yml`).
3. Check the workflow row. GitHub saves on click; the next matching event applies gating.

Details: [Enable a new workflow](guides/user/enable-a-new-workflow.md) and [Opt in or opt out](guides/user/opt-in-opt-out.md).

## 3. Pick what you need

Browse workflows by day-to-day outcome (issues, PRs, security, automerge): [Workflow catalog by outcome](workflows/by-outcome.md).

For Automerge categories: [Choose Automerge services](guides/user/automerge-services.md).

## Where to get help

- Failed run: [Troubleshoot an error](guides/operator/troubleshoot-an-error.md)
- Slack: `#observability-robots` (operators and maintainers)
