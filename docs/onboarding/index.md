---
navigation_title: Onboarding
description: Long-form onboarding for teams adopting OBLT Agentic Workflows.
applies_to: {}
---

# Onboarding

Long-form onboarding for teams that use **OBLT Agentic Workflows** (`oblt-aw`): the framework in [elastic/oblt-aw](https://github.com/elastic/oblt-aw), per-workflow client templates (`trigger-obs-aw-*.yml`), and per-repository [Control Plane dashboard](../operations/control-plane-dashboard.md) behavior.

Each **organization** owns `config/<org-key>/` (for example `config/obs/`): `workflow-registry.json` and `active-repositories.json`. Ingress and the Control Plane dashboard gate work using compound ids `org-key:workflow-id` (see [multi-org design](../architecture/multi-org-agentic-workflows.md)).

## Prefer the short user stories first

- [Onboard a repository](../user-guide/onboard-a-repository.md) — Developer path: issue form → label → agent PRs → Control Plane dashboard.
- [Get started](../get-started.md) — Ordered onboard → enable → catalog.

## Long-form guides

- [Adopting a new remote agentic workflow](adopting-agentic-workflows.md) — Ship a new routed workflow in the framework and how consumers enable it.
- [Registering resources](registering-a-repository.md) — Technical procedure for maintainers and agents (fleet list, token policy, settings, verification).
