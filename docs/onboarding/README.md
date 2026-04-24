# Onboarding

## Overview

This folder collects **onboarding** for teams that use **OBLT Agentic Workflows** (`oblt-aw`): the control plane in [elastic/oblt-aw](https://github.com/elastic/oblt-aw), consumer entrypoint [oblt-aw-ingress](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/oblt-aw-ingress.yml), and per-repository [Control Plane Dashboard](../operations/control-plane-dashboard.md) behavior.

Each **organization** owns `config/<org-key>/` (for example `config/obs/`): [`workflow-registry.json`](../../config/obs/workflow-registry.json) and [`active-repositories.json`](../../config/obs/active-repositories.json). Ingress and the dashboard gate work using compound ids `org-key:workflow-id` (see [multi-org design](../architecture/multi-org-agentic-workflows.md)).

## Guides

- **[Adopting a new remote agentic workflow](adopting-agentic-workflows.md)** — How to ship a new routed workflow on the `oblt-aw` control plane (reusable workflows, ingress, registry, docs, client template) and how consumer repositories verify and enable it via the dashboard.

- **[Registering resources](registering-a-repository.md)** — How to list a repository for the fleet (`active-repositories.json`), align Backstage token policy in `elastic/catalog-info`, and complete post-merge verification (distribution, secrets, dashboard).

## References

- [Documentation index](../README.md)
- [Architecture overview](../architecture/overview.md)
- [Multi-organization agentic workflows (design)](../architecture/multi-org-agentic-workflows.md)
