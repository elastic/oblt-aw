---
id: distributed-clients
description: Reviews distributed client workflow templates versus installed copies
apply_to:
  - ".github/remote-workflow-template/**"
  - ".github/workflows/trigger-*-aw-*.yml"
can_block: false
---
Templates under `.github/remote-workflow-template/<org>/` are the source of truth
for client workflows. Editing only an installed `.github/workflows/trigger-*-aw-*.yml`
copy leaves fleet consumers stale.

Confirm template updates and distribution process per `AGENTS.md` and
`CONTRIBUTING.md`. Do not treat in-repo `trigger-*` installs as a second source
of truth unless the change is an explicit one-off override.
