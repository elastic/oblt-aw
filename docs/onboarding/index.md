---
navigation_title: Onboarding
description: Long-form onboarding for teams adopting OBLT Agentic Workflows.
applies_to: {}
---

# Onboarding

Long-form onboarding for teams that use **OBLT Agentic Workflows** (`oblt-aw`): the control plane in [elastic/oblt-aw](https://github.com/elastic/oblt-aw), per-workflow client templates (`trigger-obs-aw-*.yml`), and per-repository [Control Plane Dashboard](../operations/control-plane-dashboard.md) behavior.

Each **organization** owns `config/<org-key>/` (for example `config/obs/`): `workflow-registry.json` and `active-repositories.json`. Ingress and the dashboard gate work using compound ids `org-key:workflow-id` (see [multi-org design](../architecture/multi-org-agentic-workflows.md)).

## Prefer the short user stories first

- [Onboard a repository](../guides/user/onboard-a-repository.md) — Developer path: issue form → label → agent PRs → dashboard.
- [Get started](../get-started.md) — Ordered onboard → enable → catalog.

## Long-form guides

- [Adopting a new remote agentic workflow](adopting-agentic-workflows.md) — Ship a new routed workflow on the control plane and how consumers enable it.
- [Registering resources](registering-a-repository.md) — Technical procedure for maintainers and agents (fleet list, token policy, settings, verification).
