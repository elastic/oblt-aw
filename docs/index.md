---
navigation_title: Home
description: Developer docs for OBLT Agentic Workflows (oblt-aw) — onboard a repo, enable agentic workflows, and operate the fleet.
applies_to: {}
---

# OBLT Agentic Workflows (`oblt-aw`)

:::{image} images/oblt-aw-framework-emblem.jpg
:alt: oblt-aw — opinionated agentic framework for Elastic
:width: 420px
:::

**oblt-aw** is an opinionated agentic framework for [GitHub Agentic Workflows](https://github.github.com/gh-aw/) across Elastic repositories. It distributes client triggers and routed workflows; the **control plane** is how you configure and gate them (Control Plane dashboard, opt-in/opt-out, audit, and prelude verification).

Upstream agent behavior (what the agent does on an issue or PR) lives in [AI GitHub Actions](https://elastic.github.io/ai-github-actions/). This portal covers how Elastic developers **adopt and operate** those agents through `oblt-aw`.

Shared vocabulary (framework vs control plane vs Control Plane dashboard): [Glossary](glossary.md).

## Get started

1. [Onboard your repository](user-guide/onboard-a-repository.md) — open one issue in `elastic/oblt-aw`, merge the agent-opened PRs, then use the Control Plane dashboard.
2. [Enable or disable an agentic workflow](user-guide/enable-a-new-workflow.md) — check or uncheck the box on the Control Plane dashboard; gating applies on the next matching event.

Continue to the full [Get started](get-started.md) guide.

## Guides

| Section | Audience |
|---------|----------|
| [User guide](user-guide/index.md) | Developers and repo owners (onboard, enable, Automerge, catalog) |
| [Admin guide](admin-guide/index.md) | Maintainers who change the framework |
| [Troubleshooting](troubleshooting/index.md) | Failed runs and secrets |
| [Knowledge base](knowledge-base/index.md) | Architecture and Frequently Asked Problems |
| [Glossary](glossary.md) | Shared terms (framework, control plane, Control Plane dashboard) |
