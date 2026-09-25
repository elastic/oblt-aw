# Autodoc E2E bait fixture

Intentional incomplete documentation page used by the live `obs:autodoc` E2E harness.

## Fixture

| Item | Value |
|------|--------|
| Path | [`docs/testing/fixtures/e2e-autodoc-bait.md`](fixtures/e2e-autodoc-bait.md) |
| Marker | `E2E_AUTODOC_BAIT_MARKER` |
| Purpose | Give docs-patrol a concrete incomplete doc page without mutating the default branch at runtime |

## Production vs E2E

- **Normal schedule / manual runs** — docs-patrol **skips** this path (checked-in E2E fixture, not a production docs gap).
- **Live E2E** — `e2e-autodoc.yml` dispatches control-plane-only `e2e-trigger-obs-aw-schedule.yml` with `e2e-autodoc-mode=true`. The wrapper injects fixed audit-only platform text (`E2E_AUTODOC_MODE=true`) so docs-patrol evaluates **only** this file and files an issue that cites the path plus `E2E_AUTODOC_BAIT_MARKER`. Client `trigger-obs-aw-schedule.yml` is unchanged.

Do **not** complete this page in product docs on `main`; that would remove the gap the E2E asserts. Fix PRs from live E2E are closed without merge.

## Related

- Harness docs: [autodoc-e2e](autodoc-e2e.md)
- Config: [`config/obs/e2e-autodoc.json`](../../config/obs/e2e-autodoc.json)
