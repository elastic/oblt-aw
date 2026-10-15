---
applyTo: ".github/remote-workflow-template/**, .github/workflows/trigger-*-aw-*.yml"
---

# Distributed client workflows

The distributed templates under `.github/remote-workflow-template/<org>/` are the source of truth for client workflows. When a client changes, verify its template is updated; changing only an installed copy leaves fleet consumers stale. Follow `AGENTS.md` and `CONTRIBUTING.md` for the distribution process.
