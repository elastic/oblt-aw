# Introducing oblt-aw — a framework for agentic workflows

## What is oblt-aw, and what problems does it solve?

**oblt-aw** ([elastic/oblt-aw](https://github.com/elastic/oblt-aw)) is an opinionated shared framework for [GitHub Agentic Workflows](https://github.github.com/gh-aw/): reusable routes, thin clients [distributed automatically](docs/operations/distribute-client-workflow.md) to repos, and a **control plane** to turn workflows on or off (dashboard, sync, distribution, shared prelude).

Today many teams still wire each agent by hand in every repo (local workflow → `gh-aw-*.lock.yml`). That does not scale. We want to mitigate:

- **Copy-paste setup** in every repo (triggers, secrets, permissions).
- **No shared on/off switch**, so fleet behavior drifts.
- **Expensive updates** — chase N repos to change the same agent.
- **Slow rollouts** — every repo reinvents install and enablement.
- **Unsustainable management** as repos and agents grow.

**oblt-aw** keeps routing and management in the framework; agents still run from pinned upstream locks. Clients are **distributed automatically**, so entry points stay centralized and sustainable.

Background: [state-of-the-art analysis for agentic workflows](https://docs.google.com/document/d/16Qz7VSYC-lvZ_vrx4C5AjNQKMGVlo-wUxSMQF20HY0I/edit?tab=t.0#heading=h.9sx6dsgd2ex5).

## How it works

In a very simplified way:

1. Clients (`trigger-obs-aw-*.yml`) are **installed** using an [automated distribution](docs/operations/distribute-client-workflow.md) ([client template](docs/workflows/obs-aw-client-template.md)).
2. On a matching event, the client calls [elastic/oblt-aw](https://github.com/elastic/oblt-aw).
3. [Prelude](docs/workflows/aw-prelude.md) checks the [Control Plane Dashboard](docs/operations/control-plane-dashboard.md).
4. If enabled, the route runs the pinned agent from [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

See the [architecture overview](docs/architecture/overview.md).

## Features and benefits

Here are some of the most important features of the **oblt-aw** framework:

- **Automatic client distribution** — no hand-copying entrypoints; [distribution](docs/operations/distribute-client-workflow.md) installs/updates `trigger-obs-aw-*.yml` ([client template](docs/workflows/obs-aw-client-template.md), [adopting workflows](docs/onboarding/adopting-agentic-workflows.md)).
- **Self-service dashboard** — enable/disable with checkboxes on `[oblt-aw] Control Plane Dashboard` ([dashboard](docs/operations/control-plane-dashboard.md), [opt-in / opt-out](docs/guides/user/opt-in-opt-out.md)).
- **Shared prelude** — same gating and allow lists before every agent run ([aw-prelude](docs/workflows/aw-prelude.md)).
- **Shared agentic assets** — resolved in the framework ([aw-resolve-agentic-assets](docs/workflows/aw-resolve-agentic-assets.md)).
- **Update once, reach the fleet** — improve in `oblt-aw`; [distribution](docs/operations/distribute-client-workflow.md) refreshes clients across active repos.
- **Quieter PRs** — narrow triggers; only matching routes run ([split-trigger](docs/architecture/overview.md#split-trigger-vs-monolithic-ingress)).
- **Catalog with maturity** — registered workflows with clear maturity levels ([workflows index](docs/workflows/README.md), [maturity](docs/operations/workflow-maturity.md)).
- **Clear ownership** — shared core in one repo; per-org data under `config/<org-key>/` ([register a repo](docs/onboarding/registering-a-repository.md)).

## Open for every Elastic organization

Not Observability-only. Each org owns `config/<org-key>/`; [distribution](docs/operations/distribute-client-workflow.md) and dashboard sync stay scoped to that org; consumers still get one shared dashboard grouped by org. Observability leads; docs already has a second org footprint. Details: [multi-org design](docs/architecture/multi-org-agentic-workflows.md).

## Quick Start

Target repositories install event-scoped client templates from this repository (for example `trigger-obs-aw-pull-request.yml`, `trigger-obs-aw-issues.yml`). Each event client calls an `obs-aw-event-*` orchestrator that runs shared dashboard gating via [aw-prelude.yml](.github/workflows/aw-prelude.yml) and passes `shared-proceed` (plus allow-list fields) into each route reusable.

- Observability templates: [.github/remote-workflow-template/obs/.github/workflows/](.github/remote-workflow-template/obs/.github/workflows/) — see [docs/workflows/obs-aw-client-template.md](docs/workflows/obs-aw-client-template.md)
- Docs templates: [.github/remote-workflow-template/docs/.github/workflows/](.github/remote-workflow-template/docs/.github/workflows/) (`trigger-docs-aw-issues.yml`, `trigger-docs-aw-issue-comment.yml`, `trigger-docs-aw-pull-request.yml`, `trigger-docs-aw-workflow-run.yml`)

Executable workflows live under [.github/workflows/](.github/workflows/); their docs live under [docs/workflows/](docs/workflows/).

## Documentation

Primary repository documentation lives under `docs/`.

- Docs home: [docs/README.md](docs/README.md)
- Architecture and design: [docs/architecture/overview.md](docs/architecture/overview.md)
- Workflow-specific docs: [docs/workflows/README.md](docs/workflows/README.md)
- Routing docs: [docs/routing/README.md](docs/routing/README.md)
- Distribution and rollout operations: [docs/operations/distribute-client-workflow.md](docs/operations/distribute-client-workflow.md)
- Onboarding: [docs/onboarding/README.md](docs/onboarding/README.md)
- Guides by role: [docs/guides/README.md](docs/guides/README.md)
- Contributing and local setup: [docs/development/contributing.md](docs/development/contributing.md)

## Development

Before opening a PR:

1. Install [pre-commit](https://pre-commit.com/) and run `pre-commit install`
2. Run `pre-commit run --all-files` to validate locally
3. Run `pytest tests/` and `npm test` for Python and TypeScript tests

See [docs/development/contributing.md](docs/development/contributing.md) for full setup and check details.
