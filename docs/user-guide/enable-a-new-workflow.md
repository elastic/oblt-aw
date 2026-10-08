# Enable or disable an agentic workflow

## Overview

Agentic workflow enablement is controlled **only** through the Control Plane dashboard issue in your repository — not through `active-repositories.json` or config files in the consumer repo.

The agentic workflow **already exists** in your org’s `workflow-registry.json`, the framework wrappers are shipped, your repository is registered, and [distribute-client-workflow](../operations/distribute-client-workflow.md) has installed the event-scoped client triggers. You opt in or out from the Control Plane dashboard.

This guide does **not** cover shipping a **new** agentic workflow in the framework — that is a maintainer task. See [Add a new agentic workflow](../admin-guide/add-a-new-agentic-workflow.md).

## Prerequisites

- Your repository is listed in `config/<org-key>/active-repositories.json` and registration is complete ([Onboard a repository](onboard-a-repository.md)).
- Your repository has an open Control Plane dashboard issue (`label:oblt-aw/dashboard`, title `[oblt-aw] Control Plane Dashboard`).
- The agentic workflow appears as a row on your repository’s Control Plane dashboard after [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) runs.

## Enable an agentic workflow

:::{image} ../images/enable-agentic-workflow.gif
:alt: Open the Control Plane dashboard from the repository Issues page, then enable an agentic workflow
:screenshot:
:::

1. **Confirm the agentic workflow row on the Control Plane dashboard** — Open the issue labeled `oblt-aw/dashboard` (from Issues, or search `label:oblt-aw/dashboard`). If the agentic workflow is missing, wait for Control Plane dashboard sync after a framework merge, or ask a maintainer to confirm it is registered in `workflow-registry.json`.

2. **Configure secrets (if required)** — Read the agentic workflow’s doc under [docs/workflows/](../workflows/index.md) (for example `obs-aw-<name>.md`). Some agentic workflows need no repository secrets (for example [obs-aw-security-detector](../workflows/obs-aw-security-detector.md) uses ephemeral tokens only). See [Configure a GitHub secret](../admin-guide/configure-a-github-secret.md).

3. **Check the agentic workflow on the Control Plane dashboard** — Open the Control Plane dashboard issue and check the checkbox for the agentic workflow. GitHub saves immediately on click. See [Control Plane dashboard — enabling an agentic workflow](../operations/control-plane-dashboard.md#enabling-an-agentic-workflow).

4. **Trigger or wait for a client run** — Gating applies on the next client workflow run (`pull_request`, `issues`, `schedule`, and so on). Checking a box does not run agentic workflows immediately. See [get-enabled-workflows](../workflows/get-enabled-workflows.md).

## Disable an agentic workflow

1. Open the Control Plane dashboard issue.
2. **Uncheck** the agentic workflow’s checkbox. GitHub saves immediately on click.
3. Reply on the same issue with a short **deactivation reason** when the audit comment asks for it (the comment also mentions `@elastic/observablt-ci`).

The agentic workflow is excluded from `enabled-workflows` on the next client run. Full UI steps: [Control Plane dashboard — disabling an agentic workflow](../operations/control-plane-dashboard.md#disabling-an-agentic-workflow).

## Default behavior

| Control Plane dashboard state | Result |
|-----------------|--------|
| No Control Plane dashboard exists | All agentic workflows are deactivated |
| Control Plane dashboard exists, all checkboxes unchecked | All agentic workflows are deactivated |
| Control Plane dashboard exists, some checkboxes checked | Only checked agentic workflows run |

Control Plane dashboard checkbox edits do **not** start agentic workflows by themselves. Runtime gating is still read inside the ingress when a client workflow runs. Separately, `issues.edited` on the Control Plane dashboard issue triggers the shared [aw-dashboard-audit](../workflows/aw-dashboard-audit.md) path so enable/disable changes are recorded as comments on that issue. See [routing README](../routing/index.md).

## See also

- [Control Plane dashboard — user instructions](../operations/control-plane-dashboard.md)
- [aw-dashboard-audit](../workflows/aw-dashboard-audit.md)
- [get-enabled-workflows](../workflows/get-enabled-workflows.md)
- [Client template index](../workflows/obs-aw-client-template.md)
- [Agentic workflow maturity badges](../operations/control-plane-dashboard.md#maturity-badges) — `stable`, `early-adoption`, `experimental`
- [Adopting a new remote agentic workflow — consumer repositories](../onboarding/adopting-agentic-workflows.md#consumer-repositories)
