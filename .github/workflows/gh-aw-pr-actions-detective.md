---
inlined-imports: true
description: "Analyze failed PR checks and report findings"
imports:
  - gh-aw-fragments/elastic-tools.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/mcp-pagination.md
  - gh-aw-fragments/messages-footer.md
  - gh-aw-fragments/network-ecosystems.md
  - gh-aw-fragments/obs-defaults.md
  - gh-aw-fragments/rigor.md
  - gh-aw-fragments/runtime-setup.md
  - gh-aw-fragments/safe-output-add-comment-pr-hide-older.md
engine:
  id: copilot
on:
  stale-check: false
  workflow_call:
    inputs:
      additional-instructions:
        description: "Repo-specific instructions appended to the agent prompt"
        type: string
        required: false
        default: ""
      setup-commands:
        description: "Shell commands to run before the agent starts (dependency install, build, etc.)"
        type: string
        required: false
        default: ""
  roles: [admin, maintainer, write]
  bots:
    # Vault app authors live E2E fixture commits (GITHUB_TOKEN cannot fire pull_request).
    - "elastic-vault-github-plugin-prod[bot]"
    - "github-actions[bot]"
concurrency:
  group: ${{ github.workflow }}-pr-actions-detective-${{ github.event.workflow_run.id }}
  cancel-in-progress: false
permissions:
  copilot-requests: write
  actions: read
  contents: read
  issues: read
  pull-requests: read
tools:
  github:
    toolsets: [repos, issues, pull_requests, search, actions]
  bash: true
  web-fetch:
safe-outputs:
  activation-comments: false
  # Also listed in obs-defaults; report-failed-jobs still does not merge from imports.
  report-failed-jobs: false
strict: false
timeout-minutes: 60
steps:
  - name: Repo-specific setup
    if: ${{ inputs.setup-commands != '' }}
    env:
      SETUP_COMMANDS: ${{ inputs.setup-commands }}
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    run: eval "$SETUP_COMMANDS"
---

# PR Actions Detective

Assist with failed GitHub Actions checks for pull requests in ${{ github.repository }}. Analyze workflow run logs, explain failures, and recommend fixes. This workflow is read-only.

## Context

- **Repository**: ${{ github.repository }}
- **Workflow Run URL**: ${{ github.event.workflow_run.html_url }}
- **Conclusion**: ${{ github.event.workflow_run.conclusion }}

## Constraints

- **CAN**: Read files, search code, run tests and commands, comment on PRs
- **CANNOT**: Push changes, merge PRs, or modify `.github/workflows/`

## Instructions

### Step 1: Gather Context

1. Identify the PRs associated with the workflow run using `github.event.workflow_run.pull_requests`. If there are none, call `noop` with message "No pull request associated with workflow run; nothing to do" and stop.
2. For each PR, call `pull_request_read` with method `get` to capture the author, branches, and fork status.
3. Fetch workflow run details and logs with `bash` + `gh api`:
   - List jobs and their conclusions:
   ```bash
     gh api repos/${{ github.repository }}/actions/runs/{run_id}/jobs \
       --jq '.jobs[] | {id: .id, name: .name, conclusion: .conclusion, html_url: .html_url}'
    ```
   - If none of the jobs have a `failure` conclusion, call `noop` with message "No failed jobs in workflow run; nothing to report" and stop.
   - Download logs to `/tmp/gh-aw/agent/` and inspect the failing step output:
    ```bash
     gh api repos/${{ github.repository }}/actions/runs/{run_id}/logs \
       -H "Accept: application/vnd.github+json" \
       > /tmp/gh-aw/agent/workflow-logs-{run_id}.zip
     unzip -o /tmp/gh-aw/agent/workflow-logs-{run_id}.zip -d /tmp/gh-aw/agent/workflow-logs-{run_id}/
    ```

### Step 2: Analyze

- Identify the failing job/step and summarize the root cause.
- Propose a concrete, minimal fix or remediation plan.
- If the logs are inconclusive, state what additional data is needed.
- Before posting, check the most recent prior `PR Actions Detective` comment on the same PR (if any) and compare:
  - failing workflow/job/step,
  - root cause summary, and
  - recommended remediation.
- If both the diagnosed issue and remediation are materially the same as the last detective report, call `noop` with a short "no meaningful change since last report" reason instead of posting another comment.

### Step 3: Respond

This workflow runs on GitHub **`workflow_run`** events. Call `add_comment` with:

- **`item_number`**: the open PR number from `github.event.workflow_run.pull_requests` (required; `target: "*"` cannot auto-target a workflow_run event).
- **`body`**: the structured comment below.
- Do **not** set the tool `target` argument to `pull_request` (invalid). Omit `target`, or use `status` only when intentionally updating the activation-status comment.
- Do **not** call `noop` after a failed `add_comment`. If commenting fails after a real investigation, call `report_incomplete` with the error.

Comment body structure:

```markdown
### TL;DR
[short actionable summary]

## Remediation
- [specific fix step]
- [specific validation step]

<details>
<summary>Investigation details</summary>

## Root Cause
[concise explanation]

## Evidence
- Workflow: [link to workflow run URL]
- Job/step: [name]
- Key log excerpt: [snippet]

## Validation
- [tests/commands run or "not run" with reason]

## Follow-up
- [optional next steps]

</details>
```

${{ inputs.additional-instructions }}
