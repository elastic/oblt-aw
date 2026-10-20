# Opt in or opt out of Automerge dependency collections

## Overview

Use the Control Plane dashboard issue in your repository to control Automerge behavior:

1. **Parent Automerge checkbox** (`obs:automerge`) enables or disables Automerge for the repository.
2. **Dependency collection checkboxes** (for example `obs:automerge:github-actions`) allow or block specific update types.

If the parent toggle is off, collection checkboxes do not apply.

## Prerequisites

- Your repository has an open Control Plane dashboard issue (label `oblt-aw/dashboard`, title `[oblt-aw] Control Plane Dashboard`).
- The repository is already onboarded to `oblt-aw`.

If onboarding is not complete, follow [Onboard a repository](onboard-a-repository.md).

## Opt in (enable) Automerge collections

1. Open your repository's Control Plane dashboard issue.
2. Check the **Automerge** parent checkbox.
3. Check one or more Automerge dependency collection checkboxes under that parent.
4. Wait for the next supported client workflow trigger (`pull_request`, `schedule`, and so on).

For collection meanings before enabling them, see [Choose Automerge dependency collections](automerge-services.md).

## Opt out (disable) Automerge collections

To disable one update type while keeping Automerge on:

1. Open the Control Plane dashboard issue.
2. Leave the **Automerge** parent checked.
3. Uncheck the specific collection checkbox you want to disable.

To disable all Automerge behavior:

1. Open the Control Plane dashboard issue.
2. Uncheck the **Automerge** parent checkbox.

## What to expect after changing checkboxes

- GitHub saves checkbox edits immediately on the issue.
- A dashboard audit comment records the change.
- Changes take effect on the next client workflow run; checkbox edits do not start Automerge immediately.

## Related guides

- [Enable or disable an agentic workflow](enable-a-new-workflow.md)
- [Choose Automerge dependency collections](automerge-services.md)
- [Control Plane dashboard — user instructions](../operations/control-plane-dashboard.md)
