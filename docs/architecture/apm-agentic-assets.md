# APM agentic assets (consumer repositories)

Consumer repositories can declare **shared** and **per-workflow** agentic assets in [`apm.yml`](https://github.com/microsoft/apm) using the `x-oblt-aw` extension. The control plane resolves those assets in [`aw-prelude.yml`](../../.github/workflows/aw-prelude.yml) before calling upstream `gh-aw-*` workflows.

## Workflow identifiers

Keys under `x-oblt-aw.workflows` must match the `id` field in the org [`workflow-registry.json`](../../config/obs/workflow-registry.json) for that product line (for example `agent-suggestions`, `autodoc`, `security`). Ingress and dashboard gating continue to use compound ids `org-key:workflow-id` (for example `obs:agent-suggestions`).

## Precedence

| Layer | Behavior |
|-------|----------|
| **Platform** (`platform-additional-instructions` / `platform-inputs-json` on `aw-prelude`) | Control-plane baseline from `elastic/oblt-aw`; always applied first for instructions (prepended). Input keys can be overridden by APM per key. |
| **`x-oblt-aw.common`** | Used when no `workflows.<id>` entry exists for the running workflow. |
| **`x-oblt-aw.workflows.<id>`** | **Override:** when this key exists, `common` is ignored entirely for that run. |

There is no merge between `common` and `workflows.<id>` (no field-level fallback from common when a workflow block is present).

## Manifest example

```yaml
name: my-service
version: 1.0.0

dependencies:
  apm:
    - microsoft/apm-sample-package#v1.0.0

x-oblt-aw:
  version: 1
  common:
    setup-commands:
      - ./scripts/ai-bootstrap.sh
    inputs:
      additional-instructions: |
        Repository-wide agent guidance for all observability agentic workflows.
  workflows:
    agent-suggestions:
      inputs:
        additional-instructions: |
          Overrides common entirely for agent-suggestions only.
    autodoc:
      inputs:
        lookback-window: 3 days ago
        additional-instructions-file: .github/ai/autodoc-extra.md
```

## Runtime behavior

When the dashboard gate passes (`proceed == true`), `aw-prelude` runs the `apm-assets` job:

1. Checks out the **consumer** repository (caller context).
2. Runs [`apm install`](https://microsoft.github.io/apm/) when `apm.yml` is present (installs declared skills, plugins, MCP servers, and other APM dependencies).
3. Runs [`scripts/resolve_apm_agentic_assets.py`](../../scripts/resolve_apm_agentic_assets.py) to produce:
   - `resolved-additional-instructions`
   - `resolved-inputs-json` (merged platform + APM inputs)
   - `resolved-setup-commands-json`

Downstream `oblt-aw-*` jobs should pass `additional-instructions: ${{ needs.prelude.outputs.resolved-additional-instructions }}` and may read other keys from `resolved-inputs-json` when needed.

## Schema

JSON Schema for the extension block: [`config/schema/apm-agentic-workflows.schema.json`](../../config/schema/apm-agentic-workflows.schema.json).

## References

- [APM (Agent Package Manager)](https://github.com/microsoft/apm)
- [Multi-org agentic workflows](./multi-org-agentic-workflows.md)
- [Agentic Workflow Prelude](../../.github/workflows/aw-prelude.yml)
