# E2E harness: `obs:automerge:all-files`

Production end-to-end harness for the catch-all Automerge collection and consumer
`apm.yml` custom trigger labels ([#2485](https://github.com/elastic/oblt-aw/issues/2485)).
Mirrors the stacked-policy / fail-closed patterns used by other live harnesses
([automerge-vm-images-e2e](automerge-vm-images-e2e.md),
[dependency-review-e2e](dependency-review-e2e.md)).

## What this harness covers

Live E2E only against **`elastic/oblt-aw`**:

1. Create a temporary **base** branch from the E2E checkout SHA (the ref under
   test, not necessarily `main`) and seed `apm.yml` with
   `workflows.automerge.policy.trigger-labels` including
   `e2e:automerge-all-files-ready`.
2. Create a **head** branch from that base, add a marker file under
   `e2e-fixtures/automerge-all-files/` (matches only the `all-files` collection),
   and open a ready same-repo PR **into the temporary base**.
3. Author the fixture as **`elastic-vault-github-plugin-prod[bot]`** via OIDC
   [`create-token`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token)
   using `workflow-token-policy` from
   [`config/e2e.json`](https://github.com/elastic/oblt-aw/blob/main/config/e2e.json)
   (or [`config/release.json`](https://github.com/elastic/oblt-aw/blob/main/config/release.json)
   under promote).
4. Happy path: apply the custom trigger label (not `oblt-aw/ai/merge-ready`), wait
   for `trigger-obs-aw-pull-request.yml` → automerge merge leaf → approving review
   → merge into the temporary base.
5. Negative path: never apply the custom label; assert no approve/merge; close the
   PR.
6. Delete stacked head and base branches and record absence evidence for the
   oracle.

Custom authors and fork `author-association` stay under unit tests; this harness
does not invent a non-bot PR author.

## Live cases

| Case id | Expectation |
|---------|-------------|
| `all-files-custom-label-live` | Custom trigger label present → approve → merge into stacked base; merge-ready absent |
| `all-files-custom-label-absent-live` | Custom trigger label absent → no approve/merge; fixture cleaned up |

## Prerequisites (live)

1. **Control Plane dashboard** — on the Control Plane dashboard for `elastic/oblt-aw`, enable:
   - `obs:automerge`
   - `obs:automerge:all-files` (opt-in; harness fails closed if missing)
2. **Token policy** — same E2E / promote Vault policies as
   [automerge-vm-images-e2e](automerge-vm-images-e2e.md#prerequisites-live).
3. **Vault bypassers** — classic BP / ruleset bypass for the Vault app when needed
   for merge (temporary base branches usually have no protection).

CI for fixture PRs is skipped when `ci.yml` sees an `e2e:*` label on an `e2e/*`
head ref. Agentic pull-request routes are **not** skipped.

**Fixture PR must stay ready (non-draft):** `validateAutomergePr` excludes drafts.

## How to run

### GitHub Actions (preferred)

```bash
gh workflow run e2e-automerge-all-files.yml
```

To run every leaf E2E (this one plus others): `gh workflow run e2e-all.yml`.

To exercise a feature branch before it is on `main`, pass that ref as
`checkout-ref` (fixture branches are created from `GITHUB_SHA`).

Triggers: `workflow_dispatch` (manual) and `workflow_call` (from `e2e-all.yml`).
Per-case concurrency groups `e2e-automerge-all-files-<case_id>`.

### Harness/oracle unit coverage (no live agent)

```bash
pytest tests/e2e/test_automerge_all_files_e2e.py -v
```

## Artifacts

Each matrix case uploads `e2e-automerge-all-files-<case_id>-<run_id>` with
`outcome.json`, `oracle-report.json`, and `summary.json`.

## Related

- Config: [`config/obs/e2e-automerge-all-files.json`](https://github.com/elastic/oblt-aw/blob/main/config/obs/e2e-automerge-all-files.json)
- Harness/oracle: [`scripts/obs/e2e/`](https://github.com/elastic/oblt-aw/tree/main/scripts/obs/e2e)
- Policy template: [`testdata/agentic/automerge-all-files/policy-apm.yml`](https://github.com/elastic/oblt-aw/blob/main/testdata/agentic/automerge-all-files/policy-apm.yml)
- Consumer policy docs: [Automerge services](../user-guide/automerge-services.md#consumer-policy-apmyml)
- Routing: [automerge-routing](../routing/automerge-routing.md)
