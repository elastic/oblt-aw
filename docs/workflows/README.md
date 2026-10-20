# Workflow documentation

Per-workflow docs for sources in [.github/workflows/](https://github.com/elastic/oblt-aw/tree/main/.github/workflows) and the distributed client templates.

- **Developer catalog:** [Catalog by outcome](../knowledge-base/agentic-workflows/by-outcome.md)
- **Alphabetical index:** [index.md](index.md)

The index includes source-backed pages for GitHub Actions workflows, gh-aw
Markdown sources, and distributed client templates. Generated `*.lock.yml`
files are documented through their authored source pages, not as separate
workflow entries.

## Buildkite pipeline pages

- [Automerge VM images E2E fixture](https://github.com/elastic/oblt-aw/blob/main/.buildkite/docs/pipeline.e2e-automerge-vm-images.md)
- [ESTC intentional-failure E2E fixture](https://github.com/elastic/oblt-aw/blob/main/.buildkite/docs/oblt-aw-e2e-estc-fail.md)

The ESTC provisioning and live-run details remain in the existing
[Buildkite E2E notes](https://github.com/elastic/oblt-aw/blob/main/.buildkite/README.e2e-estc-fail.md). Static pipeline
YAMLs do not establish remote Buildkite provisioning or agent configuration;
each page calls out the relevant source gap.
