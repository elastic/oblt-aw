# Workflow: `aw-resolve-apm-assets.yml`

## Overview

Source file: [.github/workflows/aw-resolve-apm-assets.yml](../../.github/workflows/aw-resolve-apm-assets.yml)

Resolves consumer [`apm.yml`](https://github.com/microsoft/apm) agentic assets for **one** `gh-aw-*` invocation. Call this reusable immediately before each job that `uses` an upstream agentic workflow lock file.

CI enforces the contract via [scripts/validate_aw_workflow_resolve_apm_assets.py](../../scripts/validate_aw_workflow_resolve_apm_assets.py): every local `*-aw-*` workflow with at least one `gh-aw-*` call must invoke `aw-resolve-apm-assets.yml` at least once per agent job (for example `oblt-aw-autodoc.yml` uses two resolve jobs for audit and fix).

Wrappers that only gate or run scripts (for example `oblt-aw-security-detector.yml`) do not call this workflow.

## Contract

### Inputs

| Input | Type | Default | Purpose |
|-------|------|---------|---------|
| `control-plane-workflow` | string | (required) | Basename of the calling wrapper; used to resolve org key and registry workflow id for `x-oblt-aw.<org-key>.workflows.<id>` selection |
| `platform-additional-instructions` | string | `""` | Control-plane baseline text for this agent invocation (prepended before repo APM instructions) |
| `platform-inputs-json` | string | `"{}"` | JSON object of platform inputs; APM `inputs` override per key |
| `install-apm-packages` | boolean | `true` | Run [`microsoft/apm-action`](https://github.com/microsoft/apm-action) when `apm.yml` is present (installs the APM CLI and runs `apm install`) |

Private GitHub dependencies use one of two auth paths during `apm install`:

- When `ai-assets-token-policy` is set for the consumer repository in `config/<org>/active-repositories.json`, the workflow mints an ephemeral token via `elastic/oblt-actions/github/create-token@v1` and passes it to `apm-action` as `github-token` (forwarded internally as `GITHUB_APM_PAT`).
- When `ai-assets-token-policy` is empty, `github-token` falls back to the job `GITHUB_TOKEN` (`contents: read`), which is sufficient for same-repository private path dependencies.

The `workflow-token-policy` field (exposed to route workflows as `shared-token-policy` via `aw-prelude`) is separate and covers agentic workflow `create-token` steps, not APM package clones.

### Outputs

| Output | Description |
|--------|-------------|
| `apm-manifest-present` | Consumer has `apm.yml` / `apm.yaml` |
| `apm-extension-present` | Manifest contains `x-oblt-aw` |
| `asset-source` | `none`, `common`, or `workflow` |
| `resolved-additional-instructions` | Merged platform + APM instructions |
| `resolved-inputs-json` | Merged platform + APM inputs |
| `resolved-setup-commands-json` | JSON array of shell commands from the selected asset block (`setup-commands` inline string/list and optional `setup-commands-file`) |

### Typical caller pattern

Place each `resolve-apm-assets` job **immediately before** the `gh-aw-*` job it feeds, after any prerequisite gates (verify, discover, evaluate-trigger, etc.). Use the **same `if` expression** on resolve and agent so APM install/resolution runs only when the agent will.

```yaml
jobs:
  prelude:
    uses: ./.github/workflows/aw-prelude.yml
    with:
      control-plane-workflow: oblt-aw-example.yml

  # ... optional intermediate jobs (verify, discover, menu scripts, etc.) ...

  resolve-apm-assets:
    needs: [prelude]  # plus any jobs the agent also needs
    if: >-
      needs.prelude.outputs.proceed == 'true' &&
      <same conditions as the agent job below>
    uses: ./.github/workflows/aw-resolve-apm-assets.yml
    with:
      control-plane-workflow: oblt-aw-example.yml
      platform-additional-instructions: |
        Platform prompt for this agent invocation.

  agent:
    needs: [prelude, resolve-apm-assets]  # resolve must be a direct dependency
    if: >-
      needs.prelude.outputs.proceed == 'true' &&
      <same conditions as resolve-apm-assets>
    uses: elastic/ai-github-actions/.github/workflows/gh-aw-example.lock.yml@main
    with:
      additional-instructions: ${{ needs.resolve-apm-assets.outputs.resolved-additional-instructions }}
```

Examples with upstream gates: [oblt-aw-automerge.yml](../../.github/workflows/oblt-aw-automerge.yml) (resolve after verify + dependency collection), [oblt-aw-resource-not-accessible-by-integration-detector.yml](../../.github/workflows/oblt-aw-resource-not-accessible-by-integration-detector.yml) (resolve after discover). Multi-agent wrappers use one resolve job per `gh-aw-*` invocation — see [oblt-aw-autodoc.yml](../../.github/workflows/oblt-aw-autodoc.yml).

## References

- [APM manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/) — official `apm.yml` format and vendor extension fields
- [APM agentic assets architecture](../architecture/apm-agentic-assets.md)
- [Agentic Workflow Prelude](aw-prelude.md)
- [scripts/resolve_apm_agentic_assets.py](../../scripts/resolve_apm_agentic_assets.py)
