# Automerge services

## Overview

Automerge has two layers:

1. **Parent toggle:** turns Automerge on for the repository.
2. **Service checkboxes:** choose which dependency-update categories Automerge may merge.

This lets a team say: “We trust Automerge for these update types, but not for the rest.”

If a service is **enabled**, matching bot PRs can continue through the normal validation, approval, and merge flow. If a service is **disabled**, those PRs stay unmerged; use the Automerge link on the Control Plane Dashboard or the dependency-collection gate comment to review this catalogue and enable the right category if you want it.

Technical details for eligibility, validation, approval, tokens, and merge behavior live in:

- [Automerge workflow](../../workflows/obs-aw-automerge.md)
- [Automerge routing](../../routing/automerge-routing.md)

## What each service means

| Service | What it covers | Representative files | Why enable it | Enabled vs disabled |
|---------|----------------|----------------------|---------------|---------------------|
| GitHub Actions bumps | Version updates for GitHub Actions and composite actions | `.github/workflows/**`, `.github/actions/**`, `**/action.yml`, `**/action.yaml` | Keep CI actions current without hand-merging routine bumps | Enabled: qualifying bumps can merge. Disabled: those PRs stop at the dashboard gate. |
| pre-commit hook updates | Dependency updates for pre-commit hooks | `.pre-commit-config.yaml` | Keep local and CI hook versions moving with low review overhead | Enabled: hook bump PRs may merge. Disabled: they stay queued. |
| Python dependencies | Python package and lockfile updates | `**/pyproject.toml`, `**/requirements.txt`, `**/requirements-*.txt`, `**/poetry.lock`, `**/Pipfile`, `**/Pipfile.lock` | Useful when Python bumps are routine and low risk for your repo | Enabled: matching Python update PRs may merge. Disabled: they require manual attention. |
| Go dependencies | Go module and sum updates | `go.mod`, `go.sum`, `**/go.mod`, `**/go.sum` | Good for teams that accept standard Go dependency refreshes automatically | Enabled: Go dependency PRs may merge. Disabled: they remain unmerged. |
| Update beats | elastic-agent update-beats bumps | `NOTICE.txt`, `NOTICE-fips.txt`, `go.mod`, `go.sum`, `beats` | Helpful when update-beats changes are expected and well understood | Enabled: update-beats PRs may merge. Disabled: they wait for a maintainer. |
| Node dependencies | npm/yarn/pnpm manifest and lockfile updates | `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `**/package.json`, `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml` | Keep JavaScript dependency maintenance routine and predictable | Enabled: matching Node PRs may merge. Disabled: they are left for manual review. |
| Terraform / OpenTofu | Terraform, OpenTofu, and Terragrunt dependency updates | `**/*.tf`, `**/*.tfvars`, `**/*.tfvars.json`, `**/.terraform.lock.hcl`, `**/terragrunt.hcl`, `**/.opentofu-version`, `**/.terraform-version`, `**/.terragrunt-version` | Useful for infrastructure repos that want safe, routine IaC refreshes merged automatically | Enabled: matching IaC PRs may merge. Disabled: they do not. |
| Open Policy Agent | Rego policies plus OPA version and configuration updates | `**/*.rego`, `**/.opa-version`, `**/opa.yaml`, `**/opa.yml` | Keep policy code and OPA tooling current while preserving review control elsewhere | Enabled: OPA policy/version/config update PRs may merge. Disabled: they stay pending. |
| VM / container images | CI runner, Docker/container, Compose, and snapshot-environment image-pin updates | `.buildkite/**`, `**/Dockerfile`, `**/Dockerfile.*`, `**/docker-compose.yml`, `**/docker-compose.yaml`, `testing/environments/snapshot.yml` | Handy when image-pin bumps are expected and you trust the matching automation path | Enabled: image-pin PRs may merge. Disabled: they are held back for manual review. |
| Package version | `.package-version` bump automation | `.package-version`, `**/.package-version` | Useful for repos that treat version file bumps as routine automation | Enabled: version-bump PRs may merge. Disabled: they remain open. |

## Choosing what to enable

- Start with the **parent Automerge toggle**.
- Enable only the service categories that match your repository.
- If you are unsure, leave a category disabled until you are comfortable with the risk.

## Related dashboard behavior

- The dashboard shows each service with a concise label and description.
- The dashboard's **Automerge** link opens this guide for service selection, while the technical workflow and routing docs above cover implementation details.
- The checkbox marker is the real parsing contract; the visible text is for humans.
- Parent and service checkboxes are still subject to the normal Automerge workflow rules.
