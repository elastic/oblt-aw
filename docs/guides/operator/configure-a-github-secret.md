# Configure a GitHub secret

## Overview

Not every agentic workflow needs repository secrets. Many workflows mint **ephemeral GitHub tokens** via [`elastic/oblt-actions/github/create-token@v1`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token) instead of using long-lived secrets.

Use this guide to decide which path applies, then follow the workflow-specific doc for exact secret names.

## Prerequisites

- The workflow id and its doc under [docs/workflows/](../../workflows/).
- Permission to provision secrets through [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets) when secrets are required.

## When secrets are not required

Some workflows declare **no** repository secrets. Example: [oblt-aw-security-detector](../../workflows/oblt-aw-security-detector.md) uses an ephemeral token for issue creation because `GITHUB_TOKEN` does not trigger downstream issue events.

For these workflows you still need:

- Registration and catalog token policy ([Registering resources](../../onboarding/registering-a-repository.md))
- `id-token: write` on the client `run-aw` job when `create-token` is in the call chain ([Client template index](../../workflows/oblt-aw-client-template.md))

See [Use GitHub ephemeral tokens](../maintainer/use-gh-ephemeral-tokens.md) for the token-policy model.

## When repository secrets are required

1. **Read the workflow doc** — Each `docs/workflows/oblt-aw-*.md` (or `docs-aw-*.md`) states declared secrets, if any. Start at [docs/workflows/README.md](../../workflows/README.md).

2. **Provision through Observability secrets** — Do not rely only on per-repository **Settings → Secrets** unless your process explicitly allows it. Follow [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets) for provisioning. Registration step 7: [Registering resources](../../onboarding/registering-a-repository.md).

3. **Example: workflow-specific secret** — [oblt-aw-estc-pr-buildkite-detective](../../workflows/oblt-aw-estc-pr-buildkite-detective.md) documents `BUILDKITE_LOGS_API_TOKEN` (migration note from `BUILDKITE_API_TOKEN`). Always use the name in the workflow doc, not a generic list.

## Ephemeral tokens versus catalog policy

Consumer repositories use Backstage **TokenPolicy** resources in `elastic/catalog-info` for OIDC-bound `create-token` calls. That is separate from repository secrets:

- **Catalog token policy** — Backs `create-token` for installed client workflows; required for every newly registered consumer repo. See [Registering resources](../../onboarding/registering-a-repository.md).
- **`workflow-token-policy` in `active-repositories.json`** — Optional explicit policy name per repo for agentic workflow `create-token` (via `aw-prelude`). See [distribute-client-workflow](../../operations/distribute-client-workflow.md).
- **Platform Engineering reference** — [Ephemeral tokens / GitHub Actions](https://docs.elastic.dev/platform-engineering-productivity/services/ephemeral-tokens/github-actions).

## See also

- [Registering resources — step 7 (secrets)](../../onboarding/registering-a-repository.md)
- [oblt-aw-security-detector](../../workflows/oblt-aw-security-detector.md) — no secrets pattern
- [Use GitHub ephemeral tokens](../maintainer/use-gh-ephemeral-tokens.md)
- [Troubleshoot an error](troubleshoot-an-error.md)
