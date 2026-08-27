**Implementation Workflow (sequential and methodical):**
1. Read the resolution plan from the issue and extract ordered tasks.
2. Execute the plan strictly step by step, without skipping steps.
3. For each step, document what changed and why in commit messages and PR description.
4. **Least-privilege (MANDATORY):** Grant only the minimum permissions required. Never add broad scopes (e.g., avoid `contents: write` when `contents: read` suffices). Prefer job-level permissions over workflow-root permissions.
5. **Env-indirection (MANDATORY):** Never interpolate secrets or tokens directly in command strings. Always pass them via `env:` blocks (e.g. env: TOKEN: <secret-ref>; run: ./script.sh). Never interpolate secrets in run: command strings.
6. Run validation/tests described in the plan and confirm the vulnerability is remediated.
