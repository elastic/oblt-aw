# Onboard a repository

## Overview

Use this guide when you want OBLT Agentic Workflows (`oblt-aw`) in a repository that is **not yet registered**. You open one issue in `elastic/oblt-aw`; automation opens the required pull requests; you merge them; then you enable workflows from the Control Plane Dashboard in your repository.

Technical registration detail for maintainers and agents: [Registering resources](../../onboarding/registering-a-repository.md).

## Prerequisites

- The target repository is under the `elastic` GitHub organization.
- You have **write** access (or higher) on [elastic/oblt-aw](https://github.com/elastic/oblt-aw). Opening issues alone is not enough: GitHub only applies the form label when the creator has push access, and the agent role gate requires `write` / `maintain` / `admin`.
- You (or a teammate) can merge pull requests in `elastic/catalog-info`, `elastic/oblt-aw`, `elastic/observability-github-settings`, and—when needed—`elastic/observability-github-secrets`.

## Steps

1. **Open the onboard issue** — Go to [elastic/oblt-aw Issues](https://github.com/elastic/oblt-aw/issues) → **New issue** → **Onboard a repository**.

2. **Fill only two fields**
   - **Repository** — `elastic/<repo>` (example: `elastic/my-repo`).
   - **Organization key** — `obs` or `docs` (matches a `config/<org-key>/` folder in `elastic/oblt-aw`).

3. **Submit** — The form applies the label `oblt-aw/onboard/repository`. That starts the in-repo agent `gh-aw-onboard-repository` in `elastic/oblt-aw` only (this is **not** a consumer catalog / Control Plane Dashboard workflow).

4. **Wait for the agent checklist comment** — The agent posts progress on the issue and opens **separate, normal (non-draft) pull requests**, one concern per PR. Typical PRs:

   | Order | Repository | What it changes |
   |------:|------------|-----------------|
   | 1 | `elastic/catalog-info` | TokenPolicy for client `create-token` |
   | 2 | `elastic/oblt-aw` | Entry in `config/<org-key>/active-repositories.json` |
   | 3 | `elastic/observability-github-settings` | Vault app in classic branch-protection `pull_request_bypassers` |
   | 4 | `elastic/observability-github-secrets` | When org workflow docs’ **Prerequisites** (or **API / Interface**) require consumer secrets; otherwise the agent notes “none” |

5. **Merge manually in order** — Humans merge. Merge the **catalog-info** TokenPolicy PR **before** the **oblt-aw** registration PR. Merge settings (and secrets, if any) before relying on automerge or secret-backed workflows in production. Auto-merge of these PRs is **out of scope** for now.

6. **After the oblt-aw registration PR merges to `main`** — Existing automation creates:
   - A **client template install/update PR** in your repository (`trigger-obs-aw-*.yml` or docs equivalents) via [distribute-client-workflow](../../operations/distribute-client-workflow.md).
   - A **Control Plane Dashboard** issue in your repository via [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md).

   Merge the client install PR. Confirm the dashboard issue exists (title `[oblt-aw] Control Plane Dashboard`, label `oblt-aw/dashboard`).

7. **Enable or disable workflows** — In your repository, open the Control Plane Dashboard issue and check or uncheck the workflows you want. GitHub saves on click. Workflows apply on the next supported client trigger. See [Opt in or opt out](opt-in-opt-out.md).

## Troubleshooting

- **No agent comment / no PRs** — Confirm you have **write** on `elastic/oblt-aw` and the issue has `oblt-aw/onboard/repository` (without write, GitHub drops the form label). Check the Actions run for `gh-aw-onboard-repository`. Cross-repo PR creation needs the agent TokenPolicy / minted token (see [gh-aw-onboard-repository](../../workflows/gh-aw-onboard-repository.md)).
- **Retry after a partial run** — Remove and re-apply the `oblt-aw/onboard/repository` label. If open PRs with title prefix `[oblt-aw][onboard]` for that repository already exist, the agent comments with those links and does not open duplicates.
- **Registration merged too early** — If `oblt-aw` registration landed before catalog TokenPolicy was active, follow [Registering resources — troubleshooting](../../onboarding/registering-a-repository.md#troubleshooting).
- **No install PR or dashboard** — Confirm the repository appears in `config/<org-key>/active-repositories.json` on `main`, then see [distribute-client-workflow](../../operations/distribute-client-workflow.md) and [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md).

## References

- [Registering resources](../../onboarding/registering-a-repository.md) — technical procedure the agent follows
- [Onboarding index](../../onboarding/README.md)
- [Control Plane Dashboard](../../operations/control-plane-dashboard.md)
- [gh-aw-onboard-repository](../../workflows/gh-aw-onboard-repository.md)
