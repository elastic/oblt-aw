**GitHub reads and safe outputs (mandatory for dependency-review):**
- The pull request head is already checked out in `GITHUB_WORKSPACE`. Start by reading the local PR diff (e.g. `git --no-pager log --name-status --oneline -n 50` to see changed files, and `git --no-pager diff --name-only HEAD~1..HEAD` for single-commit PRs) to identify dependency updates. Do **not** stop solely because shell `gh` cannot reach GitHub.
- Shell `gh` is **not** authenticated in the agent sandbox. That does **not** mean GitHub is unreachable.
- When you need GitHub API data (PR metadata, release notes, commit verification), use the read-only **GitHub MCP**. Do not use shell `gh` for those reads.
- Before finishing you **MUST** call at least one safe-output tool: `add_comment`, `add_labels`, `noop`, `report_incomplete`, `missing_tool`, or `missing_data`. A text-only exit with zero safe outputs is a failure.
- Use `noop` only when the PR truly has no dependency updates to review. If you cannot gather enough context to analyze a real dependency update, call `report_incomplete` (or `missing_tool` / `missing_data`) — do not claim noop in prose and do not exit without a tool call.
