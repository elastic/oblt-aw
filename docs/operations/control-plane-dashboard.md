# Control Plane Dashboard — User Instructions

**Related issue:** https://github.com/elastic/observability-robots/issues/3732

This document explains how to use the OBLT AW Control Plane Dashboard to enable or disable agentic workflows for your repository.

---

## What Is the Dashboard?

The Control Plane Dashboard is a single GitHub Issue in your repository that lists all available agentic workflows. It provides a Renovate Dependency Dashboard–style interface: you enable or disable each workflow by checking or unchecking task list items.

- **Title:** `[oblt-aw] Control Plane Dashboard`
- **Label:** `oblt-aw/dashboard`
- **Location:** Created and maintained automatically by the control-plane; you can pin it at the top of your Issues list for easy access

---

## How to Use the Dashboard

### Finding the Dashboard

1. Open the **Issues** tab of your repository
2. Search for `label:oblt-aw/dashboard` or `in:title "Control Plane Dashboard"`
3. If the dashboard does not exist, it will be created when your repository is added to `active-repositories.json` and the sync workflow runs

### Enabling a Workflow

1. Open the Control Plane Dashboard issue
2. Find the workflow you want to enable
3. **Check** the checkbox: change ☐ to ☑ in the Enabled column
4. Save or submit the edit

There is no config file. When the client workflow runs, a `check-dashboard` job reads the dashboard issue at runtime and passes `enabled_workflows` to the ingress. The workflow will run on the next trigger (e.g. `schedule`, `workflow_dispatch`, `pull_request`).

### Disabling a Workflow

1. Open the Control Plane Dashboard issue
2. Find the workflow you want to disable
3. **Uncheck** the checkbox: change ☑ to ☐ in the Enabled column
4. Save or submit the edit

The `check-dashboard` job excludes the workflow from `enabled_workflows` at runtime. The workflow will no longer run for your repository until you enable it again.

---

## What Happens at Runtime

1. **You edit the issue** — Check or uncheck one or more workflow checkboxes (no immediate action; no PRs)
2. **Client runs** — On the next trigger (schedule, workflow_dispatch, pull_request, etc.), the client workflow starts
3. **check-dashboard job runs first** — Fetches the dashboard issue via API, parses checkboxes (`☑ <!-- oblt-aw:workflow-id -->`), outputs `enabled_workflows` as JSON array
4. **Ingress receives input** — The `run-aw` job passes `enabled_workflows` to the ingress
5. **Ingress gates execution** — Only workflows listed in `enabled_workflows` run; see [Default Behavior](#default-behavior) for semantics when no dashboard exists vs. dashboard with checkboxes

---

## Default Behavior

| Dashboard state | Result |
|-----------------|--------|
| **No dashboard exists** | All workflows are activated by default |
| **Dashboard exists, all checkboxes unchecked** | All workflows are deactivated |
| **Dashboard exists, some checkboxes checked** | Only checked workflows are executed |

---

## Maturity Badges

Each workflow in the dashboard shows a maturity level:

| Maturity       | Meaning                                                                 |
|----------------|-------------------------------------------------------------------------|
| **stable**     | Production-ready; recommended for general adoption                      |
| **early-adoption** | Available for testing; feedback welcome; may have limitations     |
| **experimental**   | In development; behavior may change; for internal or limited use  |

See `docs/operations/workflow-maturity.md` for full criteria.

---

## Pinning the Dashboard

You can pin the dashboard issue so it appears at the top of your Issues list (up to 3 issues can be pinned per repository):

1. Open the dashboard issue
2. Click **Pin issue** in the right sidebar

If the sync workflow could not pin it automatically (e.g. you already have 3 pinned issues), you can manually unpin another issue and then pin the dashboard.

---

## References

- `docs/operations/control-plane-dashboard-format.md` — Dashboard issue format and checkbox syntax
- `docs/operations/workflow-maturity.md` — Maturity level definitions
- `docs/architecture/overview.md` — Control Plane Dashboard architecture
