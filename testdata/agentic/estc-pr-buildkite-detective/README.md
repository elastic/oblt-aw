# ESTC PR Buildkite Detective — E2E fixtures

Recorded fixtures for the first vertical-slice E2E harness (`obs:estc-pr-buildkite-detective`).

## Layout

```text
testdata/agentic/estc-pr-buildkite-detective/
  cases/<case-id>/
    case.json              # expectations (structured only)
    status-event.json      # synthetic GitHub status failure
    open-prs.json          # synthetic commit→PR association
    buildkite-build.json   # recorded/synthetic Buildkite build payload
    job-log.txt            # recorded/synthetic failed job log tail
```

## Cases

| Case id | Purpose |
|---------|---------|
| `status-failure-open-pr` | Status failure + Buildkite context + open PR + one failed script job |

## Notes

- Payloads are **synthetic** for v1 (no live org scrape). Prefer keeping them recorded/fixture-shaped so CI stays deterministic and free of paid agent calls.
- Integration-layer resolve→wrapper fixtures for this workflow are owned by [#1910](https://github.com/elastic/oblt-aw/issues/1910); this tree is the E2E case input for [#1911](https://github.com/elastic/oblt-aw/issues/1911).
- See [docs/testing/estc-pr-buildkite-detective-e2e.md](../../../docs/testing/estc-pr-buildkite-detective-e2e.md).
