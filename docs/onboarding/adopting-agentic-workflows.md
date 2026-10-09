# Adopting a new remote agentic workflow

## Overview

**Adopting** a new agentic workflow means: it is **defined in the framework** (`elastic/oblt-aw` — reusable `obs-aw-*` Actions workflows with [aw-prelude](../workflows/aw-prelude.md)), then **consumer repositories** run it through a distributed **event-scoped** client (`trigger-obs-aw-<event>.yml`) that calls the matching `obs-aw-event-*` orchestrator. Template source stays `@main`; installed pins follow `pin-class` ([release-model](../operations/release-model.md)).

You **cannot** meaningfully “enable” an agentic workflow in a repository until it **exists in that org’s** [`workflow-registry.json`](https://github.com/elastic/oblt-aw/blob/main/config/obs/workflow-registry.json), the **`obs-aw-*` route** is wired into the matching event orchestrator (and client when the event family is new), and [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) has rendered it on the Control Plane dashboard. An agentic workflow runs only when its checkbox is checked on that Control Plane dashboard (or after sync creates the Control Plane dashboard and you enable it).

Each **organization** owns `config/<org-key>/` (for example `config/obs/`): [`workflow-registry.json`](https://github.com/elastic/oblt-aw/blob/main/config/obs/workflow-registry.json) and [`active-repositories.json`](https://github.com/elastic/oblt-aw/blob/main/config/obs/active-repositories.json). Gating uses compound ids `org-key:workflow-id` ([`get-enabled-workflows`](../workflows/get-enabled-workflows.md), [Control Plane dashboard format](../operations/control-plane-dashboard-format.md), [multi-org design](../architecture/multi-org-agentic-workflows.md)).

**If the agentic workflow already exists in `oblt-aw`** and you only need repository-side adoption, **jump to [Consumer repositories](#consumer-repositories)** (after [Registering resources](registering-a-repository.md) where applicable).

## Prerequisites

- **Framework:** Permission to change `elastic/oblt-aw` on `main` via reviewed pull requests.
- **Consumer repos:** Target repositories listed in `active-repositories.json` with event-scoped client YAML installed ([Client template](../workflows/obs-aw-client-template.md); the **security detector** uses an ephemeral token — [obs-aw-security-detector](../workflows/obs-aw-security-detector.md)).

## Framework checklist (`elastic/oblt-aw`)

### 1. Add the reusable workflow (and upstream lock, if applicable)

- Add `.github/workflows/obs-aw-<name>.yml` (route reusable) at the repository root.
- When the agent graph lives in **`elastic/ai-github-actions`**, add a thin wrapper that calls the pinned lock file and pass domain-specific `with:` / `secrets:`.

### 2. Add route contract and event orchestration

- Route reusable (`obs-aw-*` / `docs-aw-*`): declare required `shared-proceed` (and shared allow-list / token-policy inputs); gate agent jobs with `if: inputs.shared-proceed == 'true'` plus event/label/comment guards. Do **not** call `aw-prelude.yml` from route workflows.
- Event orchestrator (`*-aw-event-*.yml`): first job calls [aw-prelude.yml](../workflows/aw-prelude.md) with `control-plane-workflows` listing every route basename for that GitHub event family; fan out with `fromJSON(needs.run-aw-prelude.outputs.proceed-by-workflow)['<basename>']` ([aw-prelude](../workflows/aw-prelude.md)). Prefer extending an existing orchestrator for that event family rather than adding a new client file.

### 3. Mirror permissions from similar workflows

- Copy `permissions` from an existing wrapper of the same class (fixer, triage, PR bot, and so on).

### 4. Add exclusion guards for overlapping generic and specialized paths

- When a **generic** workflow shares events with a **specialized** pipeline, add `if:` guards on the generic `obs-aw-*` job (for example generic issue-triage / issue-fixer exclude `oblt-aw/detector/security`, `oblt-aw/detector/res-not-accessible-by-integration`, `oblt-aw/triage/security-*`, and `oblt-aw/triage/res-not-accessible-by-integration`).

### 5. Register in `workflow-registry.json`

- Add one object with unique `id`, `name`, `description`, `maturity`, `default_enabled`, `docs` (any repo-relative documentation path; usually under `docs/workflows/`), and `inner_workflows` (basenames of every `obs-aw-*` / `docs-aw-*` wrapper that share this Control Plane dashboard id) under `config/<org-key>/workflow-registry.json`.

### 6. Wire the event-scoped client (only when needed)

- Clients are **event-scoped** (`trigger-obs-aw-pull-request.yml`, `trigger-obs-aw-issues.yml`, …), shared by all routes in that event family ([obs-aw client template](../workflows/obs-aw-client-template.md)).
- If the route fits an existing event family, update that family’s orchestrator (step 2) — do **not** add a new `trigger-obs-aw-<workflow-id>.yml`.
- Add `.github/remote-workflow-template/obs/.github/workflows/trigger-obs-aw-<event>.yml` only when introducing a **new** GitHub event family (or a conditional client such as `trigger-obs-aw-workflow-run.yml`).

### 7. Update documentation

- [`docs/workflows/README.md`](../workflows/index.md), **`docs/workflows/obs-aw-<name>.md`**, and **`docs/routing/<topic>-routing.md`** when triggers or labels are non-trivial.

### 8. Test, validate, merge, and confirm sync

- Add [unit](../knowledge-base/qa/unit.md), [integration](../knowledge-base/qa/integration.md), and [E2E](../knowledge-base/qa/e2e.md) coverage for the new route (live E2E for the production-like agent path). Unit and integration run on every PR; live E2E gates promote. See [QA](../knowledge-base/qa/index.md).
- Merge to `main`; confirm [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) renders the new checkbox.

## Consumer repositories

1. **Verify** the agentic workflow row exists on the Control Plane dashboard after sync.
2. **Install secrets** and enable via Control Plane dashboard when policy requires opt-in.
3. **Remove** legacy `.github/workflows/oblt-aw.yml` if still present.

## Control Plane dashboard gating (reference)

| Control Plane dashboard state | Effect |
|-----------------|--------|
| No open Control Plane dashboard issue (`effective-raw` empty) | None |
| Control Plane dashboard exists, all unchecked | None |
| Control Plane dashboard exists, some checked | Only checked `org-key:workflow-id` values |

## Troubleshooting

Full symptom write-ups: [Common problems](../troubleshooting/common-problems/index.md).

- **Agentic workflow never runs after checking the box** — Wait for a supported trigger on the installed `trigger-obs-aw-*.yml` client ([obs-aw-client-template](../workflows/obs-aw-client-template.md)). If jobs stay skipped, see [Workflows skipped or not running](../troubleshooting/common-problems/workflows-skipped-or-not-running.md).
- **Validation fails on the PR** — Compare `permissions` with a sibling wrapper; confirm the route basename is listed under the correct `inner_workflows` entry in `workflow-registry.json` and appears in the matching event orchestrator’s `control-plane-workflows` input.

## References

- [Architecture overview](../architecture/overview.md)
- [aw-prelude](../workflows/aw-prelude.md)
- [Control Plane dashboard format](../operations/control-plane-dashboard-format.md)
- [obs-aw client template](../workflows/obs-aw-client-template.md)
- [QA](../knowledge-base/qa/index.md) — unit, integration, and E2E layers
- [Registering resources](registering-a-repository.md)
