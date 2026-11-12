---
id: e2e-repo-scheduled-bait
schedule-profiles: [daily]
---

# E2E repo-scheduled bait

<!-- E2E_REPO_SCHEDULED_BAIT_MARKER -->

This file is the **live E2E fixture** for `obs:repo-scheduled` in `elastic/oblt-aw`.

## Production wakes

If platform additional instructions do **not** contain `E2E_REPO_SCHEDULED_MODE=true`, call `noop` immediately and stop. Do not create issues on normal schedule runs.

## E2E wakes

When `E2E_REPO_SCHEDULED_MODE=true` is present:

1. Create exactly one GitHub issue.
2. Put `E2E_REPO_SCHEDULED_BAIT_MARKER` in the issue body.
3. Cite the path `.github/ai/scheduled/e2e-repo-scheduled-bait.md` in the issue body.
4. If platform text includes `E2E_INVOCATION_ID=<token>`, copy that exact `E2E_INVOCATION_ID=<token>` line into the issue body.
5. Do not use Buildkite tools.
6. Do not call `noop`.
