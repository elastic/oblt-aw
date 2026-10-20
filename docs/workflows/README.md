# Workflow documentation

Per-workflow docs for sources in [.github/workflows/](https://github.com/elastic/oblt-aw/tree/main/.github/workflows) and the distributed client templates.

- **Developer catalog:** [Catalog by outcome](../knowledge-base/agentic-workflows/by-outcome.md)
- **Alphabetical index:** [index.md](index.md)

## Inventory gaps

The following checked-in workflow YAMLs under `.github/workflows/` and Buildkite pipelines under `.buildkite/` do not currently have a dedicated authored docs page in `docs/workflows/`. Consider adding short per-workflow pages for these sources so developers can find intent, triggers, expected outcomes, and any runtime notes.

- .github/workflows/agentics-maintenance.yml
- .github/workflows/aw-sync-apm-version.yml
- .github/workflows/codex-preview-cleanup.yml
- .github/workflows/codex-preview.yml
- .github/workflows/docs-aw-event-issue-comment.yml
- .github/workflows/docs-aw-event-issues.yml
- .github/workflows/docs-aw-event-pull-request.yml
- .github/workflows/docs-aw-event-workflow-run.yml
- .github/workflows/docs-aw-pr-ai-menu-collect.yml
- .github/workflows/e2e-all.yml
- .github/workflows/e2e-autodoc.yml
- .github/workflows/e2e-automerge-vm-images.yml
- .github/workflows/e2e-dependency-review-actions-fixture.yml
- .github/workflows/e2e-dependency-review.yml
- .github/workflows/e2e-estc-pr-buildkite-detective.yml
- .github/workflows/e2e-pr-actions-detective-fail.yml
- .github/workflows/e2e-pr-actions-detective.yml
- .github/workflows/e2e-trigger-obs-aw-schedule.yml
- .github/workflows/obs-aw-event-issue-comment.yml
- .github/workflows/obs-aw-event-issues.yml
- .github/workflows/obs-aw-event-pull-request.yml
- .github/workflows/obs-aw-event-schedule.yml
- .github/workflows/obs-aw-event-status.yml
- .github/workflows/obs-aw-event-workflow-run.yml

Buildkite pipelines with no dedicated docs page in `docs/workflows/`:

- .buildkite/pipeline.e2e-automerge-vm-images.yml
- .buildkite/pipeline.e2e-estc-fail.yml

Notes:
- This inventory documents authored Markdown pages only; generated lock files (e.g. `*.lock.yml` such as `compiler-upgrade.lock.yml`, `gh-aw-*.lock.yml`) are compile artifacts and intentionally not authored as independent docs. Do not hand-edit lock files.
- If authoring new `.md` under `.github/workflows/` remember to run `make compile-aw-check` before pushing per AGENTS.md.

If any of these are documented elsewhere (client templates, distributed sources, or in-repo fragments), mark the new doc as a pointer rather than duplicating content.
