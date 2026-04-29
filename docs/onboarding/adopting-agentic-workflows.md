# Adopting a new remote agentic workflow

## Overview

**Adopting** a new workflow means: it is **defined and routed in the remote control plane** (`elastic/oblt-aw` — reusable `gh-aw-*` workflows and `oblt-aw-ingress`), then **consumer repositories** run it through the distributed client that calls `elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main`.

You **cannot** meaningfully “enable” a workflow in a repository until it **exists in that org’s** [`workflow-registry.json`](../../config/obs/workflow-registry.json), **ingress dispatches it**, and [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) has had a chance to **render** it on the Control Plane Dashboard (or until ingress sees no dashboard and treats the full catalog as enabled). Registry rows, ingress jobs, and reusable workflow files should land in the **same reviewed change** (or a tightly coupled sequence of PRs) so sync and gating never reference a missing workflow.

Each **organization** owns `config/<org-key>/` (for example `config/obs/`): [`workflow-registry.json`](../../config/obs/workflow-registry.json) and [`active-repositories.json`](../../config/obs/active-repositories.json). Gating uses compound ids `org-key:workflow-id` ([`get-enabled-workflows`](../workflows/get-enabled-workflows.md), [Control Plane Dashboard format](../operations/control-plane-dashboard-format.md), [multi-org design](../architecture/multi-org-agentic-workflows.md)).

