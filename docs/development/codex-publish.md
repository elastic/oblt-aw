---
navigation_title: Codex publish
description: How oblt-aw docs publish to Elastic Internal Docs (Codex) with docs-builder.
applies_to: {}
---

# Publish docs to Codex

`oblt-aw` documentation is built with Elastic Docs v3 (`docs-builder`) and published to Elastic Internal Docs (Codex).

## Source of truth

- Editable Markdown lives under `docs/` in [elastic/oblt-aw](https://github.com/elastic/oblt-aw).
- Navigation and build config: [`docs/docset.yml`](../docset.yml).
- Live site (after registration): `https://codex.elastic.dev/r/oblt-aw/`

Observability Robots may link here with Docs v3 cross-links (`oblt-aw://…`) from [elastic/observability-robots](https://github.com/elastic/observability-robots) without copying this tree.

## CI in this repository

| Workflow | When | Purpose |
|----------|------|---------|
| [`.github/workflows/codex-preview.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/codex-preview.yml) | PR and push to `main` touching `docs/**` | Build and publish Codex preview / production update |
| [`.github/workflows/codex-preview-cleanup.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/codex-preview-cleanup.yml) | Any PR closed | Remove preview deployment (no-ops if none) |

Both call reusable workflows from `elastic/docs-actions`. File names must stay `codex-preview.yml` and `codex-preview-cleanup.yml` (OIDC / Vault bindings).

## One-time platform registration

New Codex corpora need:

1. This repository’s preview workflows (above) merged to `main`.
2. A PR in [elastic/docs-infra](https://github.com/elastic/docs-infra) adding `elastic/oblt-aw` to `aws/elastic-web/us-east-1/codex-internal/repositories.yml`.
3. Token policies via Backstage or [elastic/catalog-info](https://github.com/elastic/catalog-info) (Codex link-index push + pull allowlist), using the Vault role name from the first `elastic-codex` CI run.

Official walkthrough: [Set up Elastic Internal Docs](https://codex.elastic.dev/r/codex-environments/set-up-codex) (Codex; Elastic network).

## Local preview

Install `docs-builder` from [elastic/docs-builder releases](https://github.com/elastic/docs-builder/releases), then from the repository root:

```bash
docs-builder serve
```

Open the URL printed by the CLI (typically `http://localhost:3000`).

## Cross-links from other docsets

Other internal docsets with `registry: internal` can declare:

```yaml
cross_links:
  - oblt-aw
```

and link with `oblt-aw://user-guide/onboard-a-repository.md` (path relative to this repo’s `docs/`).
