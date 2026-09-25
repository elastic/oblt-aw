# Start from scratch

## Overview

You want OBLT Agentic Workflows in a repository that is not yet registered.

**Preferred path:** follow [Onboard a repository](onboard-a-repository.md) — open the **Onboard a repository** issue form in `elastic/oblt-aw`, wait for automation to open the required pull requests, merge them manually, then enable workflows from the Control Plane Dashboard.

For the full technical registration procedure (catalog token policy, secrets, verification), see [Registering resources](../../onboarding/registering-a-repository.md).

## Prerequisites

- **Write** access on [elastic/oblt-aw](https://github.com/elastic/oblt-aw) (and ability to merge related PRs) as described in [Onboard a repository](onboard-a-repository.md).
- The target repository is under the `elastic` GitHub organization.

## Steps

1. **Open an onboard issue** — Use the **[Onboard a repository](https://github.com/elastic/oblt-aw/issues/new?template=onboard-repository.yml)** form (or pick it from [New issue](https://github.com/elastic/oblt-aw/issues/new/choose)). Provide only `elastic/<repo>` and the org key (`obs` or `docs`). See [Onboard a repository](onboard-a-repository.md).

2. **Merge the agent-opened PRs manually** — Catalog TokenPolicy first, then `oblt-aw` registration, then settings (and secrets if any). Details and ordering: [Onboard a repository](onboard-a-repository.md).

3. **Merge the client workflow distribution PR** — After registration lands on `main`, confirm `distribute-client-workflow` opened a PR in your repository that installs client templates. See [Client template index](../../workflows/obs-aw-client-template.md).

4. **Confirm the Control Plane Dashboard issue** — Look for an open issue titled `[oblt-aw] Control Plane Dashboard` with label `oblt-aw/dashboard`. See [Control Plane Dashboard — user instructions](../../operations/control-plane-dashboard.md).

5. **Enable workflows on the dashboard** — Check the workflows you want. See [Opt in or opt out](opt-in-opt-out.md).

## See also

- [Onboard a repository](onboard-a-repository.md) — primary user guide
- [Registering resources](../../onboarding/registering-a-repository.md)
- [Distribution operation: distribute-client-workflow](../../operations/distribute-client-workflow.md)
- [Enable a new workflow](enable-a-new-workflow.md) — when the repo is already registered and you only need to turn on a workflow
