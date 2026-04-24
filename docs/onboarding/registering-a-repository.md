# Registering resources for OBLT agentic workflows

## Overview

This guide onboards:

1. **GitHub repository** — Listed in `elastic/oblt-aw` under `config/<org-key>/active-repositories.json` so [distribute-client-workflow](../operations/distribute-client-workflow.md) can install the client template and [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) can maintain the Control Plane Dashboard issue.
2. **GitHub token policy (Backstage Resource) in `elastic/catalog-info`** — **Always** created for each newly registered consumer repository. It backs [elastic/oblt-actions/github/create-token@v1](https://github.com/elastic/oblt-actions/tree/v1/github/create-token) for `oblt-aw.yml` so workflows can use an ephemeral token where `GITHUB_TOKEN` is insufficient ([gh-aw-security-detector](../workflows/gh-aw-security-detector.md)).

The **catalog-info** token policy must be **merged and active** before you merge the **`elastic/oblt-aw`** change that adds the repository to `main`. Otherwise automation in the consumer repository can call `create-token` before the policy exists.

## Convention: Elastic organization and repository slug

Consumer repositories in this guide are always under the **`elastic`** GitHub organization. **`<repo>`** means the **repository slug only** (for example `oblt-cli`). Do not embed `elastic/` inside the placeholder—write the slug alone. Where GitHub or config requires **`owner/repo`**, use **`elastic/<repo>`** as the full name.

## Prerequisites

- Permission to open pull requests to **`elastic/oblt-aw`**, **`elastic/catalog-info`**, and (for secrets) **`elastic/observability-github-secrets`** as required by your team’s process.
- Layout and approval rules inside **`elastic/catalog-info`** are **Unknown** in this repository—follow that repo’s maintainers.

## Steps

1. **Create a new branch on `elastic/oblt-aw`, choose the org, and add the repository** — From an up-to-date `main`, create a **feature branch** (for example `git checkout -b feat/oblt-aw-register-<repo>`; exact naming is your team’s convention). On that branch only, identify the owning **`config/<org-key>/`** folder ([multi-org design](../architecture/multi-org-agentic-workflows.md)) and edit **`active-repositories.json`** to include **`elastic/<repo>`** in **`owner/repo`** form. Use either JSON shape ([distribute-client-workflow](../operations/distribute-client-workflow.md)):

   **Object form:**

   ```json
   {
     "repositories": [
       "elastic/<repo>"
     ]
   }
   ```

   **List form:**

   ```json
   [
     "elastic/<repo>"
   ]
   ```

   Commit on the branch and open a pull request to **`main`**, but **do not merge** that registration PR until **step 3** is complete.

   - **`id-token: write` on the client** — Confirm the [client template](../workflows/oblt-aw-client-template.md) in **`elastic/oblt-aw`** grants **`id-token: write`** on the job that calls ingress so nested workflows can call `create-token` after the distributed `oblt-aw.yml` is installed. If the template is insufficient, fix it in **`elastic/oblt-aw`** on **`main`** (separate change) before merging this registration or landing the token policy that depends on OIDC in the consumer.

2. **Add the GitHub token policy in `elastic/catalog-info` (mandatory)** — In **[`elastic/catalog-info`](https://github.com/elastic/catalog-info)**, add or update the Backstage **`Resource`** / **`TokenPolicy`** for this consumer repository. Follow the [appendix template](#appendix-token-policy-yaml-template) and complete every subpoint below before opening the catalog PR (or fold them into one catalog PR as your process allows).

   - **a. `workflow_ref`** — Set `bound_claims.workflow_ref` **always** to **`elastic/<repo>/.github/workflows/oblt-aw.yml@refs/heads/main`**. The branch ref is **always** `refs/heads/main` for this onboarding contract. The appendix shows the same value.

   - **b. `additional_permissions`** — Populate `permissionset.additional_permissions` with the **union** of GitHub permissions required to run **every** agentic workflow listed for the **selected org** in `elastic/oblt-aw`’s `config/<org-key>/workflow-registry.json` (all `workflows[].id` values for that org). For each registry entry, use the matching **`docs/workflows/gh-aw-*.md`** (and routing docs where relevant) in `elastic/oblt-aw` to determine token, OIDC, and secret requirements. There is no single canonical YAML block maintained here (**Unknown**); Platform Engineering and **`elastic/catalog-info`** reviewers approve the final mapping ([Ephemeral tokens / GitHub Actions](https://docs.elastic.dev/platform-engineering-productivity/services/ephemeral-tokens/github-actions)). The shape is a mapping of permission names to access levels; for example (illustrative only—not the full union for any org):

     ```yaml
     additional_permissions:
       contents: read
       issues: write
     ```

   - **c. Policy metadata name (`token-policy-<calculated-sha>`)** — The **`calculated-sha`** (or equivalent stable id in `metadata.name`) must be derived from the **`workflow_ref` string with the branch / ref segment removed**—that is, from the repository-scoped workflow path only (for example **`elastic/<repo>/.github/workflows/oblt-aw.yml`** without `@refs/heads/main`). The exact hash algorithm is owned by **`elastic/catalog-info`** (**Unknown** here); **mirror an existing token policy resource** in that repository and match its naming rules.

   - **d. Author the manifest** — Write the YAML file(s) under paths required by **`elastic/catalog-info`**, filling the template fields from **a–c** and the [appendix](#appendix-token-policy-yaml-template).

3. **Merge the `elastic/catalog-info` change** — Complete review and merge (or otherwise land) the token policy on the branch **`elastic/catalog-info`** uses for production so vault and OIDC configuration are **active** before you merge **`elastic/oblt-aw`** `main` in step 4.

4. **Merge the `elastic/oblt-aw` registration pull request** — Merge the feature branch from step **1** into **`main`**. That triggers **distribute-client-workflow** and **sync-control-plane-dashboard** for the new target.

5. **Verify the client workflow distribution pull request** — After the push to **`main`**, confirm **distribute-client-workflow** produced an install or update PR in **`elastic/<repo>`** that adds or updates `.github/workflows/oblt-aw.yml` calling **`elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main`** ([client template](../workflows/oblt-aw-client-template.md)). Use **`workflow_dispatch`** / `force` from [distribute-client-workflow](../operations/distribute-client-workflow.md) if your runbook requires it.

6. **Verify the Control Plane Dashboard issue** — Confirm **sync-control-plane-dashboard** created or updated the open issue labeled **`oblt-aw/dashboard`** with title **`[oblt-aw] Control Plane Dashboard`** in **`elastic/<repo>`** ([sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md), [control-plane-dashboard](../operations/control-plane-dashboard.md)).

7. **Configure Action secrets through `elastic/observability-github-secrets`** — Do **not** rely only on per-repository **Settings → Secrets** in GitHub unless your process explicitly allows it. For Elastic Observability repositories, provision **`COPILOT_GITHUB_TOKEN`** for **`elastic/<repo>`** so it matches the [client template](../workflows/oblt-aw-client-template.md) (`COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}`). Other workflow secrets, if any, are listed in [docs/workflows/](../workflows/) in **`elastic/oblt-aw`**. Use either option below (or follow additional processes in **[`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets)**).

   - **Humans** — Open the pre-filled new-issue form to request the Agentic Copilot credential for the target repository: [Create `COPILOT_GITHUB_TOKEN` (new secret as input) — `elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets/issues/new?template=new-secret-issue-as-input.yaml&title=%5Bnew+secret%5D:+Add+Agentic+Copilot+Credentials&secret=github/copilot/agentic.tf). Complete and submit the issue per that template’s instructions.

   - **Agents** — Create a new issue in **`elastic/observability-github-secrets`** with label **`new-secret-as-input`**. Use a title aligned with the secret request (for example **`[new secret]: Add Agentic Copilot Credentials`**). Set the body to:

     ```markdown
     ### Secret Name to be created

     github/copilot/agentic.tf

     ### Your project name (apm-server, beats, etc)

     {{repo}}
     ```

     Replace **`{{repo}}`** with the target repository **slug** (the same value as **`<repo>`** in this guide; not `elastic/<repo>`).

8. **Humans — Opt workflows in or out from the Control Plane Dashboard** — **Humans** complete this step in the GitHub web UI by editing the dashboard issue. Workflow enablement is **not** configured in `active-repositories.json`; it is controlled only through the **Control Plane Dashboard** issue in **`elastic/<repo>`** (task-list checkboxes and `<!-- oblt-aw:<org-key>:<workflow-id> -->` markers). Read [Dashboard gating](adopting-agentic-workflows.md#dashboard-gating-reference) and complete [steps 1–2 in *Adopting a new remote agentic workflow*](adopting-agentic-workflows.md#consumer-repositories): confirm rows exist after sync, then check or uncheck workflows to match policy; save the issue and wait for a **client** run for changes to apply ([oblt-aw-client-template](../workflows/oblt-aw-client-template.md)).

## Appendix: Token policy YAML template

Validate against the current schema and reviewers in **`elastic/catalog-info`** before merging. **`<repo>`** is the slug only; **`elastic/<repo>`** is the full `owner/repo` ([convention](#convention-elastic-organization-and-repository-slug)). Apply step **2c** for **`token-policy-<calculated-sha>`**.

```yaml
# yaml-language-server: $schema=https://gist.githubusercontent.com/elasticmachine/988b80dae436cafea07d9a4a460a011d/raw/rre.schema.json
#
# Owner/org: elastic (fixed for this onboarding). <repo>: slug only.
# token-policy-<repo>-oblt-aw registers the GitHub Token Policy in Backstage.

apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: token-policy-<repo>-oblt-aw
  links:
    - url: https://github.com/elastic/catalog-info/tree/main/resources/github-token-policies/token-policy-<repo>-oblt-aw.yaml
      title: Definition
      icon: github
spec:
  type: token-policy
  owner: group:observablt-ci
  implementation:
    apiVersion: github.elastic.dev/v1
    kind: TokenPolicy
    metadata:
      name: token-policy-<calculated-sha>
    spec:
      vault:
        - ci-prod
      auth:
        type: oidc
        identity_provider: github
        bound_claims:
          # workflow_ref is always this exact string (refs/heads/main only)
          workflow_ref: elastic/<repo>/.github/workflows/oblt-aw.yml@refs/heads/main
      cached: true
      permissionset:
        additional_permissions: {}
        selector:
          - kind: Resource
            # selector.repository is the same owner/repo string elastic/<repo>
            spec.implementation.spec.repository: elastic/<repo>
            spec.implementation.apiVersion: github.elastic.dev/v1
            spec.type: github-repository
```

Draft placeholder for `additional_permissions` (not valid YAML until substituted with the union from step **2b**):

```text
        additional_permissions:
          {{agentic-workflows-permissions}}
```

**Reference only — token policies used inside `elastic/oblt-aw` (control plane, not consumer copy-paste):**

| Workflow / context | `token-policy-…` id (from YAML in this repo) |
|--------------------|-----------------------------------------------|
| [distribute-client-workflow.yml](../../.github/workflows/distribute-client-workflow.yml) | `token-policy-63405ab45244` |
| [sync-control-plane-dashboard.yml](../../.github/workflows/sync-control-plane-dashboard.yml) | `token-policy-8b60ba56dd3f` |
| [gh-aw-security-detector.yml](../../.github/workflows/gh-aw-security-detector.yml) | `token-policy-461e92da2625` |
| [gh-aw-automerge.yml](../../.github/workflows/gh-aw-automerge.yml) (ephemeral token step) | `token-policy-5a5dcea1ee13` |

## Troubleshooting

- **No install PR in the target repository** — See [distribute-client-workflow](../operations/distribute-client-workflow.md): path filters, matrix outputs, and `workflow_dispatch` / `force`.
- **No dashboard issue** — Confirm **`elastic/<repo>`** is in the union of per-org `active-repositories.json` files and that [sync-control-plane-dashboard](../workflows/sync-control-plane-dashboard.md) completed on **`main`**.
- **Ephemeral token / OIDC failures** — Match `workflow_ref` exactly to **`elastic/<repo>/.github/workflows/oblt-aw.yml@refs/heads/main`**; confirm **`id-token: write`** on the client job ([oblt-aw-client-template](../workflows/oblt-aw-client-template.md)); confirm the catalog policy merged **before** merging **`elastic/oblt-aw`** registration to **`main`**.

## References

- [Distribution operation: distribute-client-workflow](../operations/distribute-client-workflow.md)
- [Sync Control Plane Dashboard](../workflows/sync-control-plane-dashboard.md)
- [Multi-organization agentic workflows](../architecture/multi-org-agentic-workflows.md)
- [gh-aw-security-detector](../workflows/gh-aw-security-detector.md)
- [Adopting a new remote agentic workflow](adopting-agentic-workflows.md)
