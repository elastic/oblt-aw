# Autodoc routing

This folder documents routing and operational notes for the documentation improvement capability.

## Entrypoint route

`oblt-aw-ingress.yml` dispatches to `gh-aw-autodoc.yml` when:

- event is `workflow_dispatch`
- input `capability` equals `autodoc`

If `capability` is empty or unsupported on `workflow_dispatch`, ingress falls back to the detector workflow.

## Routed workflow

- `workflow_dispatch` + `capability=autodoc` -> `gh-aw-autodoc.yml`

## Notes

- `gh-aw-autodoc.yml` wraps the upstream reusable workflow `.github/workflows/gh-aw-docs-patrol.lock.yml` from `elastic/ai-github-actions`.
- It is intended to analyze repository documentation and open a focused documentation PR.
- It must not merge PRs automatically.
