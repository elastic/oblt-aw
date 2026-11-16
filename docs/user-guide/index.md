---
navigation_title: User guide
description: What Elastic developers do with oblt-aw — onboard and enable platform workflows, customize with local AI assets or scheduled automations (BYO), and choose Automerge dependency collections.
applies_to: {}
---

# User guide

Procedures for developers and target repository owners who use OBLT Agentic Workflows in a target repository. Prefer [Get started](../get-started.md) if you are new.

:::{image} ../images/control-plane-dashboard-issue.png
:alt: Control Plane dashboard issue in a target repository
:screenshot:
:::

## I want to…

### Use platform workflows

| Goal | Guide |
|------|--------|
| Onboard a repository that is not registered yet | [Onboard a repository](onboard-a-repository.md) |
| Enable or disable an agentic workflow from the Control Plane dashboard | [Enable or disable an agentic workflow](enable-a-new-workflow.md) |
| Opt in or opt out of Automerge dependency collections from the Control Plane dashboard | [Opt in or opt out of Automerge dependency collections](opt-in-opt-out.md) |
| Choose which dependency collections Automerge covers | [Choose Automerge dependency collections](automerge-services.md) |
| See what agentic workflows do and when they run | [Agentic workflow catalog by outcome](../knowledge-base/agentic-workflows/by-outcome.md) |

### Customize in your repository (BYO)

You bring the behavior: instruction text, optional local AI assets, and (for schedules) which automations run. You turn workflows on from the Control Plane dashboard. You do not own locks, schedule clients, or compilation — oblt-aw does. Both guides use root `apm.yml` under `x-oblt-aw`.

| Goal | Guide |
|------|--------|
| Define local AI assets for shipped agentic workflows | [Define local AI assets](local-ai-assets.md) |
| Run your own scheduled automations (`obs:repo-scheduled`) | [Run your own scheduled automations](run-scheduled-automations.md) |

## Related

- [Admin guide](../admin-guide/index.md) — shipping or changing framework agentic workflows, secrets
- [Troubleshooting](../troubleshooting/index.md) — failed runs and common problems
