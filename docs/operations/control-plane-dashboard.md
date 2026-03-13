# Control Plane Dashboard — User Instructions

**Related issue:** https://github.com/elastic/observability-robots/issues/3732

This document explains how to use the OBLT AW Control Plane Dashboard to enable or disable agentic workflows for your repository.

---

## What Is the Dashboard?

The Control Plane Dashboard is a single GitHub Issue in your repository that lists all available agentic workflows. It provides a Renovate Dependency Dashboard–style interface: you enable or disable each workflow by checking or unchecking task list items.

- **Title:** `[OBLT AW] Control Plane Dashboard`
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
3. **Check** the checkbox next to the workflow (change `- [ ]` to `- [x]`)
4. Save or submit the edit

The config sync workflow runs when you edit the issue. It parses the checkbox state and updates `.github/oblt-aw-config.json` in your repository. The workflow will be added to `enabled_workflows` and will run on the next trigger.

### Disabling a Workflow

1. Open the Control Plane Dashboard issue
2. Find the workflow you want to disable
3. **Uncheck** the checkbox next to the workflow (change `- [x]` to `- [ ]`)
4. Save or submit the edit

The config sync removes the workflow from `enabled_workflows`. The workflow will no longer run for your repository until you enable it again.

---

## What Happens When You Edit

1. **You edit the issue** — Check or uncheck one or more workflow checkboxes
2. **GitHub fires `issues.edited`** — The event includes the updated issue body
3. **Ingress routes to `dashboard-config-sync`** — Because the issue has label `oblt-aw/dashboard`
4. **Config sync parses the body** — Extracts which workflows are checked
5. **Config file is updated** — `.github/oblt-aw-config.json` is written with `{"enabled_workflows": ["id1", "id2", ...]}`
6. **Ingress respects the config** — On future triggers, only workflows in `enabled_workflows` run

---

## Default Behavior

- **If `.github/oblt-aw-config.json` does not exist:** All workflows are enabled (backward compatibility)
- **If the config exists:** Only workflows listed in `enabled_workflows` run

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
- `docs/routing/dashboard-config-sync-routing.md` — Routing rules for config sync
