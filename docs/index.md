---
navigation_title: Home
description: Developer docs for OBLT Agentic Workflows (oblt-aw) — onboard a repo, enable workflows, and operate the fleet.
applies_to: {}
---

# OBLT Agentic Workflows (`oblt-aw`)

**oblt-aw** is the shared control plane for [GitHub Agentic Workflows](https://github.github.com/gh-aw/) across Elastic repositories. Client triggers are distributed for you; you turn workflows on or off from a Control Plane Dashboard in your repo — not by curl-installing agents one by one.

Upstream agent behavior (what the agent does on an issue or PR) lives in [AI GitHub Actions](https://elastic.github.io/ai-github-actions/). This portal covers how Elastic developers **adopt and operate** those agents through `oblt-aw`.

## Get started

1. [Onboard your repository](user-guide/onboard-a-repository.md) — open one issue in `elastic/oblt-aw`, merge the agent-opened PRs, then use the dashboard.
2. [Enable a workflow](user-guide/enable-a-new-workflow.md) — check the box on the Control Plane Dashboard.
3. [Opt in or opt out](user-guide/opt-in-opt-out.md) — change enablement any time; gating applies on the next matching event.

Full path: [Get started](get-started.md).

## Guides

| Section | Audience |
|---------|----------|
| [User guide](user-guide/index.md) | Developers and repo owners (onboard, enable, Automerge, catalog) |
| [Admin guide](admin-guide/index.md) | Maintainers who change the control plane |
| [Troubleshooting](troubleshooting/index.md) | Failed runs and secrets |
| [Knowledge base](knowledge-base/index.md) | Architecture, reference, and Frequently Asked Problems |
