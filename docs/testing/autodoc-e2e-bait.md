# Autodoc E2E bait fixture

Intentional undocumented public API used by the live `obs:autodoc` E2E harness.

## Fixture

| Item | Value |
|------|--------|
| Path | [`scripts/e2e_autodoc_intentional_undocumented.py`](../../scripts/e2e_autodoc_intentional_undocumented.py) |
| Marker | `E2E_AUTODOC_BAIT_MARKER` |
| Purpose | Give docs-patrol a concrete undocumented public entrypoint without mutating the default branch at runtime |

## Production vs E2E

- **Normal schedule / manual runs** — docs-patrol **skips** this path (checked-in E2E fixture, not a production docs gap).
- **Live E2E** — `e2e-autodoc.yml` dispatches `trigger-obs-aw-schedule.yml` with `e2e-additional-instructions` that force evaluation of this path and require the per-run `E2E_AUTODOC_RUN_TOKEN=…` string in the audit issue body.

Do **not** document the bait entrypoint in product docs; that would remove the gap the E2E asserts.

## Related

- Harness docs: [autodoc-e2e](autodoc-e2e.md)
- Config: [`config/obs/e2e-autodoc.json`](../../config/obs/e2e-autodoc.json)
