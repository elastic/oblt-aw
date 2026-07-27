---
name: register-repository
description: 'Register a consumer repository for OBLT agentic workflows. Use when onboarding elastic/<repo>, editing config/<org-key>/active-repositories.json, sequencing catalog-info token policy merge, and verifying client workflow distribution plus dashboard setup.'
argument-hint: 'org-key=<obs|docs> repo=<slug> ai-assets-token-policy=<value|empty>'
user-invocable: true
---

# Register Repository

## When to use

Use this skill when you need to onboard a new consumer repository into the OBLT agentic workflow control plane.

Typical triggers:
- "Register elastic/<repo> for oblt-aw"
- "Add a repo to active-repositories.json"
- "Onboard a new repository and ensure token policy sequencing"

## Required inputs

- `org-key`: Organization config folder under `config/` (for example `obs` or `docs`).
- `repo`: Repository slug only (for example `oblt-cli`, not `elastic/oblt-cli`).
- `ai-assets-token-policy`: Token policy id or empty string.

## Procedure

1. Validate input format.
- Construct full repository name as `elastic/<repo>`.
- Reject values where `repo` already contains `elastic/`.

2. Create the catalog-info token policy PR first.
- In `elastic/catalog-info`, create the TokenPolicy change for `elastic/<repo>` and open a PR.
- Use this resource/file naming in `elastic/catalog-info`:
  - `metadata.name`: `token-policy-<repo>-oblt-aw`
  - file path: `resources/github-token-policies/token-policy-<repo>-oblt-aw.yaml`
- Use these token policy tags in `metadata.tags`:
  - `permission-contents-write`
  - `permission-issues-write`
  - `permission-pull-requests-write`
- Use this `permissionset.additional_permissions` block:

  ```yaml
  additional_permissions:
    contents: write
    issues: write
    pull_requests: write
  ```

- Record the created PR URL/number from this step as workflow state for later checks.

3. Derive `workflow-token-policy` for the org-key (only when an explicit policy is needed).
- `workflow-token-policy` in `active-repositories.json` is **optional**. Set it to `""` unless the repository needs an explicit policy for `create-token` calls via `aw-prelude`; when empty, Vault auto policy applies.
- If an explicit policy is required, select the workflow glob pattern for the org-key:
  - `obs`: `elastic/<repo>/.github/workflows/trigger-oblt-aw-*.yml`
  - `docs`: `elastic/<repo>/.github/workflows/trigger-docs-aw-*.yml`
- Keep only the part before `@` as the workflow ref base and derive the policy name:

  ```bash
  # obs
  base_ref='elastic/<repo>/.github/workflows/trigger-oblt-aw-*.yml'
  # docs
  # base_ref='elastic/<repo>/.github/workflows/trigger-docs-aw-*.yml'
  policy_name=$(printf '%s' "$base_ref" | shasum -a 256 | awk '{print "token-policy-" substr($1,1,12)}')
  ```

- Replace `<repo>` with the repository slug (for example `oblt-cli-buildkite-plugin`).
- Expected format is `token-policy-[a-f0-9]{12}`.

4. Record the workflow token policy for the registration step.
- If step 3 applies, set `workflow-token-policy` to `policy_name`.
- Ensure the created catalog-info TokenPolicy uses the same value in `spec.implementation.metadata.name`.
- If no explicit override is needed, `workflow-token-policy` will be `""` in step 5.

5. Update repository registration in control plane.
- Edit `config/<org-key>/active-repositories.json`.
- Add an entry under `repositories` with:
  - `repository`: `elastic/<repo>`
  - `workflow-token-policy`: `policy_name` from step 3, or `""` if no explicit override is needed
  - `ai-assets-token-policy`: input value or `""`
- Keep JSON formatting consistent with the file style.

6. Confirm token policy ordering contract.
- Require the matching `elastic/catalog-info` TokenPolicy change to be merged and active before merging the `elastic/oblt-aw` registration PR.
- Ensure `bound_claims.workflow_ref` matches this onboarding pattern in catalog-info:
  - `obs`: `elastic/<repo>/.github/workflows/trigger-oblt-aw-*.yml@*`
  - `docs`: `elastic/<repo>/.github/workflows/trigger-docs-aw-*.yml@*`

7. Create the secrets request issue in `elastic/observability-github-secrets`.
- These secrets are required to enable observability for GitHub Agentic Workflows in the consumer repository.
- Open this template URL and replace `<project>` with `elastic/<repo>`:

  ```text
  https://github.com/elastic/observability-github-secrets/issues/new?template=new-secret-issue-as-input.yaml&title=%5Bnew+secret%5D:+Add+Agentic+Workflows+Observability&secret=observability/agentic-workflows.tf&project=<project>
  ```

- For this skill, set `project` to `elastic/<repo>`.
- Record the created issue URL/number as workflow state for later checks.

8. Verify downstream automation after merge to `main`.
- Confirm `distribute-client-workflow` creates or updates the client workflow PR in `elastic/<repo>`.
- Confirm `sync-control-plane-dashboard` creates or updates issue `[oblt-aw] Control Plane Dashboard` with label `oblt-aw/dashboard`.

9. Confirm enablement flow.
- Note that workflow enablement is controlled in the dashboard issue task list, not in `active-repositories.json`.
- Ask humans to check or uncheck workflows in the issue to opt in or out.

## Output checklist

Return a concise checklist with:
- Updated file and exact entry added.
- Catalog-info PR created and computed `workflow-token-policy` id.
- Catalog-info TokenPolicy includes expected `additional_permissions` and `metadata.tags`.
- `elastic/observability-github-secrets` issue URL/number created from the template.
- Whether catalog-info TokenPolicy merge status is confirmed.
- Whether distribution PR and dashboard issue were verified.
- Any blockers or missing permissions.

## References

- `docs/onboarding/registering-a-repository.md`
- `docs/onboarding/adopting-agentic-workflows.md`
- `docs/operations/distribute-client-workflow.md`
- `docs/workflows/sync-control-plane-dashboard.md`
- `.github/remote-workflow-template/`
