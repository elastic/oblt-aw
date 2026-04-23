# Onboarding

## Overview

This folder collects **step-by-step onboarding** for teams that use **OBLT Agentic Workflows** (`oblt-aw`): the control plane in [elastic/oblt-aw](https://github.com/elastic/oblt-aw), consumer entrypoint [oblt-aw-ingress](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/oblt-aw-ingress.yml), and per-repository [Control Plane Dashboard](../operations/control-plane-dashboard.md) behavior.

## Guides

- **[Adopting a new remote agentic workflow](adopting-agentic-workflows.md)** — One **Steps** section: ship the workflow in `elastic/oblt-aw` (steps 1–7), then adopt it in consumer repos (steps 8–9). If the workflow already exists, start at step 8.
- **[Registering resources](registering-a-repository.md)** — Eight **Steps**: feature branch + `active-repositories.json` on `elastic/oblt-aw`, mandatory **`elastic/catalog-info`** token policy (template-driven `workflow_ref`, org-wide permissions union, SHA from `workflow_ref` without ref), merge catalog then merge `oblt-aw`, verify distribute and dashboard, secrets via **`elastic/observability-github-secrets`**, Control Plane opt-in/out.

## References

- [Documentation index](../README.md)
- [Architecture overview](../architecture/overview.md)
- [Multi-organization agentic workflows (design)](../architecture/multi-org-agentic-workflows.md)
