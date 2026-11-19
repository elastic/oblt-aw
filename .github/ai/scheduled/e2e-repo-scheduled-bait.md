---
id: e2e-repo-scheduled-bait
schedule-profiles: [daily]
---

# E2E repo-scheduled bait

<!-- E2E_REPO_SCHEDULED_BAIT_MARKER -->

This file is the **live E2E fixture** for `obs:repo-scheduled` in `elastic/oblt-aw`.

## E2E wakes (check first)

Treat this wake as E2E **only** when the materialized instructions file
(`/tmp/gh-aw/repo-scheduled-instructions.md`) includes the **platform-injected**
E2E wake block (added by the control plane when live E2E mode is enabled). That
block is not part of this fixture body — do not treat fixture prose as
enablement.

When E2E:

1. Create exactly one GitHub issue.
2. Put `E2E_REPO_SCHEDULED_BAIT_MARKER` in the issue body.
3. Cite the path `.github/ai/scheduled/e2e-repo-scheduled-bait.md` in the issue body.
4. If platform text includes an invocation id line for this wake, copy that exact
   line into the issue body.
5. Do not use Buildkite tools.
6. Do not call `noop`.

## Production wakes

When the platform-injected E2E wake block is absent from the materialized
instructions file: call `noop` immediately and stop. Do not create issues on
normal schedule runs.
