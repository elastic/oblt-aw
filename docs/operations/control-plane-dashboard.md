# Control Plane dashboard — user instructions

**Related issue:** [elastic/observability-robots#3732](https://github.com/elastic/observability-robots/issues/3732)

This document explains how to use the OBLT AW Control Plane dashboard to enable or disable agentic workflows for your repository.

---

## What is the Control Plane dashboard?

The Control Plane dashboard is a single GitHub Issue in your repository that lists all available agentic workflows. It provides a Renovate Dependency Dashboard–style interface: you enable or disable each agentic workflow by checking or unchecking task list items.

- **Title:** `[oblt-aw] Control Plane Dashboard`
- **Label:** `oblt-aw/dashboard`
- **Location:** Created and maintained automatically by the control plane; you can pin it at the top of your Issues list for easy access

---

## How to use the Control Plane dashboard

### Finding the Control Plane dashboard

1. Open the **Issues** tab of your repository
2. Search for `label:oblt-aw/dashboard` or `in:title "Control Plane Dashboard"`
3. If the Control Plane dashboard does not exist, it will be created when your repository is added to an org’s `config/<org-key>/active-repositories.json` in `elastic/oblt-aw` and the sync workflow runs

### Enabling an agentic workflow

1. Open the Control Plane dashboard issue
2. Find the agentic workflow you want to enable
3. **Check** the checkbox next to the agentic workflow (click it). GitHub saves the change immediately.

There is no config file. When the client workflow runs, the ingress (`get-enabled-workflows`) reads the Control Plane dashboard issue at runtime and applies `enabled-workflows` gating. The agentic workflow runs on the next trigger (e.g. `schedule`, `workflow_dispatch`, `pull_request`).

### Disabling an agentic workflow

1. Open the Control Plane dashboard issue
2. Find the agentic workflow you want to disable
3. **Uncheck** the checkbox next to the agentic workflow (click it). GitHub saves the change immediately.
4. An **audit comment** is posted on the same issue asking for a short **deactivation reason** and mentioning `@elastic/observablt-ci`. Reply on the issue with the reason so it is recorded on the audit entry.

Ingress excludes the agentic workflow from `enabled-workflows` at runtime after reading the Control Plane dashboard. The agentic workflow will no longer run for your repository until you enable it again.

### Audit trail

Every enable or disable of an agentic workflow or sub-feature checkbox produces a comment on the Control Plane dashboard issue with **when**, **what** (compound id + enabled/disabled), and **who**. Activations are audit-only (no team mention). Deactivations require a reason (via follow-up comment) and mention `@elastic/observablt-ci`. Sync / `force-sync-defaults` resets are also audited (actor = automation, fixed reason string). See [aw-dashboard-audit](../workflows/aw-dashboard-audit.md).

### Sub-features (composite agentic workflows)

Some agentic workflows expose **indented child checkboxes** under the parent on the Control Plane dashboard. These let you enable or disable individual parts of a composite agentic workflow (for example, specific dependency collections under Automerge).

For Automerge, these child checkboxes are **dependency collections**: first enable Automerge, then choose which collections you want it to merge. See [Automerge dependency collections](../user-guide/automerge-services.md) for the user-facing catalogue.

| Parent checkbox | Sub-feature checkbox | Effect |
|-----------------|----------------------|--------|
| Unchecked | Any | Parent and all sub-features are disabled |
| Checked | Unchecked | Parent runs; that sub-feature does not |
| Checked | Checked | Parent runs; that sub-feature runs |

Sub-features only take effect while the parent agentic workflow is enabled.

---

## What Happens at Runtime

1. **You edit the issue** — Check or uncheck one or more agentic workflow checkboxes (no PRs). An [aw-dashboard-audit](../workflows/aw-dashboard-audit.md) comment records when / what / who on the same issue; deactivations also ask for a reason and mention `@elastic/observablt-ci`.
2. **Client runs** — On the next trigger (schedule, workflow_dispatch, pull_request, etc.), the client workflow starts
3. **`get-enabled-workflows` runs inside the ingress** — If there is no open Control Plane dashboard issue, `effective-raw` is empty and normalized `enabled-workflows` is `[]` (no agentic workflows run). Otherwise it fetches the issue via API, parses checkboxes (`^- [x] <!-- oblt-aw:<org-key>:<workflow-id> -->` at line start; legacy `obs` lines without an org segment are accepted), and writes normalized `enabled-workflows` as a JSON array string (`[]` or `["org:workflow-id", ...]`).
4. **Ingress gating** — The ingress uses `enabled-workflows` and `effective-raw` from `get-enabled-workflows` to gate downstream jobs.
5. **Ingress gates execution** — Empty `effective-raw` or `enabled-workflows == []` → none; non-empty `enabled-workflows` → only listed compound ids. See [Default Behavior](#default-behavior).

---

## Default Behavior

| Control Plane dashboard state | Result |
|-----------------|--------|
| **No Control Plane dashboard exists** | All agentic workflows are deactivated |
| **Control Plane dashboard exists, all checkboxes unchecked** | All agentic workflows are deactivated |
| **Control Plane dashboard exists, some checkboxes checked** | Only checked agentic workflows are executed |

---

## Maturity Badges

Each agentic workflow in the Control Plane dashboard shows a maturity level:

| Maturity       | Meaning                                                                 |
|----------------|-------------------------------------------------------------------------|
| **stable**     | Production-ready; recommended for general adoption                      |
| **early-adoption** | Available for testing; feedback welcome; may have limitations     |
| **experimental**   | In development; behavior may change; for internal or limited use  |

See [docs/operations/workflow-maturity.md](workflow-maturity.md) for full criteria.

---

## Pinning the Control Plane dashboard

You can pin the Control Plane dashboard issue so it appears at the top of your Issues list (up to 3 issues can be pinned per repository):

1. Open the Control Plane dashboard issue
2. Click **Pin issue** in the right sidebar

If the sync workflow could not pin it automatically (e.g. you already have 3 pinned issues), you can manually unpin another issue and then pin the Control Plane dashboard.

---

## References

- [docs/operations/control-plane-dashboard-format.md](control-plane-dashboard-format.md) — Control Plane dashboard issue format and checkbox syntax
- [docs/user-guide/automerge-services.md](../user-guide/automerge-services.md) — What Automerge dependency collections mean
- [docs/operations/workflow-maturity.md](workflow-maturity.md) — Maturity level definitions
- [docs/architecture/overview.md](../architecture/overview.md) — Control Plane dashboard architecture
