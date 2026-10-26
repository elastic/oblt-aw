---
id: workflow-routing
description: Reviews workflow routing, prelude contracts, and org config allow-lists
apply_to:
  - ".github/workflows/**"
  - "config/**"
can_block: false
---
When event clients, routes, or `config/<org>/` change, trace the org-scoped
event-to-route and allow-list flow. A mismatch can skip an agent or run it for
the wrong organization.

Check the route naming and prelude contract in `AGENTS.md` and
`.github/skills/code-review/SKILL.md`. Treat
`.github/workflows/aw-prelude.yml` and
`scripts/validate_aw_workflow_prelude.py` as the shared prelude contract.
