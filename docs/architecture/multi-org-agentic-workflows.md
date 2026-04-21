# Multi-organization agentic workflows (design)

**Revision:** Org-specific config lives under **`config/<org-key>/`** (direct children of `config/`, e.g. **`config/obs/`**) — **not** under `config/orgs/`. **`enabled-workflows`** uses the **canonical compound id** **`org:workflow-id`** (colon). Locked details below; implementation tracking: [action plan](https://github.com/elastic/observability-robots/issues/4189#issuecomment-4287044747).

This document extends the current OBLT AW control-plane model so multiple Elastic internal organizations (product lines or programs) can **collaborate in one catalog repository**, each owning **distinct agentic workflows**, **separate distribution targets**, and **clear ownership** inside a **single** consumer-facing dashboard.

**Implemented layout:** Per-org [workflow-registry.json](../../config/obs/workflow-registry.json) and [active-repositories.json](../../config/obs/active-repositories.json) under `config/<org-key>/` only (no top-level `config/workflow-registry.json` or `config/active-repositories.json`), hard-coded dashboard label `oblt-aw/dashboard`, title `[oblt-aw] Control Plane Dashboard`, and checkbox markers `<!-- oblt-aw:<org-key>:<workflow-id> -->` (see [sync_control_plane_dashboard.py](../../scripts/sync_control_plane_dashboard.py), [get_enabled_workflows.py](../../scripts/get_enabled_workflows.py)).

**Goal:** Parameterize by **organization key** (from **`config/<org-key>/`** folder names — e.g. `config/obs/`) so other groups can add registries and repo lists. **One open dashboard issue per consumer repository** lists every workflow, **grouped by org**. Checklist markers **always include the org** so parsing and user inspection stay unambiguous.

---

## 1. Design principles

| Principle | Requirement |
|-----------|-------------|
| **Single control-plane issue** | Each consumer repository has **at most one** dashboard issue (same label and title as today, e.g. `oblt-aw/dashboard`, `[oblt-aw] Control Plane Dashboard`). **Workflows are grouped by org** inside the body (Markdown sections), not split across multiple issues. |
| **Org in every marker** | Task-list comments **must** encode **product prefix + org + workflow id** (see §2) so enabled-state parsing and support triage always know the owning org. |
| **Org identity from path only** | The **canonical org identifier** is the **`config/<org-key>/` directory name** (direct child of `config/`). Do **not** add a separate `organization.json`; optional human labels for section headings live in each org’s `workflow-registry.json` (e.g. top-level `section_title`) if needed. |
| **Visible ownership** | Dashboard sections and tables make **which org owns which workflow** obvious (e.g. `### Observability (obs)` then workflows for that org). |
| **Separated distribution** | Each org keeps its own **active-repositories.json** (who receives the client workflow and dashboard sync). **Sync** merges all org registries when updating the **single** dashboard for repos in the union of those lists (or per policy: only orgs that target that repo). |
| **Common core** | Shared Python and reusable workflows live at **repository root** (`scripts/`, `.github/workflows/`); org-specific **data** lives only under `config/<org-key>/`. |
| **Sync on change** | Path filters and automation can still scope to `config/<org-key>/**` (e.g. `config/obs/**`, `config/docs/**`) so unrelated orgs do not fan out unnecessary work. |

---

## 2. Organization key and checklist markers

- **`org-key`:** Taken **only** from the folder name **`config/<org-key>/`** (DNS-label style, e.g. `obs`, `docs`, `platform`). Implementation discovers orgs as **direct subdirectories of `config/`** that contain org data (see §3). **Reserve** names like `schema` for non-org assets under `config/` so they are not mistaken for an org key. **Note:** an org key **`docs`** maps to **`config/docs/`** (JSON config); that path is **not** the repository’s documentation tree at **`docs/`** (Markdown) at repo root.

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

Regex and tests in `sync_control_plane_dashboard.py` / `get_enabled_workflows.py` must be updated from the current two-part `oblt-aw:<id>` pattern to this **three-part** pattern.

---

## 3. Proposed folder layout

```text
config/
  obs/                                      # org-key = "obs" (folder name under config/)
    workflow-registry.json                  # workflows[] + optional top-level section_title for dashboard
    active-repositories.json                # { "repositories": [ "owner/repo", ... ] }
  docs/                                     # optional minimal second org (tests / section-merge); org-key "docs"
    workflow-registry.json
    active-repositories.json
  <other-org-key>/
    workflow-registry.json
    active-repositories.json
  # Optional: JSON Schema under config/schema/ (must not collide with org-key discovery rules)

scripts/
  common.py                                 # Helpers: list org keys, load merged registry, paths
  build_repos_matrix.py                     # --org optional; union of repos for single-dashboard sync
  sync_control_plane_dashboard.py           # Merge org registries → one issue body; same label/title
  get_enabled_workflows.py                  # Parse three-part markers; single issue by oblt-aw/dashboard

.github/workflows/
  gh-aw-*.yml                               # Reusable agent workflows — see §4
  sync-control-plane-dashboard.yml
  distribute-client-workflow.yml
  ...
```

**Common functionality at top level:** Python under `scripts/`; tests under `tests/`; docs under `docs/architecture/` and `docs/operations/`.

---

## 4. `gh-aw-*` workflow files (naming and location)

- **Keep existing flat names** such as `gh-aw-dependency-review.yml`, `gh-aw-agent-suggestions.yml`, etc., at **`.github/workflows/`** (same as today).
- **Do not move reusable workflows into subfolders:** GitHub requires reusable workflows to live **directly** under `.github/workflows/` — **subdirectories are not supported** for reusable workflows ([Reuse workflows — limitations](https://docs.github.com/en/actions/using-workflows/reusing-workflows#creating-a-reusable-workflow)).
- If you need clearer grouping without breaking `uses:` paths, rely on **naming prefixes** (e.g. `gh-aw-obs-*.yml` only if you adopt a convention) or **documentation**, not nested directories for callable workflows.

---

## 5. Single dashboard: consumer repository

| Concept | Value |
|--------|--------|
| **Issues** | **One** open issue per repo for this program |
| **Label** | Unchanged, e.g. `oblt-aw/dashboard` (single label to query) |
| **Title** | Unchanged, e.g. `[oblt-aw] Control Plane Dashboard` |
| **Body** | Intro + **sections per org** (`### … (obs)`, `### … (docs)`, …) + per-section workflow tables and **Enable / Disable** checkbox lists using markers from §2 |

**Runtime:** `get-enabled-workflows` loads **that one issue**, parses **all** checked lines with `<!-- oblt-aw:<org-key>:<workflow-id> -->`, and emits the normalized enabled list (**`org:workflow-id`**) for ingress gating.

**Ingress:** Routed jobs use the **same** compound ids in `enabled-workflows` as appear in the dashboard / registry output (e.g. `obs:agent-suggestions`).

---

## 6. Automation: repositories and sync

- **Per-org** `active-repositories.json` still defines which repos each org cares about.
- **Dashboard sync** for a given `owner/repo`: include workflows from **every org folder** that lists this repo (merge). If a repo is only in `obs`, only `obs` sections appear; if in multiple orgs, **all relevant sections** appear in the **same** issue.
- **`build_repos_matrix.py`:** May output repos needing sync from the **union** of per-org lists (deduplicated), with metadata for which orgs apply if needed.
- **Distribution** ([distribute-client-workflow](../operations/distribute-client-workflow.md)):** Unchanged idea — per-org lists drive install/remove; implementation walks **`config/*/active-repositories.json`** for org directories (or enumerates org keys explicitly — see §3).

---

## 7. Discoverability for users

- **Dashboard body:** Mandatory **org section headers** and, where helpful, a summary table column **Org**.
- **Registry:** Each workflow entry can include optional `display_name`; org is always implied by **`config/<org-key>/`** and reflected in the merged dashboard.

---

## 8. Migration sketch (Observability → `obs`)

1. Add **`config/obs/`** with folder name `obs`; move (or copy) registry + active-repositories from top-level config. **All current** registry entries and distribution targets map to **`obs`**; top-level files remain deprecated aliases for `config/obs/` until removed.
2. Optionally add minimal **`config/docs/`** as a second org (e.g. for tests proving section order and merged enabled lists); org key **`docs`** is distinct from the repo **`docs/`** documentation folder.
3. Extend marker format to `<!-- oblt-aw:obs:<id> -->` (and migrate existing lines in tests/fixtures); dashboard sync rewrites consumer issue markers accordingly.
4. Refactor `sync_control_plane_dashboard.py` to **merge** org files into **one** issue body with sections; keep **one** label/title.
5. Refactor `get_enabled_workflows.py` for three-part markers, **`org:workflow-id`** output, and single-issue read.
6. Update **`oblt-aw-ingress.yml`** gating from bare ids to **`org:workflow-id`** strings.
7. Add tests with **two org folders** (e.g. `obs` + `docs`) proving section order and merged enabled list.

---

## 9. Scope (downstream)

- **No mandatory changes** outside **`elastic/oblt-aw`** for this design (e.g. other Elastic repos or consumer-specific docs beyond normal adoption of the published control-plane). Consumer repositories continue to use the ingress and dashboard as today; only the **id strings** in `enabled-workflows` and markers gain the **`org:`** prefix.

---

## References

- [OBLT AW Architecture Overview](./overview.md)
- [Control Plane Dashboard Format](../operations/control-plane-dashboard-format.md)
- [Workflow maturity](../operations/workflow-maturity.md)
- [Reusing workflows (GitHub Docs)](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
