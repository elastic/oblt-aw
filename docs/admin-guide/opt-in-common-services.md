---
navigation_title: Opt in common services
description: Opt an org into shared agentic workflows defined under config/common without copying workflow bodies.
applies_to: {}
---

# Opt in or out of agentic workflows from other orgs

## Overview

Some agentic workflows are defined once under `config/common/services.json` and kept under the owning org’s route prefix (today: `obs-aw-*`). Other orgs can **offer the same capability in their own catalog** by listing the service id in `include_common`.

Consumers still enable or disable the workflow from the Control Plane dashboard under **that org’s section** (`docs:dependency-review`, not a Common section).

This guide is for **framework maintainers** changing an org’s registry and wiring. Repository users who only tick dashboard checkboxes should use [Enable or disable an agentic workflow](../user-guide/enable-a-new-workflow.md).

## Prerequisites

- The service already exists in [`config/common/services.json`](https://github.com/elastic/oblt-aw/blob/main/config/common/services.json).
- The reusable implementation files listed in that service’s `inner_workflows` already exist (for example `obs-aw-dependency-review.yml`).
- You can change the consuming org’s config, event orchestrators, and remote templates in one PR (CODEOWNERS for that org).

## Opt in (same PR)

Do all of these in **one** pull request for the consuming org. CI runs [`scripts/validate_common_service_opt_in.py`](https://github.com/elastic/oblt-aw/blob/main/scripts/validate_common_service_opt_in.py) and fails if wiring is incomplete.

1. **Registry** — In `config/<org-key>/workflow-registry.json`, add the service id to `include_common` (alphabetical). Do **not** copy the full workflow object into local `workflows` (duplicate ids fail expansion).

   ```json
   {
     "section_title": "Documentation",
     "include_common": ["automerge", "dependency-review"],
     "workflows": []
   }
   ```

2. **Event orchestrators** — For each included service’s `inner_workflows` basenames, update the matching `.github/workflows/<org-key>-aw-event-*.yml` files so that:
   - `run-aw-prelude` / `control-plane-workflows` lists every basename, and
   - a job `uses: ./.github/workflows/<basename>` (the owning org’s reusable) with the usual `shared-proceed` / prelude outputs.

   Example: dependency-review and automerge need the pull-request orchestrator; automerge-deferred needs the schedule (frequent) orchestrator.

3. **Remote triggers** — Under `.github/remote-workflow-template/<org-key>/.github/workflows/`, ensure a `trigger-<org-key>-aw-<event>*.yml` exists for each event family those orchestrators cover (for example `trigger-docs-aw-pull-request.yml`, `trigger-docs-aw-schedule-frequent.yml`). Edit only the remote-template tree; distribute installs consumer copies.

4. **Validate locally**

   ```bash
   python scripts/validate_common_service_opt_in.py
   pre-commit run --files <paths-you-touched>
   ```

5. **After merge** — [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) adds checkboxes under the consuming org’s section. [distribute-client-workflow](../operations/distribute-client-workflow.md) ships new or updated triggers to repos in that org’s `active-repositories.json`.

## Opt out

1. Remove the service id from that org’s `include_common`.
2. Remove the related jobs (and prelude list entries) from that org’s `*-aw-event-*.yml` files when nothing else needs them.
3. Remove remote triggers only if the org no longer needs that event family for any route.
4. Re-run `python scripts/validate_common_service_opt_in.py` and pre-commit on the touched paths.

Dashboard sync drops the checkboxes for repos that still list the org. Existing consumer enablement for removed ids becomes inert after sync.

## What not to do

- Do not add a Common dashboard section or `common:workflow-id` gating ids.
- Do not duplicate the service body into another org’s `workflows` array.
- Do not land `include_common` without orchestrator and trigger wiring in the same PR — the validator blocks that.

## See also

- Architecture: [Multi-org agentic workflows §11](../architecture/multi-org-agentic-workflows.md#11-common-services-shared-definitions-per-org-catalogs)
- [Add a new agentic workflow](add-a-new-agentic-workflow.md) — publishing a brand-new owned workflow
- [Enable or disable an agentic workflow](../user-guide/enable-a-new-workflow.md) — consumer dashboard toggles
