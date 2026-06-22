# Start from scratch

## Overview

You want to use OBLT Agentic Workflows in a repository that is not yet registered. This guide walks through registration, client template distribution, and enabling workflows from the Control Plane Dashboard.

For the full registration procedure (catalog token policy, secrets, verification), see [Registering resources](../../onboarding/registering-a-repository.md).

## Prerequisites

- Permission to open pull requests to `elastic/oblt-aw`, `elastic/catalog-info`, and (when secrets are needed) `elastic/observability-github-secrets`.
- The target repository is under the `elastic` GitHub organization.

## Steps

1. **Register the repository in `elastic/oblt-aw`** — Add the repository to the correct org’s `config/<org-key>/active-repositories.json`. Complete the mandatory token policy in `elastic/catalog-info` **before** merging the `oblt-aw` registration PR. See [Registering resources](../../onboarding/registering-a-repository.md).

2. **Merge the registration pull request** — After the catalog policy is active, merge the `oblt-aw` change to `main`. That triggers [distribute-client-workflow](../../operations/distribute-client-workflow.md) and [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md).

3. **Merge the client workflow distribution PR** — Confirm `distribute-client-workflow` opened a PR in your repository that installs `trigger-oblt-aw-*.yml` client templates from the remote workflow template. See [Client template index](../../workflows/oblt-aw-client-template.md).

4. **Confirm the Control Plane Dashboard issue** — Look for an open issue titled `[oblt-aw] Control Plane Dashboard` with label `oblt-aw/dashboard`. See [Control Plane Dashboard — user instructions](../../operations/control-plane-dashboard.md).

5. **Configure secrets (if required)** — Check the per-workflow docs in [docs/workflows/](../../workflows/) for any repository secrets. Provision them through [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets) per your team’s process. See [Configure a GitHub secret](../operator/configure-a-github-secret.md).

6. **Enable workflows on the dashboard** — Open the dashboard issue and check the workflows you want. GitHub saves immediately on click. Workflows run on the next supported client trigger (not immediately on the checkbox change). See [Opt in or opt out](opt-in-opt-out.md).

## See also

- [Registering resources](../../onboarding/registering-a-repository.md)
- [Distribution operation: distribute-client-workflow](../../operations/distribute-client-workflow.md)
- [Control Plane Dashboard — user instructions](../../operations/control-plane-dashboard.md)
- [Enable a new workflow](enable-a-new-workflow.md) — when the repo is already registered and you only need to turn on a workflow
