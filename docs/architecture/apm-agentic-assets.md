# APM agentic assets (consumer repositories)

Consumer repositories can declare **shared** and **per-workflow** agentic assets in [`apm.yml`](https://github.com/microsoft/apm) using the `x-oblt-aw` extension. The control plane resolves those assets in [`aw-resolve-agentic-assets.yml`](../../.github/workflows/aw-resolve-agentic-assets.yml) immediately before each upstream `gh-aw-*` invocation (not in [`aw-prelude.yml`](../../.github/workflows/aw-prelude.yml)).

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
| `<org-key>.workflows.<id>.inner-workflows.<basename>` | Optional | **Override:** when the running workflow basename matches, that block replaces the parent workflow block |
| `<org-key>.fragments` | Optional | Map of local fragment id → repo-relative Markdown path |

Each asset block (`common`, `workflows.<id>`, or `inner-workflows.<basename>`) may include:

| Field | Form | Behavior |
|-------|------|----------|
| `setup-commands` | Inline string or list of strings | Shell run before the agentic engine. Use a **list** for separate steps, a **single string** for one command, or a **multiline block** (`\|`) for several inline commands (one non-empty, non-`#` line per command). Entries may be repo script paths (for example `./scripts/bootstrap.sh`) or arbitrary inline shell (for example `npm ci`). |
| `setup-commands-file` | Repo-relative path | Optional. UTF-8 file with one command per line; appended after `setup-commands`. Same line rules as multiline inline text. |
| `additional-instructions-fragments` | List of ids | Ordered ids from `<org-key>.fragments`; materialized before inline `additional-instructions`. |
| `inputs` | Mapping | Agentic workflow input overrides; `*-file` keys load repo file contents (see manifest example). |

A repository in multiple org fleets may define separate `obs` and `docs` blocks with different `common` guidance.

## Precedence (per run)

| Layer | Behavior |
|-------|----------|
| **Control-plane fragments** | Org map under `config/<org-key>/` — see [instruction fragments](instruction-fragments.md). Appended before platform inline. |
| **Platform** (`platform-additional-instructions` / `platform-inputs-json` on `resolve-apm-assets`) | Control-plane baseline for that agent invocation; applied after control-plane fragments. Input keys can be overridden by APM per key. |
| **`x-oblt-aw.<org-key>.workflows.<id>.inner-workflows.<basename>`** | **Override:** when this key matches the calling wrapper basename, that block is used and parent `workflows.<id>` / `common` are ignored for asset fields. |
| **`x-oblt-aw.<org-key>.workflows.<id>`** | **Override:** when this key exists and no matching inner-workflow block applies, that org’s `common` is ignored entirely for that run. The `inner-workflows` map on the parent is structural only (not instruction text). |
| **`x-oblt-aw.<org-key>.common`** | Used when no `workflows.<id>` entry exists for the running workflow in that org. |

There is no field-level merge between `common`, `workflows.<id>`, and `inner-workflows.<basename>` (override at the selected grain). Control-plane **fragments** append across grains; see [instruction fragments](instruction-fragments.md).

If `x-oblt-aw` exists but the running org key is not configured, resolution returns platform-only assets (`asset-source: none`).

`asset-source` is one of `none`, `common`, `workflow`, or `inner-workflow`.

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
3. Runs [`microsoft/apm-action`](https://github.com/microsoft/apm-action) when `apm.yml` is present (installs the APM CLI with tool-cache reuse and runs `apm install` for declared skills, plugins, MCP servers, and other APM dependencies). Private GitHub packages use `ai-assets-token-policy` from `config/<org>/active-repositories.json` when set; otherwise the job `GITHUB_TOKEN` is passed as `github-token` (see [aw-resolve-agentic-assets](../workflows/aw-resolve-agentic-assets.md)).
4. Runs [`scripts/resolve_agentic_assets_cli.py`](../../scripts/resolve_agentic_assets_cli.py), which calls [`agentic_assets_resolver.resolve_agentic_assets`](../../scripts/agentic_assets_resolver.py), with the compound workflow id (`org-key:workflow-id`) and calling wrapper basename to select the org block (including optional `inner-workflows`) and produce:
   - `resolved-additional-instructions`
   - `resolved-inputs-json` (merged platform + APM inputs)
   - `resolved-setup-commands-json`
   - `resolved-instruction-layers-json` (which fragments/inline/auto layers were appended)

Downstream `gh-aw-*` jobs should pass `additional-instructions: ${{ needs.<resolve-job>.outputs.resolved-additional-instructions }}` and may read other keys from `resolved-inputs-json` when needed. Use one resolve job per agent invocation when platform prompts differ (see `obs-aw-autodoc.yml`).

## Schema

`x-oblt-aw` is a vendor extension on consumer `apm.yml`. APM preserves unknown top-level keys per the [APM manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/).

JSON Schema for this extension block: [`config/schema/apm-agentic-workflows.schema.json`](../../config/schema/apm-agentic-workflows.schema.json).

## References

- [Instruction fragments](instruction-fragments.md) — control-plane prompt composition
- [APM (Agent Package Manager)](https://github.com/microsoft/apm)
- [APM manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/) — official `apm.yml` format and vendor extension fields
- [Multi-org agentic workflows](./multi-org-agentic-workflows.md)
- [Resolve agentic assets](../../.github/workflows/aw-resolve-agentic-assets.yml)
- [Agentic Workflow Prelude](../../.github/workflows/aw-prelude.yml)
