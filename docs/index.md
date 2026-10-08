---
navigation_title: Home
description: Developer docs for OBLT Agentic Workflows (oblt-aw) — onboard a repo, enable agentic workflows, and operate the fleet.
applies_to: {}
---

# OBLT Agentic Workflows (`oblt-aw`)

:::{image} images/oblt-aw-framework-emblem.jpg
:alt: oblt-aw — opinionated agentic framework for Elastic
:width: 720px
:::

**oblt-aw** is an opinionated agentic framework for [GitHub Agentic Workflows](https://github.github.com/gh-aw/) across Elastic repositories.

Agent behavior (what the agent does on an issue or PR) is defined in locked `gh-aw-*` workflows. Some already live in this repository; others still live in [AI GitHub Actions](https://elastic.github.io/ai-github-actions/) and will move here over time. This portal covers how Elastic developers adopt and operate those agents through `oblt-aw`.

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
| [Troubleshooting](troubleshooting/index.md) | Failed runs and common problems |
| [Knowledge base](knowledge-base/index.md) | Agentic Workflows, architecture, release, and QA |
| [Glossary](glossary.md) | Shared terms (framework, control plane, Control Plane dashboard, dependency collection) |