**If the workflow already exists in `oblt-aw`** and you only need repository-side adoption, **jump to [Consumer repositories](#consumer-repositories)** (after [Registering resources](registering-a-repository.md) where applicable).

## Prerequisites

- **Control plane:** Permission to change `elastic/oblt-aw` on `main` via reviewed pull requests.
- **Consumer repos:** Target repositories listed in `active-repositories.json`, client workflow installed, and **`COPILOT_GITHUB_TOKEN`** (or other secrets) only where the routed workflow requires them ([Client template](../workflows/oblt-aw-client-template.md); the **security detector** uses an ephemeral token instead — [gh-aw-security-detector](../workflows/gh-aw-security-detector.md)).

## Control plane checklist (`elastic/oblt-aw`)

Ship these in order when adding a **new** routed workflow. The sequence mirrors a typical end-to-end PR: implement the callable surface, prove it can run under GitHub’s permission model, wire ingress (including collisions with specialized flows), register for the dashboard, document, align the **client template**, then validate and merge.

### 1. Add the reusable workflow (and upstream lock, if applicable)

- Add `.github/workflows/gh-aw-<name>.yml` **at the repository root** (GitHub does not support `workflow_call` in subfolders) ([multi-org agentic workflows §4](../architecture/multi-org-agentic-workflows.md)).
- When the executable agentic graph lives in **`elastic/ai-github-actions`**, add a thin **wrapper** in `oblt-aw` that calls the pinned lock file, for example `uses: elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main`, and pass domain-specific `with:` / `secrets:` there. Specialized fixers in this repo already follow that pattern (see [.github/workflows/gh-aw-security-fixer.yml](../../.github/workflows/gh-aw-security-fixer.yml) and [.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml](../../.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml)).

### 2. Mirror permissions from similar workflows

- Reusable workflows that open issues, discussions, or PRs need explicit `permissions` compatible with nested `uses:` and with anything the lock workflow expects. Copy the set from an existing wrapper of the same class rather than guessing.
- For **fixer-style** wrappers that call `gh-aw-issue-fixer.lock.yml`, align with existing fixers: include at least `actions: read`, `contents: write`, `discussions: write`, `issues: write`, and `pull-requests: write` at workflow (or job) scope unless you have a narrower design that is still validated end-to-end. Omitting scopes that nested actions need tends to fail **workflow validation on pull requests** (this showed up in early `oblt-aw` ingress and wrapper PRs such as **#14** and **#15**).

### 3. Route from `oblt-aw-ingress.yml`

- Add a job (or jobs) in [`.github/workflows/oblt-aw-ingress.yml`](../../.github/workflows/oblt-aw-ingress.yml) with `uses:` pointing at your reusable workflow.
- Use `needs: dashboard-enabled-workflows` and an `if:` that:
  - Gates on `contains(fromJSON(needs['dashboard-enabled-workflows'].outputs['enabled-workflows']), '<org-key>:<workflow-id>')` when `effective-raw` is non-empty, **or** respects the “no dashboard → all enabled” behavior documented in [oblt-aw-ingress](../workflows/oblt-aw-ingress.md).
- Restrict **when** the job runs to the right **event** and **payload** (for example `issues` with `labeled` and `github.event.label.name == 'oblt-aw/ai/fix-ready'` for fix-ready flows).
- Observability compound ids use the **`obs:`** prefix today (for example `obs:security`).

### 4. Add exclusion guards for overlapping generic and specialized paths

- When a **generic** workflow would otherwise run on the same labels or events as a **specialized** pipeline, add **`if:`** guards on the generic ingress job so specialized issues are not double-handled.
- Concrete patterns already in ingress: a **generic issue fixer** must **not** run when issue labels match specialized triage namespaces, for example:
  - `oblt-aw/triage/security-*` (security fixer owns fix-ready there)
  - `oblt-aw/triage/res-not-accessible-by-integration` (resource-not-accessible fixer owns fix-ready there)
- Implement exclusions with explicit `contains(...)` / `join(github.event.issue.labels.*.name, ',')` (or equivalent) so label additions are unambiguous.

### 5. Register in `workflow-registry.json`

- Under `config/<org-key>/workflow-registry.json`, add one object with a unique `id` within that org, plus `name`, `description`, `maturity`, and `default_enabled`. **Defaults for new workflows:** set `maturity` to **`experimental`** and `default_enabled` to **`false`** so new dashboard rows start opt-in; change to `stable`, `early-adoption`, or `true` only when you intentionally want broader rollout ([workflow maturity](../operations/workflow-maturity.md)).
- The `id` you choose is what appears after `obs:` in ingress `contains(...)` checks (for example `id: issue-fixer` → gate `obs:issue-fixer`).

### 6. Update documentation

- **[`docs/workflows/README.md`](../workflows/README.md)** — Add a bullet for the new workflow page.
- **[`docs/workflows/oblt-aw-ingress.md`](../workflows/oblt-aw-ingress.md)** — Add a registry subsection (table row, triggers, dashboard gate) so ingress behavior stays the single catalogued source of truth.
- **`docs/workflows/gh-aw-<name>.md`** — New page for operators (purpose, triggers, secrets, links to routing doc if any).
- When label or trigger semantics are non-trivial, add or extend **`docs/routing/<topic>-routing.md`** and link it from the ingress doc ([routing index](../routing/README.md)).

### 7. Keep the distributed client entrypoint aligned

- If consumers need new **event types** or **activity types** (for example `issues: [opened, labeled]`), update **only** the distributed client template under [`.github/remote-workflow-template/obs/`](../../.github/remote-workflow-template/obs/) (or the relevant org subtree). See [oblt-aw client template](../workflows/oblt-aw-client-template.md).
- **Do not** edit the protected installed client [`.github/workflows/oblt-aw.yml`](../../.github/workflows/oblt-aw.yml) in this repository for distribution semantics; it is out of scope for normal changes ([AGENTS.md](../../AGENTS.md)).

### 8. Validate, merge, and confirm sync

- Run local checks from [Contributing](../development/contributing.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md).
- Merge the registry entry, workflow(s), ingress changes, guards, docs, and any client-template updates to **`elastic/oblt-aw` `main`** in reviewed units.
- [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) updates each target repo’s `[oblt-aw] Control Plane Dashboard` issue; confirm the new `workflow-id` appears under the right org section with the expected initial checkbox from `default_enabled`. Until this (or until consumers have no dashboard and rely on “all enabled”), consumer verification has nothing concrete to assert for that id.

## Consumer repositories

Nothing here **creates** the workflow; it only consumes what the registry and sync expose.

1. **Verify the workflow is present and runnable** — Complete [Registering resources](registering-a-repository.md) if the repo is not yet on `active-repositories.json` or missing the client. Open the auto-maintained dashboard issue (`oblt-aw/dashboard`, `[oblt-aw] Control Plane Dashboard`) and confirm there is a task-list row for **`<!-- oblt-aw:<org-key>:<your-workflow-id> -->`** after sync. Install secrets the workflow needs. If the row is missing, wait for sync on `main` or investigate sync failures before continuing.

2. **Align enablement with policy** — Ingress behavior is summarized in [Dashboard gating (reference)](#dashboard-gating-reference): **no** open dashboard issue means **all** registry workflows (including the new one) are treated as enabled; **with** a dashboard, only checked compound ids run, and new rows start from `default_enabled`. Edit checkboxes only when you need a different combination; **save** the issue, then rely on a **later** client run (`schedule`, `pull_request`, `issues`, …) for `get-enabled-workflows` to pick up edits ([oblt-aw-client-template](../workflows/oblt-aw-client-template.md), [user instructions](../operations/control-plane-dashboard.md)).

## Dashboard gating (reference)

| Dashboard state | Effect on gated ingress jobs |
|-----------------|------------------------------|
| No open dashboard issue (`effective-raw` empty) | All registry workflows treated as enabled |
| Dashboard exists, all checkboxes unchecked | None |
| Dashboard exists, some checked | Only checked `org-key:workflow-id` values |

New rows introduced by sync use `default_enabled` from `workflow-registry.json` until edited in the issue ([control-plane-dashboard-format](../operations/control-plane-dashboard-format.md)).

## Troubleshooting

- **Workflow never runs after checking the box** — Wait for a supported client/ingress trigger; checkbox edits alone do not enqueue a run ([oblt-aw-client-template](../workflows/oblt-aw-client-template.md), [oblt-aw-ingress](../workflows/oblt-aw-ingress.md)).
- **All workflows off unexpectedly** — A dashboard issue with every box unchecked yields `enabled-workflows` `[]` ([control-plane-dashboard](../operations/control-plane-dashboard.md)).
- **Validation fails on the PR that adds the workflow** — Compare `permissions` with a sibling wrapper of the same class; confirm nested `uses:` repositories and scopes match what the lock workflow needs.

## References

- [Architecture overview](../architecture/overview.md)
- [oblt-aw-ingress](../workflows/oblt-aw-ingress.md)
- [oblt-aw client template](../workflows/oblt-aw-client-template.md)
- [Control Plane Dashboard format](../operations/control-plane-dashboard-format.md)
- [Registering resources](registering-a-repository.md)
