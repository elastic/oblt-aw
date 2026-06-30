# Use GitHub ephemeral tokens

## Overview

Many agentic workflows call [`elastic/oblt-actions/github/create-token@v1`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token) to mint short-lived tokens instead of storing long-lived repository secrets. This guide summarizes when and how token policies apply in `oblt-aw`.

For Platform Engineering policy and catalog authoring rules, see [Ephemeral tokens / GitHub Actions](https://docs.elastic.dev/platform-engineering-productivity/services/ephemeral-tokens/github-actions).

## Prerequisites

- Consumer registration complete or in progress ([Registering resources](../../onboarding/registering-a-repository.md)).
- Client templates grant `id-token: write` on the client entrypoint job (for example `run-oblt-aw-pull-request`) when the call chain includes `create-token` ([Client template index](../../workflows/oblt-aw-client-template.md)).

## Two token-policy fields (consumer repos)

Per-repository entries in `config/<org-key>/active-repositories.json` include:

| Field | Purpose |
|-------|---------|
| `workflow-token-policy` | Explicit Backstage policy name for agentic workflow `create-token` steps (exposed as `shared-token-policy` via [aw-prelude](../../workflows/aw-prelude.md)). Use `""` when Vault auto policy applies per trigger workflow ref. |
| `ai-assets-token-policy` | Policy for private APM package clones during [aw-resolve-agentic-assets](../../workflows/aw-resolve-agentic-assets.md). Use `""` when the job `GITHUB_TOKEN` is sufficient. |

Details: [distribute-client-workflow — distribution configuration contract](../../operations/distribute-client-workflow.md#distribution-configuration-contract-per-org-active-repositoriesjson).

## Catalog TokenPolicy (mandatory for new consumers)

Every newly registered consumer repository needs a Backstage **TokenPolicy** in `elastic/catalog-info` **before** merging the `oblt-aw` registration to `main`:

- `bound_claims.workflow_ref` must match each client workflow that calls `create-token` (for example `elastic/<repo>/.github/workflows/trigger-oblt-aw-automerge.yml@refs/heads/main`).
- `additional_permissions` is the union of permissions required by workflows in the org registry.

Full procedure and YAML template: [Registering resources](../../onboarding/registering-a-repository.md).

## Control-plane fixed policies

Some control-plane workflows use explicit policy ids in YAML (not copied into consumer repos):

| Workflow | Policy id (in this repo) |
|----------|--------------------------|
| [distribute-client-workflow](../../.github/workflows/distribute-client-workflow.yml) | `token-policy-63405ab45244` |
| [sync-control-plane-dashboard](../../.github/workflows/sync-control-plane-dashboard.yml) | `token-policy-8b60ba56dd3f` |

See the reference table in [Registering resources — appendix](../../onboarding/registering-a-repository.md).

## Example: workflow without repository secrets

[oblt-aw-security-detector](../../workflows/oblt-aw-security-detector.md) declares no `secrets` on `workflow_call`. Issue creation uses an ephemeral token so downstream issue-triggered workflows can run. The client template must include `id-token: write` on the client entrypoint job (for example `run-oblt-aw-pull-request`).

## Troubleshooting OIDC / create-token failures

- Match `workflow_ref` exactly to the invoking client workflow file.
- Confirm `id-token: write` on the client `run-oblt-aw-<event>` job.
- Confirm catalog policy merged **before** `oblt-aw` registration merged to `main`.

See [Registering resources — troubleshooting](../../onboarding/registering-a-repository.md#troubleshooting) and [Troubleshoot an error](../operator/troubleshoot-an-error.md).

## See also

- [Registering resources](../../onboarding/registering-a-repository.md)
- [aw-resolve-agentic-assets](../../workflows/aw-resolve-agentic-assets.md) — `ai-assets-token-policy` and APM installs
- [aw-prelude](../../workflows/aw-prelude.md) — `token-policy` output
- [Configure a GitHub secret](../operator/configure-a-github-secret.md) — when long-lived secrets are still required
