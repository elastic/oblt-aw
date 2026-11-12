---
inlined-imports: true
description: "Run consumer-defined scheduled automations from instruction files"
imports:
  - gh-aw-fragments/elastic-tools.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/messages-footer.md
  - gh-aw-fragments/obs-defaults.md
  - gh-aw-fragments/rigor.md
  - gh-aw-fragments/runtime-setup.md
  - gh-aw-fragments/safe-output-create-issue.md
engine:
  id: copilot
  # Required on gh-aw >= v0.91.x: BYOK Copilot disables native web-fetch unless SDK mode is on.
  copilot-sdk: true
on:
  stale-check: false
  workflow_call:
    inputs:
      additional-instructions:
        description: "Platform + optional APM resolved instructions for this automation"
        type: string
        required: false
        default: ""
      automation-id:
        description: "Consumer automation id from the instruction file frontmatter or filename"
        type: string
        required: false
        default: ""
      instruction-path:
        description: "Repo-relative path to the consumer instruction Markdown file"
        type: string
        required: true
    secrets:
      BUILDKITE_API_TOKEN:
        required: false
        description: >-
          Optional Buildkite API token for the buildkite-logs capability
          (consumer secret BUILDKITE_LOGS_API_TOKEN mapped by schedule clients).
  roles: [admin, maintainer, write]
  bots:
    - "github-actions[bot]"
concurrency:
  group: ${{ github.workflow }}-repo-scheduled-${{ inputs.automation-id || github.run_id }}
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
# Buildkite MCP is compiled into this generic AW for the buildkite-logs capability.
# Schedule clients forward BUILDKITE_LOGS_API_TOKEN as optional BUILDKITE_API_TOKEN.
# Automations that do not request buildkite-logs must not call these tools.
mcp-servers:
  buildkite:
    type: http
    url: "https://mcp.buildkite.com/direct"
    headers:
      Authorization: "Bearer ${{ secrets.BUILDKITE_API_TOKEN }}"
    allowed:
      - user_token_organization
      - list_builds
      - get_build
      - get_build_failure_summary
      - list_jobs
      - get_job
      - read_logs
      - list_annotations
      - list_step_uploads
network:
  allowed:
    - defaults
    - "mcp.buildkite.com"
    - "buildkite.com"
    - "api.buildkite.com"
safe-outputs:
  activation-comments: false
  add-comment:
    max: 3
    target: "*"
    pull-requests: true
    issues: true
    discussions: false
  add-labels:
    max: 5
  create-issue:
    max: 3
    title-prefix: "[oblt-aw][repo-scheduled] "
    close-older-issues: false
    expires: 14d
strict: false
timeout-minutes: 60
steps:
  - name: Materialize consumer instruction body
    env:
      AUTOMATION_ID: ${{ inputs.automation-id }}
      INSTRUCTION_PATH: ${{ inputs.instruction-path }}
    run: |
      set -euo pipefail
      mkdir -p /tmp/gh-aw
      python3 - <<'PY'
      import os
      import pathlib
      import re
      import sys

      declared = pathlib.Path(os.environ["INSTRUCTION_PATH"])
      repo_root = pathlib.Path(".").resolve()
      candidate = declared if declared.is_absolute() else repo_root / declared
      if not candidate.exists():
          print(f"instruction file missing: {declared}", file=sys.stderr)
          sys.exit(1)
      resolved = candidate.resolve()
      try:
          resolved.relative_to(repo_root)
      except ValueError:
          print(
              f"instruction file escapes repository root: {declared}",
              file=sys.stderr,
          )
          sys.exit(1)
      if not resolved.is_file():
          print(f"instruction file is not a regular file: {declared}", file=sys.stderr)
          sys.exit(1)
      text = resolved.read_text(encoding="utf-8")
      match = re.match(r"\A---\s*\n.*?\n---\s*\n?(.*)\Z", text, re.DOTALL)
      body = match.group(1).strip() if match else text.strip()
      if not body:
          print(f"instruction body empty: {declared}", file=sys.stderr)
          sys.exit(1)
      source_label = (
          declared.as_posix()
          if not declared.is_absolute()
          else resolved.relative_to(repo_root).as_posix()
      )
      out = pathlib.Path("/tmp/gh-aw/repo-scheduled-instructions.md")
      out.write_text(
          f"# Automation `{os.environ.get('AUTOMATION_ID', '')}`\n\n"
          f"Source: `{source_label}`\n\n{body}\n",
          encoding="utf-8",
      )
      print(f"Wrote {out} ({out.stat().st_size} bytes)")
      PY
---

# repo-scheduled

You run one **consumer-defined** scheduled automation for this repository.

## Instructions source

1. Read `/tmp/gh-aw/repo-scheduled-instructions.md` (materialized from the consumer `instructions-file` declared in `apm.yml`). That file is the source of truth for detection, categorization, triage, and output shape.
2. Apply any extra guidance in `additional-instructions` (platform / optional APM overlays).

Automation id: `${{ inputs.automation-id }}`
Instruction path: `${{ inputs.instruction-path }}`

## Hard rules

1. Prefer `noop` when there is nothing actionable.
2. Call at least one safe-output tool before finishing (`create_issue`, `add_comment`, `noop`, `missing_tool`, `missing_data`, or `report_incomplete`). A text-only exit is a failure.
3. Use Buildkite MCP tools (`mcp__buildkite__*`) **only** when the consumer instructions require Buildkite log/build inspection and the `buildkite-logs` capability applies. If the token is missing or Buildkite tools fail and the instructions require Buildkite data, call `missing_data` or `report_incomplete` — do not invent build results.
4. Do not merge, push, close issues, approve PRs, or take other destructive actions. Allowed writes are the safe-outputs configured for this workflow.
5. Keep issue titles under the safe-output limits. Do not pass custom `expires` or issue `fields` unless the consumer instructions explicitly require labels that already exist in the repository.
