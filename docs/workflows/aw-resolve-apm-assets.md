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
| `install-apm-packages` | boolean | `true` | Run `apm install` when `apm.yml` is present |
| `ingress-event-name` | string | `""` | Relayed `github.event_name` from ingress (prepended gh-aw context block) |
| `ingress-event-action` | string | `""` | Relayed `github.event.action` from ingress |
| `ingress-event-payload-json` | string | `""` | Relayed `github.event` JSON from ingress; drives authoritative PR/issue numbers in agent prompts and optional PR checkout setup commands |

### Outputs

| Output | Description |
|--------|-------------|
| `apm-manifest-present` | Consumer has `apm.yml` / `apm.yaml` |
| `apm-extension-present` | Manifest contains `x-oblt-aw` |
| `asset-source` | `none`, `common`, or `workflow` |
| `resolved-additional-instructions` | Relayed ingress context (when present), then merged platform + APM instructions |
| `resolved-inputs-json` | Merged platform + APM inputs |
| `resolved-setup-commands-json` | Relayed PR checkout commands (when applicable), then APM `setup-commands` |

### Relayed GitHub context

Consumer entrypoints relay the original webhook payload through ingress (`ingress-event-payload-json`). Upstream `gh-aw-*` lock files still read native `github.event`, which is empty under the `workflow_dispatch` entrypoint model. This workflow injects an authoritative **Relayed ingress context** block at the top of `resolved-additional-instructions` and, for pull requests, prepends authenticated PR checkout setup commands (`gh auth setup-git`, then `git fetch` / `git checkout`) to `resolved-setup-commands-json`. Callers should pass `setup-commands: ${{ join(fromJSON(needs.<resolve-job>.outputs.resolved-setup-commands-json), ' && ') }}` to `gh-aw-*` jobs that accept the input.

```yaml
  resolve-apm-assets:
    uses: ./.github/workflows/aw-resolve-apm-assets.yml
    with:
      control-plane-workflow: oblt-aw-example.yml
      ingress-event-name: ${{ inputs.ingress-event-name }}
      ingress-event-action: ${{ inputs.ingress-event-action }}
      ingress-event-payload-json: ${{ inputs.ingress-event-payload-json }}
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
      setup-commands: ${{ join(fromJSON(needs.resolve-apm-assets.outputs.resolved-setup-commands-json), ' && ') }}
```

Place each `resolve-apm-assets` job **immediately before** the `gh-aw-*` job it feeds, after any prerequisite gates (verify, discover, evaluate-trigger, etc.). Use the **same `if` expression** on resolve and agent so APM install/resolution runs only when the agent will.

Examples with upstream gates: [oblt-aw-automerge.yml](../../.github/workflows/oblt-aw-automerge.yml) (resolve after verify + dependency collection), [oblt-aw-resource-not-accessible-by-integration-detector.yml](../../.github/workflows/oblt-aw-resource-not-accessible-by-integration-detector.yml) (resolve after discover). Multi-agent wrappers use one resolve job per `gh-aw-*` invocation — see [oblt-aw-autodoc.yml](../../.github/workflows/oblt-aw-autodoc.yml).

## References

- [APM manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/) — official `apm.yml` format and vendor extension fields
- [APM agentic assets architecture](../architecture/apm-agentic-assets.md)
- [Agentic Workflow Prelude](aw-prelude.md)
- [scripts/resolve_apm_agentic_assets.py](../../scripts/resolve_apm_agentic_assets.py)
- [scripts/ingress_github_context.py](../../scripts/ingress_github_context.py)
