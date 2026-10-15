---
applyTo: ".github/workflows/**, config/**"
---

# Workflow routing and control-plane review

When event clients, routes, or `config/<org>/` change, trace the org-scoped event-to-route and allow-list flow; mismatches can silently skip an intended agent or run it for the wrong organization. Use the route naming and prelude contract in `AGENTS.md` and `.github/skills/code-review/SKILL.md` as the detailed checklist.
