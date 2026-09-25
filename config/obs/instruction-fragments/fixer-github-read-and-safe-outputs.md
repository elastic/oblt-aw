**GitHub reads and safe outputs (mandatory for fixers):**
- Workflow job `if:` conditions already enforced route preconditions (labels and/or `/ai implement`). Do **not** stop solely to re-verify those preconditions with shell `gh`.
- Shell `gh` is **not** authenticated in the agent sandbox. That does **not** mean GitHub is unreachable.
- **Start by reading the triggering issue** (body, labels, and comments — including the triage resolution plan) with the read-only **GitHub MCP** or the `github` CLI on `PATH`. Do not use shell `gh` for those reads.
- Before finishing you **MUST** call at least one safe-output tool: `create_pull_request`, `noop`, `report_incomplete`, `missing_tool`, or `missing_data`. A text-only exit with zero safe outputs is a failure.
