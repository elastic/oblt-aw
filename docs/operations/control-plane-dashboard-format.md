# Control Plane Dashboard Issue Format

**Related issues:** [elastic/observability-robots#3732](https://github.com/elastic/observability-robots/issues/3732), [elastic/observability-robots#4189](https://github.com/elastic/observability-robots/issues/4189)

This document defines the structure and format of the OBLT AW Control Plane Dashboard issue. The format enables reliable parsing when users edit checkboxes to opt in or opt out of agentic workflows.

---

## Overview

The Control Plane Dashboard is a **single** GitHub issue per consumer repository that lists all available agentic workflows, **grouped by owning org** (see `config/<org-key>/` in this repository). Users enable or disable each workflow by checking task-list items. When the client workflow runs, the ingress (`get-enabled-workflows`) looks for an open issue labeled `oblt-aw/dashboard` and sets gating from `effective-raw` and normalized `enabled-workflows`:

- **No such issue** → `effective-raw` is empty; no agentic workflows run until sync creates the dashboard and workflows are enabled.
- **Dashboard exists** → normalized outputs are a JSON array string: `[]` if **no** checkboxes are checked (no agentic workflows run), or `["org:workflow-id", ...]` for only the checked workflows, using the **canonical compound id** (colon-separated).

There is no config file (no `.github/obs-aw-config.json`) and no PRs when users toggle checkboxes. Runtime gating is read each time the client runs via `get-enabled-workflows`. Separately, `issues.edited` on the dashboard issue triggers the shared [aw-dashboard-audit](../workflows/aw-dashboard-audit.md) path to record enable/disable comments on that issue.

---

## Canonical compound id (`org:workflow-id`)

Every workflow in ingress gating is identified by **`org-key:workflow-id`**:

- **`org-key`** — Directory name under `config/<org-key>/` in `elastic/oblt-aw` (for example `obs`, `docs`). Not to be confused with the repository’s root `docs/` Markdown tree.
- **`workflow-id`** — Unique within that org’s [`workflow-registry.json`](../../config/obs/workflow-registry.json). Each registry entry lists every control-plane reusable it gates via `control_plane_workflows` (basenames under `.github/workflows/`, for example `obs-aw-security-detector.yml`); multiple files may share one `id` (detector/fixer/triage).

**Examples:** `obs:agent-suggestions`, `docs:example-workflow`.

### Sub-feature compound id (`org:workflow-id:sub-feature-id`)

Workflows may declare optional **`sub_features`** in the registry. Each sub-feature is identified by a **three-segment** compound id:

- **`org-key:workflow-id:sub-feature-id`** — for example `obs:automerge:github-actions`

Parent workflows remain **`org:workflow-id`** (two segments). Sub-feature ids appear in the same `enabled-workflows` JSON array as parent ids.

Legacy dashboard lines used **`<!-- oblt-aw:<workflow-id> -->`** (no org). Parsers treat those as **`obs:<workflow-id>`**. New and synced bodies use the three-part HTML comment (see below).

---

## Markdown Structure

The dashboard issue body MUST follow this structure:

1. **Intro** — Short description of the dashboard and how to use it
2. **One section per org** — For each org that lists this repo in `config/<org-key>/active-repositories.json`: heading `### {section_title} ({org_key})`, workflow summary table, then `#### Enable / Disable` with task-list checkboxes
3. **Instructions for users** — How to enable/disable workflows and what happens when they do (once, at the end)

### Example Structure (multi-org)

```markdown
## Control Plane Dashboard

Use this dashboard to enable or disable agentic workflows for this repository. Click the checkboxes below to toggle workflows on or off.

### Observability (obs)

| Workflow | Maturity | Description |
|----------|----------|-------------|
| [Agent Suggestions](https://github.com/elastic/oblt-aw/blob/main/docs/workflows/obs-aw-agent-suggestions.md) | 🟠 experimental | … |

#### Enable / Disable

Click a checkbox to enable or disable a workflow:

- [x] <!-- oblt-aw:obs:dependency-review --> Dependency Review
- [ ] <!-- oblt-aw:obs:agent-suggestions --> Agent Suggestions
  - [x] <!-- oblt-aw:obs:automerge:github-actions --> GitHub Actions bumps
  - [ ] <!-- oblt-aw:obs:automerge:python-dependencies --> Python dependencies

### Documentation (docs)

| Workflow | Maturity | Description |
|----------|----------|-------------|
| Example workflow | 🟠 experimental | … |

#### Enable / Disable

Click a checkbox to enable or disable a workflow:

- [ ] <!-- oblt-aw:docs:example-workflow --> Example workflow

### Instructions

- **Enable a workflow:** Check the checkbox next to the workflow.
- **Disable a workflow:** Uncheck the checkbox.
- Changes are applied at runtime when the client runs; `get-enabled-workflows` reads this issue and supplies `enabled-workflows` to the ingress.
```

---

## Checkbox Format

### Parseable Pattern

Use GitHub task list syntax in a **list** (not in a table). Task lists in list context render as **interactive checkboxes**:

```
- [x] <!-- oblt-aw:<org-key>:<workflow-id> --> display-name
  - [x] <!-- oblt-aw:<org-key>:<workflow-id>:<sub-feature-id> --> sub-feature display-name
```

Sub-feature lines are **indented** with two spaces directly under their parent checkbox. Sub-features are always rendered when declared in the registry; they take effect only while the parent workflow is enabled.

or, when enabled:

```
- [x] <!-- oblt-aw:<org-key>:<workflow-id> --> display-name
```

**Legacy (deprecated, migrated to `obs:`):**

```
- [x] <!-- oblt-aw:<workflow-id> --> display-name
```

### Rules

| Rule | Requirement |
|------|-------------|
| **Checkbox syntax** | `- [ ]` (unchecked) or `- [x]` (checked) — task list in list context |
| **Line position** | MUST be at the **start of a line** (parsers anchor to line start to avoid false positives in prose/code blocks) |
| **HTML comment** | MUST appear on the **same line** as the checkbox, immediately after it |
| **Comment format** | Parent: `<!-- oblt-aw:<org-key>:<workflow-id> -->`; sub-feature: `<!-- oblt-aw:<org-key>:<workflow-id>:<sub-feature-id> -->` — no spaces around colons inside the comment |
| **workflow-id** | Lowercase, hyphen-separated; unique within that org’s registry |
| **sub-feature-id** | Lowercase, hyphen-separated; unique within the parent workflow’s `sub_features` array |
| **enabled-workflows output** | JSON array of strings **`org:workflow-id`** and **`org:workflow-id:sub-feature-id`**, matching ingress gating exactly |

### Why This Format

- **Interactive:** Task lists in list context render as clickable checkboxes in GitHub Issues.
- **Multi-org:** Section headings and compound ids make ownership explicit.
- **Reliable parsing:** The HTML comment is invisible in the rendered issue but preserved when users check/uncheck.

### Initial Checkbox State for New Workflow IDs

When dashboard sync introduces a workflow ID that does not already exist in the dashboard issue body, initial checkbox state comes from that entry's `default_enabled` value in the org’s `workflow-registry.json`:

- `default_enabled: true` → rendered as `- [x]`
- `default_enabled: false` → rendered as `- [ ]`

If a workflow checkbox already exists in the issue body, the current issue state is preserved on sync updates. The same policy applies to sub-feature checkboxes.

### Sub-feature gating

| Parent | Sub-feature | Result |
|--------|-------------|--------|
| unchecked | any | Entire workflow (parent + all children) disabled |
| checked | unchecked | Parent workflow runs; that sub-feature does not |
| checked | checked | Parent workflow runs; that sub-feature runs |
| (no sub-features) | — | Existing single-checkbox behaviour, unchanged |

When a control-plane workflow file is listed under a sub-feature’s `control_plane_workflows`, prelude gating requires **both** the parent compound id and the sub-feature compound id in `enabled-workflows`.

### Parsing Algorithm

To extract enabled workflows from the issue body (when a dashboard issue exists):

1. Split the body into lines.
2. For each checked line matching **sub-feature** pattern at line start (optional leading whitespace):
   `^\s*- [x] <!-- oblt-aw:([a-z0-9-]+):([a-z0-9-]+):([a-z0-9-]+) -->`
   emit compound id `org-key:workflow-id:sub-feature-id`.
3. For each checked line matching **parent** pattern at line start:
   `^\s*- [x] <!-- oblt-aw:([a-z0-9-]+):([a-z0-9-]+) -->`
   emit compound id `org-key:workflow-id`.
4. For each checked line matching **legacy two-part** pattern:
   `^\s*- [x] <!-- oblt-aw:([a-z0-9-]+) -->`
   emit `obs:workflow-id`.
5. Emit a compact JSON array string of those compound ids in document order (deduplicated). That string is what `get-enabled-workflows` writes to the `enabled-workflows` output when the dashboard issue exists.

**No open dashboard issue:** The job outputs `[]` for the normalized `enabled-workflows` output (same as an empty selection). Prelude treats empty `effective-raw` the same way: no workflows run.

---

## Workflow Table Columns

| Column | Description |
|--------|-------------|
| **Workflow** | Human-readable name from the org’s `workflow-registry.json`. When the entry sets `docs` (repo-relative path under `docs/workflows/`), the name is a Markdown link to `https://github.com/elastic/oblt-aw/blob/main/<docs>` |
| **Maturity** | `stable`, `early-adoption`, or `experimental` (from the org’s `workflow-registry.json`) |
| **Description** | Short description from the org’s `workflow-registry.json` |

---

## Instructions for Users

The dashboard MUST include clear instructions. Recommended text:

- **Enable a workflow:** Check the checkbox next to the workflow. `get-enabled-workflows` will include its compound id in `enabled-workflows` at runtime.
- **Disable a workflow:** Uncheck the checkbox. `get-enabled-workflows` will exclude it from `enabled-workflows` at runtime.
- **Sub-features:** Some workflows expose indented child checkboxes. Enable or disable individual parts of a composite workflow. Sub-features apply only while the parent workflow is enabled.
- **When changes apply:** The dashboard is read at runtime when the client runs. No config file; no PRs on checkbox edits.
- **Default behavior:** No dashboard or dashboard with all unchecked → no workflows run; dashboard exists with some checked → only checked workflows executed.

---

## Reference

- **Multi-org design:** [docs/architecture/multi-org-agentic-workflows.md](../architecture/multi-org-agentic-workflows.md)
- **Renovate Dependency Dashboard:** [docs.renovatebot.com/key-concepts/dashboard](https://docs.renovatebot.com/key-concepts/dashboard/) — single issue per repo, dynamic Markdown checkboxes
- **Implementation plan:** [Issue #3732 comment](https://github.com/elastic/observability-robots/issues/3732#issuecomment-4054356635)
