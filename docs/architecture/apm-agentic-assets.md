# APM agentic assets (consumer repositories)

Consumer repositories can declare **shared** and **per-workflow** agentic assets in [`apm.yml`](https://github.com/microsoft/apm) using the `x-oblt-aw` extension. The control plane resolves those assets in [`aw-resolve-apm-assets.yml`](../../.github/workflows/aw-resolve-apm-assets.yml) immediately before each upstream `gh-aw-*` invocation (not in [`aw-prelude.yml`](../../.github/workflows/aw-prelude.yml)).

## Workflow identifiers

Keys under `x-oblt-aw.<org-key>.workflows` must match the `id` field in that org’s [`workflow-registry.json`](../../config/obs/workflow-registry.json) (for example `agent-suggestions` under `obs`, `docs-pr-ai-menu` under `docs`). Ingress and dashboard gating continue to use compound ids `org-key:workflow-id` (for example `obs:agent-suggestions`).

## Structure

`x-oblt-aw` is nested by **org key** (same names as `config/<org-key>/` in the control plane, e.g. `obs`, `docs`):

| Path | Requirement | Behavior |
|------|-------------|----------|
| `version` | Required | Schema version (`1`) |
| `<org-key>` | Per org that configures assets | Container for that product line |
| `<org-key>.common` | **Required** for each org block | Shared assets when no workflow override exists |
| `<org-key>.workflows.<id>` | Optional | **Override:** when present, `common` is ignored entirely for that run |

Each asset block (`common` or `workflows.<id>`) may include:

| Field | Form | Behavior |
|-------|------|----------|
| `setup-commands` | Inline string or list of strings | Shell run before the agentic engine. Use a **list** for separate steps, a **single string** for one command, or a **multiline block** (`\|`) for several inline commands (one non-empty, non-`#` line per command). Entries may be repo script paths (for example `./scripts/bootstrap.sh`) or arbitrary inline shell (for example `npm ci`). |
| `setup-commands-file` | Repo-relative path | Optional. UTF-8 file with one command per line; appended after `setup-commands`. Same line rules as multiline inline text. |
| `inputs` | Mapping | Agentic workflow input overrides; `*-file` keys load repo file contents (see manifest example). |

A repository in multiple org fleets may define separate `obs` and `docs` blocks with different `common` guidance.

## Precedence (per run)

| Layer | Behavior |
|-------|----------|
| **Platform** (`platform-additional-instructions` / `platform-inputs-json` on `resolve-apm-assets`) | Control-plane baseline for that agent invocation; always applied first for instructions (prepended). Input keys can be overridden by APM per key. |
| **`x-oblt-aw.<org-key>.common`** | Used when no `workflows.<id>` entry exists for the running workflow in that org. |
| **`x-oblt-aw.<org-key>.workflows.<id>`** | **Override:** when this key exists, that org’s `common` is ignored entirely for that run. |

There is no merge between `common` and `workflows.<id>` (no field-level fallback from common when a workflow block is present).

If `x-oblt-aw` exists but the running org key is not configured, resolution returns platform-only assets (`asset-source: none`).

## Manifest example

```yaml
name: my-service
version: 1.0.0

dependencies:
  apm:
    - microsoft/apm-sample-package#v1.0.0

x-oblt-aw:
  version: 1
  obs:
    common:
      setup-commands:
        - ./scripts/ai-bootstrap.sh
        - npm ci --ignore-scripts
      inputs:
        additional-instructions: |
          Repository-wide agent guidance for observability agentic workflows.
    workflows:
      agent-suggestions:
        setup-commands: |
          export AGENT_CONTEXT=agent-suggestions
          ./scripts/validate-agent-env.sh
        inputs:
          additional-instructions: |
            Overrides obs.common entirely for agent-suggestions only.
      autodoc:
        inputs:
          lookback-window: 3 days ago
          additional-instructions-file: .github/ai/autodoc-extra.md
  docs:
    common:
      inputs:
        additional-instructions: |
          Shared guidance for documentation agentic workflows.
    workflows:
      docs-pr-ai-menu:
        inputs:
          additional-instructions: |
            Overrides docs.common for the PR AI menu workflow.
```

## Runtime behavior

When the dashboard gate passes (`proceed == true`), each agent job’s preceding `resolve-apm-assets` call:

1. Checks out the **consumer** repository (caller context).
2. Installs [`requirements-runtime.txt`](../../requirements-runtime.txt) with pip cache via `actions/setup-python`.
3. Runs [`apm install`](https://microsoft.github.io/apm/) when `apm.yml` is present (installs declared skills, plugins, MCP servers, and other APM dependencies).
4. Runs [`scripts/resolve_apm_agentic_assets.py`](../../scripts/resolve_apm_agentic_assets.py) with the compound workflow id (`org-key:workflow-id`) to select the org block and produce:
   - `resolved-additional-instructions`
   - `resolved-inputs-json` (merged platform + APM inputs)
   - `resolved-setup-commands-json`

Downstream `gh-aw-*` jobs should pass `additional-instructions: ${{ needs.<resolve-job>.outputs.resolved-additional-instructions }}` and may read other keys from `resolved-inputs-json` when needed. Use one resolve job per agent invocation when platform prompts differ (see `oblt-aw-autodoc.yml`).

## Schema

`x-oblt-aw` is a vendor extension on consumer `apm.yml`. APM preserves unknown top-level keys per the [APM manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/).

JSON Schema for this extension block: [`config/schema/apm-agentic-workflows.schema.json`](../../config/schema/apm-agentic-workflows.schema.json).

## References

- [APM (Agent Package Manager)](https://github.com/microsoft/apm)
- [APM manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/) — official `apm.yml` format and vendor extension fields
- [Multi-org agentic workflows](./multi-org-agentic-workflows.md)
- [Resolve APM agentic assets](../../.github/workflows/aw-resolve-apm-assets.yml)
- [Agentic Workflow Prelude](../../.github/workflows/aw-prelude.yml)
