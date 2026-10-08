---
navigation_title: Get started
description: Onboard a repository and enable OBLT Agentic Workflows from the Control Plane Dashboard.
applies_to: {}
---

# Get started

Use this path if you are an Elastic developer and want agentic workflows in a repository through **oblt-aw**.

## 1. Onboard the repository

If the repository is **not** listed in `config/<org-key>/active-repositories.json` yet:

1. Open an **[Onboard a repository](https://github.com/elastic/oblt-aw/issues/new?template=onboard-repository.yml)** issue in [elastic/oblt-aw](https://github.com/elastic/oblt-aw).
2. Follow the agent checklist on the issue and merge the pull requests it opens.
3. Merge the agentic workflows triggers PR in your repository and confirm the Control Plane Dashboard issue exists.

For further details, see [Onboard a repository](user-guide/onboard-a-repository.md).

If the repository is **already** registered, skip to step 2.

## 2. Enable agentic workflows

1. Open the `[oblt-aw] Control Plane Dashboard` issue in your repository (GitHub label `oblt-aw/dashboard`).
2. Check the agentic workflow row. GitHub saves on click; the next matching event applies gating.

:::{image} images/control-plane-dashboard-enable.png
:alt: Control Plane Dashboard Enable/Disable checkboxes for agentic workflows
:screenshot:
:::

For further details, see [Enable or disable an agentic workflow](user-guide/enable-a-new-workflow.md).

## 3. Pick what agentic automation you need

Browse by what you want to automate: [Agentic workflow catalog by outcome](workflows/by-outcome.md).

For Automerge categories: [Choose Automerge services](user-guide/automerge-services.md).

More in the [User guide](user-guide/index.md).

## Where to get help

- Failed run: [Troubleshooting](troubleshooting/index.md)
- Recurring issues: [Frequently Asked Problems](knowledge-base/frequent-asked-problems/index.md)
- Slack: `#observability-robots` (operators and maintainers)
