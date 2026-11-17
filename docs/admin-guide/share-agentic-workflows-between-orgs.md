---
navigation_title: Share workflows between orgs
description: Publish an agentic workflow into config/common so other orgs can offer it in their own catalogs.
applies_to: {}
---

# Share agentic workflows between orgs

## Overview

Some agentic workflows are useful to more than one org. The control plane keeps **one definition** under [`config/common/services.json`](https://github.com/elastic/oblt-aw/blob/main/config/common/services.json) and lets each org **opt into its own catalog**. There is no Common dashboard section and no `common:workflow-id` gating id.

This guide is the **owning-org publish** path: move (or add) a service definition into `config/common` so other orgs can reuse the same implementation. Consuming orgs then follow [Opt in or out of agentic workflows from other orgs](opt-in-common-services.md) in their own PRs.

Ship a brand-new owned workflow first with [Add a new agentic workflow](add-a-new-agentic-workflow.md). Share it only when a second org needs the same capability without copying the workflow body.

```mermaid
flowchart LR
  A[Owned route exists] --> B[Add to config/common/services.json]
  B --> C[Owning org include_common]
  C --> D[Validate owning wiring]
  D --> E[Other orgs opt in separately]
```

## Prerequisites

- The reusable implementation already exists under the owning org prefix (today’s pilots use `obs-aw-*`, for example `obs-aw-dependency-review.yml`).
- The owning org already wires that basename in its `*-aw-event-*.yml` orchestrators and remote triggers (same rules as a normal owned route).
- You can change `config/common/services.json` and the owning org’s registry in one PR (`config/common/` CODEOWNERS: `@elastic/observablt-ci`).
- If any `inner_workflows` reusable calls [aw-resolve-agentic-assets](../workflows/aw-resolve-agentic-assets.md), that reusable already accepts `shared-org-key` and forwards it as `org-key` on each resolve call (see `obs-aw-dependency-review.yml` / `obs-aw-estc-pr-buildkite-detective.yml`). Adapt the reusable and its owning-org callers **before** publishing; otherwise consuming orgs that pass `shared-org-key` hit an undeclared input, and omitting it resolves assets for the owning org instead of the consumer.

## Publish (owning org)

Do these in **one** pull request for the owning org. After merge, other orgs opt in separately.

1. **Common catalog** — Add a normal workflow object to `config/common/services.json` under `services` (alphabetical by `id` with peers). Use the same fields as an org registry entry: `id`, `name`, `description`, `maturity`, `default_enabled`, `docs`, `inner_workflows`, and optional `sub_features`.

   Example shape (adapt fields; do not invent new ids here):

   ```json
   {
     "id": "dependency-review",
     "name": "Dependency Review",
     "description": "Analyzes dependency-update PRs from bots, applies merge-ready labels when criteria are met.",
     "maturity": "stable",
     "default_enabled": false,
     "docs": "docs/workflows/obs-aw-dependency-review.md",
     "inner_workflows": ["obs-aw-dependency-review.yml"]
   }
   ```

2. **Owning org registry** — In `config/<owner-org>/workflow-registry.json`:
   - Add the service `id` to `include_common` (alphabetical) if that org should still offer it.
   - Remove the full object from the local `workflows` array if it lived there. Duplicate ids between `include_common` and `workflows` fail expansion.

3. **Keep owning wiring green** — Owning-org event orchestrators must still list every `inner_workflows` basename under `control-plane-workflows` and `uses:` those reusables. Pass `shared-org-key: <owner-org>` on those jobs when the reusable declares that input (same pattern consuming orgs use in the opt-in guide). Remote triggers for those event families must remain under `.github/remote-workflow-template/<owner-org>/`. Do not rename implementation files when publishing; other orgs call the same owning-prefix reusables.

4. **Validate locally**

   ```bash
   python scripts/validate_common_service_opt_in.py
   pre-commit run --files <paths-you-touched>
   ```

5. **After merge** — [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) continues to expand `include_common` into each org’s section only. Consumers enable the workflow as `<org-key>:<workflow-id>` (for example `docs:dependency-review`), not a shared Common id.

## After publish (consuming orgs)

Publishing does **not** enable the workflow for other orgs. Each consuming org lands its own PR that:

1. Lists the service id in that org’s `include_common`.
2. Wires that org’s event orchestrators and remote triggers.

Follow [Opt in or out of agentic workflows from other orgs](opt-in-common-services.md). CI runs the same `validate_common_service_opt_in.py` check and fails if wiring is incomplete.

## What not to do

- Do not add a Common dashboard section or `common:workflow-id` gating ids.
- Do not copy the workflow body into another org’s `workflows` array; point at `config/common` and use `include_common`.
- Do not change the owning-prefix reusable filename solely to make it look “shared” — consumers call the existing basename.
- Do not publish a route that resolves APM assets without a `shared-org-key` input wired through to `aw-resolve-agentic-assets`.
- Do not fold a second org’s opt-in into the publish PR unless that org’s CODEOWNERS deliberately review the same change set.

## See also

- Architecture: [Multi-org agentic workflows §11](../architecture/multi-org-agentic-workflows.md#common-services)
- [Add a new agentic workflow](add-a-new-agentic-workflow.md) — ship a new owned route before sharing
- [Opt in or out of agentic workflows from other orgs](opt-in-common-services.md) — consuming-org wiring
- [Enable or disable an agentic workflow](../user-guide/enable-a-new-workflow.md) — consumer dashboard toggles
