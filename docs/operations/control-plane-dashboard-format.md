# Control Plane Dashboard Issue Format

**Related issue:** [elastic/observability-robots#3732](https://github.com/elastic/observability-robots/issues/3732)

This document defines the structure and format of the OBLT AW Control Plane Dashboard issue. The format enables reliable parsing when users edit checkboxes to opt in or opt out of agentic workflows.

---

## Overview

The Control Plane Dashboard is a single GitHub Issue per repository that lists all available agentic workflows. Users can enable or disable each workflow by checking or unchecking task list items. When the client workflow runs, the ingress (`get-enabled-workflows`) looks for an open issue labeled `oblt-aw/dashboard` and sets gating from `effective-raw` and normalized `enabled-workflows`: **no such issue** → `effective-raw` is empty (ingress enables **all** workflows by default); **dashboard exists** → normalized outputs are a JSON array string—`[]` if **no** checkboxes are checked (no agentic workflows run), or `["id", ...]` for only the checked workflows. There is no config file (no `.github/oblt-aw-config.json`), no PRs when users toggle checkboxes, and no `issues.edited` trigger—the dashboard is read at runtime each time the client runs.

---

## Markdown Structure

The dashboard issue body MUST follow this structure:

1. **Intro** — Short description of the dashboard and how to use it
2. **Workflow table** — Summary table with columns: Workflow | Maturity | Description
3. **Enable/Disable list** — Task list with interactive checkboxes (`- [ ]` / `- [x]`)
4. **Instructions for users** — How to enable/disable workflows and what happens when they do

### Example Structure

```markdown
## Control Plane Dashboard

Use this dashboard to enable or disable agentic workflows for this repository. Click the checkboxes below to toggle workflows on or off.

### Workflows

| Workflow | Maturity | Description |
|----------|----------|-------------|
| dependency-review | 🟢 stable | Reviews dependency changes in PRs |
| agent-suggestions | 🟡 early-adoption | Suggests agent actions |
| some-workflow | 🟠 experimental | In development; behavior may change |

### Enable / Disable

Click a checkbox to enable or disable a workflow:

- [x] <!-- oblt-aw:dependency-review --> dependency-review
- [ ] <!-- oblt-aw:agent-suggestions --> agent-suggestions
- [ ] <!-- oblt-aw:some-workflow --> some-workflow

### Instructions

- **Enable a workflow:** Check the checkbox next to the workflow.
- **Disable a workflow:** Uncheck the checkbox.
- Changes are applied at runtime when the client runs; `get-enabled-workflows` reads this issue and supplies `enabled-workflows` to the ingress.
```

---

## Checkbox Format

### Parseable Pattern

Use GitHub task list syntax in a **list** (not in a table). Task lists in list context render as **interactive checkboxes** that users can click to toggle:

```
- [ ] <!-- oblt-aw:workflow-id --> workflow-name
```

or, when enabled:

```
- [x] <!-- oblt-aw:workflow-id --> workflow-name
```

Where `workflow-id` is the canonical identifier from [workflow-registry.json](../../config/workflow-registry.json) (e.g., `dependency-review`, `agent-suggestions`).

**Important:** Task list syntax does NOT render as checkboxes inside table cells (GitHub limitation). The checkboxes MUST be in a list section.

### Rules

| Rule | Requirement |
|------|-------------|
| **Checkbox syntax** | `- [ ]` (unchecked) or `- [x]` (checked) — task list in list context |
| **Line position** | MUST be at the **start of a line** (parsers use `^` anchor to avoid false positives in prose/code blocks) |
| **HTML comment** | MUST appear on the **same line** as the checkbox, immediately after it |
| **Comment format** | `<!-- oblt-aw:workflow-id -->` — no spaces around the colon |
| **workflow-id** | Lowercase, hyphen-separated; must match an entry in [workflow-registry.json](../../config/workflow-registry.json) |

### Why This Format

- **Interactive:** Task lists in list context render as clickable checkboxes in GitHub Issues.
- **Reliable parsing:** The HTML comment is invisible in the rendered issue but preserved when users check/uncheck. Parsers extract workflow IDs from the preceding checkbox state on the same line.
- **User edits:** When users click a checkbox, GitHub updates `[ ]` to `[x]` or vice versa. The comment stays intact.

### Initial Checkbox State for New Workflow IDs

When dashboard sync introduces a workflow ID that does not already exist in the dashboard issue body, initial checkbox state comes from that entry's `default_enabled` value in [workflow-registry.json](../../config/workflow-registry.json):

- `default_enabled: true` → rendered as `- [x]`
- `default_enabled: false` → rendered as `- [ ]`

If a workflow checkbox already exists in the issue body, the current issue state is preserved on sync updates.

### Parsing Algorithm

To extract enabled workflows from the issue body (when a dashboard issue exists):

1. Split the body into lines.
2. For each line matching `^- [x] <!-- oblt-aw:([a-z0-9-]+) -->` (enabled; `^` anchors to line start):
   - Capture the workflow ID and add it to the enabled list.
3. Emit a compact JSON array string of those IDs: `[]` if the list is empty, otherwise `["id1", "id2", ...]`. That string is what `get-enabled-workflows` writes to the `enabled-workflows` output when the dashboard issue exists.

**No open dashboard issue:** The job outputs `[]` for the normalized `enabled-workflows` output (same as an empty selection). The ingress uses `effective-raw` (empty string when no dashboard) to treat that as “all workflows enabled.”

### Example Lines

| Line | Parsed as |
|------|-----------|
| `- [x] <!-- oblt-aw:dependency-review --> dependency-review` | `dependency-review` enabled |
| `- [ ] <!-- oblt-aw:agent-suggestions --> agent-suggestions` | `agent-suggestions` disabled |

---

## Workflow Table Columns

| Column | Description |
|--------|-------------|
| **Workflow** | Human-readable name or ID of the workflow |
| **Maturity** | `stable`, `early-adoption`, or `experimental` (from [workflow-registry.json](../../config/workflow-registry.json)) |
| **Description** | Short description from [workflow-registry.json](../../config/workflow-registry.json) |

The **Enable/Disable** section below the table contains a list with task list checkboxes (`- [ ]` / `- [x]`) and `<!-- oblt-aw:workflow-id -->` on each line.

---

## Instructions for Users

The dashboard MUST include clear instructions. Recommended text:

- **Enable a workflow:** Check the checkbox next to the workflow. `get-enabled-workflows` will include it in `enabled-workflows` at runtime.
- **Disable a workflow:** Uncheck the checkbox. `get-enabled-workflows` will exclude it from `enabled-workflows` at runtime.
- **When changes apply:** The dashboard is read at runtime when the client runs. No config file; no PRs on checkbox edits.
- **Default behavior:** No dashboard → all workflows activated; dashboard exists with all unchecked → all workflows deactivated; dashboard exists with some checked → only checked workflows executed.

---

## Reference

- **Renovate Dependency Dashboard:** [docs.renovatebot.com/key-concepts/dashboard](https://docs.renovatebot.com/key-concepts/dashboard/) — single issue per repo, dynamic Markdown checkboxes
- **Implementation plan:** [Issue #3732 comment](https://github.com/elastic/observability-robots/issues/3732#issuecomment-4054356635)
