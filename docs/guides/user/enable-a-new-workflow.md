# Enable a new workflow

## Overview

The workflow **already exists** in your org’s `workflow-registry.json`, the control-plane wrappers are shipped, and your repository is registered. You only need to opt in from the Control Plane Dashboard and confirm the event-scoped client for its trigger type is installed.

This guide does **not** cover shipping a **new** workflow on the control plane — that is a maintainer task. See [Add a new agentic workflow](../maintainer/add-a-new-agentic-workflow.md).

## Prerequisites

- Your repository is listed in `config/<org-key>/active-repositories.json` and registration is complete ([Start from scratch](start-from-scratch.md)).
- The workflow appears as a row on your repository’s Control Plane Dashboard after [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md) runs.

## Steps

1. **Confirm the workflow row on the dashboard** — Open the issue labeled `oblt-aw/dashboard`. If the workflow is missing, wait for dashboard sync after a control-plane merge, or ask a maintainer to confirm the workflow is registered in `workflow-registry.json`.

2. **Confirm the event-scoped client is installed** — Workflows share client templates by GitHub event family (for example `trigger-oblt-aw-issues.yml` for `issues` events), not one file per workflow id. Check that the client for your workflow’s trigger type exists under `.github/workflows/`. See the template index in [Client template index](../../workflows/oblt-aw-client-template.md). If it is missing, see [distribute-client-workflow](../../operations/distribute-client-workflow.md).

3. **Configure secrets (if required)** — Read the workflow’s doc under [docs/workflows/](../../workflows/) (for example `oblt-aw-<name>.md`). Some workflows need no repository secrets (for example [oblt-aw-security-detector](../../workflows/oblt-aw-security-detector.md) uses ephemeral tokens only). See [Configure a GitHub secret](../operator/configure-a-github-secret.md).

4. **Check the workflow on the dashboard** — Open the dashboard issue and check the checkbox for the workflow. GitHub saves immediately on click. See [Control Plane Dashboard — enabling a workflow](../../operations/control-plane-dashboard.md#enabling-a-workflow).

5. **Trigger or wait for a client run** — Gating applies on the next client workflow run (`pull_request`, `issues`, `schedule`, and so on). Checking a box does not run workflows immediately. See [get-enabled-workflows](../../workflows/get-enabled-workflows.md).

## See also

- [Opt in or opt out](opt-in-opt-out.md)
- [Control Plane Dashboard — user instructions](../../operations/control-plane-dashboard.md)
- [Client template index](../../workflows/oblt-aw-client-template.md)
- [Adopting a new remote agentic workflow — consumer repositories](../../onboarding/adopting-agentic-workflows.md#consumer-repositories)
