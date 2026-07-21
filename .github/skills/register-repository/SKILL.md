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
- Record the created PR URL/number from this step as workflow state for later checks.

3. Derive `workflow-token-policy` with a deterministic rule.
- Compute the policy id from this exact base string pattern:
  - `elastic/<repo>/.github/workflows/trigger-oblt-aw-*.yml`
- Command:

  ```bash
  policy_id=$(printf '%s' 'elastic/<repo>/.github/workflows/trigger-oblt-aw-*.yml' | shasum -a 256 | awk '{print $1}' | cut -c1-12)
  policy_name="token-policy-${policy_id}"
  ```
 
- Replace `<repo>` with the repository slug (for example `oblt-cli-buildkite-plugin`).
- Expected format is `token-policy-[a-f0-9]{12}`.

4. Derive the workflow token policy value from the PR.
- Set `workflow-token-policy` to `policy_name` from step 3.
- Ensure the created catalog-info TokenPolicy uses the same value in `spec.implementation.metadata.name`.

5. Update repository registration in control plane.
- Edit `config/<org-key>/active-repositories.json`.
- Add an entry under `repositories` with:
  - `repository`: `elastic/<repo>`
  - `workflow-token-policy`: PR-derived token policy id from step 4
  - `ai-assets-token-policy`: input value or `""`
- Keep JSON formatting consistent with the file style.

6. Confirm token policy ordering contract.
- Require the matching `elastic/catalog-info` TokenPolicy change to be merged and active before merging the `elastic/oblt-aw` registration PR.
- Ensure `bound_claims.workflow_ref` uses `@refs/heads/main` for each installed client workflow that calls `create-token`.

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
