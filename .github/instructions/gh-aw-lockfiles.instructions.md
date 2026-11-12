---
applyTo: ".github/workflows/gh-aw-*.md, .github/workflows/gh-aw-fragments/**/*.md, .github/workflows/compiler-upgrade.md, .github/workflows/obs-aw-compiler-upgrade.md"
---

# gh-aw lock files

In-repo agentic workflows are authored as Markdown under `.github/workflows/` and compiled to matching `*.lock.yml` files. Do **not** hand-edit generated locks.

When you change any matching source (including Autofix / suggested patches):

1. Run `make compile-aw` (or `make compile-aw-check`) from the repository root.
2. Include every regenerated `.lock.yml` in the **same** commit as the Markdown change.
3. Never land a Markdown-only commit that leaves lock files stale — CI and pre-commit will fail or rewrite them.

`gh-aw-fragments/**` imports affect many locks; regenerate after fragment edits too.
