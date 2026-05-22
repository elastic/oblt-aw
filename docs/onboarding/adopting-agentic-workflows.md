# Adopting a new remote agentic workflow

## Overview

**Adopting** a new workflow means: it is **defined in the remote control plane** (`elastic/oblt-aw` — reusable `oblt-aw-*` workflows with [aw-prelude](../workflows/aw-prelude.md)), then **consumer repositories** run it through a distributed **`trigger-oblt-aw-<workflow-id>.yml`** client template that calls `elastic/oblt-aw/.github/workflows/oblt-aw-<name>.yml@main`.

You **cannot** meaningfully “enable” a workflow in a repository until it **exists in that org’s** [`workflow-registry.json`](../../config/obs/workflow-registry.json), the **client template and `oblt-aw-*` wrapper** exist, and [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) has rendered it on the Control Plane Dashboard (or until prelude sees no dashboard and treats the full catalog as enabled).

Each **organization** owns `config/<org-key>/` (for example `config/obs/`): [`workflow-registry.json`](../../config/obs/workflow-registry.json) and [`active-repositories.json`](../../config/obs/active-repositories.json). Gating uses compound ids `org-key:workflow-id` ([`get-enabled-workflows`](../workflows/get-enabled-workflows.md), [Control Plane Dashboard format](../operations/control-plane-dashboard-format.md), [multi-org design](../architecture/multi-org-agentic-workflows.md)).

**If the workflow already exists in `oblt-aw`** and you only need repository-side adoption, **jump to [Consumer repositories](#consumer-repositories)** (after [Registering resources](registering-a-repository.md) where applicable).

## Prerequisites

- **Control plane:** Permission to change `elastic/oblt-aw` on `main` via reviewed pull requests.
- **Consumer repos:** Target repositories listed in `active-repositories.json`, per-workflow client YAML installed, and **`COPILOT_GITHUB_TOKEN`** (or other secrets) only where the workflow requires them ([Client template](../workflows/oblt-aw-client-template.md); the **security detector** uses an ephemeral token — [oblt-aw-security-detector](../workflows/oblt-aw-security-detector.md)).

## Control plane checklist (`elastic/oblt-aw`)

### 1. Add the reusable workflow (and upstream lock, if applicable)

- Add `.github/workflows/trigger-oblt-aw-<name>.yml (client); oblt-aw-<name>.yml` at the repository root.
- When the agent graph lives in **`elastic/ai-github-actions`**, add a thin wrapper that calls the pinned lock file and pass domain-specific `with:` / `secrets:`.

### 2. Add prelude and route conditions

- First job: `uses: ./.github/workflows/aw-prelude.yml` with `enabled-workflow-id: <org-key>:<workflow-id>` and `load-allowed-authors: true` when PR/issue allow lists apply.
- Downstream jobs: `needs: prelude` and `if: needs.prelude.outputs.proceed == 'true'` plus event/label/comment guards ([aw-prelude](../workflows/aw-prelude.md)).

### 3. Mirror permissions from similar workflows

- Copy `permissions` from an existing wrapper of the same class (fixer, triage, PR bot, and so on).

### 4. Add exclusion guards for overlapping generic and specialized paths

- When a **generic** workflow shares events with a **specialized** pipeline, add `if:` guards on the generic `oblt-aw-*` job (for example generic issue-fixer excludes `oblt-aw/triage/security-*` and `oblt-aw/triage/res-not-accessible-by-integration`).

### 5. Register in `workflow-registry.json`

- Add one object with unique `id`, `name`, `description`, `maturity`, and `default_enabled` under `config/<org-key>/workflow-registry.json`.

### 6. Add a client template

- Add `.github/remote-workflow-template/obs/.github/workflows/trigger-oblt-aw-<workflow-id>.yml` with **only** the triggers for this workflow ([oblt-aw client template](../workflows/oblt-aw-client-template.md)).

### 7. Update documentation

- [`docs/workflows/README.md`](../workflows/README.md), **`docs/workflows/oblt-aw-<name>.md`**, and **`docs/routing/<topic>-routing.md`** when triggers or labels are non-trivial.

### 8. Validate, merge, and confirm sync

- Merge to `main`; confirm [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) renders the new checkbox.

## Consumer repositories

1. **Verify** the workflow row exists on the Control Plane Dashboard after sync.
2. **Install secrets** and enable via dashboard when policy requires opt-in.
3. **Remove** legacy `.github/workflows/oblt-aw.yml` if still present.

## Dashboard gating (reference)

| Dashboard state | Effect |
|-----------------|--------|
| No open dashboard issue (`effective-raw` empty) | All registry workflows enabled |
| Dashboard exists, all unchecked | None |
| Dashboard exists, some checked | Only checked `org-key:workflow-id` values |

## Troubleshooting

- **Workflow never runs after checking the box** — Wait for a supported trigger on the installed `trigger-oblt-aw-*.yml` client ([oblt-aw-client-template](../workflows/oblt-aw-client-template.md)).
- **Validation fails on the PR** — Compare `permissions` with a sibling wrapper; confirm prelude `enabled-workflow-id` matches registry `obs:<id>`.

## References

- [Architecture overview](../architecture/overview.md)
- [aw-prelude](../workflows/aw-prelude.md)
- [oblt-aw client template](../workflows/oblt-aw-client-template.md)
- [Control Plane Dashboard format](../operations/control-plane-dashboard-format.md)
- [Registering resources](registering-a-repository.md)
