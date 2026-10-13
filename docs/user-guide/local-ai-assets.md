# Define local AI assets

## Overview

Agentic workflows ship with framework defaults. In your **target repository**, you can add local AI assets so agents get repo-specific instructions, setup commands, and (optionally) APM packages before they run.

Declare those assets in [`apm.yml`](https://github.com/microsoft/apm) at the repository root, under the `x-oblt-aw` extension. When an enabled agentic workflow runs, [aw-resolve-agentic-assets](../workflows/aw-resolve-agentic-assets.md) reads that file from your repo and resolves instructions, inputs, and setup commands for the agent job.

You do **not** need `apm.yml` to enable workflows from the Control Plane dashboard. Add it only when you want to customize behavior for your repository.

Schema, precedence, and runtime detail: [APM agentic assets](../architecture/apm-agentic-assets.md).

## Prerequisites

- The repository is registered and client triggers are installed ([Onboard a repository](onboard-a-repository.md)).
- The agentic workflow you care about is enabled on the Control Plane dashboard ([Enable or disable an agentic workflow](enable-a-new-workflow.md)).
- You know your **org key** (`obs`, `docs`, …) and the workflow **id** from that org’s registry (for example `agent-suggestions`, `autodoc`). Dashboard gating uses compound ids such as `obs:agent-suggestions`; keys under `x-oblt-aw.<org-key>.workflows` use the short id only.

## What you can set

Under `x-oblt-aw.<org-key>`, each org block needs a `common` section. Optional `workflows.<id>` (and `inner-workflows.<basename>`) blocks **replace** `common` for that run — they do not merge field-by-field.

| Asset | Where | Effect |
|-------|--------|--------|
| Extra agent instructions | `inputs.additional-instructions` or `inputs.additional-instructions-file` | Appended after framework and platform prompts |
| Local Markdown fragments | `<org-key>.fragments` + `additional-instructions-fragments` | Ordered fragment files, then inline instructions |
| Setup shell | `setup-commands` and optional `setup-commands-file` | Runs in the consumer checkout before the agent engine |
| Workflow inputs | other keys under `inputs` | Overrides platform inputs per key (for example `lookback-window` for autodoc) |
| APM packages | top-level `dependencies.apm` | Installed with `apm install` when `apm.yml` is present |

## Steps

1. **Add or edit `apm.yml` at the repository root** — Include `x-oblt-aw.version: 1` and an org block for your fleet. Keep `common` for shared guidance; add `workflows.<id>` only when one workflow needs different assets.

2. **Put shared guidance in `common`** — Use this for setup and instructions that apply to every agentic workflow in that org when no per-workflow override exists.

3. **Override per workflow when needed** — If you define `workflows.<id>`, that block is used **instead of** `common` for that workflow (full override). Copy any shared setup or instructions you still need into the override. For wrappers that share one dashboard row, use `inner-workflows.<wrapper-basename>` the same way (full override of the parent workflow block).

4. **Optional: local fragments** — Map fragment ids to repo-relative Markdown paths under `<org-key>.fragments`, then list those ids in `additional-instructions-fragments` on the asset block you want.

5. **Commit on the default branch (or the branch the workflow checks out)** — Resolution uses the consumer checkout for that run. After merge, trigger the agentic workflow (or wait for its normal event) and confirm the agent followed the new guidance.

## Minimal example

Repository-wide Observability guidance, plus a full override for `agent-suggestions`:

```yaml
name: my-service
version: 1.0.0

x-oblt-aw:
  version: 1
  obs:
    fragments:
      repo-conventions: .github/ai/fragments/repo-conventions.md
    common:
      setup-commands:
        - ./scripts/ai-bootstrap.sh
      additional-instructions-fragments:
        - repo-conventions
      inputs:
        additional-instructions: |
          Prefer existing package managers and CI scripts in this repository.
    workflows:
      agent-suggestions:
        setup-commands:
          - ./scripts/ai-bootstrap.sh
        inputs:
          additional-instructions: |
            Overrides obs.common for agent-suggestions only.
            Focus suggestions on CI and Buildkite failures.
```

Optional APM package dependencies (skills, plugins, MCP servers) use the standard APM `dependencies.apm` list in the same file. Private GitHub packages need `ai-assets-token-policy` set for the repo in `config/<org-key>/active-repositories.json` (maintainer change); otherwise install uses the job `GITHUB_TOKEN`.

## Check that it applied

1. Open the GitHub Actions run for the agentic workflow in your repository.
2. Find the resolve job (often named `resolve-apm-assets`) that calls `aw-resolve-agentic-assets`.
3. Confirm it saw your manifest (`apm-manifest-present` / `apm-extension-present`) and that `asset-source` is `common`, `workflow`, or `inner-workflow` as you expect (`none` means the org block did not apply).

If `apm install` fails, the resolve job warns and continues; instruction resolution still runs. Fix the package path or token policy if agents need those packages.

## References

- [APM agentic assets](../architecture/apm-agentic-assets.md) — full structure, precedence, and schema
- [Resolve agentic assets](../workflows/aw-resolve-agentic-assets.md) — reusable workflow contract
- [APM manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/) — official `apm.yml` format
- [Enable or disable an agentic workflow](enable-a-new-workflow.md)
