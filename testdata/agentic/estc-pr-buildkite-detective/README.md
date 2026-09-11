# ESTC PR Buildkite Detective — test cases

Fixtures and live case definitions for `obs:estc-pr-buildkite-detective`.

## Layout

```text
testdata/agentic/estc-pr-buildkite-detective/
  cases/<case-id>/
    case.json                 # expectations (structured only)
    status-event.json         # fixture mode only
    open-prs.json             # fixture mode only
    buildkite-build.json      # fixture mode only
    job-log.txt               # fixture mode only
```

## Cases

| Case id | Mode | Purpose |
|---------|------|---------|
| `status-failure-open-pr` | fixture (integration) | Recorded status failure + open PR + failed script job |
| `status-failure-open-pr-live` | live (E2E) | Production status→agent→PR comment |
| `status-success-skipped` | live (E2E) | Success status must not run detective |
| `status-failure-non-buildkite` | live (E2E) | Non-Buildkite failure must not run detective |
| `status-failure-no-open-pr` | live (E2E) | Failed Buildkite status without open PR stops before agent |

## Notes

- Fixture payloads are **synthetic** so CI unit tests stay deterministic and free of paid agent calls.
- Live cases drive the real `trigger-obs-aw-status.yml` path on `elastic/oblt-aw`.
- Resolve→wrapper integration suite remains [#1910](https://github.com/elastic/oblt-aw/issues/1910).
- See [docs/testing/estc-pr-buildkite-detective-e2e.md](../../../docs/testing/estc-pr-buildkite-detective-e2e.md).
