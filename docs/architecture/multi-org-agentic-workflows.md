# Multi-organization agentic workflows (design)

**Revision:** Org-specific config lives under **`config/<org-key>/`** (direct children of `config/`, e.g. **`config/obs/`**) — **not** under `config/orgs/`. **`enabled-workflows`** uses the **canonical compound id** **`org:workflow-id`** (colon). Locked details below; implementation tracking: [action plan](https://github.com/elastic/observability-robots/issues/4189#issuecomment-4287044747).

This document extends the current OBLT AW framework model so multiple Elastic internal organizations (product lines or programs) can **collaborate in one catalog repository**, each owning **distinct agentic workflows**, **separate distribution targets**, and **clear ownership** inside a **single** consumer-facing Control Plane dashboard.

**Implemented layout:** Per-org [workflow-registry.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/workflow-registry.json), [active-repositories.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/active-repositories.json), [allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json), and [allowed_issue_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_issue_authors.json) (Observability) under `config/<org-key>/` only — **no JSON files directly under `config/`** (only subdirectories such as `config/obs/`, `config/docs/`, `config/security/`, or reserved `config/schema/`), hard-coded Control Plane dashboard label `oblt-aw/dashboard`, title `[oblt-aw] Control Plane Dashboard`, and checkbox markers `<!-- oblt-aw:<org-key>:<workflow-id> -->` (see [sync_control_plane_dashboard.py](https://github.com/elastic/oblt-aw/blob/main/scripts/sync_control_plane_dashboard.py), [get_enabled_workflows.py](https://github.com/elastic/oblt-aw/blob/main/scripts/get_enabled_workflows.py)).

**Goal:** Parameterize by **organization key** (from **`config/<org-key>/`** folder names — e.g. `config/obs/`) so other groups can add registries and repo lists. **One open Control Plane dashboard issue per consumer repository** lists every workflow, **grouped by org**. Checklist markers **always include the org** so parsing and user inspection stay unambiguous.

---

## 1. Design principles

| Principle | Requirement |
|-----------|-------------|
| **Single Control Plane dashboard issue** | Each consumer repository has **at most one** Control Plane dashboard issue (same label and title as today, e.g. `oblt-aw/dashboard`, `[oblt-aw] Control Plane Dashboard`). **Workflows are grouped by org** inside the body (Markdown sections), not split across multiple issues. |
| **Org in every marker** | Task-list comments **must** encode **product prefix + org + workflow id** (see §2) so enabled-state parsing and support triage always know the owning org. |
| **Org identity from path only** | The **canonical org identifier** is the **`config/<org-key>/` directory name** (direct child of `config/`). Do **not** add a separate `organization.json`; optional human labels for section headings live in each org’s `workflow-registry.json` (e.g. top-level `section_title`) if needed. |
| **Visible ownership** | Control Plane dashboard sections and tables make **which org owns which workflow** obvious (e.g. `### Observability (obs)` then workflows for that org). |
| **Separated distribution** | Each org keeps its own **active-repositories.json** (who receives the client workflow and Control Plane dashboard sync). **Sync** merges all org registries when updating the **single** Control Plane dashboard for repos in the union of those lists (or per policy: only orgs that target that repo). |
| **Common core** | Shared Python and reusable workflows live at **repository root** (`scripts/`, `.github/workflows/`); org-specific **data** lives only under `config/<org-key>/`. |
| **Sync on change** | Path filters and automation can still scope to `config/<org-key>/**` (e.g. `config/obs/**`, `config/docs/**`, `config/security/**`) so unrelated orgs do not fan out unnecessary work. |

---

## 2. Organization key and checklist markers

- **`org-key`:** Taken **only** from the folder name **`config/<org-key>/`** (DNS-label style, e.g. `obs`, `docs`, `security`). Implementation discovers orgs as **direct subdirectories of `config/`** that contain org data (see §3). **Reserve** names like `schema` and `common` for non-org assets under `config/` so they are not mistaken for an org key. **Note:** an org key **`docs`** maps to **`config/docs/`** (JSON config); that path is **not** the repository’s documentation tree at **`docs/`** (Markdown) at repo root. Org key **`security`** is not the Observability registry workflow id `obs:security`.

**Checkbox comment format (mandatory):** Include **org** and **workflow id**, with a stable product-scoped prefix so one parser can handle all lines:

```text
<!-- oblt-aw:<org-key>:<workflow-id> -->
```

Example:

```markdown
- [x] <!-- oblt-aw:obs:agent-suggestions --> Agent Suggestions
- [ ] <!-- oblt-aw:docs:example-workflow --> Example (docs org)
```

- **`workflow-id`** remains unique **within** that org’s `workflow-registry.json` (same as today per file).
- **`enabled-workflows`** JSON passed to ingress uses **globally unique** entries in the **canonical** form **`org:workflow-id`** (e.g. `obs:agent-suggestions`, `docs:example-workflow`). Documented in [control-plane-dashboard-format.md](../operations/control-plane-dashboard-format.md). Ingress gating uses **`contains(fromJSON(...), 'org:workflow-id')`** with these exact strings.

Regex and tests in `sync_control_plane_dashboard.py` / `get_enabled_workflows.py` are already updated to the three-part `<!-- oblt-aw:<org-key>:<workflow-id> -->` pattern (with legacy two-part compatibility for previously generated dashboards).

---

## 3. Proposed folder layout

```text
config/
  obs/                                      # org-key = "obs" (folder name under config/)
    workflow-registry.json                  # workflows[] + optional top-level section_title for Control Plane dashboard
    active-repositories.json                # { "repositories": [ "owner/repo", ... ] }
  docs/                                     # docs org; org-key "docs"
    workflow-registry.json
    active-repositories.json
  security/                                 # security org; org-key "security" (empty registry until routes land)
    workflow-registry.json
    active-repositories.json
  <other-org-key>/
    workflow-registry.json
    active-repositories.json
  common/                                   # reserved: shared service definitions (not an org)
    services.json
  # Optional: JSON Schema under config/schema/ (must not collide with org-key discovery rules)

scripts/
  common.py                                 # Shared helpers (org discovery, markers, distribution inputs)
  build_target_operations.py                # Distribution matrix builder (all org templates)
  build_repos_matrix.py                     # Union of repos for sync-control-plane-dashboard matrix
  sync_control_plane_dashboard.py         # Merge org registries → one Control Plane dashboard issue body
  get_enabled_workflows.py                # Parse Control Plane dashboard; normalized enabled-workflows for ingress
  summarize_pr_results.sh                   # PR result summary for distribute-client-workflow
  update_license_files.py                   # Apache headers / NOTICE (repo-wide)
  obs/
    validateAutomergePr.ts                  # Automerge verify step
    security-scan.sh                        # Security detector scan driver
    create-security-issues.sh               # Open grouped SEC issues from findings
    supersede-security-issues.sh            # Close older open SEC detector issues on new scan
    install_security_detector_tools.sh      # Tooling bootstrap for detector
  docs/
    issue-menu/                             # Docs AI issue menu (github-script modules)
    pr-menu/                                # Docs AI PR menu (github-script modules)

.github/workflows/
  obs-aw-*.yml                               # Reusable agentic workflows — see §4
  docs-aw-*.yml
  security-aw-*.yml
  sync-control-plane-dashboard.yml
  distribute-client-workflow.yml
  ...
```

**Layout:** Cross-org framework and distribution Python at `scripts/` root; Observability-only tooling under `scripts/obs/`; Docs menu scripts under `scripts/docs/`; tests under `tests/`; docs under `docs/architecture/` and `docs/operations/`.

---

## 4. `obs-aw-*` workflow files (naming and location)

- **Keep existing flat names** such as `obs-aw-dependency-review.yml`, `obs-aw-agent-suggestions.yml`, etc., at **`.github/workflows/`** (same as today).
- **Do not move reusable workflows into subfolders:** GitHub requires reusable workflows to live **directly** under `.github/workflows/` — **subdirectories are not supported** for reusable workflows ([Reuse workflows — limitations](https://docs.github.com/en/actions/using-workflows/reusing-workflows#creating-a-reusable-workflow)).
- If you need clearer grouping without breaking `uses:` paths, rely on **naming prefixes** (org key is already the `obs-aw-` / `docs-aw-` / `security-aw-` prefix) or **documentation**, not nested directories for callable workflows.

---

## 5. Single Control Plane dashboard: consumer repository

| Concept | Value |
|--------|--------|
| **Issues** | **One** open issue per repo for this program |
| **Label** | Unchanged, e.g. `oblt-aw/dashboard` (single label to query) |
| **Title** | Unchanged, e.g. `[oblt-aw] Control Plane Dashboard` |
| **Body** | Intro + **sections per org** (`### … (obs)`, `### … (docs)`, …) + per-section workflow tables and **Enable / Disable** checkbox lists using markers from §2 |

**Runtime:** `get-enabled-workflows` loads **that one issue**, parses **all** checked lines with `<!-- oblt-aw:<org-key>:<workflow-id> -->`, and emits the normalized enabled list (**`org:workflow-id`**) for ingress gating.

**Ingress:** Routed jobs use the **same** compound ids in `enabled-workflows` as appear in the Control Plane dashboard / registry output (e.g. `obs:agent-suggestions`).

---

## 6. Automation: repositories and sync

- **Per-org** `active-repositories.json` still defines which repos each org cares about.
- **Control Plane dashboard sync** for a given `owner/repo`: include workflows from **every org folder** that lists this repo (merge). If a repo is only in `obs`, only `obs` sections appear; if in multiple orgs, **all relevant sections** appear in the **same** issue.
- **`build_repos_matrix.py`:** Runs with **no CLI arguments**. It discovers org trees under `config/<org-key>/`, unions and deduplicates `active-repositories.json` entries, and writes workflow outputs:
  - `repos`: JSON array for matrix strategy in the shape `[{"repository":"owner/repo"}, ...]`
  - `has_repos`: `"true"` when at least one repository exists, otherwise `"false"`
  - `repos_count`: number of repositories in `repos`
- **Distribution** ([distribute-client-workflow](../operations/distribute-client-workflow.md)):** Unchanged idea — per-org lists drive install/remove; implementation walks **`config/*/active-repositories.json`** for org directories (or enumerates org keys explicitly — see §3).

---

## 7. Discoverability for users

- **Control Plane dashboard body:** Mandatory **org section headers** and, where helpful, a summary table column **Org**.
- **Registry:** Each workflow entry can include optional `display_name`; org is always implied by **`config/<org-key>/`** and reflected in the merged Control Plane dashboard.

---

## 8. Migration status (Observability → `obs`)

This migration is already implemented in this repository:

1. `config/obs/` is the source of truth for Observability org configuration, and top-level `config/*.json` aliases are removed.
2. Marker format and parser behavior use org-aware identifiers (`<!-- oblt-aw:<org-key>:<workflow-id> -->` and `org:workflow-id`) with legacy two-part parsing support.
3. Control Plane dashboard sync merges org data into one issue body with one Control Plane dashboard label/title.
4. Ingress gating uses compound `org:workflow-id` identifiers.
5. Tests cover org-aware parsing and Control Plane dashboard generation, including multi-org section and marker handling.

---

## 9. Scope (downstream)

- **No mandatory changes** outside **`elastic/oblt-aw`** for this design (e.g. other Elastic repos or consumer-specific docs beyond normal adoption of the published framework). Consumer repositories continue to use the ingress and Control Plane dashboard as today; only the **id strings** in `enabled-workflows` and markers gain the **`org:`** prefix.

---

## 10. Adding a new org key (implementation checklist)

Use this when scaffolding another `config/<org-key>/` (same shape as `obs`, `docs`, `security`):

| Step | What to change |
|------|----------------|
| Config | `config/<org-key>/workflow-registry.json` + `active-repositories.json` (both files required for discovery) |
| Clients | `.github/remote-workflow-template/<org-key>/.github/workflows/trigger-<org-key>-aw-*.yml` |
| Orchestrators | `.github/workflows/<org-key>-aw-event-*.yml` (dashboard-audit-only is fine until routes exist) |
| CODEOWNERS | Rules for config, remote templates, `<org-key>-aw-*`, and `trigger-<org-key>-aw-*` |
| Onboard / docs | Issue form, onboard prompt, and docs that enumerate org keys |
| Prelude routes | `scripts/validate_aw_workflow_prelude.py` **derives** `<org-key>-aw-*` route prefixes from discovered org dirs — do **not** hard-code org names in that script |
| Unit tests | `tests/unit/test_validate_aw_workflow_prelude.py` parametrizes `shared-proceed` route cases over discovered org keys — adding the config dir pulls the new prefix into coverage |

Validate with `python scripts/validate_aw_workflow_prelude.py` and `pytest tests/unit/test_validate_aw_workflow_prelude.py`.

---

## 11. Common services (shared definitions, per-org catalogs)

Some agentic capabilities are useful to more than one org. The control plane keeps **one definition** and lets each org **opt into its own catalog**. There is **no** Common dashboard section and **no** `common:workflow-id` gating id.

| Piece | Behavior |
|-------|----------|
| **Catalog** | `config/common/services.json` — reserved path (not an org). Each service is a normal workflow object (`id`, `name`, `inner_workflows`, optional `sub_features`, …). |
| **Opt-in** | Org `workflow-registry.json` lists `"include_common": ["dependency-review", "automerge", …]`. Sync expands those ids into that org’s section only. |
| **Dashboard** | Included services appear under `### … (obs)`, `### … (docs)`, etc., with markers `<!-- oblt-aw:<org-key>:<workflow-id> -->`. |
| **Gating** | Compound ids stay per org (`docs:dependency-review`, `obs:automerge:github-actions`). Enabling in one org does not enable another. |
| **Implementation** | Shared services keep reusable workflows under the owning prefix (pilot: `obs-aw-dependency-review.yml`, `obs-aw-automerge.yml`, …). Other orgs call those reusables from their `*-aw-event-*` orchestrators. |
| **Index** | The same basename may map to multiple `org:workflow-id` entries when every listing shares the same workflow id (intentional share). Conflicting mappings still fail closed. Prelude proceeds if **any** matching compound id is enabled. |
| **Ownership** | `config/common/` CODEOWNERS: `@elastic/observablt-ci`. Route implementation files stay under the implementing org’s CODEOWNERS paths. |

**Pilot:** `dependency-review` and `automerge` live in `config/common/services.json`. Observability opts in via `include_common` and already wires `obs-aw-event-*` plus remote triggers. Other orgs opt in in **their own PRs** (registry + event orchestrators + remote triggers). CI runs `scripts/validate_common_service_opt_in.py` so an incomplete opt-in fails closed.

**Operator guide:** [Opt in or out of agentic workflows from other orgs](../admin-guide/opt-in-common-services.md).

**Publishing a common service (owning org):**

1. Add the workflow object to `config/common/services.json` (implementation already exists as `<owner>-aw-*`).
2. Include it from the owning org’s `include_common` if that org should offer it too.
3. Keep owning-org event orchestrators and triggers green under `validate_common_service_opt_in.py`.

**Opting into a common service (consuming org):** do all of the following in the **same** PR — see the admin guide.

---

## References

- [OBLT AW Architecture Overview](./overview.md)
- [Control Plane dashboard Format](../operations/control-plane-dashboard-format.md)
- [Workflow maturity](../operations/workflow-maturity.md)
- [Reusing workflows (GitHub Docs)](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
