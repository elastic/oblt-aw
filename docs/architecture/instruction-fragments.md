# Instruction fragments (control plane)

Control-plane agentic prompts can be composed from reusable Markdown fragments under each org config tree. The resolver loads them in [`aw-resolve-agentic-assets.yml`](../../.github/workflows/aw-resolve-agentic-assets.yml) before platform inline text and consumer `apm.yml` assets.

## Layout

| Path | Role |
|------|------|
| `config/<org-key>/instruction-fragment-map.json` | Composition manifest |
| `config/<org-key>/instruction-fragments/<fragment-id>.md` | Fragment body (UTF-8 Markdown) |

`fragment-id` is kebab-case (same pattern as registry workflow ids).

## Manifest shape

```json
{
  "common": ["obs-review-assignment"],
  "workflows": {
    "issue-fixer": {
      "fragments": ["issue-fixer-preamble", "fixer-pr-requirements"]
    },
    "security": {
      "fragments": [],
      "inner-workflows": {
        "obs-aw-security-fixer.yml": {
          "fragments": [
            "security-fixer-preamble",
            "security-fixer-pr-requirements"
          ]
        }
      }
    }
  }
}
```

- **`common`** — appended for every workflow in the org when the map exists.
- **`workflows.<workflow-id>.fragments`** — appended for that registry workflow id (dashboard unit).
- **`workflows.<workflow-id>.inner-workflows.<basename>.fragments`** — appended for one control-plane wrapper when several wrappers share a registry id (for example `security` → fixer vs triage).

Shorthand: a workflow entry may be a bare array of fragment ids instead of `{ "fragments": [...] }`.

## Compose order (append)

1. Control-plane `common` fragments
2. Control-plane `workflows.<id>.fragments`
3. Control-plane `inner-workflows.<basename>.fragments`
4. Platform inline `platform-additional-instructions`
5. Consumer fragments / inline / auto (see [APM agentic assets](apm-agentic-assets.md))

Absent map file ⇒ no control-plane fragments (existing callers unchanged). Unknown fragment ids or missing `.md` files fail the resolve job.

## Observability

`aw-resolve-agentic-assets` exposes `resolved-instruction-layers-json` listing every layer that contributed (fragment ids, inline present flags, auto sources) plus `org-key`, `workflow-id`, and `control-plane-workflow`.

## Registry vocabulary

In `workflow-registry.json`, the list of wrapper basenames for a workflow id is **`inner_workflows`** (same concept as `inner-workflows` in the fragment map and consumer `apm.yml`, snake_case in registry JSON).

## Implementation

- Loader: [`scripts/instruction_fragments.py`](../../scripts/instruction_fragments.py)
- Composition entrypoint: [`scripts/agentic_assets_resolver.py`](../../scripts/agentic_assets_resolver.py)
