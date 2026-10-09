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

## Problems it solves

Today many teams still wire each agent by hand in every repo (local workflow → `gh-aw-*.lock.yml`). That does not scale. **oblt-aw** mitigates:

- **Copy-paste setup** in every repo (triggers, secrets, permissions).
- **No shared on/off switch**, so fleet behavior drifts.
- **Expensive updates** — chase N repos to change the same agent.
- **Slow rollouts** — every repo reinvents install and enablement.
- **Unsustainable management** as repos and agents grow.

## Features and benefits

- **Automatic client distribution** — no hand-copying entrypoints; [distribution](operations/distribute-client-workflow.md) installs/updates `trigger-obs-aw-*.yml` ([client template](workflows/obs-aw-client-template.md), [adopting workflows](onboarding/adopting-agentic-workflows.md)).
- **Self-service Control Plane dashboard** — enable/disable with checkboxes on `[oblt-aw] Control Plane Dashboard` ([Control Plane dashboard](operations/control-plane-dashboard.md), [enable or disable](user-guide/enable-a-new-workflow.md)).
- **Control plane (prelude)** — same Control Plane dashboard gating and allow lists before every agent run ([aw-prelude](workflows/aw-prelude.md)).
- **Shared agentic assets** — resolved in the framework ([aw-resolve-agentic-assets](workflows/aw-resolve-agentic-assets.md)).
- **Update once, reach the fleet** — improve in `oblt-aw`; [distribution](operations/distribute-client-workflow.md) refreshes clients across active repos.
- **Quieter PRs** — narrow triggers; only matching routes run ([split-trigger](architecture/overview.md#split-trigger-vs-monolithic-ingress)).
- **Catalog with maturity** — registered workflows with clear maturity levels ([workflows index](workflows/index.md), [maturity](operations/workflow-maturity.md)).
- **Clear ownership** — shared core in one repo; per-org data under `config/<org-key>/` ([onboard a repo](user-guide/onboard-a-repository.md), [technical registration](onboarding/registering-a-repository.md)).

## How it works

Agent behavior (what the agent does on an issue or PR) is defined in locked `gh-aw-*` workflows. Some already live in this repository; others still live in [AI GitHub Actions](https://elastic.github.io/ai-github-actions/) and will move here over time. This portal covers how Elastic developers adopt and operate those agents through `oblt-aw`.

In simplified form:

1. Clients (`trigger-<org-key>-aw-*.yml`) are **installed** using [automated distribution](operations/distribute-client-workflow.md) ([Observability client template](workflows/obs-aw-client-template.md), [Docs client template](workflows/docs-aw-client-template.md)).
2. On a matching event, the client calls [elastic/oblt-aw](https://github.com/elastic/oblt-aw).
3. [Prelude](workflows/aw-prelude.md) checks the [Control Plane dashboard](operations/control-plane-dashboard.md).
4. If enabled, the route runs its pinned implementation — an in-repo or upstream `gh-aw-*` lock, a Docs Actions reusable, or a deterministic framework workflow.

See the [architecture overview](architecture/overview.md).

## Get started

1. [Onboard your repository](user-guide/onboard-a-repository.md) — open one issue in `elastic/oblt-aw`, merge the agent-opened PRs, then use the Control Plane dashboard.
2. [Enable or disable an agentic workflow](user-guide/enable-a-new-workflow.md) — check or uncheck the box on the Control Plane dashboard; gating applies on the next matching event.

Continue to the full [Get started](get-started.md) guide.

## Guides

| Section | Audience |
|---------|----------|
| [User guide](user-guide/index.md) | Developers and target repository owners (onboard, enable, Automerge, catalog) |
| [Admin guide](admin-guide/index.md) | Framework maintainers who change `elastic/oblt-aw` |
| [Troubleshooting](troubleshooting/index.md) | Failed runs and common problems |
| [Knowledge base](knowledge-base/index.md) | Agentic Workflows, architecture, release, and QA |
| [Glossary](glossary.md) | Shared terms (framework, control plane, Control Plane dashboard, dependency collection) |
