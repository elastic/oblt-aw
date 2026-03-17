# Control Plane Dashboard Issue Format

**Related issue:** https://github.com/elastic/observability-robots/issues/3732

This document defines the structure and format of the OBLT AW Control Plane Dashboard issue. The format enables reliable parsing when users edit checkboxes to opt in or opt out of agentic workflows.

---

## Overview

The Control Plane Dashboard is a single GitHub Issue per repository that lists all available agentic workflows. Users can enable or disable each workflow by checking or unchecking task list items. When the client workflow runs, a `check-dashboard` job fetches the dashboard issue (labeled `oblt-aw/dashboard`), parses the checkbox state, and outputs `enabled_workflows` as a JSON array. That output is passed to the ingress, which conditionally runs only workflows whose IDs appear in `enabled_workflows`. There is no config file (no `.github/oblt-aw-config.json`), no PRs when users toggle checkboxes, and no `issues.edited` trigger—the dashboard is read at runtime each time the client runs. If no dashboard exists or no checkboxes are checked, all workflows are enabled by default.

---

## Markdown Structure

The dashboard issue body MUST follow this structure:

1. **Intro** — Short description of the dashboard and how to use it
2. **Workflow table** — Summary table with columns: Workflow | Maturity | Opt-in | Description
3. **Instructions for users** — How to enable/disable workflows and what happens when they do

### Example Structure

```markdown
## Control Plane Dashboard

Use this dashboard to enable or disable agentic workflows for this repository. Check a workflow to enable it; uncheck to disable.

### Workflows

| Workflow | Maturity | Opt-in | Description |
|----------|----------|--------|-------------|
| dependency-review | stable | - [x] <!-- oblt-aw:dependency-review --> | Reviews dependency changes in PRs |
| agent-suggestions | early-adoption | - [ ] <!-- oblt-aw:agent-suggestions --> | Suggests agent actions |

### Instructions

- **Enable a workflow:** Check the checkbox next to the workflow.
- **Disable a workflow:** Uncheck the checkbox.
- Changes take effect on the next client run (dashboard is read at runtime).
```

---

## Checkbox Format

### Parseable Pattern

Each opt-in checkbox MUST use this format on a single line:

```
- [ ] <!-- oblt-aw:workflow-id -->
```

or, when enabled:

```
- [x] <!-- oblt-aw:workflow-id -->
```

Where `workflow-id` is the canonical identifier from `workflow-registry.json` (e.g., `dependency-review`, `agent-suggestions`).

### Rules

| Rule | Requirement |
|------|-------------|
| **Checkbox syntax** | GitHub task list: `- [ ]` (unchecked) or `- [x]` (checked) |
| **HTML comment** | MUST appear on the **same line** as the checkbox, immediately after it |
| **Comment format** | `<!-- oblt-aw:workflow-id -->` — no spaces around the colon |
| **workflow-id** | Lowercase, hyphen-separated; must match an entry in `workflow-registry.json` |

### Why This Format

- **Reliable parsing:** The HTML comment is invisible in the rendered issue but preserved when users check/uncheck. Parsers can use the regex `<!-- oblt-aw:([a-z0-9-]+) -->` to extract workflow IDs and associate them with the preceding checkbox state on the same line.
- **User edits:** When users toggle checkboxes, GitHub only changes `[ ]` to `[x]` or vice versa. The comment stays intact, so the workflow ID remains associated with the correct checkbox.

### Parsing Algorithm

To extract enabled workflows from the issue body:

1. Split the body into lines.
2. For each line matching `^- \[([ x])\] <!-- oblt-aw:([a-z0-9-]+) -->`:
   - Capture group 1: checkbox state (` ` = unchecked, `x` = checked)
   - Capture group 2: workflow ID
3. If state is `x`, add the workflow ID to `enabled_workflows`.
4. Output `{"enabled_workflows": ["id1", "id2", ...]}`.

### Example Lines

| Line | Parsed as |
|------|-----------|
| `- [x] <!-- oblt-aw:dependency-review -->` | `dependency-review` enabled |
| `- [ ] <!-- oblt-aw:agent-suggestions -->` | `agent-suggestions` disabled |
| `- [x] <!-- oblt-aw:resource-not-accessible-by-integration-detector -->` | `resource-not-accessible-by-integration-detector` enabled |

---

## Workflow Table Columns

| Column | Description |
|--------|-------------|
| **Workflow** | Human-readable name or ID of the workflow |
| **Maturity** | `stable`, `early-adoption`, or `experimental` (from `workflow-registry.json`) |
| **Opt-in** | Checkbox with `<!-- oblt-aw:workflow-id -->` on the same line |
| **Description** | Short description from `workflow-registry.json` |

---

## Instructions for Users

The dashboard MUST include clear instructions. Recommended text:

- **Enable a workflow:** Check the checkbox next to the workflow. The next time the client runs, the `check-dashboard` job will include it in `enabled_workflows`.
- **Disable a workflow:** Uncheck the checkbox. The next run will exclude it from `enabled_workflows`.
- **When changes apply:** Changes take effect on the next client run. The dashboard is read at runtime; there is no config file and no PRs when you toggle checkboxes.
- **Default behavior:** If no dashboard exists or no checkboxes are checked, all workflows are enabled.

---

## Reference

- **Implementation plan:** `docs/plans/issue-3732-control-plane-dashboard.md`
