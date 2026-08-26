# Troubleshoot an error

## Overview

Use this checklist when a workflow run fails or a user reports that agentic workflows are not running. Work through the steps in order; each step points to the doc that owns the behavior.

## Prerequisites

- A GitHub Actions workflow run URL (or enough detail to find it: repository, workflow name, time).
- Read access to the consumer repository and, when the failure is in control-plane reusables, `elastic/oblt-aw`.

## Steps

1. **Identify where the run lives** — Open the run URL.
   - **Consumer repo** (`trigger-obs-aw-*.yml`): start with the client template and event orchestrator. See [Client template index](../../workflows/obs-aw-client-template.md).
   - **`elastic/oblt-aw`**: control-plane operation (distribution, dashboard sync, CI). See [docs/workflows/](../../workflows/) for the matching workflow doc.

2. **Check dashboard gating** — If jobs were skipped or `shared-proceed` is false, the workflow may not be enabled on the Control Plane Dashboard.
   - Confirm an open dashboard issue exists and the workflow checkbox is checked. See [Control Plane Dashboard](../../operations/control-plane-dashboard.md).
   - Review [get-enabled-workflows](../../workflows/get-enabled-workflows.md) and [aw-prelude](../../workflows/aw-prelude.md) outputs (`effective-raw`, `enabled-workflows`, `proceed-by-workflow`).

3. **Check registration and distribution** — For new or recently registered repositories:
   - Repository listed in `config/<org-key>/active-repositories.json`? See [Registering resources](../../onboarding/registering-a-repository.md).
   - Client templates installed via [distribute-client-workflow](../../operations/distribute-client-workflow.md)?
   - Dashboard issue created via [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md)?

4. **Check permissions, OIDC, and ephemeral tokens** — Failures on `create-token` or OIDC often mean:
   - `workflow_ref` in the catalog token policy does not match the client workflow file path.
   - The client `run-obs-aw-<event>` job is missing `id-token: write`. See [Client template index](../../workflows/obs-aw-client-template.md).
   - Catalog policy was not merged before the `oblt-aw` registration merge.

   Registration troubleshooting: [Registering resources — troubleshooting](../../onboarding/registering-a-repository.md#troubleshooting). Maintainer detail: [Use GitHub ephemeral tokens](../maintainer/use-gh-ephemeral-tokens.md).

5. **Check workflow-specific conditions** — After prelude gating, each route applies its own labels, comments, or allow lists. Open the workflow doc and routing doc:
   - Workflow catalog: [docs/workflows/README.md](../../workflows/README.md)
   - Routing index: [docs/routing/README.md](../../routing/README.md)

6. **Check secrets** — If the workflow doc declares repository secrets, confirm they are provisioned via [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets). See [Configure a GitHub secret](configure-a-github-secret.md).

## See also

- [Registering resources — troubleshooting](../../onboarding/registering-a-repository.md#troubleshooting)
- [Adopting a new remote agentic workflow — troubleshooting](../../onboarding/adopting-agentic-workflows.md#troubleshooting)
- [Control Plane Dashboard — default behavior](../../operations/control-plane-dashboard.md#default-behavior)
- [Guides by role](../README.md)
