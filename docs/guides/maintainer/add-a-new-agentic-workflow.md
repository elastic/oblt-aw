# Add a new agentic workflow

## Overview

You are shipping a **new** routed workflow on the `elastic/oblt-aw` control plane so consumer repositories can enable it from the Control Plane Dashboard.

This is the maintainer path. Repo owners who only need to **enable** an existing workflow should use [Enable a new workflow](../user/enable-a-new-workflow.md).

## Prerequisites

- Permission to change `elastic/oblt-aw` on `main` via reviewed pull requests.
- When the agent graph lives in **`elastic/ai-github-actions`**, access to add or update the pinned `gh-aw-*.lock.yml` wrapper there.

## Steps

Follow the control-plane checklist in [Adopting a new remote agentic workflow](../../onboarding/adopting-agentic-workflows.md#control-plane-checklist-elasticoblt-aw):

1. **Add reusable workflows** — Control-plane wrapper (`oblt-aw-<name>.yml` or `docs-aw-<name>.yml`) and, when applicable, a thin wrapper that calls the pinned lock file from `elastic/ai-github-actions`.

2. **Add route contract and event orchestration** — Route reusables declare `shared-proceed`; event orchestrators call [aw-prelude](../../workflows/aw-prelude.md) once and fan out. Route workflows must not call `aw-prelude` directly.

3. **Register in `workflow-registry.json`** — Add `id`, `name`, `description`, `maturity`, `default_enabled`, and `control_plane_workflows` under `config/<org-key>/`.

4. **Add a client template** — Under `.github/remote-workflow-template/<org-key>/.github/workflows/trigger-oblt-aw-<workflow-id>.yml`. See [Client template index](../../workflows/oblt-aw-client-template.md).

5. **Update documentation** — `docs/workflows/oblt-aw-<name>.md`, routing doc when triggers are non-trivial, and [docs/workflows/README.md](../../workflows/README.md).

6. **Validate and merge** — CI must pass. After merge, [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md) adds the new checkbox to consumer dashboards.

7. **Consumer adoption** — Registered repos receive template updates via [distribute-client-workflow](../../operations/distribute-client-workflow.md). Users enable the workflow from the dashboard ([Enable a new workflow](../user/enable-a-new-workflow.md)).

When a workflow calls `gh-aw-*`, each agent job must invoke [aw-resolve-agentic-assets](../../workflows/aw-resolve-agentic-assets.md) immediately before the lock file (enforced by CI).

## See also

- [Adopting a new remote agentic workflow](../../onboarding/adopting-agentic-workflows.md) — full checklist and consumer section
- [Contributing to oblt-aw](../../development/contributing.md) — local setup and pre-commit
- [Change maturity level](change-maturity-level.md)
- [Use GitHub ephemeral tokens](use-gh-ephemeral-tokens.md)
